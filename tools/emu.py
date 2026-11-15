"""Mini-emulador de SNES para testes automatizados do protótipo.

Implementa a CPU 65816 (só os opcodes que o montador gera), DMA, controle,
VRAM/CGRAM/OAM e um renderizador do modo 1 (BG1 4bpp, BG3 2bpp, sprites).
Não é preciso em ciclos — serve para validar lógica e imagem.
"""
from PIL import Image
from asm65816 import OPS, IMPLIED, BRANCHES
from spc700 import SPC, IPL

DECODE = {}
for mn, modes in OPS.items():
    for mode, op in modes.items():
        DECODE[op] = (mn.rstrip('_'), mode)
for mn, op in IMPLIED.items():
    DECODE[op] = (mn, 'imp')
for mn, op in BRANCHES.items():
    DECODE[op] = (mn, 'rel')
DECODE[0xC2] = ('rep', 'imm8')
DECODE[0xE2] = ('sep', 'imm8')

BUTTONS = dict(B=0x8000, Y=0x4000, SELECT=0x2000, START=0x1000, UP=0x0800, DOWN=0x0400,
               LEFT=0x0200, RIGHT=0x0100, A=0x0080, X=0x0040, L=0x0020, R=0x0010)


class EmuError(Exception):
    pass


class SNES:
    def __init__(self, rom):
        self.rom = rom
        self.wram = bytearray(0x20000)
        self.vram = bytearray(0x10000)
        self.cgram = bytearray(512)
        self.oam = bytearray(544)
        self.regs = {}
        self.io = bytearray(0x10000)
        self.vaddr = 0
        self.cgaddr = 0
        self.cg_latch = None
        self.oamaddr = 0
        self.scroll_latch = 0
        self.scroll = {}
        self.joy = 0
        self.nmitimen = 0
        self.waiting = False
        self.trace = []
        self.frame = 0
        self.spc = SPC()
        self.ipl = IPL(self.spc)
        # CPU
        self.A = self.X = self.Y = 0
        self.S = 0x1FF
        self.D = 0
        self.DB = 0
        self.PB = 0
        self.P = 0x34
        self.E = 1
        self.PC = self.r16(0xFFFC)

    # ------------------------------------------------------------ memória
    def read(self, addr):
        bank, off = (addr >> 16) & 0xFF, addr & 0xFFFF
        if bank in (0x7E, 0x7F):
            return self.wram[((bank - 0x7E) << 16) | off]
        if (bank & 0x7F) < 0x40:
            if off < 0x2000:
                return self.wram[off]
            if off >= 0x8000:
                return self.rom[((bank & 0x3F) << 15 | (off - 0x8000)) % len(self.rom)]
            return self.io_read(off)
        if off >= 0x8000:
            return self.rom[(((bank & 0x7F) << 15) | (off - 0x8000)) % len(self.rom)]
        raise EmuError('leitura em endereço não mapeado %06X' % addr)

    def write(self, addr, v):
        bank, off = (addr >> 16) & 0xFF, addr & 0xFFFF
        v &= 0xFF
        if bank in (0x7E, 0x7F):
            self.wram[((bank - 0x7E) << 16) | off] = v; return
        if (bank & 0x7F) < 0x40:
            if off < 0x2000:
                self.wram[off] = v; return
            if off < 0x8000:
                self.io_write(off, v); return
        raise EmuError('escrita em ROM/endereço inválido %06X (PC=%04X)' % (addr, self.PC))

    def r16(self, addr):
        return self.read(addr) | (self.read(addr + 1) << 8)

    def io_read(self, off):
        if 0x2140 <= off <= 0x2143:
            return self.spc.out[off - 0x2140]
        if off == 0x4210:
            return 0x80
        if off == 0x4212:
            return 0
        if off == 0x4218:
            return self.joy & 0xFF
        if off == 0x4219:
            return self.joy >> 8
        return 0

    def io_write(self, off, v):
        self.io[off] = v
        if 0x2140 <= off <= 0x2143:
            self.ipl.cpu_write(off - 0x2140, v)
            return
        if off == 0x2102:
            self.oamaddr = (self.oamaddr & 0x200) | (v << 1)
        elif off == 0x2103:
            self.oamaddr = (self.oamaddr & 0x1FE) | ((v & 1) << 9)
        elif off == 0x2104:
            self.oam[self.oamaddr % 544] = v; self.oamaddr += 1
        elif 0x210D <= off <= 0x2114:
            self.scroll[off] = ((v << 8) | self.scroll_latch) & 0x3FF
            self.scroll_latch = v
        elif off == 0x2116:
            self.vaddr = (self.vaddr & 0xFF00) | v
        elif off == 0x2117:
            self.vaddr = (self.vaddr & 0x00FF) | (v << 8)
        elif off == 0x2118:
            self._check_vram_access()
            self.vram[(self.vaddr * 2) & 0xFFFF] = v
            if not self.io[0x2115] & 0x80: self.vaddr = (self.vaddr + 1) & 0x7FFF
        elif off == 0x2119:
            self._check_vram_access()
            self.vram[(self.vaddr * 2 + 1) & 0xFFFF] = v
            if self.io[0x2115] & 0x80: self.vaddr = (self.vaddr + 1) & 0x7FFF
        elif off == 0x2121:
            self.cgaddr = v; self.cg_latch = None
        elif off == 0x2122:
            if self.cg_latch is None:
                self.cg_latch = v
            else:
                self.cgram[self.cgaddr * 2] = self.cg_latch
                self.cgram[self.cgaddr * 2 + 1] = v & 0x7F
                self.cgaddr = (self.cgaddr + 1) & 0xFF; self.cg_latch = None
        elif off == 0x4200:
            self.nmitimen = v
        elif off == 0x420B:
            self.do_dma(v)

    def _check_vram_access(self):
        if not self.in_vblank and not (self.io[0x2100] & 0x80):
            raise EmuError('escrita na VRAM fora do vblank (PC=%04X)' % self.PC)

    in_vblank = False

    def do_dma(self, mask):
        for ch in range(8):
            if not mask & (1 << ch):
                continue
            b = 0x4300 + ch * 16
            mode = self.io[b] & 7
            fixed = self.io[b] & 0x08
            if self.io[b] & 0x80:
                raise EmuError('DMA B->A não suportado')
            breg = self.io[b + 1]
            src = self.io[b + 2] | (self.io[b + 3] << 8) | (self.io[b + 4] << 16)
            count = self.io[b + 5] | (self.io[b + 6] << 8) or 0x10000
            pattern = {0: [0], 1: [0, 1]}[mode]
            for i in range(count):
                self.io_write(0x2100 + breg + pattern[i % len(pattern)], self.read(src))
                if not fixed:
                    src = (src & 0xFF0000) | ((src + 1) & 0xFFFF)
            self.io[b + 5] = self.io[b + 6] = 0

    # ------------------------------------------------------------ flags
    @property
    def m8(self): return bool(self.P & 0x20) or self.E
    @property
    def x8(self): return bool(self.P & 0x10) or self.E

    def setnz(self, v, eight):
        if eight:
            v &= 0xFF; n = v & 0x80
        else:
            v &= 0xFFFF; n = v & 0x8000
        self.P = (self.P & ~0x82) | (0x80 if n else 0) | (0x02 if v == 0 else 0)
        return v

    def push(self, v):
        self.write(self.S, v)
        self.S = (self.S - 1) & 0xFFFF
        if self.E: self.S = 0x100 | (self.S & 0xFF)

    def pull(self):
        self.S = (self.S + 1) & 0xFFFF
        if self.E: self.S = 0x100 | (self.S & 0xFF)
        return self.read(self.S)

    def push16(self, v): self.push(v >> 8); self.push(v & 0xFF)
    def pull16(self): lo = self.pull(); return lo | (self.pull() << 8)

    def fetch(self):
        v = self.read((self.PB << 16) | self.PC)
        self.PC = (self.PC + 1) & 0xFFFF
        return v

    def fetch16(self): lo = self.fetch(); return lo | (self.fetch() << 8)
    def fetch24(self): lo = self.fetch16(); return lo | (self.fetch() << 16)

    # ------------------------------------------------------------ execução
    def ea(self, mode):
        if mode == 'dp': return (self.D + self.fetch()) & 0xFFFF
        if mode == 'abs': return (self.DB << 16) | self.fetch16()
        if mode == 'absx': return ((self.DB << 16) | self.fetch16()) + self.X & 0xFFFFFF
        if mode == 'absy': return ((self.DB << 16) | self.fetch16()) + self.Y & 0xFFFFFF
        if mode == 'long': return self.fetch24()
        if mode == 'longx': return (self.fetch24() + self.X) & 0xFFFFFF
        if mode == 'indy':
            p = (self.D + self.fetch()) & 0xFFFF
            return (((self.DB << 16) | self.r16(p)) + self.Y) & 0xFFFFFF
        if mode == 'indly':
            p = (self.D + self.fetch()) & 0xFFFF
            return ((self.r16(p) | (self.read(p + 2) << 16)) + self.Y) & 0xFFFFFF
        raise EmuError('modo ' + mode)

    def load(self, mode, eight):
        if mode in ('imm', 'immx'):
            return self.fetch() if eight else self.fetch16()
        a = self.ea(mode)
        return self.read(a) if eight else self.read(a) | (self.read(a + 1) << 8)

    def store(self, a, v, eight):
        self.write(a, v & 0xFF)
        if not eight: self.write(a + 1, (v >> 8) & 0xFF)

    def getA(self): return self.A & 0xFF if self.m8 else self.A
    def setA(self, v):
        if self.m8: self.A = (self.A & 0xFF00) | (v & 0xFF)
        else: self.A = v & 0xFFFF

    def step(self):
        pc0 = self.PC
        op = self.fetch()
        if op not in DECODE:
            raise EmuError('opcode desconhecido %02X em %04X' % (op, pc0))
        mn, mode = DECODE[op]
        m8, x8 = self.m8, self.x8
        P = self.P
        if mn == 'lda':
            self.setA(self.setnz(self.load(mode, m8), m8))
        elif mn in ('ldx', 'ldy'):
            v = self.setnz(self.load(mode, x8), x8)
            setattr(self, mn[2].upper(), v)
        elif mn in ('sta', 'stx', 'sty', 'stz'):
            v = {'sta': self.A, 'stx': self.X, 'sty': self.Y, 'stz': 0}[mn]
            eight = m8 if mn in ('sta', 'stz') else x8
            self.store(self.ea(mode), v, eight)
        elif mn in ('adc', 'sbc'):
            v = self.load(mode, m8)
            mask = 0xFF if m8 else 0xFFFF
            sign = 0x80 if m8 else 0x8000
            if mn == 'sbc': v ^= mask
            a = self.getA()
            r = a + v + (P & 1)
            c = r > mask
            r &= mask
            ov = (~(a ^ v) & (a ^ r) & sign) != 0
            self.P = (self.P & ~0x41) | (1 if c else 0) | (0x40 if ov else 0)
            self.setA(self.setnz(r, m8))
        elif mn in ('and', 'ora', 'eor'):
            v = self.load(mode, m8); a = self.getA()
            r = {'and': a & v, 'ora': a | v, 'eor': a ^ v}[mn]
            self.setA(self.setnz(r, m8))
        elif mn in ('cmp', 'cpx', 'cpy'):
            eight = m8 if mn == 'cmp' else x8
            v = self.load(mode, eight)
            a = {'cmp': self.getA(), 'cpx': self.X, 'cpy': self.Y}[mn]
            if eight: a &= 0xFF
            self.P = (self.P & ~1) | (1 if a >= v else 0)
            self.setnz(a - v, eight)
        elif mn == 'bit':
            v = self.load(mode, m8); a = self.getA()
            self.P = (self.P & ~2) | (2 if (a & v) == 0 else 0)
            if mode != 'imm':
                top = 0x80 if m8 else 0x8000
                self.P = (self.P & ~0xC0) | (0x80 if v & top else 0) | (0x40 if v & (top >> 1) else 0)
        elif mn in ('inc', 'dec', 'asl', 'lsr', 'rol', 'ror'):
            mask = 0xFF if m8 else 0xFFFF
            top = 0x80 if m8 else 0x8000
            if mode == 'acc':
                v = self.getA(); a = None
            else:
                a = self.ea(mode)
                v = self.read(a) if m8 else self.read(a) | (self.read(a + 1) << 8)
            c = P & 1
            if mn == 'inc': r = v + 1
            elif mn == 'dec': r = v - 1
            elif mn == 'asl': r = v << 1; c = 1 if v & top else 0
            elif mn == 'lsr': r = v >> 1; c = v & 1
            elif mn == 'rol': r = (v << 1) | c; c = 1 if v & top else 0
            else: r = (v >> 1) | (top if c else 0); c = v & 1
            self.P = (self.P & ~1) | c if mn not in ('inc', 'dec') else self.P
            r = self.setnz(r & mask, m8)
            if a is None: self.setA(r)
            else: self.store(a, r, m8)
        elif mode == 'rel':
            d = self.fetch()
            if d & 0x80: d -= 256
            cond = {'bra': True, 'beq': P & 2, 'bne': not P & 2, 'bcc': not P & 1,
                    'bcs': P & 1, 'bpl': not P & 0x80, 'bmi': P & 0x80,
                    'bvc': not P & 0x40, 'bvs': P & 0x40}[mn]
            if cond: self.PC = (self.PC + d) & 0xFFFF
        elif mn == 'jmp':
            t = self.fetch16()
            if mode == 'absxind':
                t = self.r16((self.PB << 16) | ((t + self.X) & 0xFFFF))
            self.PC = t
        elif mn == 'jsr':
            t = self.fetch16()
            self.push16((self.PC - 1) & 0xFFFF)
            if mode == 'absxind':
                t = self.r16((self.PB << 16) | ((t + self.X) & 0xFFFF))
            self.PC = t
        elif mn == 'rts':
            self.PC = (self.pull16() + 1) & 0xFFFF
        elif mn == 'rti':
            self.did_rti = True
            self.P = self.pull()
            self.PC = self.pull16()
            if not self.E: self.PB = self.pull()
            self.fix_index()
        elif mn in ('rep', 'sep'):
            v = self.fetch()
            self.P = self.P & ~v if mn == 'rep' else self.P | v
            if self.E: self.P |= 0x30
            self.fix_index()
        elif mn == 'xce':
            c = self.P & 1
            self.P = (self.P & ~1) | self.E
            self.E = c
            if self.E:
                self.P |= 0x30; self.S = 0x100 | (self.S & 0xFF)
            self.fix_index()
        elif mn in ('inx', 'iny', 'dex', 'dey'):
            r = mn[2].upper()
            v = getattr(self, r) + (1 if mn[0] == 'i' else -1)
            setattr(self, r, self.setnz(v, x8))
        elif mn in ('tax', 'tay'):
            v = self.A if not x8 else self.A & 0xFF
            setattr(self, mn[2].upper(), self.setnz(v, x8))
        elif mn in ('txa', 'tya'):
            self.setA(self.setnz(getattr(self, mn[1].upper()), m8))
        elif mn == 'txy': self.Y = self.setnz(self.X, x8)
        elif mn == 'tyx': self.X = self.setnz(self.Y, x8)
        elif mn == 'tcd': self.D = self.setnz(self.A, False)
        elif mn == 'txs': self.S = self.X if not self.E else 0x100 | (self.X & 0xFF)
        elif mn == 'tsx': self.X = self.setnz(self.S, x8)
        elif mn == 'xba':
            self.A = ((self.A >> 8) | (self.A << 8)) & 0xFFFF
            self.setnz(self.A, True)
        elif mn == 'pha':
            if m8: self.push(self.A & 0xFF)
            else: self.push16(self.A)
        elif mn == 'pla':
            self.setA(self.setnz(self.pull() if m8 else self.pull16(), m8))
        elif mn in ('phx', 'phy'):
            v = getattr(self, mn[2].upper())
            if x8: self.push(v & 0xFF)
            else: self.push16(v)
        elif mn in ('plx', 'ply'):
            setattr(self, mn[2].upper(), self.setnz(self.pull() if x8 else self.pull16(), x8))
        elif mn == 'php': self.push(self.P)
        elif mn == 'plp': self.P = self.pull(); self.fix_index()
        elif mn == 'phb': self.push(self.DB)
        elif mn == 'plb': self.DB = self.setnz(self.pull(), True)
        elif mn == 'phk': self.push(self.PB)
        elif mn == 'phd': self.push16(self.D)
        elif mn == 'pld': self.D = self.setnz(self.pull16(), False)
        elif mn == 'clc': self.P &= ~1
        elif mn == 'sec': self.P |= 1
        elif mn == 'sei': self.P |= 4
        elif mn == 'cli': self.P &= ~4
        elif mn == 'cld': self.P &= ~8
        elif mn == 'wai': self.waiting = True
        elif mn == 'nop': pass
        else:
            raise EmuError('não implementado: %s %s em %04X' % (mn, mode, pc0))

    def fix_index(self):
        if self.x8:
            self.X &= 0xFF; self.Y &= 0xFF

    def nmi(self):
        self.push(self.PB); self.push16(self.PC); self.push(self.P)
        self.P = (self.P | 4) & ~8
        self.PB = 0
        self.PC = self.r16(0xFFEA)

    def run_frame(self, joy=0, limit=200000):
        """Roda o programa principal até o WAI, depois o NMI (vblank)."""
        self.joy = joy
        n = 0
        while not self.waiting:
            self.step(); n += 1
            if n > limit:
                raise EmuError('laço sem WAI (PC=%04X)' % self.PC)
        self.in_vblank = True
        if self.nmitimen & 0x80:
            sp = self.S
            self.nmi()
            while True:
                self.did_rti = False
                self.step(); n += 1
                if self.did_rti and self.S == sp:
                    break
                if n > limit:
                    raise EmuError('NMI não retornou')
        self.in_vblank = False
        self.waiting = False
        self.frame += 1
        self.spc.run_frame()
        return n

    # ------------------------------------------------------------ vídeo
    def color(self, i):
        v = self.cgram[i * 2] | (self.cgram[i * 2 + 1] << 8)
        return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3)

    def tile_px(self, base, tile, bpp, x, y):
        words = 4 * bpp
        addr = (base + tile * words) * 2
        row = addr + y * 2
        bit = 7 - x
        v = 0
        for p in range(bpp):
            off = row + (p & 1) + (p >> 1) * 16
            if self.vram[off & 0xFFFF] & (1 << bit):
                v |= 1 << p
        return v

    def bg_pixel(self, sc_reg, nba_word, bpp, x, y, hofs, vofs):
        sc = self.io[sc_reg]
        mapbase = (sc >> 2) << 10
        bx, by = (x + hofs) & 255, (y + vofs) & 255
        e_addr = (mapbase + (by >> 3) * 32 + (bx >> 3)) * 2
        e = self.vram[e_addr] | (self.vram[e_addr + 1] << 8)
        tile = e & 0x3FF
        pal = (e >> 10) & 7
        px, py = bx & 7, by & 7
        if e & 0x4000: px = 7 - px
        if e & 0x8000: py = 7 - py
        c = self.tile_px(nba_word, tile, bpp, px, py)
        if c == 0:
            return None, e
        return pal * (1 << bpp) + c, e

    def render(self):
        img = Image.new('RGB', (256, 224))
        if self.io[0x2100] & 0x80:
            return img
        pix = img.load()
        tm = self.io[0x212C]
        nba12, nba34 = self.io[0x210B], self.io[0x210C]
        bg1base = (nba12 & 0xF) << 12
        bg3base = (nba34 & 0xF) << 12
        v1 = self.scroll.get(0x210E, 0)
        v3 = self.scroll.get(0x2112, 0)
        # sprites: pré-calcula camada
        spr = {}
        obsel = self.io[0x2101]
        obase = (obsel & 7) << 13
        small = {0: 8, 1: 8, 2: 8, 3: 16, 4: 16, 5: 32}[obsel >> 5]
        large = {0: 16, 1: 32, 2: 64, 3: 32, 4: 64, 5: 64}[obsel >> 5]
        if tm & 0x10:
            for i in range(127, -1, -1):
                x, y, t, at = self.oam[i * 4:i * 4 + 4]
                hi = (self.oam[512 + i // 4] >> ((i % 4) * 2)) & 3
                if hi & 1: x -= 256
                size = large if hi & 2 else small
                t |= (at & 1) << 8
                pal = 128 + ((at >> 1) & 7) * 16
                for sy in range(size):
                    row = (y + 1 + sy) & 255
                    sr = row - 1
                    if not 0 <= sr < 224: continue
                    for sx in range(size):
                        px = x + sx
                        if not 0 <= px < 256: continue
                        fx = size - 1 - sx if at & 0x40 else sx
                        fy = size - 1 - sy if at & 0x80 else sy
                        tt = ((t & 0xF) + (fx >> 3)) & 0xF | (((t >> 4) + (fy >> 3)) & 0xF) << 4 | (t & 0x100)
                        c = self.tile_px(obase, tt, 4, fx & 7, fy & 7)
                        if c:
                            spr[(px, sr)] = pal + c
        for y in range(224):
            for x in range(256):
                c = 0
                if tm & 1:
                    p, _ = self.bg_pixel(0x2107, bg1base, 4, x, y + 1, 0, v1)
                    if p is not None: c = p
                if (x, y) in spr:
                    c = spr[(x, y)]
                if tm & 4:
                    p, _ = self.bg_pixel(0x2109, bg3base, 2, x, y + 1, 0, v3)
                    if p is not None: c = p
                pix[x, y] = self.color(c)
        return img


def run_script(rom, script, shots_dir=None, every=None):
    """script: lista de (botões, quadros, nome_da_captura|None)."""
    emu = SNES(rom)
    shots = []
    for buttons, frames, shot in script:
        mask = 0
        for b in buttons.split('+') if buttons else []:
            mask |= BUTTONS[b]
        for _ in range(frames):
            emu.run_frame(mask)
        if shot and shots_dir:
            path = '%s/%s.png' % (shots_dir, shot)
            emu.render().resize((512, 448), Image.NEAREST).save(path)
            shots.append(path)
    return emu, shots

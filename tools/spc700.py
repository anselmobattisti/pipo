"""Montador mínimo de SPC700 (processador de som do SNES), codificador BRR
e um emulador simples do SPC700 usado só nos testes.

Só os opcodes realmente usados pelo driver de som estão aqui.
"""

# nome: (opcode, formato dos operandos)
#   d = endereço direct page (1 byte), a = absoluto (2 bytes), i = imediato (1 byte),
#   r = desvio relativo, 'id' = imediato e depois dp (MOV dp,#imm), 'sd' = dp origem, dp destino
OPS = {
    'mov_a_imm': (0xE8, 'i'), 'mov_x_imm': (0xCD, 'i'), 'mov_y_imm': (0x8D, 'i'),
    'mov_a_dp': (0xE4, 'd'), 'mov_dp_a': (0xC4, 'd'),
    'mov_a_dpx': (0xF4, 'd'), 'mov_dpx_a': (0xD4, 'd'),
    'mov_a_abs': (0xE5, 'a'), 'mov_abs_a': (0xC5, 'a'),
    'mov_a_absx': (0xF5, 'a'), 'mov_absx_a': (0xD5, 'a'),
    'mov_a_absy': (0xF6, 'a'), 'mov_absy_a': (0xD6, 'a'),
    'mov_a_indy': (0xF7, 'd'), 'mov_indy_a': (0xD7, 'd'),
    'mov_dp_imm': (0x8F, 'id'), 'mov_dp_dp': (0xFA, 'sd'),
    'mov_x_a': (0x5D, ''), 'mov_a_x': (0x7D, ''), 'mov_y_a': (0xFD, ''), 'mov_a_y': (0xDD, ''),
    'mov_x_dp': (0xF8, 'd'), 'mov_dp_x': (0xD8, 'd'), 'mov_y_dp': (0xEB, 'd'), 'mov_dp_y': (0xCB, 'd'),
    'mov_sp_x': (0xBD, ''),
    'cmp_a_imm': (0x68, 'i'), 'cmp_a_dp': (0x64, 'd'), 'cmp_x_imm': (0xC8, 'i'), 'cmp_y_imm': (0xAD, 'i'),
    'adc_a_imm': (0x88, 'i'), 'adc_a_dp': (0x84, 'd'), 'sbc_a_imm': (0xA8, 'i'),
    'and_a_imm': (0x28, 'i'), 'or_a_imm': (0x08, 'i'), 'or_a_dp': (0x04, 'd'), 'eor_a_imm': (0x48, 'i'),
    'inc_a': (0xBC, ''), 'dec_a': (0x9C, ''), 'inc_x': (0x3D, ''), 'dec_x': (0x1D, ''),
    'inc_y': (0xFC, ''), 'dec_y': (0xDC, ''), 'inc_dp': (0xAB, 'd'), 'dec_dp': (0x8B, 'd'),
    'asl_a': (0x1C, ''), 'lsr_a': (0x5C, ''),
    'clrc': (0x60, ''), 'setc': (0x80, ''),
    'bra': (0x2F, 'r'), 'beq': (0xF0, 'r'), 'bne': (0xD0, 'r'), 'bcc': (0x90, 'r'),
    'bcs': (0xB0, 'r'), 'bmi': (0x30, 'r'), 'bpl': (0x10, 'r'),
    'jmp': (0x5F, 'a'), 'call': (0x3F, 'a'), 'ret': (0x6F, ''),
    'push_a': (0x2D, ''), 'pop_a': (0xAE, ''), 'push_x': (0x4D, ''), 'pop_x': (0xCE, ''),
    'nop': (0x00, ''),
}


class SpcAsm:
    def __init__(self, org):
        self.org = org
        self.buf = bytearray()
        self.labels = {}
        self.fixups = []

    @property
    def pc(self):
        return self.org + len(self.buf)

    def label(self, name):
        assert name not in self.labels, name
        self.labels[name] = self.pc

    def byte(self, *vals):
        for v in vals:
            if isinstance(v, (bytes, bytearray, list)):
                self.buf.extend(v)
            else:
                self._val(v, 1)

    def word(self, *vals):
        for v in vals:
            self._val(v, 2)

    def pad_to(self, addr):
        assert self.pc <= addr, 'código do SPC passou de $%04X (está em $%04X)' % (addr, self.pc)
        self.buf.extend(b'\0' * (addr - self.pc))

    def _val(self, v, size, kind='abs'):
        if isinstance(v, int) and kind == 'abs':
            self.buf.extend((v & ((1 << (8 * size)) - 1)).to_bytes(size, 'little'))
        else:
            self.fixups.append((len(self.buf), size, v, kind))
            self.buf.extend(b'\0' * size)

    def resolve(self, v):
        if isinstance(v, int):
            return v
        if isinstance(v, tuple):
            op, x, y = v
            x, y = self.resolve(x), self.resolve(y)
            return {'+': x + y, '-': x - y}[op]
        return self.labels[v]

    def __getattr__(self, name):
        if name not in OPS:
            raise AttributeError(name)
        op, fmt = OPS[name]

        def emit(*args):
            self.buf.append(op)
            if fmt == 'i' or fmt == 'd':
                self._val(args[0], 1)
            elif fmt == 'a':
                self._val(args[0], 2)
            elif fmt == 'r':
                self._val(args[0], 1, 'rel')
            elif fmt == 'id':            # mov dp,#imm  -> 8F imm dp
                dp, imm = args
                self._val(imm, 1); self._val(dp, 1)
            elif fmt == 'sd':            # mov dst,src -> FA src dst
                dst, src = args
                self._val(src, 1); self._val(dst, 1)
        return emit

    def assemble(self):
        for off, size, expr, kind in self.fixups:
            v = self.resolve(expr)
            if kind == 'rel':
                d = v - (self.org + off + 1)
                assert -128 <= d <= 127, 'desvio SPC fora de alcance: %r' % (expr,)
                self.buf[off] = d & 0xFF
            else:
                self.buf[off:off + size] = (v & ((1 << (8 * size)) - 1)).to_bytes(size, 'little')
        return bytes(self.buf)


# ---------------------------------------------------------------- BRR
def brr_encode_loop(samples, shift=11):
    """Codifica uma forma de onda em BRR (filtro 0), com loop.
    `samples`: valores de -7 a 7 (múltiplo de 16 amostras)."""
    assert len(samples) % 16 == 0
    out = bytearray()
    nblocks = len(samples) // 16
    for b in range(nblocks):
        hdr = (shift << 4) | 0x02            # filtro 0, loop
        if b == nblocks - 1:
            hdr |= 0x01                       # fim
        out.append(hdr)
        blk = samples[b * 16:(b + 1) * 16]
        for i in range(0, 16, 2):
            hi, lo = blk[i] & 0xF, blk[i + 1] & 0xF
            out.append((hi << 4) | lo)
    return bytes(out)


def brr_decode(data, shift_ok=True):
    """Decodifica BRR com filtro 0 (para os testes)."""
    out = []
    for b in range(0, len(data), 9):
        hdr = data[b]
        shift = hdr >> 4
        for byte in data[b + 1:b + 9]:
            for n in (byte >> 4, byte & 0xF):
                if n >= 8:
                    n -= 16
                out.append((n << shift) >> 1)
        if hdr & 1:
            break
    return out


# ---------------------------------------------------------------- emulador (testes)
DECODE = {op: (name, fmt) for name, (op, fmt) in OPS.items()}


class SPC:
    """Emulador simplificado: CPU SPC700 (subconjunto), portas, timer 0 e
    registradores do DSP (só guarda os valores e registra os KON)."""

    def __init__(self):
        self.ram = bytearray(0x10000)
        self.A = self.X = self.Y = 0
        self.SP = 0xEF
        self.PC = 0
        self.N = self.Z = self.C = 0
        self.inp = [0, 0, 0, 0]      # escrito pela CPU principal
        self.out = [0, 0, 0, 0]      # lido pela CPU principal
        self.dsp = bytearray(128)
        self.dsp_addr = 0
        self.t0_target = 0
        self.t0_on = False
        self.t0_count = 0
        self.kon_log = []            # (quadro, bits, [(voz, pitch, srcn)])
        self.frame = 0
        self.running = False

    def read(self, a):
        a &= 0xFFFF
        if 0xF4 <= a <= 0xF7:
            return self.inp[a - 0xF4]
        if a == 0xF3:
            return self.dsp[self.dsp_addr & 0x7F]
        if a == 0xFD:
            v = self.t0_count; self.t0_count = 0
            return v
        return self.ram[a]

    def write(self, a, v):
        a &= 0xFFFF; v &= 0xFF
        if 0xF4 <= a <= 0xF7:
            self.out[a - 0xF4] = v; return
        if a == 0xF1:
            self.t0_on = bool(v & 1); return
        if a == 0xF2:
            self.dsp_addr = v; return
        if a == 0xF3:
            r = self.dsp_addr & 0x7F
            self.dsp[r] = v
            if r == 0x4C and v:
                info = []
                for vc in range(8):
                    if v & (1 << vc):
                        b = vc * 16
                        pitch = self.dsp[b + 2] | (self.dsp[b + 3] << 8)
                        info.append((vc, pitch, self.dsp[b + 4]))
                self.kon_log.append((self.frame, v, info))
            return
        if a == 0xFA:
            self.t0_target = v
        self.ram[a] = v

    def fetch(self):
        v = self.ram[self.PC]; self.PC = (self.PC + 1) & 0xFFFF
        return v

    def nz(self, v):
        v &= 0xFF
        self.N = v >> 7; self.Z = int(v == 0)
        return v

    def step(self):
        pc0 = self.PC
        op = self.fetch()
        if op not in DECODE:
            raise RuntimeError('SPC: opcode %02X desconhecido em %04X' % (op, pc0))
        name, fmt = DECODE[op]
        arg = arg2 = None
        if fmt in ('i', 'd'):
            arg = self.fetch()
        elif fmt == 'a':
            arg = self.fetch() | (self.fetch() << 8)
        elif fmt == 'r':
            arg = self.fetch(); arg = arg - 256 if arg & 0x80 else arg
        elif fmt == 'id':
            arg2 = self.fetch(); arg = self.fetch()       # imm, dp
        elif fmt == 'sd':
            arg2 = self.fetch(); arg = self.fetch()       # src, dst
        n = name
        if n == 'mov_a_imm': self.A = self.nz(arg)
        elif n == 'mov_x_imm': self.X = self.nz(arg)
        elif n == 'mov_y_imm': self.Y = self.nz(arg)
        elif n == 'mov_a_dp' or n == 'mov_a_abs': self.A = self.nz(self.read(arg))
        elif n == 'mov_dp_a' or n == 'mov_abs_a': self.write(arg, self.A)
        elif n == 'mov_a_dpx': self.A = self.nz(self.read((arg + self.X) & 0xFF))
        elif n == 'mov_dpx_a': self.write((arg + self.X) & 0xFF, self.A)
        elif n == 'mov_a_absx': self.A = self.nz(self.read(arg + self.X))
        elif n == 'mov_absx_a': self.write(arg + self.X, self.A)
        elif n == 'mov_a_absy': self.A = self.nz(self.read(arg + self.Y))
        elif n == 'mov_absy_a': self.write(arg + self.Y, self.A)
        elif n == 'mov_a_indy':
            p = self.read(arg) | (self.read((arg + 1) & 0xFF) << 8)
            self.A = self.nz(self.read(p + self.Y))
        elif n == 'mov_indy_a':
            p = self.read(arg) | (self.read((arg + 1) & 0xFF) << 8)
            self.write(p + self.Y, self.A)
        elif n == 'mov_dp_imm': self.write(arg, arg2)
        elif n == 'mov_dp_dp': self.write(arg, self.read(arg2))
        elif n == 'mov_x_a': self.X = self.nz(self.A)
        elif n == 'mov_a_x': self.A = self.nz(self.X)
        elif n == 'mov_y_a': self.Y = self.nz(self.A)
        elif n == 'mov_a_y': self.A = self.nz(self.Y)
        elif n == 'mov_x_dp': self.X = self.nz(self.read(arg))
        elif n == 'mov_dp_x': self.write(arg, self.X)
        elif n == 'mov_y_dp': self.Y = self.nz(self.read(arg))
        elif n == 'mov_dp_y': self.write(arg, self.Y)
        elif n == 'mov_sp_x': self.SP = self.X
        elif n.startswith('cmp_'):
            reg = {'a': self.A, 'x': self.X, 'y': self.Y}[n[4]]
            v = self.read(arg) if n.endswith('dp') else arg
            self.C = int(reg >= v); self.nz(reg - v)
        elif n in ('adc_a_imm', 'adc_a_dp', 'sbc_a_imm'):
            v = self.read(arg) if n.endswith('dp') else arg
            if n.startswith('sbc'): v ^= 0xFF
            r = self.A + v + self.C
            self.C = int(r > 0xFF); self.A = self.nz(r)
        elif n == 'and_a_imm': self.A = self.nz(self.A & arg)
        elif n == 'or_a_imm': self.A = self.nz(self.A | arg)
        elif n == 'or_a_dp': self.A = self.nz(self.A | self.read(arg))
        elif n == 'eor_a_imm': self.A = self.nz(self.A ^ arg)
        elif n in ('inc_a', 'dec_a'): self.A = self.nz(self.A + (1 if n[0] == 'i' else -1))
        elif n in ('inc_x', 'dec_x'): self.X = self.nz(self.X + (1 if n[0] == 'i' else -1))
        elif n in ('inc_y', 'dec_y'): self.Y = self.nz(self.Y + (1 if n[0] == 'i' else -1))
        elif n in ('inc_dp', 'dec_dp'): self.write(arg, self.nz(self.read(arg) + (1 if n[0] == 'i' else -1)))
        elif n == 'asl_a': self.C = self.A >> 7; self.A = self.nz(self.A << 1)
        elif n == 'lsr_a': self.C = self.A & 1; self.A = self.nz(self.A >> 1)
        elif n == 'clrc': self.C = 0
        elif n == 'setc': self.C = 1
        elif fmt == 'r':
            cond = {'bra': True, 'beq': self.Z, 'bne': not self.Z, 'bcc': not self.C,
                    'bcs': self.C, 'bmi': self.N, 'bpl': not self.N}[n]
            if cond: self.PC = (self.PC + arg) & 0xFFFF
        elif n == 'jmp': self.PC = arg
        elif n == 'call':
            self.push(self.PC >> 8); self.push(self.PC & 0xFF); self.PC = arg
        elif n == 'ret':
            lo = self.pull(); self.PC = lo | (self.pull() << 8)
        elif n == 'push_a': self.push(self.A)
        elif n == 'pop_a': self.A = self.pull()
        elif n == 'push_x': self.push(self.X)
        elif n == 'pop_x': self.X = self.pull()
        elif n == 'nop': pass
        else:
            raise RuntimeError('SPC: %s não implementado' % n)

    def push(self, v):
        self.ram[0x100 + self.SP] = v & 0xFF; self.SP = (self.SP - 1) & 0xFF

    def pull(self):
        self.SP = (self.SP + 1) & 0xFF; return self.ram[0x100 + self.SP]

    def run_frame(self, steps=1500):
        """Um quadro de vídeo: ~1,67 ticks do timer 0 (100 Hz) e `steps` instruções."""
        self.frame += 1
        if not self.running:
            return
        ticks_before = int((self.frame - 1) * 100 / 60)
        ticks_now = int(self.frame * 100 / 60)
        pending = ticks_now - ticks_before if (self.t0_on and self.t0_target == 80) else 0
        for i in range(steps):
            if pending and i % (steps // 2) == 0:
                self.t0_count = (self.t0_count + 1) & 0xF; pending -= 1
            self.step()


class IPL:
    """Imita o protocolo de carga do IPL do SPC700 (sem o código da ROM original)."""

    def __init__(self, spc):
        self.spc = spc
        spc.out[0], spc.out[1] = 0xAA, 0xBB
        self.state = 'idle'
        self.dest = 0
        self.expect = 0

    def cpu_write(self, port, v):
        s = self.spc
        s.inp[port] = v
        if port != 0 or s.running:
            return
        if self.state == 'idle':
            if v == 0xCC:
                self.dest = s.inp[2] | (s.inp[3] << 8)
                self.state = 'data'; self.expect = 0
                s.out[0] = 0xCC
        elif self.state == 'data':
            if v == self.expect:
                s.ram[(self.dest + v) & 0xFFFF] = s.inp[1]
                s.out[0] = v
                self.expect = (v + 1) & 0xFF
                if v == 0xFF:
                    self.dest += 0x100
            else:                       # novo comando: outro bloco ou executar
                addr = s.inp[2] | (s.inp[3] << 8)
                s.out[0] = v
                if s.inp[1] == 0:
                    s.PC = addr; s.running = True
                else:
                    self.dest = addr; self.expect = 0

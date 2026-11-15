"""Montador 65816 minimalista em Python (DSL).

Uso:
    a = Asm(org=0x8000)
    a.label('reset')
    a.sei(); a.clc(); a.xce()
    a.rep(0x30)            # A e X/Y em 16 bits (o montador acompanha o estado)
    a.lda('#', 0x1234)
    a.sta(0x2116)
    a.bra('reset')
    rom = a.assemble()

Operandos podem ser números ou nomes de rótulos (resolvidos na 2a passada).
Modos de endereçamento:
    a.lda('#', v)      imediato (tamanho segue M/X)
    a.lda(v)           absoluto (16 bits)
    a.lda(v, 'x')      absoluto,X       a.lda(v, 'y')  absoluto,Y
    a.lda('dp', v)     direct page
    a.lda('long', v)   longo (24 bits)  a.lda('long', v, 'x') longo,X
    a.lda('(dp),y', v) indireto DP indexado Y
    a.lda('[dp],y', v) indireto longo DP indexado Y
"""

OPS = {
    # mnem: {mode: opcode}
    'adc': dict(imm=0x69, dp=0x65, abs=0x6D, absx=0x7D, absy=0x79, long=0x6F, longx=0x7F),
    'sbc': dict(imm=0xE9, dp=0xE5, abs=0xED, absx=0xFD, absy=0xF9, long=0xEF, longx=0xFF),
    'and_': dict(imm=0x29, dp=0x25, abs=0x2D, absx=0x3D, absy=0x39, long=0x2F, longx=0x3F),
    'ora': dict(imm=0x09, dp=0x05, abs=0x0D, absx=0x1D, absy=0x19, long=0x0F, longx=0x1F),
    'eor': dict(imm=0x49, dp=0x45, abs=0x4D, absx=0x5D, absy=0x59, long=0x4F, longx=0x5F),
    'cmp': dict(imm=0xC9, dp=0xC5, abs=0xCD, absx=0xDD, absy=0xD9, long=0xCF, longx=0xDF),
    'lda': dict(imm=0xA9, dp=0xA5, abs=0xAD, absx=0xBD, absy=0xB9, long=0xAF, longx=0xBF,
                indy=0xB1, indly=0xB7),
    'sta': dict(dp=0x85, abs=0x8D, absx=0x9D, absy=0x99, long=0x8F, longx=0x9F,
                indy=0x91, indly=0x97),
    'ldx': dict(immx=0xA2, dp=0xA6, abs=0xAE, absy=0xBE),
    'ldy': dict(immx=0xA0, dp=0xA4, abs=0xAC, absx=0xBC),
    'stx': dict(dp=0x86, abs=0x8E),
    'sty': dict(dp=0x84, abs=0x8C),
    'stz': dict(dp=0x64, abs=0x9C, absx=0x9E),
    'cpx': dict(immx=0xE0, dp=0xE4, abs=0xEC),
    'cpy': dict(immx=0xC0, dp=0xC4, abs=0xCC),
    'inc': dict(acc=0x1A, dp=0xE6, abs=0xEE, absx=0xFE),
    'dec': dict(acc=0x3A, dp=0xC6, abs=0xCE, absx=0xDE),
    'asl': dict(acc=0x0A, abs=0x0E),
    'lsr': dict(acc=0x4A, abs=0x4E),
    'rol': dict(acc=0x2A),
    'ror': dict(acc=0x6A),
    'bit': dict(imm=0x89, abs=0x2C),
    'jmp': dict(abs=0x4C, absxind=0x7C),
    'jsr': dict(abs=0x20, absxind=0xFC),
}

IMPLIED = dict(
    inx=0xE8, iny=0xC8, dex=0xCA, dey=0x88, tax=0xAA, tay=0xA8, txa=0x8A, tya=0x98,
    txy=0x9B, tyx=0xBB, tcd=0x5B, txs=0x9A, tsx=0xBA, xba=0xEB,
    pha=0x48, pla=0x68, phx=0xDA, plx=0xFA, phy=0x5A, ply=0x7A, php=0x08, plp=0x28,
    phb=0x8B, plb=0xAB, phd=0x0B, pld=0x2B, phk=0x4B,
    clc=0x18, sec=0x38, sei=0x78, cli=0x58, xce=0xFB, cld=0xD8,
    rts=0x60, rtl=0x6B, rti=0x40, wai=0xCB, nop=0xEA, stp=0xDB,
)

BRANCHES = dict(bra=0x80, beq=0xF0, bne=0xD0, bcc=0x90, bcs=0xB0, bpl=0x10, bmi=0x30,
                bvc=0x50, bvs=0x70)
INVERT = dict(beq='bne', bne='beq', bcc='bcs', bcs='bcc', bpl='bmi', bmi='bpl',
              bvc='bvs', bvs='bvc')


class Asm:
    def __init__(self, org=0x8000):
        self.org = org
        self.buf = bytearray()
        self.labels = {}
        self.fixups = []  # (offset, size, expr, kind, pc_after)
        self.m16 = False
        self.x16 = False
        self._anon = 0

    # ------------------------------------------------------------ util
    @property
    def pc(self):
        return self.org + len(self.buf)

    def label(self, name):
        if name in self.labels:
            raise ValueError('rótulo duplicado: ' + name)
        self.labels[name] = self.pc

    def anon(self, prefix='L'):
        self._anon += 1
        return '_%s%d' % (prefix, self._anon)

    def byte(self, *vals):
        for v in vals:
            if isinstance(v, (bytes, bytearray, list)):
                self.buf.extend(v)
            else:
                self._emit(v, 1)

    def word(self, *vals):
        for v in vals:
            self._emit(v, 2)

    def align(self, n):
        while len(self.buf) % n:
            self.buf.append(0)

    def _emit(self, v, size, kind='abs'):
        if isinstance(v, int) and kind == 'abs':
            self.buf.extend((v & ((1 << (8 * size)) - 1)).to_bytes(size, 'little'))
        else:
            self.fixups.append((len(self.buf), size, v, kind))
            self.buf.extend(b'\0' * size)

    def resolve(self, v):
        if isinstance(v, int):
            return v
        if isinstance(v, tuple):  # (op, a, b) expressão simples
            op, a, b = v
            a, b = self.resolve(a), self.resolve(b)
            return {'+': a + b, '-': a - b, '>>': a >> b, '&': a & b}[op]
        if v not in self.labels:
            raise KeyError('rótulo não definido: %r' % (v,))
        return self.labels[v]

    # ------------------------------------------------------------ flags
    def rep(self, v):
        self.buf.extend((0xC2, v))
        if v & 0x20: self.m16 = True
        if v & 0x10: self.x16 = True

    def sep(self, v):
        self.buf.extend((0xE2, v))
        if v & 0x20: self.m16 = False
        if v & 0x10: self.x16 = False

    def a8(self): self.sep(0x20)
    def a16(self): self.rep(0x20)

    def assume(self, m16=None, x16=None):
        if m16 is not None: self.m16 = m16
        if x16 is not None: self.x16 = x16

    # ------------------------------------------------------------ genérico
    def _op(self, mnem, *args):
        modes = OPS[mnem]
        if len(args) == 0:
            self.buf.append(modes['acc']); return
        a0 = args[0]
        if a0 == '#':
            v = args[1]
            if 'imm' in modes:
                self.buf.append(modes['imm']); self._emit(v, 2 if self.m16 else 1)
            else:
                self.buf.append(modes['immx']); self._emit(v, 2 if self.x16 else 1)
            return
        if a0 == 'dp':
            self.buf.append(modes['dp']); self._emit(args[1], 1); return
        if a0 == 'long':
            mode = 'longx' if len(args) > 2 and args[2] == 'x' else 'long'
            self.buf.append(modes[mode]); self._emit(args[1], 3); return
        if a0 == '(dp),y':
            self.buf.append(modes['indy']); self._emit(args[1], 1); return
        if a0 == '[dp],y':
            self.buf.append(modes['indly']); self._emit(args[1], 1); return
        if a0 == '(abs,x)':
            self.buf.append(modes['absxind']); self._emit(args[1], 2); return
        mode = 'abs'
        if len(args) > 1:
            mode = 'abs' + args[1]
        self.buf.append(modes[mode]); self._emit(a0, 2)

    def __getattr__(self, name):
        if name in OPS:
            return lambda *a: self._op(name, *a)
        if name in IMPLIED:
            return lambda: self.buf.append(IMPLIED[name])
        if name in BRANCHES:
            def br(target):
                self.buf.append(BRANCHES[name])
                self._emit(target, 1, kind='rel')
            return br
        if name.startswith('j') and ('b' + name[1:]) in INVERT:
            # desvio "longo": jeq, jne, jcc ... -> branch invertido + JMP
            def jb(target):
                skip = self.anon('J')
                getattr(self, INVERT['b' + name[1:]])(skip)
                self.jmp(target)
                self.label(skip)
            return jb
        raise AttributeError(name)

    # ------------------------------------------------------------ final
    def assemble(self):
        for off, size, expr, kind in self.fixups:
            v = self.resolve(expr)
            if kind == 'rel':
                d = v - (self.org + off + 1)
                if not -128 <= d <= 127:
                    raise ValueError('desvio fora de alcance para %r (%d)' % (expr, d))
                self.buf[off] = d & 0xFF
            else:
                self.buf[off:off + size] = (v & ((1 << (8 * size)) - 1)).to_bytes(size, 'little')
        return bytes(self.buf)

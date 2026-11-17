"""Driver de som (programa do SPC700), instrumento, música e efeitos.

A CPU principal manda efeitos assim: escreve o número do efeito em $2141 e
depois muda o valor de $2140 (um contador). O driver percebe a mudança e toca.
"""
import math
from spc700 import SpcAsm, brr_encode_loop

ORG = 0x0200          # o programa é carregado e executado a partir daqui
DIR_ADDR = 0x0800     # diretório de amostras (precisa começar numa página)

# ids dos efeitos (usados pelo build.py)
SFX = {'pick': 1, 'yay': 2, 'gate': 3, 'star': 4, 'piu': 5, 'leaves': 6,
       'bell1': 7, 'bell2': 8, 'bell3': 9, 'note1': 10, 'note2': 11, 'note3': 12,
       'grow': 13, 'crow': 14, 'water': 15,
       'croak': 16, 'hop': 17, 'mischief': 18, 'laugh': 19}
# comandos especiais (mesmo canal dos efeitos)
CMD_MUTE, CMD_UNMUTE = 0x40, 0x41   # desliga / liga o volume geral (o 2º toca 'pick')

TICK_HZ = 100         # timer 0: 8000 Hz / 80
Q = 54                # semínima em ticks (~110 bpm)


def midi(name):
    """'C5' -> número MIDI."""
    notes = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    n = notes[name[0]]
    rest = name[1:]
    if rest.startswith('#'):
        n += 1; rest = rest[1:]
    return 12 * (int(rest) + 1) + n


def seq(*events, loop=False):
    """events: ('C5', duração) ou (None, duração) para pausa."""
    out = bytearray()
    for note, dur in events:
        assert 1 <= dur <= 255
        out += bytes((midi(note) if note else 0, dur))
    out.append(0xFE if loop else 0xFF)
    return bytes(out)


# ---------------------------------------------------------------- música
# Melodia da cantiga folclórica "Sapo Cururu" (domínio público), em dó maior e 2/4,
# com um final que volta para o dó para a música repetir sem emenda.
#   Sa-po cu-ru-ru / na bei-ra do ri-o / quan-do o sa-po can-ta, ó ma-ni-nha /
#   é por-que tem fri-o
H, E = 2 * Q, Q // 2
MELODY = seq(
    ('G4', E), ('A4', E), ('G4', E), ('E4', E), ('C5', Q), (None, Q),        # sapo cururu
    ('G4', E), ('A4', E), ('G4', E), ('A4', E), ('C5', Q), ('C5', Q),        # na beira do rio
    ('E5', E), ('E5', E), ('D5', E), ('E5', E), ('F5', Q), ('D5', Q),        # quando o sapo canta
    ('B4', E), ('G4', E), ('G4', Q),                                         # ó maninha
    ('A4', E), ('A4', E), ('G4', E), ('F4', E), ('E4', Q), ('D4', Q),        # é porque tem frio
    ('C4', H),
    loop=True)
BASS = seq(                       # um acorde por compasso (mínimas)
    ('C3', H), ('C3', H), ('F3', H), ('C3', H), ('C3', H),
    ('D3', H), ('G2', H), ('F3', H), ('G2', H), ('C3', H),
    loop=True)


EFFECTS = {
    'pick': seq(('C6', 5), ('G6', 12)),
    'yay': seq(('C5', 7), ('E5', 7), ('G5', 7), ('C6', 20)),
    'gate': seq(('C5', 5), ('E5', 5), ('G5', 5), ('C6', 5), ('E6', 5), ('G6', 22)),
    'star': seq(('G5', 10), ('G5', 5), ('C6', 10), ('E6', 10), ('G6', 25),
                ('E6', 8), ('G6', 40)),
    'piu': seq(('A6', 4), ('C7', 9)),
    'leaves': seq(('G4', 5), ('E4', 8)),
    'bell1': seq(('C6', 4), ('C6', 40)),
    'bell2': seq(('E6', 4), ('E6', 40)),
    'bell3': seq(('G6', 4), ('G6', 40)),
    'note1': seq(('D5', 20)),
    'note2': seq(('A5', 20)),
    'note3': seq(('B5', 20)),
    'grow': seq(('C5', 4), ('D5', 4), ('E5', 4), ('F5', 4), ('G5', 4), ('A5', 4), ('B5', 4),
                ('C6', 4), ('D6', 4), ('E6', 4), ('G6', 25)),
    'crow': seq(('G5', 12), ('G5', 12), ('C6', 14), ('E6', 45), ('C6', 30)),
    # sapo Cururu
    'croak': seq(('A3', 9), (None, 4), ('E3', 9), (None, 4), ('A3', 16)),
    'hop': seq(('C5', 3), ('G5', 5)),
    'mischief': seq(('A5', 4), ('E5', 4), ('C5', 4), ('A4', 4), ('E4', 10)),
    'laugh': seq(('E5', 6), (None, 4), ('E5', 6), (None, 4), ('G5', 6), (None, 4), ('E5', 14)),
    'water': seq(('E6', 3), ('C6', 3), ('A5', 3), ('F5', 3), ('D5', 3), ('C5', 10)),
}


def instrument():
    """Uma onda suave (seno + um pouco de 3ª harmônica), 32 amostras = 1 ciclo."""
    vals = []
    for i in range(32):
        t = 2 * math.pi * i / 32
        v = math.sin(t) + 0.25 * math.sin(3 * t)
        vals.append(v)
    m = max(abs(v) for v in vals)
    return [max(-7, min(7, round(v / m * 7))) for v in vals]


def pitch_value(n):
    """Valor de PITCH do DSP para a nota MIDI n (amostra de 32 pontos por ciclo)."""
    f = 440.0 * 2 ** ((n - 69) / 12)
    return min(0x3FFF, round(f * 4096 / 1000))


# ---------------------------------------------------------------- driver
# variáveis na direct page do SPC
T = 0x10              # 3 trilhas x 8 bytes: ptr(2) timer voz_base bit_voz ativo loop(2)
P = 0x30              # ponteiro temporário (2)
NOTE = 0x32
LAST = 0x33           # último valor visto na porta 0
KON = 0x34            # vozes a disparar neste tick (escritas juntas no KON)


def build_driver():
    a = SpcAsm(ORG)
    a.label('start')
    a.mov_x_imm(0xEF); a.mov_sp_x()
    # registradores do DSP
    a.mov_x_imm(0)
    a.label('dsp_loop')
    a.mov_a_absx('dsp_init'); a.cmp_a_imm(0xFF); a.beq('dsp_done')
    a.mov_dp_a(0xF2); a.inc_x()
    a.mov_a_absx('dsp_init'); a.mov_dp_a(0xF3); a.inc_x()
    a.bra('dsp_loop')
    a.label('dsp_done')
    # trilhas
    a.mov_x_imm(0)
    a.label('trk_loop')
    a.mov_a_absx('track_init'); a.mov_dpx_a(T)
    a.inc_x(); a.cmp_x_imm(24); a.bne('trk_loop')
    # timer 0 a 100 Hz
    a.mov_dp_imm(0xFA, 80)
    a.mov_dp_imm(0xF1, 0x01)
    a.mov_a_dp(0xF4); a.mov_dp_a(LAST)
    a.mov_dp_imm(KON, 0)

    a.label('main')
    a.mov_a_dp(0xFD); a.beq('check_cmd')
    a.mov_x_imm(0); a.call('track_tick')
    a.mov_x_imm(8); a.call('track_tick')
    a.mov_x_imm(16); a.call('track_tick')
    a.mov_a_dp(KON); a.beq('check_cmd')
    a.mov_dp_imm(0xF2, 0x4C); a.mov_dp_a(0xF3)  # um único KON por tick
    a.mov_dp_imm(KON, 0)
    a.label('check_cmd')
    a.mov_a_dp(0xF4); a.cmp_a_dp(LAST); a.beq('main')
    a.mov_dp_a(LAST)
    a.mov_a_dp(0xF5); a.call('start_sfx')
    a.bra('main')

    # start_sfx: A = número do efeito (1..N) ou comando de volume
    a.label('start_sfx')
    a.cmp_a_imm(CMD_MUTE); a.beq('cmd_mute')
    a.cmp_a_imm(CMD_UNMUTE); a.bne('ss_play')
    a.mov_a_imm(0x7F); a.call('set_mvol')
    a.mov_a_imm(SFX['pick'])
    a.bra('ss_play')
    a.label('cmd_mute')
    a.mov_a_imm(0)
    a.label('set_mvol')                         # volume geral (esq. e dir.) = A
    a.mov_dp_imm(0xF2, 0x0C); a.mov_dp_a(0xF3)
    a.mov_dp_imm(0xF2, 0x1C); a.mov_dp_a(0xF3)
    a.ret()
    a.label('ss_play')
    a.asl_a(); a.mov_y_a()
    a.mov_a_absy(('-', 'sfx_ptrs', 2)); a.mov_dp_a(T + 16)
    a.mov_a_absy(('-', 'sfx_ptrs', 1)); a.mov_dp_a(T + 17)
    a.mov_dp_imm(T + 18, 0)
    a.mov_dp_imm(T + 21, 1)
    a.ret()

    # track_tick: X = trilha*8
    a.label('track_tick')
    a.mov_a_dpx(T + 5); a.beq('tt_ret')
    a.mov_a_dpx(T + 2); a.beq('tt_read')
    a.dec_a(); a.mov_dpx_a(T + 2); a.bne('tt_ret')
    a.label('tt_read')
    a.mov_a_dpx(T + 0); a.mov_dp_a(P)
    a.mov_a_dpx(T + 1); a.mov_dp_a(P + 1)
    a.mov_y_imm(0)
    a.mov_a_indy(P)
    a.cmp_a_imm(0xFF); a.bne('tt_1')
    a.mov_a_imm(0); a.mov_dpx_a(T + 5)          # fim do efeito
    a.ret()
    a.label('tt_1')
    a.cmp_a_imm(0xFE); a.bne('tt_2')
    a.mov_a_dpx(T + 6); a.mov_dpx_a(T + 0)      # volta ao começo da música
    a.mov_a_dpx(T + 7); a.mov_dpx_a(T + 1)
    a.bra('tt_read')
    a.label('tt_2')
    a.mov_dp_a(NOTE)
    a.inc_y(); a.mov_a_indy(P); a.mov_dpx_a(T + 2)
    a.mov_a_dp(P); a.clrc(); a.adc_a_imm(2); a.mov_dpx_a(T + 0)
    a.mov_a_dp(P + 1); a.adc_a_imm(0); a.mov_dpx_a(T + 1)
    a.mov_a_dp(NOTE); a.beq('tt_ret')           # pausa
    a.asl_a(); a.mov_y_a()
    a.mov_a_dpx(T + 3); a.or_a_imm(0x02); a.mov_dp_a(0xF2)
    a.mov_a_absy('pitch_tab'); a.mov_dp_a(0xF3)
    a.mov_a_dpx(T + 3); a.or_a_imm(0x03); a.mov_dp_a(0xF2)
    a.mov_a_absy(('+', 'pitch_tab', 1)); a.mov_dp_a(0xF3)
    a.mov_a_dpx(T + 4); a.or_a_dp(KON); a.mov_dp_a(KON)
    a.label('tt_ret')
    a.ret()

    # ---- dados
    a.label('dsp_init')
    regs = [
        (0x6C, 0x20),                 # FLG: som ligado, eco sem escrita
        (0x5C, 0x00),                 # KOF
        (0x0C, 0x7F), (0x1C, 0x7F),   # volume geral
        (0x2C, 0x00), (0x3C, 0x00),   # volume do eco
        (0x4D, 0x00), (0x3D, 0x00), (0x2D, 0x00),   # EON, NON, PMON
        (0x5D, DIR_ADDR >> 8),        # diretório de amostras
        (0x6D, 0xFF), (0x7D, 0x00),   # eco: endereço/tamanho
        # voz 0: melodia
        (0x00, 0x30), (0x01, 0x30), (0x04, 0), (0x05, 0xDF), (0x06, 0x6C), (0x07, 0),
        # voz 1: baixo
        (0x10, 0x38), (0x11, 0x38), (0x14, 0), (0x15, 0xDF), (0x16, 0x8B), (0x17, 0),
        # voz 7: efeitos
        (0x70, 0x60), (0x71, 0x60), (0x74, 0), (0x75, 0xDF), (0x76, 0x4E), (0x77, 0),
    ]
    for r, v in regs:
        a.byte(r, v)
    a.byte(0xFF)
    a.label('track_init')
    for ptr, base, bit, active in (('song_mel', 0x00, 0x01, 1), ('song_bass', 0x10, 0x02, 1),
                                   ('song_mel', 0x70, 0x80, 0)):
        a.word(ptr); a.byte(0, base, bit, active); a.word(ptr)
    a.label('sfx_ptrs')
    for name, _ in sorted(SFX.items(), key=lambda kv: kv[1]):
        a.word('sfx_' + name)
    a.label('pitch_tab')
    a.word(*[pitch_value(n) for n in range(128)])
    a.label('song_mel'); a.byte(MELODY)
    a.label('song_bass'); a.byte(BASS)
    for name, data in EFFECTS.items():
        a.label('sfx_' + name); a.byte(data)

    # diretório + amostra
    a.pad_to(DIR_ADDR)
    sample_addr = DIR_ADDR + 4
    a.word(sample_addr, sample_addr)
    a.byte(brr_encode_loop(instrument(), shift=12))
    blob = a.assemble()
    return blob, a

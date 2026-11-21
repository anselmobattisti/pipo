#!/usr/bin/env python3
"""Gera pipo.sfc — "Pipo no Jardim", jogo de SNES para crianças pequenas.

    python3 build.py

Não precisa de nenhum assembler externo: o código 65816 é escrito com a DSL de
tools/asm65816.py e os gráficos são gerados por tools/assets.py.
As fases ficam em level1.py ... level10.py (trilha do sapo) e pato1.py ... pato5.py
(trilha do Pato Pateta: letras e números).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from asm65816 import Asm  # noqa: E402
import assets as A  # noqa: E402
import sound  # noqa: E402
import growth  # noqa: E402
import level1  # noqa: E402
import level2  # noqa: E402
import level3  # noqa: E402
import level4  # noqa: E402
import level5  # noqa: E402
import level6  # noqa: E402
import level7  # noqa: E402
import level8  # noqa: E402
import level9  # noqa: E402
import level10  # noqa: E402
import pato1  # noqa: E402
import pato2  # noqa: E402
import pato3  # noqa: E402
import pato4  # noqa: E402
import pato5  # noqa: E402
import title  # noqa: E402
import ending  # noqa: E402
import ending2  # noqa: E402

# as trilhas (escolhidas no menu): 0 = do sapo Cururu, 1 = do Pato Pateta (letras e números)
TRAILS = [[level1, level2, level3, level4, level5, level6, level7, level8, level9, level10],
          [pato1, pato2, pato3, pato4, pato5]]
LEVELS = TRAILS[0] + TRAILS[1]     # todas as fases, uma trilha depois da outra
TRAIL_BASE = [0, len(TRAILS[0])]   # número da primeira fase de cada trilha
SCREENS = [title, ending, ending2]  # abertura e telas finais usam a mesma estrutura de mapa
ALL = LEVELS + SCREENS
TITLE, ENDING, ENDING2 = len(LEVELS), len(LEVELS) + 1, len(LEVELS) + 2
TRAIL_END = [ENDING, ENDING2]      # tela final de cada trilha
NBANKS = 16                        # ROM de 512 KB
assert title.NLEVELS == max(len(t) for t in TRAILS) and title.MENU.index('level0') == 4


def trail_pos(i):
    """(trilha, posição dentro dela) da fase i."""
    t = max(k for k, b in enumerate(TRAIL_BASE) if b <= i)
    return t, i - TRAIL_BASE[t]


def level_next(i):
    """Para onde vai depois da fase i: a próxima da trilha ou a tela final dela."""
    t, k = trail_pos(i)
    return i + 1 if k + 1 < len(TRAILS[t]) else TRAIL_END[t]


MODE_PLAY, MODE_TITLE, MODE_END, MODE_INTRO = 0, 1, 2, 3
MSG_AUTO_FRAMES = 300   # os diálogos passam sozinhos depois de 5 s (ou antes, com um botão)

# todas as mensagens de todas as fases, com prefixo "<fase>_": primeiro todas em
# português, depois as mesmas em inglês (índice + NPT)
MESSAGES = []
for _li, _L in enumerate(ALL):
    for _name, _lines, _nxt in _L.MESSAGES:
        MESSAGES.append(('%d_%s' % (_li, _name), _lines, '%d_%s' % (_li, _nxt) if _nxt else None))
NPT = len(MESSAGES)
for _li, _L in enumerate(ALL):
    _en = getattr(_L, 'MESSAGES_EN', {})
    for _name, _lines, _nxt in _L.MESSAGES:
        MESSAGES.append(('%d_%s@en' % (_li, _name), _en.get(_name, _lines),
                         '%d_%s@en' % (_li, _nxt) if _nxt else None))
MSG = {name: i for i, (name, _, _) in enumerate(MESSAGES)}
LANG_PT, LANG_EN = 0, 1

# ------------------------------------------------------------------ memória (WRAM)
VARS = {}
_next = 0x10
for _n in ('joy joy_prev joy_new px py tx ty move_cnt move_dir facing frame_ctr '
           'nmi_count nmi_ready map_dirty text_dirty tm_val inidisp carry delivered '
           'msg_active msg_next msg_timer reset_after happy bump_lock target cur_mt '
           'ntx nty tmp0 tmp1 tmp2 tmp3 ptr hop txt_scroll level rng ball_i '
           'up_src up_bank up_left up_vaddr up_chunk msg_pending fx_timer fx_x fx_y '
           'followers hist_head mother_x mother_y snd_req snd_cnt '
           'pal_id pal_dirty pslot slot_stage slot_stage1 grow_t pu_src pu_bank pu_left pu_vaddr pu_slot '
           'mode scr_t hide_player scene_on scene_x scene_y scene_tile logo_req lang menu_sel menu_page snd_off speed spd_acc msg_auto '
           'lptr lptr_bank trail song song_req').split():
    VARS[_n] = _next
    _next += 2
assert _next < 0x100
V = VARS

OAM = 0x0200      # 544 bytes
BG1BUF = 0x0800   # 2048 bytes (mapa 32x32 do BG1)
TXTBUF = 0x1000   # 512 bytes (linhas 20..27 do BG3)
MAPBUF = 0x1200   # 224 bytes (16x14 metatiles)
# atores (bolas puladoras / patinhos): 3, uma palavra cada; índice X = ator*2
B_ACT, B_TX, B_TY, B_X, B_Y = 0x1300, 0x1310, 0x1320, 0x1330, 0x1340
B_DX, B_DY, B_TIM, B_MOV, B_H = 0x1350, 0x1360, 0x1370, 0x1380, 0x1390
B_KIND, B_SLOT, B_ITEM = 0x13A0, 0x13B0, 0x13C0
KIND_BALL, KIND_DUCK, KIND_FLY = 0, 1, 2
DUCK_WAIT, DUCK_FOLLOW, DUCK_HOME = 1, 2, 3
# histórico das posições do Pipo (para a fila de patinhos)
HIST_X, HIST_Y = 0x1400, 0x1480   # 64 palavras cada
HIST_LEN = 64
# o sapo Cururu bagunçando a fase (introdução)
IN_IP, IN_T, IN_X, IN_Y, IN_VX, IN_VY = 0x1500, 0x1502, 0x1504, 0x1506, 0x1508, 0x150A
IN_PAUSE, IN_REVEAL, IN_HOP, IN_CNT = 0x150C, 0x150E, 0x1510, 0x1512
FROG_OAM = 12
# cena final (papai, mamãe e a coberta do Cururu)
CUT_T, CUT_OFS, CUT_EV, CUT_DONE, CUT_PB = 0x1520, 0x1522, 0x1524, 0x1526, 0x1528
CUT_OAM = 13          # OAM 13 coberta, 14 papai, 15 mamãe (32x32), 16 Cururu
# amigos que correm para se esconder (fase 4): 3 de cada, uma palavra por amigo
R_ON, R_X, R_Y, R_VX, R_VY, R_T, R_DST = 0x1530, 0x1538, 0x1540, 0x1548, 0x1550, 0x1558, 0x1560
RUN_OAM = 17          # OAM 17-19
RUN_FRAMES = 64       # quadros da corrida até o arbusto (posição em 8.8: v = distância*4)
SCARE = 0x80          # bit de "assustar" no campo REVELA do roteiro do sapo

VRAM_BG1_TILES = 0x0000
VRAM_FONT = 0x3000
VRAM_MSG_TILES = VRAM_FONT + A.MSG_TILE_BASE * 8
VRAM_SPR = 0x4000
VRAM_BG1_MAP = 0x6000
VRAM_BG3_MAP = 0x6400
VRAM_TEXT_ROWS = VRAM_BG3_MAP + 20 * 32
UPLOAD_CHUNK = 1536                # bytes de texto enviados por vblank

TM_FIELD = 0x11   # BG1 + sprites
TM_TEXT = 0x15    # BG1 + BG3 + sprites

BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT = 0x0800, 0x0400, 0x0200, 0x0100
BTN_ANY = 0xF0F0  # B Y Select Start A X L R
SPEED_SLOW, SPEED_NORMAL, SPEED_FAST = 0, 1, 2
SPEED_FRAMES = [32, 20, 12]        # quadros para andar um bloco (16 px) em cada velocidade
SPEED_INC = [round(256 * 8 / f) for f in SPEED_FRAMES]   # a cada 256 acumulados = passo de 2 px

MT = A.MT
COLORS = 'rby'
# itens carregáveis (número = posição + 1): (sprite, metatile no chão)
ITEMS = [('ball_r', 'ball_r'), ('ball_b', 'ball_b'), ('ball_y', 'ball_y'),
         ('shape_c', 'shape_c'), ('shape_s', 'shape_s'), ('shape_t', 'shape_t'),
         ('can', 'can'), ('carrot', 'carrot'), ('corn', 'corn'), ('bone', 'bone'),
         ('firefly', 'grass'), ('egg', 'egg')]
ITEMS += [('blk_' + s, 'blk_' + s) for s in A.SYMBOLS]     # bloquinhos de letras e números
ITEM = {spr: i + 1 for i, (spr, _) in enumerate(ITEMS)}
# o que cada metatile vira quando a ação dá certo
MT_NEXT = {
    'basket_r': 'basketf_r', 'basket_b': 'basketf_b', 'basket_y': 'basketf_y',
    'hole_c': 'holef_c', 'hole_s': 'holef_s', 'hole_t': 'holef_t',
    'rabbit_h': 'rabbit_f', 'hen_h': 'hen_f', 'dog_h': 'dog_f', 'lantern': 'lantern_on',
    'nest_0': 'nest_1', 'nest_1': 'nest_2', 'nest_2': 'nest_3',
    'sprout_1': 'bloom_1', 'sprout_2': 'bloom_2', 'sprout_3': 'bloom_3',
    'bell_r': 'bellr_r', 'bell_b': 'bellr_b', 'bell_y': 'bellr_y',
}
MT_NEXT.update({'slot_' + s: 'slotf_' + s for s in A.SYMBOLS})
MT_NEXT.update({'dots_%d' % n: 'dotsf_%d' % n for n in range(1, 6)})
MT_NEXT.update({'button_' + c: 'buttonp_' + c for c in COLORS})
MT_NEXT.update({'nbutton_%d' % k: 'nbuttonp_%d' % k for k in (1, 2, 3)})
# quem bagunça a fase na introdução: desenhos (pulando, parado, rindo) e sons
# (ao chegar, a cada bagunça, na última, ao voltar para casa)
VISITORS = {
    'frog': dict(tile='frog', under='water', sprites=('frog_jump', 'frog_sit', 'frog_laugh'),
                 sfx=('croak', 'mischief', 'laugh', 'croak')),
    'pato': dict(tile='pato', under='grass', sprites=('pato_jump', 'pato_sit', 'pato_laugh'),
                 sfx=('quack', 'oops', 'quack', 'quack')),
}
VISITOR_ORDER = ['frog', 'pato']


def visitor(L):
    return VISITORS[getattr(L, 'VISITOR', 'frog')]


def sprite_word(name, prio=0x20):
    """tile | atributos << 8 de um sprite 16x16 (da folha principal ou da folha extra)."""
    if name in A.SPR:
        t, pal2 = A.spr_tile(A.SPR[name]), name in A.SPR_PAL2_CELLS
    else:
        t, pal2 = A.hud_tile(name), name in A.HUD_PAL2_CELLS
    return (t & 0xFF) | ((prio | (2 if pal2 else 0) | (t >> 8)) << 8)
STAGE_SLOT_VRAM = [VRAM_SPR + 128 * 16, VRAM_SPR + 256 * 16]   # 2 áreas de 128 tiles
STAGE_SLOT_TILE = [128, 256]
GROW_FRAMES = 160      # duração do "crescer" (pisca nos últimos 100 quadros)


def sfx(a, name):
    """Pede um efeito sonoro (enviado ao SPC700 no próximo quadro). A em 16 bits."""
    a.lda('#', sound.SFX[name]); a.sta(V['snd_req'])


def build():
    bg_tiles, mt_table, _ = A.build_bg()
    spr_tiles, _ = A.build_sprites()
    box_tiles = A.build_box_tiles()
    msgs, _ = A.build_text([lines for _, lines, _ in MESSAGES])
    logo_tiles, logo_maps = A.build_logos([A.render_logo([('PIPO', 34), ('NO JARDIM', 20)]),
                                           A.render_logo([('FIM!', 40)], width=160, height=48),
                                           A.render_logo([('THE END!', 36)], width=200, height=48)])

    # gráficos no banco 1, tiles das mensagens onde couber (bancos 1 a 3)
    banks = {b: bytearray() for b in range(1, NBANKS)}
    gfx = {}
    for name, blob in (('bg_tiles', bg_tiles), ('box_tiles', box_tiles), ('spr_tiles', spr_tiles),
                       ('logo_tiles', logo_tiles)):
        gfx[name] = 0x8000 + len(banks[1])
        banks[1] += blob
    gfx['logo_size'] = len(logo_tiles)
    stage_src = []
    for st in range(growth.STAGES):
        blob = stage_tiles(st)
        bank = next(b for b in range(2, NBANKS) if len(banks[b]) + len(blob) <= 0x8000)
        stage_src.append((bank, 0x8000 + len(banks[bank])))
        banks[bank] += blob
    # papai e mamãe (uma área de sprites inteira) e a cena final quadro a quadro
    par = growth.parents_sheet()
    par_tiles = b''.join(A.tile_4bpp(par, tx * 8, ty * 8) for ty in range(8) for tx in range(16))
    pb = next(b for b in range(2, NBANKS) if len(banks[b]) + len(par_tiles) <= 0x8000)
    gfx['parents'] = (pb, 0x8000 + len(banks[pb]))
    banks[pb] += par_tiles
    cut_blob, cut_events = ending_cutscene()
    cb = next(b for b in range(2, NBANKS) if len(banks[b]) + len(cut_blob) <= 0x8000)
    cut_addr = (cb << 16) | (0x8000 + len(banks[cb]))
    banks[cb] += cut_blob
    global PARENTS_SRC, CUT_EVENT_LIST
    PARENTS_SRC = gfx['parents']
    CUT_EVENT_LIST = cut_events
    hud_tiles, _ = A.build_hud()             # placar: estrelinhas e desenhos extras
    hb = next(b for b in range(2, NBANKS) if len(banks[b]) + len(hud_tiles) <= 0x8000)
    gfx['hud'] = (hb, 0x8000 + len(banks[hb]), len(hud_tiles))
    banks[hb] += hud_tiles
    msg_src = []
    for tiles, m in msgs:
        mapb = b''.join((0x2400 | t).to_bytes(2, 'little') for t in m)   # prioridade + paleta 1
        blob = mapb + tiles
        bank = next(b for b in range(1, NBANKS) if len(banks[b]) + len(blob) <= 0x8000)
        base = 0x8000 + len(banks[bank])
        msg_src.append((bank, base + len(mapb), len(tiles), base))   # banco, tiles, tamanho, mapa
        banks[bank] += blob

    a = Asm(0x8000)
    emit_init(a, gfx, bg_tiles, box_tiles, spr_tiles, stage_src)
    emit_main(a)
    emit_text(a)
    emit_player(a)
    emit_actions(a)
    emit_level(a)
    emit_actors(a)
    emit_sprites(a)
    emit_hud(a)
    emit_intro(a)
    emit_cutscene(a, cut_addr)
    emit_runners(a)
    emit_nmi(a)
    emit_data(a, mt_table, msgs, msg_src, stage_src, logo_maps)
    spc_blob, _ = sound.build_driver()
    a.label('spc_blob'); a.byte(spc_blob)
    a.label('spc_end')

    code = a.assemble()
    end = 0x8000 + len(code)
    if end > 0xFFB0:
        raise SystemExit('ROM do banco 0 cheia: $%X' % end)
    usage = {b: len(v) for b, v in banks.items()}
    return finish_rom(code, banks, a), a, end, usage


# ================================================================== INICIALIZAÇÃO
def emit_init(a, gfx, bg_tiles, box_tiles, spr_tiles, stage_src):
    a.label('reset')
    a.sei(); a.clc(); a.xce()
    a.rep(0x38)                      # A/X/Y 16 bits, modo binário
    a.ldx('#', 0x1FFF); a.txs()
    a.lda('#', 0); a.tcd()
    a.phk(); a.plb()

    # zera registradores do PPU
    a.a8()
    a.lda('#', 0x80); a.sta(0x2100)  # tela desligada (force blank)
    for r in list(range(0x2101, 0x210D)) + list(range(0x2123, 0x2134)):
        a.stz(r)
    for r in range(0x210D, 0x2115):  # rolagem: escrita dupla
        a.stz(r); a.stz(r)
    for r in range(0x211B, 0x2121):
        a.stz(r); a.stz(r)
    a.stz(0x4200)
    a.rep(0x20)

    # zera WRAM $0000-$1EFF
    a.ldx('#', 0)
    a.label('clr_ram')
    a.stz(0, 'x'); a.inx(); a.inx()
    a.cpx('#', 0x1F00); a.bne('clr_ram')

    # zera VRAM inteira (DMA de fonte fixa)
    a.a8()
    a.lda('#', 0x80); a.sta(0x2115)
    a.rep(0x20)
    a.stz(0x2116)
    dma(a, 0, 0x09, 0x18, 'zero_word', 0)   # 0 = 65536 bytes
    vram_upload(a, VRAM_BG1_TILES, gfx['bg_tiles'], len(bg_tiles), bank=1)
    vram_upload(a, VRAM_FONT, gfx['box_tiles'], len(box_tiles), bank=1)
    vram_upload(a, VRAM_SPR, gfx['spr_tiles'], len(spr_tiles), bank=1)
    vram_upload(a, VRAM_FONT + A.LOGO_TILE_BASE * 8, gfx['logo_tiles'], gfx['logo_size'], bank=1)
    hb, hsrc, hsize = gfx['hud']
    vram_upload(a, VRAM_SPR + A.HUD_TILE_BASE * 16, hsrc, hsize, bank=hb)
    bank0, src0 = stage_src[0]                # Pipo pequenino na área 0
    vram_upload(a, STAGE_SLOT_VRAM[0], src0, 4096, bank=bank0)
    a.a8(); a.stz(0x2121); a.rep(0x20)
    dma(a, 0, 0x00, 0x22, 'palettes', 512)

    # registradores de vídeo
    a.a8()
    a.lda('#', 0x09); a.sta(0x2105)           # modo 1, BG3 com prioridade alta
    a.lda('#', (VRAM_BG1_MAP >> 10) << 2); a.sta(0x2107)
    a.lda('#', (VRAM_BG3_MAP >> 10) << 2); a.sta(0x2109)
    a.lda('#', VRAM_BG1_TILES >> 12); a.sta(0x210B)
    a.lda('#', VRAM_FONT >> 12); a.sta(0x210C)
    a.lda('#', 0x60 | (VRAM_SPR >> 13)); a.sta(0x2101)  # sprites 16x16 / 32x32
    for reg in (0x210E, 0x2112):              # rolagem vertical = -1
        a.lda('#', 0xFF); a.sta(reg); a.lda('#', 0x03); a.sta(reg)
    a.lda('#', TM_FIELD); a.sta(V['tm_val'])
    a.sta(0x212C)
    a.lda('#', 0x0F); a.sta(V['inidisp'])
    a.rep(0x20)
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])

    # moldura da caixa de texto
    a.ldx('#', 0)
    a.label('cp_box')
    a.lda('box_template', 'x'); a.sta(TXTBUF, 'x')
    a.inx(); a.inx(); a.cpx('#', 512); a.bne('cp_box')

    # OAM: tudo escondido
    a.ldx('#', 0)
    a.label('cp_oam')
    a.lda('#', 0xF000); a.sta(OAM, 'x')       # x=0, y=240
    a.stz(OAM + 2, 'x')
    a.inx(); a.inx(); a.inx(); a.inx()
    a.cpx('#', 512); a.bne('cp_oam')
    a.label('cp_oam_hi')
    a.stz(OAM, 'x'); a.inx(); a.inx()
    a.cpx('#', 544); a.bne('cp_oam_hi')
    a.lda('#', 0x20); a.sta(OAM + 512)        # sprite 2 (Pipo) no tamanho grande 32x32
    a.lda('#', 0xA0); a.sta(OAM + 515)        # 14 e 15 (papai e mamãe) também
    a.stz(V['pslot']); a.stz(V['slot_stage'])
    a.lda('#', 0xFF); a.sta(V['slot_stage1'])

    a.jsr('spc_upload')
    a.lda('#', 0xACE1); a.sta(V['rng'])
    a.lda('#', SPEED_NORMAL); a.sta(V['speed'])
    a.lda('#', TITLE); a.sta(V['level'])     # começa pela abertura
    a.jsr('reset_level')

    a.a8()
    a.lda('#', 1); a.sta(V['text_dirty']); a.sta(V['map_dirty'])
    a.lda('#', 0x81); a.sta(0x4200)           # NMI + leitura automática do controle
    a.rep(0x20)


# ================================================================== LAÇO PRINCIPAL
def emit_main(a):
    a.label('main_loop')
    a.jsr('wait_frame')
    a.jsr('read_joy')
    a.jsr('send_sound')
    a.inc(V['frame_ctr'])
    a.jsr('rand')                             # o sorteio depende de quando se aperta os botões
    a.lda(V['happy']); a.beq('no_happy'); a.dec(V['happy'])
    a.label('no_happy')
    a.lda(V['fx_timer']); a.beq('no_fx'); a.dec(V['fx_timer'])
    a.label('no_fx')
    a.jsr('update_grow')
    a.lda(V['mode']); a.beq('ml_game')
    a.cmp('#', MODE_TITLE); a.bne('ml_intro')
    a.jsr('update_title'); a.bra('ml_draw')
    a.label('ml_intro')
    a.cmp('#', MODE_INTRO); a.bne('ml_end')
    a.jsr('update_intro'); a.bra('ml_draw')
    a.label('ml_end')
    a.jsr('update_ending'); a.bra('ml_draw')
    a.label('ml_game')
    a.lda(V['msg_active']); a.beq('ml_play')
    a.jsr('update_msg')
    a.bra('ml_draw')
    a.label('ml_play')
    a.jsr('update_player')
    a.jsr('update_actors')
    a.label('ml_draw')
    a.jsr('draw_sprites')
    a.jsr('draw_hud')
    a.jsr('draw_frog')
    a.jsr('draw_runners')
    a.jmp('main_loop')

    a.label('wait_frame')
    a.a8(); a.lda('#', 1); a.sta(V['nmi_ready']); a.rep(0x20)
    a.lda(V['nmi_count']); a.sta(V['tmp0'])
    a.label('wf_loop')
    a.wai()
    a.lda(V['nmi_count']); a.cmp(V['tmp0']); a.beq('wf_loop')
    a.rts()

    a.label('read_joy')
    a.a8()
    a.label('rj_wait')
    a.lda(0x4212); a.and_('#', 1); a.bne('rj_wait')
    a.rep(0x20)
    a.lda(0x4218); a.sta(V['joy'])
    a.lda(V['joy_prev']); a.eor('#', 0xFFFF); a.and_(V['joy']); a.sta(V['joy_new'])
    a.lda(V['joy']); a.sta(V['joy_prev'])
    a.rts()

    # ---------------------------------------------------------- abertura
    a.label('update_title')
    a.lda(V['msg_pending']); a.beq('ut_0'); a.jsr('update_msg')
    a.label('ut_0')
    a.inc(V['scr_t'])
    a.lda(V['scr_t']); a.cmp('#', 1000); a.bcc('ut_1')
    a.lda('#', 200); a.sta(V['scr_t'])
    a.label('ut_1')
    a.lda(V['scr_t']); a.cmp('#', 90); a.bcs('ut_after')
    # ovo balançando (qualquer botão pula a animação)
    a.lda(V['joy_new']); a.and_('#', 0xFFF0); a.beq('ut_egg')
    a.lda('#', 89); a.sta(V['scr_t'])
    a.label('ut_egg')
    a.lda(V['py']); a.sta(V['scene_y'])
    a.lda(V['scr_t']); a.cmp('#', 60); a.bcs('ut_crack')
    a.lda('#', A.spr_tile(A.SPR['egg'])); a.sta(V['scene_tile'])
    a.lda(V['scr_t']); a.lsr(); a.lsr(); a.lsr(); a.bra('ut_wob')
    a.label('ut_crack')
    a.bne('ut_crack2')
    sfx(a, 'leaves')                          # crec!
    a.label('ut_crack2')
    a.lda('#', A.spr_tile(A.SPR['egg_crack'])); a.sta(V['scene_tile'])
    a.lda(V['scr_t']); a.lsr()
    a.label('ut_wob')
    a.and_('#', 1); a.asl(); a.clc(); a.adc(V['px']); a.dec(); a.sta(V['scene_x'])
    a.rts()
    a.label('ut_after')
    a.bne('ut_wait')
    # nasceu!
    a.stz(V['hide_player'])
    a.lda('#', A.spr_tile(A.SPR['egg_shell'])); a.sta(V['scene_tile'])
    a.lda(V['px']); a.sta(V['scene_x'])
    a.lda(V['py']); a.clc(); a.adc('#', 3); a.sta(V['scene_y'])
    sfx(a, 'piu')
    a.lda('#', 60); a.sta(V['happy'])
    a.stz(V['menu_page'])
    a.jmp('show_page')

    # show_page: mostra a tela do menu (idioma / som / velocidade) com a opção atual
    a.label('show_page')
    a.lda(V['menu_page']); a.asl(); a.tax()
    a.lda('menu_msg', 'x'); a.jsr('show_msg')
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])
    a.ldx(V['menu_page'])
    a.lda(V['lang']); a.cpx('#', 0); a.beq('sp_set')
    a.lda(V['snd_off']); a.cpx('#', 1); a.beq('sp_set')
    a.lda(V['speed']); a.cpx('#', 2); a.beq('sp_set')
    a.lda(V['trail']); a.cpx('#', 3); a.beq('sp_set')
    a.lda('#', 0)                             # escolha da fase: começa na fase 1
    a.label('sp_set')
    a.sta(V['menu_sel'])
    a.jmp('draw_menu')
    a.label('ut_wait')
    a.lda(V['scr_t']); a.and_('#', 127); a.bne('ut_2')
    a.lda('#', 40); a.sta(V['happy'])
    a.label('ut_2')
    a.lda(V['scr_t']); a.cmp('#', 110); a.jcc('ut_ret')
    a.lda(V['msg_pending']); a.jne('ut_ret')
    # direcional: troca a opção
    a.lda(V['joy_new']); a.and_('#', 0x0F00); a.beq('ut_btn')
    a.ldx(V['menu_page']); a.cpx('#', 2); a.bcs('ut_speed')
    a.lda(V['menu_sel']); a.eor('#', 1); a.sta(V['menu_sel'])
    a.cpx('#', 1); a.bne('ut_note')
    # som: vale na hora (desligado = volume zero; ligado = volume e um "plim")
    a.sta(V['snd_off'])
    a.eor('#', 1); a.ora('#', sound.CMD_MUTE); a.sta(V['snd_req'])
    a.jmp('draw_menu')
    a.label('ut_speed')                       # várias opções: cima/esquerda volta, baixo/direita avança
    a.lda('#', 3); a.cpx('#', 2); a.beq('ut_sp_n')      # velocidade: 3; trilha: 2; fase: as da trilha
    a.lda('#', 2); a.cpx('#', 3); a.beq('ut_sp_n')
    a.lda(V['trail']); a.asl(); a.tax(); a.lda('trail_len', 'x')
    a.label('ut_sp_n')
    a.sta(V['tmp1'])
    a.lda(V['joy_new']); a.and_('#', BTN_UP | BTN_LEFT); a.beq('ut_sp_inc')
    a.lda(V['menu_sel']); a.dec(); a.bpl('ut_sp_ok')
    a.lda(V['tmp1']); a.dec(); a.bra('ut_sp_ok')
    a.label('ut_sp_inc')
    a.lda(V['menu_sel']); a.inc(); a.cmp(V['tmp1']); a.bcc('ut_sp_ok')
    a.lda('#', 0)
    a.label('ut_sp_ok')
    a.sta(V['menu_sel'])
    a.label('ut_note')
    sfx(a, 'note1')
    a.jmp('draw_menu')
    a.label('ut_btn')
    # qualquer outro botão: confirma e vai para a próxima tela (ou começa a fase 1)
    a.lda(V['joy_new']); a.and_('#', BTN_ANY); a.beq('ut_ret')
    a.lda(V['menu_sel'])
    a.ldx(V['menu_page']); a.bne('ut_c1')
    a.sta(V['lang']); a.bra('ut_cdone')
    a.label('ut_c1')
    a.cpx('#', 1); a.bne('ut_c2')
    a.sta(V['snd_off']); a.bra('ut_cdone')
    a.label('ut_c2')
    a.cpx('#', 2); a.bne('ut_c3')
    a.sta(V['speed']); a.bra('ut_cdone')
    a.label('ut_c3')
    a.cpx('#', 3); a.bne('ut_cdone')          # a fase escolhida fica em menu_sel
    a.sta(V['trail'])
    a.label('ut_cdone')
    sfx(a, 'pick')
    a.inc(V['menu_page'])
    a.lda(V['menu_page']); a.cmp('#', len(title.MENU)); a.jcc('show_page')
    a.lda(V['trail']); a.asl(); a.tax()       # a última tela é a da fase (dentro da trilha)
    a.lda(V['menu_sel']); a.clc(); a.adc('trail_base', 'x'); a.sta(V['level'])
    a.jmp('reset_level')
    a.label('ut_ret')
    a.rts()

    # draw_menu: coração ao lado da opção escolhida (dentro da caixa de texto).
    # menu_hpos[(lang*4 + página)*3 + opção] = posição no TXTBUF ($FFFF = não existe)
    a.label('draw_menu')
    a.lda(V['menu_page']); a.cmp('#', 4); a.bne('dm_heart')
    # escolha da fase: em vez do coração, troca a caixa pela do número escolhido
    a.lda('#', MSG['%d_level0' % TITLE]); a.clc(); a.adc(V['menu_sel']); a.jsr('show_msg')
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])
    a.rts()
    a.label('dm_heart')
    a.lda(V['lang']); a.asl(); a.asl(); a.clc(); a.adc(V['menu_page'])
    a.sta(V['tmp0']); a.asl(); a.clc(); a.adc(V['tmp0']); a.sta(V['tmp0'])
    for sel in range(3):                      # apaga os corações da tela
        a.lda(V['tmp0']); a.clc(); a.adc('#', sel); a.asl(); a.tax()
        a.lda('menu_hpos', 'x'); a.bmi('dm_skip_%d' % sel)
        a.tax(); a.lda('#', 0x2400 | A.box_tile('fill'))
        a.sta(TXTBUF, 'x'); a.sta(TXTBUF + 64, 'x')
        a.label('dm_skip_%d' % sel)
    a.lda(V['tmp0']); a.clc(); a.adc(V['menu_sel']); a.asl(); a.tax()
    a.lda('menu_hpos', 'x'); a.tax()
    a.lda('#', 0x2400 | A.box_tile('heart_t')); a.sta(TXTBUF, 'x')
    a.lda('#', 0x2400 | A.box_tile('heart_b')); a.sta(TXTBUF + 64, 'x')
    a.a8(); a.lda('#', 1); a.sta(V['text_dirty']); a.rep(0x20)
    a.rts()

    # ---------------------------------------------------------- tela final
    a.label('update_ending')
    a.lda(V['msg_pending']); a.beq('ue_0'); a.jsr('update_msg')
    a.label('ue_0')
    a.lda(V['level']); a.cmp('#', ENDING2); a.beq('ue_on')   # trilha do pato: sem a cena da coberta
    a.jsr('cut_step')
    a.lda(CUT_DONE); a.bne('ue_on')
    a.rts()                                   # durante a cena: o Pipo só assiste
    a.label('ue_on')
    a.inc(V['scr_t'])
    a.lda(V['scr_t']); a.cmp('#', 30000); a.bcc('ue_1')
    a.lda('#', 1000); a.sta(V['scr_t'])
    a.label('ue_1')
    # a caixa alterna a cada ~4 s: amigos felizes <-> autores
    a.lda(V['scr_t']); a.and_('#', 511); a.cmp('#', 256); a.bne('ue_c1')
    a.lda('#', MSG['%d_credits' % ENDING])
    a.ldx(V['level']); a.cpx('#', ENDING2); a.bne('ue_cr')
    a.lda('#', MSG['%d_credits' % ENDING2])
    a.label('ue_cr')
    a.jsr('show_msg'); a.bra('ue_c2')
    a.label('ue_c1')
    a.cmp('#', 0); a.bne('ue_c2')
    a.lda('#', MSG['%d_box' % ENDING])
    a.ldx(V['level']); a.cpx('#', ENDING2); a.bne('ue_bx')
    a.lda('#', MSG['%d_box' % ENDING2])
    a.label('ue_bx')
    a.jsr('show_msg')
    a.label('ue_c2')
    # botão: volta para a abertura
    a.lda(V['scr_t']); a.cmp('#', 120); a.bcc('ue_walk')
    a.lda(V['msg_pending']); a.bne('ue_walk')
    a.lda(V['joy_new']); a.and_('#', 0xFFF0); a.beq('ue_walk')
    a.lda('#', TITLE); a.sta(V['level'])
    a.jmp('reset_level')
    a.label('ue_walk')
    # o galo passeia sozinho: 6 blocos para a direita, pausa, 6 para a esquerda
    a.lda(V['scr_t']); a.and_('#', 511); a.sta(V['tmp0'])
    a.cmp('#', 48); a.bcs('ue_2')
    a.lda('#', BTN_RIGHT); a.bra('ue_set')
    a.label('ue_2')
    a.cmp('#', 256); a.bcc('ue_none')
    a.cmp('#', 304); a.bcs('ue_none')
    a.lda('#', BTN_LEFT); a.bra('ue_set')
    a.label('ue_none')
    a.lda('#', 0)
    a.label('ue_set')
    a.sta(V['joy'])
    a.lda(V['tmp0']); a.cmp('#', 120); a.beq('ue_crow')
    a.cmp('#', 376); a.bne('ue_go')
    a.label('ue_crow')
    sfx(a, 'crow')
    a.lda('#', 90); a.sta(V['happy'])
    a.stz(V['facing'])
    a.label('ue_go')
    a.jmp('update_player')

    # update_grow: depois de pegar a estrela o Pipo pisca entre o tamanho
    # antigo e o novo; no fim passa a usar o novo
    a.label('update_grow')
    a.lda(V['grow_t']); a.beq('ug_ret')
    a.lda(V['pu_left']); a.bne('ug_ret')      # esperando os gráficos chegarem
    a.dec(V['grow_t'])
    a.lda(V['grow_t']); a.cmp('#', 100); a.bne('ug_1')
    sfx(a, 'grow')
    a.label('ug_1')
    a.lda(V['grow_t']); a.bne('ug_ret')
    a.lda(V['pslot']); a.eor('#', 1); a.sta(V['pslot'])
    a.asl(); a.tax(); a.lda(V['slot_stage'], 'x'); a.cmp('#', growth.STAGES - 1); a.bne('ug_ret')
    sfx(a, 'crow')                            # virou galo!
    a.label('ug_ret')
    a.rts()

    # load_stage: A = estágio, X = área (0/1). Agenda o envio dos gráficos (NMI).
    a.label('load_stage')
    a.stx(V['pu_slot'])
    a.pha()
    a.txa(); a.asl(); a.tax()
    a.pla(); a.sta(V['slot_stage'], 'x')
    a.lda('slot_vram', 'x'); a.sta(V['pu_vaddr'])
    a.lda(V['slot_stage'], 'x'); a.asl(); a.tax()
    a.lda('stage_src', 'x'); a.sta(V['pu_src'])
    a.lda('stage_bank', 'x'); a.sta(V['pu_bank'])
    a.lda('#', 4096); a.sta(V['pu_left'])
    a.rts()

    # envia um pedido de efeito sonoro por quadro
    a.label('send_sound')
    a.lda(V['snd_req']); a.bne('ss_send')
    a.lda(V['song_req']); a.beq('ss_ret')     # troca de música: quando não há efeito na fila
    a.stz(V['song_req'])
    a.label('ss_send')
    a.a8()
    a.sta(0x2141)
    a.inc(V['snd_cnt']); a.lda(V['snd_cnt']); a.sta(0x2140)
    a.rep(0x20)
    a.stz(V['snd_req'])
    a.label('ss_ret')
    a.rts()

    # spc_upload: carrega o driver de som no SPC700 pelo protocolo do IPL
    a.label('spc_upload')
    a.a8()
    a.label('su_wait')
    a.lda(0x2140); a.cmp('#', 0xAA); a.bne('su_wait')
    a.lda(0x2141); a.cmp('#', 0xBB); a.bne('su_wait')
    a.rep(0x20); a.lda('#', sound.ORG); a.sta(0x2142); a.a8()
    a.lda('#', 0x01); a.sta(0x2141)
    a.lda('#', 0xCC); a.sta(0x2140)
    a.label('su_w1')
    a.cmp(0x2140); a.bne('su_w1')
    a.ldx('#', 0)
    a.label('su_loop')
    a.lda('spc_blob', 'x'); a.sta(0x2141)
    a.txa(); a.sta(0x2140)
    a.label('su_w2')
    a.cmp(0x2140); a.bne('su_w2')
    a.inx(); a.cpx('#', ('-', 'spc_end', 'spc_blob')); a.bne('su_loop')
    # executar a partir de ORG
    a.rep(0x20); a.lda('#', sound.ORG); a.sta(0x2142); a.a8()
    a.stz(0x2141)
    a.txa(); a.clc(); a.adc('#', 2); a.bne('su_go'); a.inc()
    a.label('su_go')
    a.sta(0x2140)
    a.label('su_w3')
    a.cmp(0x2140); a.bne('su_w3')
    a.sta(V['snd_cnt'])
    a.rep(0x20)
    a.rts()

    a.label('rand')                           # LFSR de 16 bits
    a.lda(V['rng']); a.lsr(); a.bcc('rnd_ok'); a.eor('#', 0xB400)
    a.label('rnd_ok')
    a.sta(V['rng'])
    a.rts()


# ================================================================== MENSAGENS
def emit_text(a):
    a.label('update_msg')
    # esperando os tiles da mensagem chegarem na VRAM
    a.lda(V['msg_pending']); a.beq('um_shown')
    a.lda(V['up_left']); a.bne('um_done')
    a.stz(V['msg_pending'])
    a.a8()
    a.lda('#', TM_TEXT); a.sta(V['tm_val'])
    a.lda('#', 1); a.sta(V['text_dirty'])
    a.rep(0x20)
    a.rts()
    a.label('um_shown')
    a.dec(V['msg_auto']); a.beq('um_adv')     # passou o tempo: segue sozinho
    a.lda(V['msg_timer']); a.beq('um_ready')
    a.dec(V['msg_timer']); a.rts()
    a.label('um_ready')
    a.lda(V['joy_new']); a.and_('#', BTN_ANY); a.beq('um_done')
    a.label('um_adv')
    a.lda(V['msg_next']); a.cmp('#', 0xFF); a.beq('um_close')
    a.jmp('show_msg_raw')                     # encadeia a próxima (já no idioma certo)
    a.label('um_close')
    a.stz(V['msg_active'])
    a.lda('#', 1); a.sta(V['bump_lock'])
    a.a8(); a.lda('#', TM_FIELD); a.sta(V['tm_val']); a.rep(0x20)
    a.lda(V['reset_after']); a.beq('um_done')
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_next', 'x'); a.sta(V['level'])
    a.jmp('reset_level')
    a.label('um_done')
    a.rts()

    # show_msg: A = número da mensagem. Agenda o envio dos tiles (feito no NMI)
    # e monta o mapa da caixa; a caixa só aparece quando os tiles chegarem.
    a.label('show_msg')                       # A = mensagem em português; soma NPT se inglês
    a.ldx(V['lang']); a.beq('show_msg_raw')
    a.clc(); a.adc('#', NPT)
    a.label('show_msg_raw')                   # A = índice exato da mensagem
    a.asl(); a.tax()
    a.lda('msg_next_tbl', 'x'); a.sta(V['msg_next'])
    a.lda('msg_tsrc', 'x'); a.sta(V['up_src'])
    a.lda('msg_tbank', 'x'); a.sta(V['up_bank'])
    a.lda('#', VRAM_MSG_TILES); a.sta(V['up_vaddr'])
    a.lda('msg_tsize', 'x'); a.sta(V['up_left'])
    a.lda('msg_map_src', 'x'); a.sta(V['lptr'])
    a.lda('msg_tbank', 'x'); a.sta(V['lptr_bank'])
    a.ldy('#', 0)
    a.ldx('#', (1 * 32 + 1) * 2)
    a.lda('#', 6); a.sta(V['tmp2'])
    a.label('sm_row')
    a.lda('#', 30); a.sta(V['tmp1'])
    a.label('sm_col')
    a.lda('[dp],y', V['lptr']); a.sta(TXTBUF, 'x')
    a.iny(); a.iny(); a.inx(); a.inx()
    a.dec(V['tmp1']); a.bne('sm_col')
    a.inx(); a.inx(); a.inx(); a.inx()        # pula as bordas
    a.dec(V['tmp2']); a.bne('sm_row')
    # caixa embaixo, ou em cima se o Pipo estiver na metade de baixo
    a.lda('#', 0x3FF)                         # rolagem -1: linhas 20..27 embaixo
    a.ldx(V['py']); a.cpx('#', 112); a.bcc('sm_pos')
    a.lda('#', 160 - 1)                       # linhas 20..27 aparecem no topo
    a.label('sm_pos')
    a.sta(V['txt_scroll'])
    a.lda('#', 1); a.sta(V['msg_active']); a.sta(V['msg_pending'])
    a.lda('#', 20); a.sta(V['msg_timer'])
    a.lda('#', MSG_AUTO_FRAMES); a.sta(V['msg_auto'])
    a.a8(); a.lda('#', TM_FIELD); a.sta(V['tm_val']); a.rep(0x20)  # esconde até carregar
    a.rts()


# ================================================================== JOGADOR
def emit_player(a):
    a.label('update_player')
    a.lda(V['move_cnt']); a.jeq('up_idle')
    # velocidade escolhida no menu (na tela final o galo anda sempre no normal)
    a.lda(V['mode']); a.cmp('#', MODE_END); a.beq('up_move')
    a.lda(V['speed']); a.asl(); a.tax()
    a.lda(V['spd_acc']); a.clc(); a.adc('speed_inc', 'x')
    a.cmp('#', 256); a.bcs('up_go')
    a.sta(V['spd_acc'])
    a.rts()
    a.label('up_go')
    a.sec(); a.sbc('#', 256); a.sta(V['spd_acc'])

    a.label('up_move')                        # um passo de 2 px
    a.lda(V['move_dir'])
    a.cmp('#', 0); a.bne('up_m1'); a.lda(V['py']); a.clc(); a.adc('#', 2); a.sta(V['py']); a.bra('up_mdone')
    a.label('up_m1')
    a.cmp('#', 1); a.bne('up_m2'); a.lda(V['py']); a.sec(); a.sbc('#', 2); a.sta(V['py']); a.bra('up_mdone')
    a.label('up_m2')
    a.cmp('#', 2); a.bne('up_m3'); a.lda(V['px']); a.sec(); a.sbc('#', 2); a.sta(V['px']); a.bra('up_mdone')
    a.label('up_m3')
    a.lda(V['px']); a.clc(); a.adc('#', 2); a.sta(V['px'])
    a.label('up_mdone')
    # grava a posição no histórico (fila de patinhos)
    a.lda(V['hist_head']); a.inc(); a.and_('#', HIST_LEN - 1); a.sta(V['hist_head'])
    a.asl(); a.tax()
    a.lda(V['px']); a.sta(HIST_X, 'x')
    a.lda(V['py']); a.sta(HIST_Y, 'x')
    a.lda(V['move_cnt']); a.sec(); a.sbc('#', 2); a.sta(V['move_cnt'])
    a.beq('up_step')
    a.rts()
    a.label('up_step')
    a.jmp('on_step')                          # terminou o passo: pisou em algo?

    a.label('up_idle')
    a.lda(V['tx']); a.sta(V['ntx'])
    a.lda(V['ty']); a.sta(V['nty'])
    a.lda(V['joy'])
    a.bit('#', BTN_UP); a.beq('up_d1')
    a.dec(V['nty']); a.lda('#', 1); a.bra('up_dir')
    a.label('up_d1')
    a.bit('#', BTN_DOWN); a.beq('up_d2')
    a.inc(V['nty']); a.lda('#', 0); a.bra('up_dir')
    a.label('up_d2')
    a.bit('#', BTN_LEFT); a.beq('up_d3')
    a.dec(V['ntx']); a.lda('#', 2); a.bra('up_dir')
    a.label('up_d3')
    a.bit('#', BTN_RIGHT); a.beq('up_nodir')
    a.inc(V['ntx']); a.lda('#', 3); a.bra('up_dir')
    a.label('up_nodir')
    a.stz(V['bump_lock'])
    a.rts()

    a.label('up_dir')
    a.sta(V['facing'])
    a.sta(V['tmp3'])
    a.lda(V['nty']); a.asl(); a.asl(); a.asl(); a.asl()
    a.clc(); a.adc(V['ntx']); a.sta(V['target'])
    a.tax(); a.lda(MAPBUF, 'x'); a.and_('#', 0xFF); a.sta(V['cur_mt'])
    a.asl(); a.tax()
    a.lda('mt_solid', 'x'); a.bne('up_blocked')
    a.lda(V['ntx']); a.sta(V['tx'])
    a.lda(V['nty']); a.sta(V['ty'])
    a.lda(V['tmp3']); a.sta(V['move_dir'])
    a.lda('#', 16); a.sta(V['move_cnt'])
    a.stz(V['bump_lock'])
    a.jmp('update_player')                    # já dá o primeiro passo
    a.label('up_blocked')
    a.lda(V['bump_lock']); a.bne('up_ret')
    a.lda('#', 1); a.sta(V['bump_lock'])
    a.jsr('(abs,x)', 'mt_action')             # X = cur_mt*2
    a.label('up_ret')
    a.rts()

    # on_step: o Pipo acabou de chegar num bloco
    a.label('on_step')
    a.lda(V['ty']); a.asl(); a.asl(); a.asl(); a.asl()
    a.clc(); a.adc(V['tx']); a.sta(V['target'])
    a.tax(); a.lda(MAPBUF, 'x'); a.and_('#', 0xFF)
    a.asl(); a.tax()
    a.jmp('(abs,x)', 'mt_step')


# ================================================================== AÇÕES
def emit_actions(a):
    """Ações ao encostar (mt_action) e ao pisar (mt_step). Entram com X = metatile*2."""
    a.label('act_none')
    a.label('step_none')
    a.rts()

    a.label('act_ball')                       # pega o item (ou troca pelo que carrega)
    a.lda('mt_arg', 'x'); a.sta(V['tmp3'])
    a.lda(V['carry']); a.beq('ab_empty')
    a.asl(); a.tax(); a.lda('item_mt', 'x'); a.bra('ab_set')
    a.label('ab_empty')
    a.lda('#', MT['grass'])
    a.label('ab_set')
    a.jsr('set_tile')
    a.lda(V['tmp3']); a.sta(V['carry'])
    a.lda('#', 50); a.sta(V['happy'])
    sfx(a, 'pick')
    a.rts()

    a.label('act_basket')                     # cesta/buraco/bicho/lanterna/ninho: só aceita o item certo
    a.lda('mt_arg', 'x'); a.sta(V['tmp3'])
    a.lda('mt_next', 'x'); a.sta(V['tmp2'])
    a.lda(V['carry']); a.beq('ak_ret')
    a.cmp(V['tmp3']); a.bne('ak_ret')
    a.lda(V['tmp2'])
    a.jsr('set_tile')
    a.jsr('bubble_heart')
    a.stz(V['carry'])
    a.jmp('goal_reached')
    a.label('ak_ret')
    a.rts()

    # bubble_heart: se acima do bloco houver um balão de comida, vira coração
    a.label('bubble_heart')
    a.lda(V['target']); a.sec(); a.sbc('#', 16); a.bcc('bh_ret')
    a.tax(); a.lda(MAPBUF, 'x'); a.and_('#', 0xFF)
    a.cmp('#', MT['bubble_carrot']); a.bcc('bh_ret')
    a.cmp('#', MT['bubble_heart']); a.bcs('bh_ret')
    a.stx(V['target'])
    a.lda('#', MT['bubble_heart']); a.jmp('set_tile')
    a.label('bh_ret')
    a.rts()

    a.label('act_use')                        # ferramenta (regador): não se gasta
    a.lda('mt_arg', 'x'); a.cmp(V['carry']); a.bne('au_ret')
    a.lda('mt_next', 'x'); a.jsr('set_tile')
    a.jsr('fx_at_target')
    sfx(a, 'water')
    a.jmp('goal_quiet')
    a.label('au_ret')
    a.rts()

    a.label('act_bell')                       # sino / flor musical: toca a nota
    a.lda('mt_arg', 'x'); a.sta(V['snd_req'])
    a.lda('#', 30); a.sta(V['happy'])
    a.lda('mt_next', 'x'); a.beq('abl_ret')   # já tocado (ou só flor): não conta
    a.jsr('set_tile')
    a.jmp('goal_quiet')
    a.label('abl_ret')
    a.rts()

    a.label('act_reveal')                     # feno com ovo escondido
    a.lda('mt_arg', 'x'); a.jsr('set_tile')
    sfx(a, 'piu')
    a.jmp('fx_at_target')

    # goal_reached: mais um objetivo cumprido; no último (lvl_goal, quase sempre o 3º) o portão abre
    a.label('goal_reached')
    sfx(a, 'yay')
    a.label('goal_quiet')
    a.inc(V['delivered'])
    a.lda('#', 120); a.sta(V['happy'])
    a.lda(V['level']); a.asl(); a.tax()
    a.lda(V['delivered']); a.cmp('lvl_goal', 'x'); a.bne('gr_ret')
    sfx(a, 'gate')
    a.jmp('open_gate')
    a.label('gr_ret')
    a.rts()

    a.label('act_hide')                       # arbusto com amigo escondido
    a.lda('mt_arg', 'x')
    a.jsr('set_tile')
    a.jsr('fx_at_target')
    a.jmp('goal_reached')

    a.label('act_leaves')                     # arbusto comum: só folhinhas
    sfx(a, 'leaves')
    a.jmp('fx_at_target')

    a.label('act_friend')                     # amigo já achado: o Pipo dá um pulinho
    a.lda('#', 40); a.sta(V['happy'])
    sfx(a, 'piu')
    a.rts()

    a.label('act_quack')                      # o Pato Pateta: quá-quá e um pulinho do Pipo
    a.lda('#', 40); a.sta(V['happy'])
    sfx(a, 'quack')
    a.rts()

    a.label('fx_at_target')
    a.lda(V['target']); a.and_('#', 0x0F); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(V['fx_x'])
    a.lda(V['target']); a.and_('#', 0xF0); a.sta(V['fx_y'])
    a.lda('#', 24); a.sta(V['fx_timer'])
    a.rts()

    a.label('act_mother')                     # mamãe pata recebe os patinhos da fila
    a.lda('mt_arg', 'x'); a.sta(V['tmp3'])    # qual pedaço dela foi tocado (ela ocupa 2x2 blocos)
    a.lda(V['target']); a.and_('#', 0x0F); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(V['mother_x'])
    a.lda(V['target']); a.and_('#', 0xF0); a.sta(V['mother_y'])
    a.lda(V['tmp3']); a.and_('#', 1); a.beq('am_left')
    a.lda(V['mother_x']); a.sec(); a.sbc('#', 16); a.sta(V['mother_x'])
    a.label('am_left')
    a.lda(V['tmp3']); a.and_('#', 2); a.beq('am_top')
    a.lda(V['mother_y']); a.sec(); a.sbc('#', 16); a.sta(V['mother_y'])
    a.label('am_top')
    a.ldx('#', 0)
    a.label('am_loop')
    a.lda(B_ACT, 'x'); a.cmp('#', DUCK_FOLLOW); a.bne('am_next')
    a.lda('#', DUCK_HOME); a.sta(B_ACT, 'x')
    a.lda(V['delivered']); a.asl(); a.tay()
    a.lda(V['mother_x']); a.clc(); a.adc('home_dx', 'y'); a.sta(B_X, 'x')
    a.lda(V['mother_y']); a.clc(); a.adc('home_dy', 'y'); a.sta(B_Y, 'x')
    a.stx(V['ball_i'])
    a.jsr('goal_reached')
    a.ldx(V['ball_i'])
    a.label('am_next')
    a.inx(); a.inx(); a.cpx('#', 6); a.bne('am_loop')
    a.stz(V['followers'])
    a.rts()

    a.label('act_star')
    # o Pipo cresce: carrega o próximo estágio na outra área de sprites
    a.lda(V['pslot']); a.eor('#', 1); a.tax()
    a.lda(V['level']); a.asl(); a.tay()
    a.lda('lvl_stage_next', 'y')
    a.jsr('load_stage')
    a.lda('#', GROW_FRAMES); a.sta(V['grow_t'])
    a.lda('#', 1); a.sta(V['reset_after'])
    a.lda('#', 600); a.sta(V['happy'])
    sfx(a, 'star')
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_star_msg', 'x')
    a.jmp('show_msg')

    a.label('step_button')                    # pisou num botão: aparece a ponte
    a.lda('mt_arg', 'x'); a.sta(V['tmp3'])
    a.lda('mt_next', 'x')
    a.jsr('set_tile')
    a.lda('#', 60); a.sta(V['happy'])
    sfx(a, 'gate')
    a.lda(V['level']); a.asl(); a.sta(V['tmp1']); a.asl(); a.clc(); a.adc(V['tmp1'])
    a.sta(V['tmp1'])                          # fase*6
    a.lda(V['tmp3']); a.dec(); a.asl(); a.clc(); a.adc(V['tmp1']); a.tax()
    a.jmp('(abs,x)', 'lvl_bridge')

    # rotinas geradas por fase: portão e pontes
    a.label('open_gate')
    a.lda(V['level']); a.asl(); a.tax()
    a.jmp('(abs,x)', 'lvl_gate')
    for li, L in enumerate(ALL):
        a.label('open_gate_%d' % li)
        emit_replace(a, L, 'G', 'path')
        for ch, col in zip('xvz', COLORS):
            a.label('open_bridge_%d_%s' % (li, col))
            emit_replace(a, L, ch, 'bridge_' + col)

    # set_tile: A = metatile, target = índice no mapa
    a.label('set_tile')
    a.ldx(V['target'])
    a.a8(); a.sta(MAPBUF, 'x'); a.rep(0x20)
    a.jsr('draw_cell')
    a.a8(); a.lda('#', 1); a.sta(V['map_dirty']); a.rep(0x20)
    a.rts()

    # draw_cell: X = índice no mapa -> escreve 4 entradas no buffer do BG1
    a.label('draw_cell')
    a.lda(MAPBUF, 'x'); a.and_('#', 0xFF)
    a.asl(); a.asl(); a.asl(); a.tay()
    a.txa(); a.and_('#', 0xF0); a.asl(); a.asl(); a.asl(); a.sta(V['tmp1'])
    a.txa(); a.and_('#', 0x0F); a.asl(); a.asl(); a.clc(); a.adc(V['tmp1']); a.tax()
    a.lda('mt_table', 'y'); a.sta(BG1BUF, 'x')
    a.lda(('+', 'mt_table', 2), 'y'); a.sta(BG1BUF + 2, 'x')
    a.lda(('+', 'mt_table', 4), 'y'); a.sta(BG1BUF + 64, 'x')
    a.lda(('+', 'mt_table', 6), 'y'); a.sta(BG1BUF + 66, 'x')
    a.rts()


def emit_replace(a, L, ch, mt_name):
    """Troca todas as letras `ch` do mapa da fase pelo metatile `mt_name`."""
    for y, row in enumerate(L.LEVEL):
        for x, c in enumerate(row):
            if c == ch:
                a.lda('#', y * 16 + x); a.sta(V['target'])
                a.lda('#', MT[mt_name]); a.jsr('set_tile')
    a.rts()


# ================================================================== FASE
def emit_level(a):
    a.label('reset_level')
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_data', 'x'); a.sta(V['ptr'])
    a.ldy('#', 0)
    a.label('rl_copy')
    a.lda('(dp),y', V['ptr']); a.sta(MAPBUF, 'y')
    a.iny(); a.iny(); a.cpy('#', 224); a.bne('rl_copy')
    # fase com sapo: começa arrumada (o sapo vai bagunçar)
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_tidy', 'x'); a.beq('rl_notidy'); a.tax()
    a.label('rl_tidy')
    a.lda(0, 'x'); a.cmp('#', 0xFFFF); a.beq('rl_notidy')
    a.tay(); a.lda(2, 'x')
    a.a8(); a.sta(MAPBUF, 'y'); a.rep(0x20)
    a.inx(); a.inx(); a.inx(); a.inx(); a.bra('rl_tidy')
    a.label('rl_notidy')
    for i in range(3):
        a.stz(R_ON + 2 * i)
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_hide', 'x'); a.beq('rl_nohide')
    a.jsr('hide_friends')
    a.label('rl_nohide')
    a.stz(V['tmp0'])
    a.label('rl_draw')
    a.ldx(V['tmp0']); a.jsr('draw_cell')
    a.inc(V['tmp0']); a.lda(V['tmp0']); a.cmp('#', 224); a.bne('rl_draw')
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_start_x', 'x'); a.sta(V['tx']); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(V['px'])
    a.lda('lvl_start_y', 'x'); a.sta(V['ty']); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(V['py'])
    # crescimento: se ainda estava piscando, já usa o tamanho novo
    a.lda(V['grow_t']); a.beq('rl_nogrow')
    a.stz(V['grow_t'])
    a.lda(V['pslot']); a.eor('#', 1); a.sta(V['pslot'])
    a.label('rl_nogrow')
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_stage', 'x'); a.sta(V['tmp0'])
    a.lda(V['pslot']); a.asl(); a.tax()
    a.lda(V['slot_stage'], 'x'); a.cmp(V['tmp0']); a.beq('rl_stage_ok')
    a.ldx(V['pslot']); a.lda(V['tmp0']); a.jsr('load_stage')
    a.label('rl_stage_ok')
    # paleta (dia/noite)
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_pal', 'x'); a.sta(V['pal_id'])
    a.lda('lvl_song', 'x'); a.cmp(V['song']); a.beq('rl_song_ok')   # música da trilha
    a.sta(V['song']); a.ora('#', sound.CMD_SONG); a.sta(V['song_req'])
    a.label('rl_song_ok')
    a.a8(); a.lda('#', 1); a.sta(V['pal_dirty']); a.rep(0x20)
    for n in ('carry', 'delivered', 'reset_after', 'move_cnt', 'happy', 'facing', 'msg_active',
              'msg_pending', 'fx_timer', 'followers', 'hist_head'):
        a.stz(V[n])
    # histórico começa todo na posição inicial
    a.ldx('#', 0)
    a.label('rl_hist')
    a.lda(V['px']); a.sta(HIST_X, 'x')
    a.lda(V['py']); a.sta(HIST_Y, 'x')
    a.inx(); a.inx(); a.cpx('#', HIST_LEN * 2); a.bne('rl_hist')
    # atores: Y percorre a tabela da fase (3 atores x 3 palavras)
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_spawn_ofs', 'x'); a.tay()
    a.ldx('#', 0)
    a.label('rl_actor')
    a.lda('lvl_spawn', 'y'); a.cmp('#', 0xFF); a.beq('rl_noactor')
    a.sta(V['tmp1'])
    a.lda('#', 1); a.sta(B_ACT, 'x')
    a.lda(V['tmp1']); a.sta(B_TX, 'x'); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(B_X, 'x')
    a.lda(('+', 'lvl_spawn', 2), 'y'); a.sta(B_TY, 'x'); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(B_Y, 'x')
    a.lda(('+', 'lvl_spawn', 4), 'y'); a.sta(B_KIND, 'x')
    a.lda(('+', 'lvl_spawn', 6), 'y'); a.sta(B_ITEM, 'x')
    a.txa(); a.asl(); a.asl(); a.asl(); a.asl(); a.clc(); a.adc('#', 40); a.sta(B_TIM, 'x')
    a.stz(B_MOV, 'x'); a.stz(B_H, 'x')
    a.bra('rl_anext')
    a.label('rl_noactor')
    a.stz(B_ACT, 'x')
    a.label('rl_anext')
    for _ in range(8):
        a.iny()
    a.inx(); a.inx(); a.cpx('#', 6); a.bne('rl_actor')
    a.a8(); a.lda('#', 1); a.sta(V['map_dirty']); a.lda('#', TM_FIELD); a.sta(V['tm_val'])
    a.rep(0x20)
    for i in range(4):                        # esconde a cena final
        a.lda('#', 0xE000); a.sta(OAM + 4 * (CUT_OAM + i))
    # modo: jogo, abertura ou final
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])
    a.stz(V['scr_t']); a.stz(V['hide_player']); a.stz(V['scene_on'])
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_mode', 'x'); a.sta(V['mode'])
    a.bne('rl_screen')
    a.lda('#', 3); a.sta(V['logo_req'])      # jogo: apaga o logotipo do BG3
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_intro', 'x'); a.beq('rl_nointro')
    a.sta(IN_IP)
    a.lda('lvl_in_x', 'x'); a.sta(IN_X)
    a.lda('lvl_in_y', 'x'); a.sta(IN_Y)
    a.stz(IN_HOP); a.stz(IN_REVEAL)
    a.lda('#', 50); a.sta(IN_PAUSE)
    a.lda('#', MODE_INTRO); a.sta(V['mode'])
    a.lda('lvl_in_sfx', 'x'); a.sta(V['snd_req'])
    a.label('rl_nointro')
    a.rts()
    a.label('rl_screen')
    a.cmp('#', MODE_TITLE); a.bne('rl_final')
    a.lda('#', 1); a.sta(V['hide_player']); a.sta(V['scene_on'])
    a.sta(V['logo_req'])                      # logotipo PIPO NO JARDIM
    a.rts()
    a.label('rl_final')
    a.lda(V['level']); a.cmp('#', ENDING2); a.bne('rl_final1')
    # final da trilha do Pato Pateta: sem cena, já mostra o FIM!
    a.lda('#', 1); a.sta(CUT_DONE)
    a.lda(V['lang']); a.asl(); a.clc(); a.adc('#', 2); a.sta(V['logo_req'])   # FIM! / THE END!
    a.lda('#', MSG['%d_box' % ENDING2]); a.jmp('show_msg')
    a.label('rl_final1')
    # começa a cena do papai e da mamãe; o FIM! aparece no fim dela
    a.stz(CUT_T); a.stz(CUT_OFS); a.stz(CUT_EV); a.stz(CUT_DONE)
    # desenhos do papai e da mamãe na área de sprites que o Pipo não está usando
    a.lda(V['pslot']); a.eor('#', 1); a.sta(V['pu_slot']); a.asl(); a.tax()
    a.lda('#', 0xFF); a.sta(V['slot_stage'], 'x')
    a.lda('slot_vram', 'x'); a.sta(V['pu_vaddr'])
    a.lda('slot_tile', 'x'); a.sta(CUT_PB)
    a.lda('#', PARENTS_SRC[1]); a.sta(V['pu_src'])
    a.lda('#', PARENTS_SRC[0]); a.sta(V['pu_bank'])
    a.lda('#', 4096); a.sta(V['pu_left'])
    a.rts()


# ================================================================== ATORES
def emit_actors(a):
    a.label('update_actors')
    a.ldx('#', 0)
    a.label('ua_loop')
    a.stx(V['ball_i'])
    a.lda(B_ACT, 'x'); a.jeq('ua_next')
    a.lda(B_KIND, 'x'); a.cmp('#', KIND_DUCK); a.jeq('ua_duck')

    # ---- bola puladora
    a.lda(B_MOV, 'x'); a.beq('ub_wait')
    a.lda(B_X, 'x'); a.clc(); a.adc(B_DX, 'x'); a.sta(B_X, 'x')
    a.lda(B_Y, 'x'); a.clc(); a.adc(B_DY, 'x'); a.sta(B_Y, 'x')
    a.dec(B_MOV, 'x')
    a.lda(B_MOV, 'x'); a.asl(); a.tay()
    a.lda('arc_table', 'y'); a.sta(B_H, 'x')
    a.bra('ub_catch')
    a.label('ub_wait')
    a.lda(B_TIM, 'x'); a.and_('#', 15); a.asl(); a.tay()
    a.lda('bounce_table', 'y'); a.sta(B_H, 'x')
    a.dec(B_TIM, 'x'); a.bne('ub_catch')
    a.jsr('ball_try_move')
    a.ldx(V['ball_i'])
    a.label('ub_catch')
    a.lda(V['carry']); a.jne('ua_next')
    a.jsr('near_player'); a.jcs('ua_next')
    a.stz(B_ACT, 'x')
    a.lda(B_ITEM, 'x'); a.sta(V['carry'])
    a.lda('#', 50); a.sta(V['happy'])
    sfx(a, 'pick')
    a.jmp('ua_next')

    # ---- patinho
    a.label('ua_duck')
    a.lda(B_ACT, 'x'); a.cmp('#', DUCK_FOLLOW); a.beq('ua_follow')
    a.dec(B_TIM, 'x'); a.lda(B_TIM, 'x'); a.and_('#', 15); a.asl(); a.tay()
    a.lda('bounce_table', 'y'); a.sta(B_H, 'x')
    a.lda(B_ACT, 'x'); a.cmp('#', DUCK_WAIT); a.jne('ua_next')
    a.jsr('near_player'); a.jcs('ua_next')
    a.lda('#', DUCK_FOLLOW); a.sta(B_ACT, 'x')
    a.lda(V['followers']); a.sta(B_SLOT, 'x'); a.inc(V['followers'])
    a.lda('#', 40); a.sta(V['happy'])
    sfx(a, 'piu')
    a.jmp('ua_next')
    a.label('ua_follow')
    a.lda(B_SLOT, 'x'); a.inc(); a.asl(); a.asl(); a.asl(); a.sta(V['tmp1'])   # (slot+1)*8
    a.lda(V['hist_head']); a.sec(); a.sbc(V['tmp1']); a.and_('#', HIST_LEN - 1); a.asl(); a.tay()
    a.lda(HIST_X, 'y'); a.sta(B_X, 'x')
    a.lda(HIST_Y, 'y'); a.sta(B_Y, 'x')
    a.stz(B_H, 'x')

    a.label('ua_next')
    a.ldx(V['ball_i'])
    a.inx(); a.inx(); a.cpx('#', 6); a.jne('ua_loop')
    a.rts()

    # near_player: X = ator*2. Carry limpo se estiver encostado no Pipo.
    a.label('near_player')
    a.lda(B_X, 'x'); a.sec(); a.sbc(V['px']); a.bpl('np_ax')
    a.eor('#', 0xFFFF); a.inc()
    a.label('np_ax')
    a.cmp('#', 12); a.bcs('np_ret')
    a.lda(B_Y, 'x'); a.sec(); a.sbc(V['py']); a.bpl('np_ay')
    a.eor('#', 0xFFFF); a.inc()
    a.label('np_ay')
    a.cmp('#', 12)
    a.label('np_ret')
    a.rts()

    # ball_try_move: sorteia uma direção; pula se o bloco estiver livre
    a.label('ball_try_move')
    a.jsr('rand'); a.and_('#', 3); a.sta(V['tmp3'])
    a.ldx(V['ball_i'])
    a.lda(B_TX, 'x'); a.sta(V['ntx'])
    a.lda(B_TY, 'x'); a.sta(V['nty'])
    a.lda(V['tmp3']); a.asl(); a.tay()
    a.lda(V['ntx']); a.clc(); a.adc('dir_dx', 'y'); a.sta(V['ntx'])
    a.lda(V['nty']); a.clc(); a.adc('dir_dy', 'y'); a.sta(V['nty'])
    a.lda(V['nty']); a.asl(); a.asl(); a.asl(); a.asl(); a.clc(); a.adc(V['ntx']); a.tax()
    a.lda(MAPBUF, 'x'); a.and_('#', 0xFF); a.asl(); a.tax()
    a.lda('mt_solid', 'x'); a.bne('bt_fail')
    a.ldx(V['ball_i'])
    a.lda(V['ntx']); a.sta(B_TX, 'x')
    a.lda(V['nty']); a.sta(B_TY, 'x')
    a.lda('dir_dx', 'y'); a.sta(B_DX, 'x')
    a.lda('dir_dy', 'y'); a.sta(B_DY, 'x')
    a.lda('#', 16); a.sta(B_MOV, 'x')
    a.label('bt_fail')
    a.jsr('rand'); a.and_('#', 63); a.clc(); a.adc('#', 30)
    a.ldx(V['ball_i']); a.sta(B_TIM, 'x')
    a.rts()


# ================================================================== SPRITES
def emit_sprites(a):
    # OAM 0 coração, 1 item carregado, 2 Pipo, 3/4 brilhos, 5-7 atores,
    # 8-10 sombras, 11 folhinhas
    a.label('draw_sprites')
    a.stz(V['hop'])
    a.lda(V['happy']); a.beq('ds_nohop')
    a.lda(V['frame_ctr']); a.and_('#', 15); a.asl(); a.tax()
    a.lda('hop_table', 'x'); a.sta(V['hop'])
    a.label('ds_nohop')
    a.lda(V['move_cnt']); a.beq('ds_idle')
    a.lda(V['frame_ctr']); a.lsr(); a.lsr(); a.lsr(); a.bra('ds_fr')
    a.label('ds_idle')
    a.lda(V['frame_ctr']); a.lsr(); a.lsr(); a.lsr(); a.lsr(); a.lsr()
    a.label('ds_fr')
    a.and_('#', 1); a.sta(V['tmp1'])
    a.lda(V['facing']); a.asl(); a.clc(); a.adc(V['tmp1']); a.asl(); a.tax()
    a.lda('player_frames', 'x'); a.sta(V['tmp2'])    # deslocamento do tile | espelho<<8
    # qual área mostrar (pisca entre as duas enquanto cresce)
    a.ldx(V['pslot'])
    a.lda(V['grow_t']); a.beq('ds_slot')
    a.cmp('#', 100); a.bcs('ds_slot')
    a.lda(V['frame_ctr']); a.and_('#', 4); a.beq('ds_slot')
    a.txa(); a.eor('#', 1); a.tax()
    a.label('ds_slot')
    a.stx(V['tmp3'])
    a.txa(); a.asl(); a.tax()
    a.lda(V['tmp2']); a.and_('#', 0xFF); a.clc(); a.adc('slot_tile', 'x'); a.sta(V['tmp0'])  # tile (9 bits)
    a.lda(V['slot_stage'], 'x'); a.and_('#', 0x0F); a.asl(); a.tax()
    a.lda('head_top', 'x'); a.sta(V['tmp1'])          # topo da cabeça (y relativo a py)
    a.lda(V['carry']); a.asl(); a.tax()
    a.lda('item_tiles', 'x'); a.sta(V['ptr'])
    a.lda('item_attr', 'x'); a.sta(V['cur_mt'])

    a.a8()
    a.lda(V['px']); a.sec(); a.sbc('#', 8); a.sta(OAM + 8)
    a.lda(V['py']); a.sec(); a.sbc('#', 16); a.sec(); a.sbc(V['hop']); a.sta(OAM + 9)
    a.lda(V['tmp0']); a.sta(OAM + 10)
    a.lda(V['tmp0'] + 1); a.and_('#', 1); a.ora('#', 0x20); a.ora(V['tmp2'] + 1); a.sta(OAM + 11)
    # escondido enquanto os gráficos dessa área estão chegando
    a.lda(V['pu_left']); a.ora(V['pu_left'] + 1); a.beq('ds_pvis')
    a.lda(V['pu_slot']); a.cmp(V['tmp3']); a.bne('ds_pvis')
    a.lda('#', 0xE0); a.sta(OAM + 9)          # 224: um sprite de 32 px some por inteiro
    a.label('ds_pvis')
    a.lda(V['hide_player']); a.beq('ds_pshow')
    a.lda('#', 0xE0); a.sta(OAM + 9)
    a.label('ds_pshow')
    # sprite de cena (ovo da abertura)
    a.lda(V['scene_on']); a.beq('ds_noscene')
    a.lda(V['scene_x']); a.sta(OAM + 48)
    a.lda(V['scene_y']); a.sta(OAM + 49)
    a.lda(V['scene_tile']); a.sta(OAM + 50)
    a.lda('#', 0x22); a.sta(OAM + 51)
    a.bra('ds_scene_done')
    a.label('ds_noscene')
    a.lda('#', 0xF0); a.sta(OAM + 49)
    a.label('ds_scene_done')
    # item carregado (OAM 1), em cima da cabeça
    a.lda(V['carry']); a.beq('ds_noball')
    a.lda(V['ptr']); a.sta(OAM + 6)
    a.lda(V['cur_mt']); a.sta(OAM + 7)
    a.lda(V['px']); a.sta(OAM + 4)
    a.lda(V['py']); a.clc(); a.adc(V['tmp1']); a.sec(); a.sbc('#', 16 + 12)
    a.sec(); a.sbc(V['hop']); a.sta(OAM + 5)
    a.bra('ds_ball_done')
    a.label('ds_noball')
    a.lda('#', 0xF0); a.sta(OAM + 5)
    a.label('ds_ball_done')
    # coração + brilhos (OAM 0, 3, 4)
    a.lda(V['happy']); a.beq('ds_nohappy')
    a.lda(V['frame_ctr']); a.lsr(); a.lsr(); a.lsr(); a.and_('#', 3); a.sta(V['tmp2'])
    a.lda(V['px']); a.clc(); a.adc('#', 10); a.sta(OAM + 0)
    a.lda(V['py']); a.clc(); a.adc(V['tmp1']); a.sec(); a.sbc('#', 16 + 10)
    a.sec(); a.sbc(V['tmp2']); a.sta(OAM + 1)
    a.lda('#', A.spr_tile(A.SPR['heart'])); a.sta(OAM + 2)
    a.lda('#', 0x30); a.sta(OAM + 3)
    a.lda(V['frame_ctr']); a.and_('#', 0x08); a.bne('ds_sp2')
    a.lda(V['px']); a.sec(); a.sbc('#', 12); a.sta(OAM + 12)
    a.lda(V['py']); a.sec(); a.sbc('#', 6); a.sta(OAM + 13)
    a.lda('#', 0xF0); a.sta(OAM + 17)
    a.bra('ds_sp_t')
    a.label('ds_sp2')
    a.lda(V['px']); a.clc(); a.adc('#', 14); a.sta(OAM + 16)
    a.lda(V['py']); a.clc(); a.adc('#', 4); a.sta(OAM + 17)
    a.lda('#', 0xF0); a.sta(OAM + 13)
    a.label('ds_sp_t')
    a.lda('#', A.spr_tile(A.SPR['sparkle']))
    a.sta(OAM + 14); a.sta(OAM + 18)
    a.lda('#', 0x30); a.sta(OAM + 15); a.sta(OAM + 19)
    a.bra('ds_fx')
    a.label('ds_nohappy')
    a.lda('#', 0xF0); a.sta(OAM + 1); a.sta(OAM + 13); a.sta(OAM + 17)
    # folhinhas (OAM 11): sobem do bloco
    a.label('ds_fx')
    a.lda(V['fx_timer']); a.beq('ds_nofx')
    a.lda(V['fx_x']); a.sta(OAM + 44)
    a.lda(V['fx_timer']); a.lsr(); a.clc(); a.adc(V['fx_y']); a.sec(); a.sbc('#', 14)
    a.sta(OAM + 45)
    a.lda('#', A.spr_tile(A.SPR['leaves'])); a.sta(OAM + 46)
    a.lda('#', 0x32); a.sta(OAM + 47)
    a.bra('ds_end')
    a.label('ds_nofx')
    a.lda('#', 0xF0); a.sta(OAM + 45)
    a.label('ds_end')
    a.rep(0x20)

    # atores: OAM 5..7, sombras OAM 8..10
    a.ldx('#', 0); a.ldy('#', 0)
    a.label('db_loop')
    a.lda(B_KIND, 'x'); a.cmp('#', KIND_DUCK); a.beq('db_duck')
    a.phy()
    a.lda(B_ITEM, 'x'); a.asl(); a.tay()
    a.lda('item_tiles', 'y'); a.sta(V['tmp0'])
    a.lda('item_attr', 'y'); a.sta(V['tmp1'])
    a.ply()
    a.bra('db_show')
    a.label('db_duck')
    # o patinho olha para o Pipo (os que já estão com a mamãe olham para ela)
    a.lda('#', 0x22); a.sta(V['tmp1'])         # paleta de sprites 1
    a.lda(B_ACT, 'x'); a.cmp('#', DUCK_HOME); a.beq('db_side')
    a.lda(V['px']); a.sec(); a.sbc(B_X, 'x'); a.sta(V['tmp2'])   # dx (Pipo - patinho)
    a.bpl('db_dxp'); a.eor('#', 0xFFFF); a.inc()
    a.label('db_dxp')
    a.sta(V['tmp3'])                           # |dx|
    a.lda(V['py']); a.sec(); a.sbc(B_Y, 'x'); a.sta(V['nty'])    # dy
    a.bpl('db_dyp'); a.eor('#', 0xFFFF); a.inc()
    a.label('db_dyp')
    a.cmp(V['tmp3']); a.bcc('db_horiz'); a.beq('db_horiz')
    # mais longe na vertical: de frente (Pipo embaixo) ou de costas (Pipo em cima),
    # gingando (espelha a cada 8 quadros)
    a.lda(V['frame_ctr']); a.and_('#', 8); a.beq('db_fb0')
    a.lda('#', 0x62); a.sta(V['tmp1'])
    a.label('db_fb0')
    a.lda(V['nty']); a.bmi('db_back')
    a.lda('#', A.spr_tile(A.SPR['duck_front'])); a.bra('db_dt')
    a.label('db_back')
    a.lda('#', A.spr_tile(A.SPR['duck_back'])); a.bra('db_dt')
    a.label('db_horiz')                        # de lado: o desenho olha para a esquerda
    a.lda(V['tmp2']); a.bmi('db_side'); a.beq('db_side')
    a.lda('#', 0x62); a.sta(V['tmp1'])         # Pipo à direita: espelha
    a.label('db_side')
    a.lda(V['frame_ctr']); a.and_('#', 8); a.beq('db_d0')
    a.lda('#', A.spr_tile(A.SPR['duck1'])); a.bra('db_dt')
    a.label('db_d0')
    a.lda('#', A.spr_tile(A.SPR['duck0']))
    a.label('db_dt')
    a.sta(V['tmp0'])
    a.label('db_show')
    a.lda(V['mode']); a.cmp('#', MODE_INTRO); a.bne('db_vis')   # na introdução: só os que o sapo já soltou
    a.lda('bit_tbl', 'x'); a.and_(IN_REVEAL); a.bne('db_vis')
    a.a8(); a.bra('db_hide')
    a.assume(m16=True)
    a.label('db_vis')
    a.lda(B_ACT, 'x')
    a.a8()
    a.beq('db_hide')
    a.lda(B_X, 'x'); a.sta(OAM + 20, 'y'); a.sta(OAM + 32, 'y')
    a.lda(B_Y, 'x'); a.sta(OAM + 33, 'y')
    a.sec(); a.sbc(B_H, 'x'); a.sec(); a.sbc('#', 2); a.sta(OAM + 21, 'y')
    a.lda(V['tmp0']); a.sta(OAM + 22, 'y')
    a.lda(V['tmp1']); a.sta(OAM + 23, 'y')
    a.lda(B_KIND, 'x'); a.bne('db_noshadow')
    a.lda('#', A.spr_tile(A.SPR['shadow'])); a.sta(OAM + 34, 'y')
    a.lda('#', 0x22); a.sta(OAM + 35, 'y')
    a.bra('db_next')
    a.label('db_hide')
    a.lda('#', 0xF0); a.sta(OAM + 21, 'y')
    a.label('db_noshadow')
    a.lda('#', 0xF0); a.sta(OAM + 33, 'y')
    a.label('db_next')
    a.rep(0x20)
    a.iny(); a.iny(); a.iny(); a.iny()
    a.inx(); a.inx(); a.cpx('#', 6); a.jne('db_loop')
    a.rts()


HUD_OAM = 20          # OAM 20-21: número da fase (1 ou 2 algarismos)
HUD_RIGHT_X = 256 - 8 - 14   # x do último algarismo (canto superior direito)
HUD_DIGIT_STEP = 9


def hud_digits():
    """Para cada fase: 2 palavras (posição, tile|atributos) por algarismo; y=$F0 = vazio."""
    out = []
    for lv in range(len(LEVELS)):
        txt = str(trail_pos(lv)[1] + 1)       # número dentro da trilha
        cells = []
        for i, ch in enumerate(txt):
            x = HUD_RIGHT_X - HUD_DIGIT_STEP * (len(txt) - 1 - i)
            cells += [x | (2 << 8), A.hud_tile(ch) | (0x31 << 8)]   # prioridade 3, tiles 256+
        cells += [0xF000, 0] * (2 - len(txt))
        out += cells
    return out


def emit_hud(a):
    # número da fase no canto superior direito (só durante as fases)
    a.label('draw_hud')
    a.lda(V['mode']); a.beq('hud_on')
    a.cmp('#', MODE_INTRO); a.beq('hud_on')
    for i in range(2):
        a.lda('#', 0xF000); a.sta(OAM + 4 * (HUD_OAM + i))
    a.rts()
    a.label('hud_on')
    a.lda(V['level']); a.asl(); a.asl(); a.asl(); a.tax()     # 8 bytes por fase
    for i in range(4):
        a.lda(('+', 'hud_digits', 2 * i), 'x'); a.sta(OAM + 4 * HUD_OAM + 2 * i)
    a.rts()


INTRO_HOP = 16            # quadros de cada pulo do sapo
INTRO_ARC = [round(4 * 12 * t * (INTRO_HOP - t) / INTRO_HOP ** 2) for t in range(INTRO_HOP)]
# como cada coisa estava antes do sapo bagunçar (letra do mapa -> metatile)
CURURU_TIDY = {
    'r': 'grass', 'b': 'grass', 'y': 'grass', '1': 'basketf_r', '2': 'basketf_b', '3': 'basketf_y',
    'c': 'grass', 'q': 'grass', 't': 'grass', '4': 'holef_c', '5': 'holef_s', '6': 'holef_t',
    'h': 'rabbit', 'j': 'bird', 'k': 'hedgehog', 'x': 'bridge_r', 'v': 'bridge_b', 'z': 'bridge_y',
    's': 'bloom_1', 'i': 'bloom_2', 'l': 'bloom_3', 'C': 'grass', 'K': 'grass', 'o': 'grass',
    'A': 'bubble_heart', 'E': 'bubble_heart', 'J': 'bubble_heart', 'L': 'lantern_on', 'N': 'nest_3',
}
CURURU_SFX = {'X': 'bell1', 'Y': 'bell2', 'Z': 'bell3'}


def char_mt(L, c):
    """Metatile de uma letra do mapa (a fase pode ter letras só dela, em CHARS)."""
    return getattr(L, 'CHARS', {}).get(c) or CHAR_MT.get(c)


def tidy_mt(L, ch):
    """Como a letra `ch` estava antes da bagunça (None = igual)."""
    name = getattr(L, 'CHARS', {}).get(ch)
    if name is None:
        return CURURU_TIDY.get(ch)
    if name in MT_NEXT:                                    # casinha: começa cheia
        return MT_NEXT[name]
    if any(name == m for _, m in ITEMS):                   # bloquinho: ainda não estava no chão
        return 'grass'
    return None


def intro_data(L):
    """Roteiro do sapo (ou do Pato Pateta) numa fase: (lista de arrumação, roteiro em
    palavras, início x/y) ou None. Roteiro: por pulo X0 Y0 VX VY (12.4 px) SFX N
    [ÍNDICE MT]*N REVELA PAUSA; fim = $8000.
    Cada parada de CURURU é uma ou mais letras do mapa: ele pula até a 1ª e todas mudam."""
    spots = getattr(L, 'CURURU', None)
    if not spots:
        return None
    vis = visitor(L)
    sfx_step, sfx_last, sfx_home = vis['sfx'][1:]
    local = getattr(L, 'CHARS', {})
    _, spawns = level_bytes(L)
    pos = {}
    for y, row in enumerate(L.LEVEL):
        for x, c in enumerate(row):
            pos.setdefault(c, []).append((x, y))
    seen = {}
    tidy, events = [], []
    for k, spot in enumerate(spots):
        last = k == len(spots) - 1
        if isinstance(spot, tuple):                        # (x, y, 'scare'): assusta os amigos
            x, y, _ = spot
            events.append(((x * 16, y * 16), sfx_last if last else sfx_step, [], SCARE, 90))
            continue
        changes, reveal, land = [], 0, None
        for ch in spot:
            n = seen.get(ch, 0); seen[ch] = n + 1
            x, y = pos[ch][n]
            land = land or (x * 16, y * 16)
            idx = y * 16 + x
            actor = [i for i, sp in enumerate(spawns) if sp[:2] == (x, y)] if ch not in local else []
            if actor:
                reveal |= 1 << actor[0]
                changes.append((idx, MT['grass']))           # só para as folhinhas aparecerem
                continue
            changes.append((idx, MT[char_mt(L, ch)]))
            if tidy_mt(L, ch):
                tidy.append((idx, MT[tidy_mt(L, ch)]))
            if ch in 'AEJ' and ch not in local:            # bichinho embaixo do balão
                below = L.LEVEL[y + 1][x]
                tidy.append((idx + 16, MT[MT_NEXT[CHAR_MT[below]]]))
                changes.append((idx + 16, MT[CHAR_MT[below]]))
        sfx_name = sfx_last if last else CURURU_SFX.get(spot if spot not in local else '', sfx_step)
        events.append((land, sfx_name, changes, reveal, 45 if last else 22))
    home = next((p[0] for c, p in pos.items() if char_mt(L, c) == vis['tile']), None)
    if home:                                               # mora na fase (o sapo, na lagoa)
        hidx = home[1] * 16 + home[0]
        tidy.append((hidx, MT[vis['under']]))
        start = end = (home[0] * 16, home[1] * 16)
        events.append((end, sfx_home, [(hidx, MT[vis['tile']])], 0, 20))
    else:                                                  # vem de fora do jardim, por cima
        start = (events[0][0][0], -40)
        end = (events[-1][0][0], -40)
        events.append((end, None, [], 0, 1))
    words = []
    cur = start
    for target, sfx_name, changes, reveal, pause in events:
        dx, dy = target[0] - cur[0], target[1] - cur[1]
        nh = max(1, -(-int((dx * dx + dy * dy) ** 0.5) // 48))
        for h in range(nh):
            x0, y0 = cur[0] + dx * h / nh, cur[1] + dy * h / nh
            words += [round(x0 * 16), round(y0 * 16),
                      round(dx / nh * 16 / INTRO_HOP), round(dy / nh * 16 / INTRO_HOP)]
            if h < nh - 1:
                words += [0, 0, 0, 3]                      # pulinho no meio do caminho
            else:
                words += [sound.SFX[sfx_name] if sfx_name else 0, len(changes)]
                for i, m in changes:
                    words += [i, m]
                words += [reveal, pause]
        cur = target
    words.append(0x8000)
    return tidy, [w & 0xFFFF for w in words], (round(start[0] * 16) & 0xFFFF, round(start[1] * 16) & 0xFFFF)


def emit_intro(a):
    # update_intro: o sapo pula de lugar em lugar bagunçando a fase
    a.label('update_intro')
    a.jsr('update_runners')
    a.lda(IN_HOP); a.bne('ui_hopping')
    a.dec(IN_PAUSE); a.beq('ui_next')
    a.rts()
    a.label('ui_next')
    a.ldx(IN_IP)
    a.lda(0, 'x'); a.cmp('#', 0x8000); a.beq('ui_end')
    a.sta(IN_X)
    a.lda(2, 'x'); a.sta(IN_Y)
    a.lda(4, 'x'); a.sta(IN_VX)
    a.lda(6, 'x'); a.sta(IN_VY)
    a.txa(); a.clc(); a.adc('#', 8); a.sta(IN_IP)
    a.stz(IN_T)
    a.lda('#', 1); a.sta(IN_HOP)
    sfx(a, 'hop')
    a.rts()
    a.label('ui_end')                          # acabou: mostra o que o sapo fez e começa a fase
    a.stz(V['mode'])
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_intro_msg', 'x')
    a.jmp('show_msg')
    a.label('ui_hopping')
    a.lda(IN_X); a.clc(); a.adc(IN_VX); a.sta(IN_X)
    a.lda(IN_Y); a.clc(); a.adc(IN_VY); a.sta(IN_Y)
    a.inc(IN_T)
    a.lda(IN_T); a.cmp('#', INTRO_HOP); a.beq('ui_land')
    a.rts()
    a.label('ui_land')
    a.stz(IN_HOP)
    a.ldx(IN_IP)
    a.lda(0, 'x'); a.beq('ui_nosfx')
    a.sta(V['snd_req'])
    a.label('ui_nosfx')
    a.lda(2, 'x'); a.sta(IN_CNT)
    a.inx(); a.inx(); a.inx(); a.inx()
    a.label('ui_chg')
    a.lda(IN_CNT); a.beq('ui_chg_done')
    a.lda(0, 'x'); a.sta(V['target'])
    a.lda(2, 'x')
    a.phx(); a.jsr('set_tile'); a.jsr('fx_at_target'); a.plx()
    a.inx(); a.inx(); a.inx(); a.inx()
    a.dec(IN_CNT); a.bra('ui_chg')
    a.label('ui_chg_done')
    a.lda(0, 'x'); a.bit('#', SCARE); a.beq('ui_norun')
    a.phx(); a.jsr('start_runners'); a.plx()
    a.lda(0, 'x')
    a.label('ui_norun')
    a.ora(IN_REVEAL); a.sta(IN_REVEAL)
    a.lda(2, 'x'); a.sta(IN_PAUSE)
    a.inx(); a.inx(); a.inx(); a.inx()
    a.stx(IN_IP)
    a.rts()

    # draw_frog: OAM 12 (só na introdução)
    a.label('draw_frog')
    a.lda(V['mode']); a.cmp('#', MODE_INTRO); a.beq('df_on')
    a.lda('#', 0xF000); a.sta(OAM + 4 * FROG_OAM)
    a.rts()
    a.label('df_on')
    a.lda(IN_X); a.lsr(); a.lsr(); a.lsr(); a.lsr(); a.sta(V['tmp0'])
    a.lda(IN_Y)
    for _ in range(4):
        a.cmp('#', 0x8000); a.ror()            # desloca mantendo o sinal
    a.sta(V['tmp1'])
    a.lda(IN_HOP); a.beq('df_sit')
    a.lda(IN_T); a.asl(); a.tax()
    a.lda(V['tmp1']); a.sec(); a.sbc('intro_arc', 'x'); a.sta(V['tmp1'])
    a.lda('#', 0); a.bra('df_tile')            # pulando
    a.label('df_sit')
    a.lda(V['frame_ctr']); a.and_('#', 16); a.beq('df_s0')
    a.lda('#', 4); a.bra('df_tile')            # rindo
    a.label('df_s0')
    a.lda('#', 2)                              # parado
    a.label('df_tile')
    a.sta(V['tmp2'])
    a.lda(V['level']); a.asl(); a.tax()        # sapo Cururu ou Pato Pateta
    a.lda('lvl_visitor', 'x'); a.clc(); a.adc(V['tmp2']); a.tax()
    a.lda('vis_tiles', 'x')                    # tile | atributos (prioridade 2)
    a.sta(OAM + 4 * FROG_OAM + 2)
    a.a8()
    a.lda(V['tmp0']); a.sta(OAM + 4 * FROG_OAM)
    a.lda(V['tmp1']); a.sta(OAM + 4 * FROG_OAM + 1)
    a.rep(0x20)
    a.rts()


CUT_N, CUT_LOOP = 792, 32       # quadros da cena; os últimos 32 se repetem
CUT_EVENTS = {'sfx': 1, 'msg': 2, 'happy': 3, 'done': 4}


def ending_cutscene():
    """Cena final quadro a quadro: para cada quadro, 4 sprites (coberta, papai,
    mamãe, Cururu) já no formato da OAM (x, y, tile, atributos). Os tiles do papai e
    da mamãe são relativos à área de sprites deles (somada no jogo).
    Devolve (bytes, eventos [(quadro, tipo, valor)])."""
    HIDE = (0, 0xE0, 0, 0)
    fr = [[HIDE] * 4 for _ in range(CUT_N)]

    def spr(x, y, tile, attr):
        return (int(x) & 0xFF, int(y) & 0xFF, tile & 0xFF, attr | (tile >> 8))

    def parent(who, k, x, y, flip=False):
        return spr(x, y, growth.parent_tile(who, k), 0x20 | (0x40 if flip else 0))

    PY = 10 * 16 - 16                  # papai e mamãe com os pés na linha 10
    POPI_X, PIPA_X = 7 * 16, 10 * 16
    BL_X, BL_Y = 144, 150              # coberta entre os dois
    FROG_Y = 11 * 16
    for f in range(CUT_N):
        walk = 2 + (f // 8) % 2        # quadros de lado (desenho olha para a direita)
        idle = (f // 16) % 2
        # ---- papai
        if f >= 40:
            x = max(POPI_X, 255 - (f - 40))
            if x > POPI_X:
                p = parent(0, walk, x, PY, flip=True)
            elif 290 <= f < 420:       # costurando: virado para a mamãe
                p = parent(0, 2 + (f // 12) % 2, x, PY)
            else:
                hop = 3 if 584 <= f < 640 and (f // 6) % 2 else 0
                p = parent(0, idle, x, PY - hop)
            fr[f][1] = p
        # ---- mamãe
        if f >= 88:
            x = max(PIPA_X, 255 - (f - 88))
            if x > PIPA_X:
                p = parent(1, walk, x, PY, flip=True)
            elif 290 <= f < 420:
                p = parent(1, 2 + (f // 12) % 2, x, PY, flip=True)
            else:
                hop = 3 if 590 <= f < 646 and (f // 6) % 2 else 0
                p = parent(1, idle, x, PY - hop)
            fr[f][2] = p
        # ---- coberta
        if 320 <= f < 380:
            fr[f][0] = spr(BL_X, BL_Y, A.hud_tile('blanket_half'), 0x22)
        elif 380 <= f < 560:
            fr[f][0] = spr(BL_X, BL_Y, A.hud_tile('blanket'), 0x22)
        elif 560 <= f < 584:
            fr[f][0] = spr(BL_X, BL_Y + (FROG_Y - BL_Y) * (f - 560) / 24, A.hud_tile('blanket'), 0x22)
        # ---- Cururu: sai da lagoa, pula até perto deles e treme de frio
        if 420 <= f < 584:
            pts = [40, 75, 110, 144]
            x, y, t = pts[0], FROG_Y, A.SPR['frog_sit']
            for i in range(3):
                h0 = 440 + i * 20
                if f >= h0:
                    x = pts[i + 1]
                if h0 <= f < h0 + INTRO_HOP:
                    k = f - h0
                    x = pts[i] + (pts[i + 1] - pts[i]) * k / INTRO_HOP
                    y = FROG_Y - INTRO_ARC[k]
                    t = A.SPR['frog_jump']
            if f >= 500:
                x += (f // 3) % 2      # tremendo de frio
            fr[f][3] = spr(x, y, A.spr_tile(t), 0x22)
        elif f >= 584:                 # enroladinho na coberta
            fr[f][3] = spr(144, FROG_Y, A.hud_tile('frog_wrap%d' % idle), 0x22)
    events = [
        (191, 'sfx', 'yay'), (191, 'happy', 60),
        (196, 'msg', 'parents'),
        (290, 'msg', 'blanket'),
        (320, 'sfx', 'pick'), (350, 'sfx', 'pick'), (380, 'sfx', 'yay'),
        (420, 'sfx', 'croak'), (440, 'sfx', 'hop'), (460, 'sfx', 'hop'), (480, 'sfx', 'hop'),
        (584, 'sfx', 'star'), (584, 'happy', 90),
        (600, 'msg', 'warm'),
        (CUT_N - CUT_LOOP, 'done', 0),
    ]
    out = []
    for f, kind, arg in events:
        if kind == 'sfx':
            arg = sound.SFX[arg]
        elif kind == 'msg':
            arg = MSG['%d_%s' % (ENDING, arg)]
        out.append((f, CUT_EVENTS[kind], arg))
    blob = bytes(b for frame in fr for s4 in frame for b in s4)
    return blob, out


def emit_cutscene(a, cut_addr):
    # cut_step: copia o quadro atual da cena para a OAM e dispara os eventos
    a.label('cut_step')
    a.ldx(CUT_OFS)
    for i in range(4):
        o = OAM + 4 * (CUT_OAM + i)
        a.lda('long', cut_addr + 4 * i, 'x'); a.sta(o)
        a.lda('long', cut_addr + 4 * i + 2, 'x')
        if i in (1, 2):                       # papai e mamãe: soma o início da área deles
            a.clc(); a.adc(CUT_PB)
        a.sta(o + 2)
    a.ldy(CUT_EV)
    a.label('ce_loop')
    a.lda('cut_ev', 'y'); a.cmp(CUT_T); a.bne('ce_done')
    a.lda(('+', 'cut_ev', 2), 'y')
    a.cmp('#', CUT_EVENTS['sfx']); a.bne('ce_1')
    a.lda(('+', 'cut_ev', 4), 'y'); a.sta(V['snd_req']); a.bra('ce_next')
    a.label('ce_1')
    a.cmp('#', CUT_EVENTS['msg']); a.bne('ce_2')
    a.phy(); a.lda(('+', 'cut_ev', 4), 'y'); a.jsr('show_msg'); a.ply(); a.bra('ce_next')
    a.label('ce_2')
    a.cmp('#', CUT_EVENTS['happy']); a.bne('ce_3')
    a.lda(('+', 'cut_ev', 4), 'y'); a.sta(V['happy']); a.bra('ce_next')
    a.label('ce_3')                           # fim da cena: FIM!, amigos felizes, o galo passeia
    a.phy()
    a.lda('#', 1); a.sta(CUT_DONE)
    a.stz(V['scr_t'])
    a.lda(V['lang']); a.asl(); a.clc(); a.adc('#', 2); a.sta(V['logo_req'])   # FIM! / THE END!
    a.lda('#', MSG['%d_box' % ENDING]); a.jsr('show_msg')
    a.ply()
    a.label('ce_next')
    a.iny(); a.iny(); a.iny(); a.iny(); a.iny(); a.iny()
    a.bra('ce_loop')
    a.label('ce_done')
    a.sty(CUT_EV)
    a.inc(CUT_T)
    a.lda(CUT_OFS); a.clc(); a.adc('#', 16); a.sta(CUT_OFS)
    a.lda(CUT_T); a.cmp('#', CUT_N); a.bne('ce_ret')
    a.lda('#', CUT_N - CUT_LOOP); a.sta(CUT_T)
    a.lda('#', (CUT_N - CUT_LOOP) * 16); a.sta(CUT_OFS)
    a.label('ce_ret')
    a.rts()


HIDE_LEVELS = [L for L in LEVELS if getattr(L, 'HIDE_RANDOM', False)]
assert len(HIDE_LEVELS) <= 1
FRIEND_NAMES = ['rabbit_s', 'bird_s', 'hedgehog_s']   # amigo i se esconde no metatile bush_(i+1)


def hide_list(L):
    """Índices no mapa de todos os arbustos (B) da fase."""
    out = [y * 16 + x for y, row in enumerate(L.LEVEL) for x, c in enumerate(row) if c == 'B']
    assert 3 <= len(out) <= 16, 'a fase de esconde-esconde precisa de 3 a 16 arbustos'
    return out


def emit_runners(a):
    # hide_friends: A = endereço da lista de arbustos (quantidade, índices...).
    # Sorteia 3 arbustos diferentes, um para cada amigo, e põe os amigos juntos.
    a.label('hide_friends')
    a.sta(V['tmp3'])
    a.ldy('#', 0)
    a.label('hf_pick')
    a.jsr('rand')
    a.and_('#', 15); a.ldx(V['tmp3']); a.cmp(0, 'x'); a.bcs('hf_pick')
    a.asl(); a.clc(); a.adc(V['tmp3']); a.tax(); a.lda(2, 'x')
    a.cpy('#', 0); a.beq('hf_ok')
    a.cmp(R_DST); a.beq('hf_pick')
    a.cpy('#', 2); a.beq('hf_ok')
    a.cmp(R_DST + 2); a.beq('hf_pick')
    a.label('hf_ok')
    a.sta(R_DST, 'y')
    a.iny(); a.iny(); a.cpy('#', 6); a.bne('hf_pick')
    for i in range(3):
        a.ldx(R_DST + 2 * i)
        a.lda('#', MT['bush_%d' % (i + 1)])
        a.a8(); a.sta(MAPBUF, 'x'); a.rep(0x20)
        a.lda(('+', 'hide_group', 4 * i)); a.sta(R_X + 2 * i)
        a.lda(('+', 'hide_group', 4 * i + 2)); a.sta(R_Y + 2 * i)
        a.lda('#', 1); a.sta(R_ON + 2 * i)
    a.rts()

    # start_runners: o sapo assustou! cada amigo corre para o seu arbusto
    a.label('start_runners')
    for i in range(3):
        a.lda('#', 2); a.sta(R_ON + 2 * i)
        a.lda('#', RUN_FRAMES); a.sta(R_T + 2 * i)
        a.lda(R_X + 2 * i); a.xba(); a.and_('#', 0xFF); a.sta(V['tmp0'])
        a.lda(R_DST + 2 * i); a.and_('#', 0x0F); a.asl(); a.asl(); a.asl(); a.asl()
        a.sec(); a.sbc(V['tmp0']); a.asl(); a.asl(); a.sta(R_VX + 2 * i)
        a.lda(R_Y + 2 * i); a.xba(); a.and_('#', 0xFF); a.sta(V['tmp0'])
        a.lda(R_DST + 2 * i); a.and_('#', 0xF0)
        a.sec(); a.sbc(V['tmp0']); a.asl(); a.asl(); a.sta(R_VY + 2 * i)
    a.rts()                                   # (o som é a risada do sapo, no mesmo quadro)

    # update_runners: anda; quem chega some no arbusto (com folhinhas)
    a.label('update_runners')
    for i in range(3):
        nxt = 'ur_n%d' % i
        a.lda(R_ON + 2 * i); a.cmp('#', 2); a.bne(nxt)
        a.lda(R_X + 2 * i); a.clc(); a.adc(R_VX + 2 * i); a.sta(R_X + 2 * i)
        a.lda(R_Y + 2 * i); a.clc(); a.adc(R_VY + 2 * i); a.sta(R_Y + 2 * i)
        a.dec(R_T + 2 * i); a.bne(nxt)
        a.stz(R_ON + 2 * i)
        a.lda(R_DST + 2 * i); a.sta(V['target'])
        a.lda('#', MT['bush_%d' % (i + 1)]); a.jsr('set_tile'); a.jsr('fx_at_target')
        sfx(a, 'leaves')
        a.label(nxt)
    a.rts()

    # draw_runners: OAM 17-19
    a.label('draw_runners')
    for i in range(3):
        o = OAM + 4 * (RUN_OAM + i)
        hide, done = 'dr_h%d' % i, 'dr_d%d' % i
        a.lda(R_ON + 2 * i); a.beq(hide)
        a.lda(V['frame_ctr']); a.lsr(); a.lsr()
        a.ldx(R_ON + 2 * i); a.cpx('#', 2); a.beq('dr_run%d' % i)
        a.lsr(); a.lsr()                      # parados: pulinhos mais lentos
        a.label('dr_run%d' % i)
        a.and_('#', 1); a.asl(); a.sta(V['tmp0'])    # 0 ou 2 px para cima
        a.lda(R_Y + 2 * i); a.xba(); a.and_('#', 0xFF); a.sec(); a.sbc(V['tmp0']); a.xba()
        a.sta(V['tmp1'])
        a.lda(R_X + 2 * i); a.xba(); a.and_('#', 0xFF); a.ora(V['tmp1'])
        a.sta(o)
        t = A.hud_tile(FRIEND_NAMES[i])
        attr = 0x20 | (0x02 if FRIEND_NAMES[i] in A.HUD_PAL2_CELLS else 0) | (t >> 8)
        a.lda('#', (t & 0xFF) | (attr << 8)); a.sta(o + 2)
        a.bra(done)
        a.label(hide)
        a.lda('#', 0xE000); a.sta(o)
        a.label(done)
    a.rts()


# ================================================================== NMI
def emit_nmi(a):
    a.label('nmi')
    a.rep(0x30)
    a.pha(); a.phx(); a.phy(); a.phb(); a.phd()
    a.phk(); a.plb()
    a.lda('#', 0); a.tcd()
    a.a8()
    a.lda(0x4210)
    a.lda(V['nmi_ready']); a.jeq('nmi_skip')
    a.stz(0x2102); a.stz(0x2103)
    a.rep(0x20)
    dma(a, 0, 0x00, 0x04, OAM, 544)
    a.a8()
    a.lda('#', 0x80); a.sta(0x2115)
    # tiles da mensagem (em pedaços)
    a.rep(0x20)
    a.lda(V['up_left']); a.beq('nmi_noup')
    a.cmp('#', UPLOAD_CHUNK); a.bcc('nmi_upc')
    a.lda('#', UPLOAD_CHUNK)
    a.label('nmi_upc')
    a.sta(V['up_chunk'])
    a.lda(V['up_vaddr']); a.sta(0x2116)
    a.a8()
    a.lda('#', 0x01); a.sta(0x4300)
    a.lda('#', 0x18); a.sta(0x4301)
    a.lda(V['up_bank']); a.sta(0x4304)
    a.rep(0x20)
    a.lda(V['up_src']); a.sta(0x4302)
    a.lda(V['up_chunk']); a.sta(0x4305)
    a.a8(); a.lda('#', 1); a.sta(0x420B); a.rep(0x20)
    a.lda(V['up_src']); a.clc(); a.adc(V['up_chunk']); a.sta(V['up_src'])
    a.lda(V['up_chunk']); a.lsr(); a.clc(); a.adc(V['up_vaddr']); a.sta(V['up_vaddr'])
    a.lda(V['up_left']); a.sec(); a.sbc(V['up_chunk']); a.sta(V['up_left'])
    a.bra('nmi_upd')
    a.label('nmi_noup')
    # gráficos do Pipo (só quando não há texto chegando)
    a.lda(V['pu_left']); a.beq('nmi_upd')
    a.cmp('#', UPLOAD_CHUNK); a.bcc('nmi_puc')
    a.lda('#', UPLOAD_CHUNK)
    a.label('nmi_puc')
    a.sta(V['up_chunk'])
    a.lda(V['pu_vaddr']); a.sta(0x2116)
    a.a8()
    a.lda('#', 0x01); a.sta(0x4300)
    a.lda('#', 0x18); a.sta(0x4301)
    a.lda(V['pu_bank']); a.sta(0x4304)
    a.rep(0x20)
    a.lda(V['pu_src']); a.sta(0x4302)
    a.lda(V['up_chunk']); a.sta(0x4305)
    a.a8(); a.lda('#', 1); a.sta(0x420B); a.rep(0x20)
    a.lda(V['pu_src']); a.clc(); a.adc(V['up_chunk']); a.sta(V['pu_src'])
    a.lda(V['up_chunk']); a.lsr(); a.clc(); a.adc(V['pu_vaddr']); a.sta(V['pu_vaddr'])
    a.lda(V['pu_left']); a.sec(); a.sbc(V['up_chunk']); a.sta(V['pu_left'])
    a.label('nmi_upd')
    a.a8()
    # paleta do cenário (dia/noite)
    a.lda(V['pal_dirty']); a.beq('nmi_nopal')
    a.stz(0x2121)
    a.rep(0x20)
    a.lda(V['pal_id']); a.beq('nmi_pday')
    a.lda('#', 'pal_night'); a.bra('nmi_pset')
    a.label('nmi_pday')
    a.lda('#', 'pal_day')
    a.label('nmi_pset')
    a.sta(V['tmp0'])
    a.sta(0x4302); a.a8(); a.stz(0x4304); a.stz(0x4300)
    a.lda('#', 0x22); a.sta(0x4301); a.rep(0x20)
    a.lda('#', 2); a.sta(0x4305)
    a.a8(); a.lda('#', 1); a.sta(0x420B)
    a.lda('#', 16); a.sta(0x2121)
    a.rep(0x20)
    a.lda(V['tmp0']); a.clc(); a.adc('#', 2); a.sta(0x4302)
    a.lda('#', 64); a.sta(0x4305)
    a.a8(); a.lda('#', 1); a.sta(0x420B)
    a.stz(V['pal_dirty'])
    a.label('nmi_nopal')
    # logotipo no BG3 (linhas 1..8): 1 título, 2 FIM!, 3 apagar, 4 THE END!
    a.lda(V['logo_req']); a.beq('nmi_nologo')
    a.rep(0x20)
    a.lda('#', VRAM_BG3_MAP + 32); a.sta(0x2116)
    a.lda(V['logo_req']); a.asl(); a.tax()
    a.lda('logo_src', 'x'); a.sta(0x4302)
    a.lda('logo_dma', 'x')
    a.a8()
    a.sta(0x4300)
    a.lda('#', 0x18); a.sta(0x4301); a.stz(0x4304)
    a.rep(0x20); a.lda('#', 512); a.sta(0x4305)
    a.a8(); a.lda('#', 1); a.sta(0x420B)
    a.stz(V['logo_req'])
    a.label('nmi_nologo')
    a.lda(V['map_dirty']); a.beq('nmi_nomap')
    a.rep(0x20); a.lda('#', VRAM_BG1_MAP); a.sta(0x2116)
    dma(a, 0, 0x01, 0x18, BG1BUF, 2048)
    a.a8(); a.stz(V['map_dirty'])
    a.label('nmi_nomap')
    a.lda(V['text_dirty']); a.beq('nmi_notext')
    a.rep(0x20); a.lda('#', VRAM_TEXT_ROWS); a.sta(0x2116)
    dma(a, 0, 0x01, 0x18, TXTBUF, 512)
    a.a8(); a.stz(V['text_dirty'])
    a.label('nmi_notext')
    a.lda(V['txt_scroll']); a.sta(0x2112)
    a.lda(V['txt_scroll'] + 1); a.sta(0x2112)
    a.lda(V['tm_val']); a.sta(0x212C)
    a.lda(V['inidisp']); a.sta(0x2100)
    a.stz(V['nmi_ready'])
    a.label('nmi_skip')
    a.rep(0x30)
    a.inc(V['nmi_count'])
    a.pld(); a.plb(); a.ply(); a.plx(); a.pla()
    a.rti()

    a.label('irq')
    a.rti()


# ================================================================== DADOS
def emit_data(a, mt_table, msgs, msg_src, stage_src, logo_maps):
    a.label('zero_word'); a.word(0)
    solid, action, arg, step = metatile_rules()
    a.label('mt_action'); a.word(*action)
    a.label('mt_step'); a.word(*step)
    a.label('mt_solid'); a.word(*solid)
    a.label('mt_arg'); a.word(*arg)
    a.label('mt_table'); a.word(*mt_table)
    a.label('mt_next'); a.word(*[MT[MT_NEXT[n]] if n in MT_NEXT else 0 for n, _, _ in A.METATILES])
    a.label('item_mt'); a.word(0, *[MT[m] for _, m in ITEMS])
    a.label('item_tiles')
    a.word(0, *[sprite_word(n) & 0xFF for n, _ in ITEMS])
    a.label('item_attr')
    a.word(0, *[sprite_word(n) >> 8 for n, _ in ITEMS])
    a.label('vis_tiles')                      # 3 palavras por visitante: pulando, parado, rindo
    for name in VISITOR_ORDER:
        a.word(*[sprite_word(sp) for sp in VISITORS[name]['sprites']])
    a.label('lvl_visitor')
    a.word(*[VISITOR_ORDER.index(getattr(L, 'VISITOR', 'frog')) * 6 for L in ALL])
    a.label('lvl_in_sfx'); a.word(*[sound.SFX[visitor(L)['sfx'][0]] for L in ALL])
    a.label('lvl_goal'); a.word(*[getattr(L, 'GOAL', 3) for L in ALL])
    a.label('lvl_song')                       # cada trilha tem a sua música
    a.word(*([trail_pos(i)[0] for i in range(len(LEVELS))] + [0, 0, 1]))
    a.label('trail_base'); a.word(*TRAIL_BASE)
    a.label('trail_len'); a.word(*[len(t) for t in TRAILS])
    intros = [intro_data(L) if L in LEVELS else None for L in ALL]
    for i, d in enumerate(intros):
        if d:
            a.label('intro_tidy_%d' % i)
            for idx, m in d[0]:
                a.word(idx, m)
            a.word(0xFFFF)
            a.label('intro_script_%d' % i)
            a.word(*d[1])
    a.label('lvl_tidy'); a.word(*[('intro_tidy_%d' % i) if d else 0 for i, d in enumerate(intros)])
    a.label('lvl_intro'); a.word(*[('intro_script_%d' % i) if d else 0 for i, d in enumerate(intros)])
    a.label('lvl_in_x'); a.word(*[d[2][0] if d else 0 for d in intros])
    a.label('lvl_in_y'); a.word(*[d[2][1] if d else 0 for d in intros])
    a.label('lvl_intro_msg')
    a.word(*[MSG['%d_intro' % i] if d else 0 for i, d in enumerate(intros)])
    a.label('intro_arc'); a.word(*INTRO_ARC)
    a.label('hud_digits'); a.word(*hud_digits())
    a.label('cut_ev')
    for f, kind, arg in CUT_EVENT_LIST:
        a.word(f, kind, arg)
    a.word(0xFFFF, 0, 0)
    a.label('bit_tbl'); a.word(1, 2, 4)
    for i, L in enumerate(ALL):
        if L in HIDE_LEVELS:
            lst = hide_list(L)
            a.label('hide_list_%d' % i); a.word(len(lst), *lst)
    a.label('lvl_hide'); a.word(*[('hide_list_%d' % i) if L in HIDE_LEVELS else 0 for i, L in enumerate(ALL)])
    a.label('hide_group')
    grp = HIDE_LEVELS[0].FRIENDS if HIDE_LEVELS else [(0, 0)] * 3
    for x, y in grp:
        a.word(x * 16 * 256, y * 16 * 256)
    a.label('speed_inc')
    a.word(*SPEED_INC)
    a.label('menu_msg')                       # mensagem (em português) de cada tela do menu
    a.word(*[MSG['%d_%s' % (TITLE, pg)] for pg in title.MENU])
    a.label('menu_hpos')
    a.word(*menu_heart_pos())
    a.label('player_frames')
    # ordem: (facing*2 + quadro); facing 0=baixo 1=cima 2=esq 3=dir
    for k, flip in [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0x40), (5, 0x40), (4, 0), (5, 0)]:
        a.word(growth.frame_tile(k) | (flip << 8))
    a.label('slot_tile'); a.word(*STAGE_SLOT_TILE)
    a.label('slot_vram'); a.word(*STAGE_SLOT_VRAM)
    a.label('stage_src'); a.word(*[src for _, src in stage_src])
    a.label('stage_bank'); a.word(*[b for b, _ in stage_src])
    a.label('head_top'); a.word(*([growth.head_top(st) for st in range(growth.STAGES)] + [16] * 4))
    a.label('pal_day')
    a.byte(A.pal_bytes([A.rgb(A.GRASS)] + A.BG_PAL1 + A.BG_PAL2))
    a.label('pal_night')
    a.byte(A.pal_bytes([A.NIGHT_GRASS] + A.NIGHT_PAL1 + A.NIGHT_PAL2))
    a.label('hop_table')
    a.word(*[0, 2, 4, 5, 6, 6, 5, 4, 2, 0, 0, 0, 0, 0, 0, 0])
    a.label('arc_table')    # altura do pulo (índice = quadros restantes)
    a.word(*[0, 3, 5, 7, 9, 10, 11, 12, 12, 12, 11, 10, 9, 7, 5, 3])
    a.label('bounce_table')  # quicadinho parado
    a.word(*[0, 1, 2, 3, 3, 4, 4, 4, 4, 3, 3, 2, 1, 0, 0, 0])
    a.label('dir_dx'); a.word(0, 0, 0xFFFF, 1)    # baixo, cima, esquerda, direita
    a.label('dir_dy'); a.word(1, 0xFFFF, 0, 0)
    # onde os patinhos ficam ao lado da mamãe pata (à esquerda dela, na água)
    a.label('home_dx'); a.word(*[(-v) & 0xFFFF for v in (13, 24, 35)])
    a.label('home_dy'); a.word(13, 19, 13)

    # por fase
    n = len(ALL)
    nl = len(LEVELS)
    a.label('lvl_data'); a.word(*['level_data_%d' % i for i in range(n)])
    a.label('lvl_start_x'); a.word(*[L.START[0] for L in ALL])
    a.label('lvl_start_y'); a.word(*[L.START[1] for L in ALL])
    a.label('lvl_star_msg'); a.word(*[MSG['%d_star1' % i] if i < nl else 0 for i in range(n)])
    a.label('lvl_next'); a.word(*[level_next(i) if i < nl else 0 for i in range(n)])
    a.label('lvl_mode'); a.word(*([MODE_PLAY] * nl + [MODE_TITLE, MODE_END, MODE_END]))
    a.label('lvl_stage')
    a.word(*([stage_for(i) for i in range(nl)] + [0, growth.STAGES - 1, growth.STAGES - 1]))
    a.label('lvl_stage_next'); a.word(*[stage_after(i) for i in range(nl)])
    for i, m in enumerate(logo_maps):
        a.label('logo_map_%d' % i); a.word(*m)
    a.label('logo_src'); a.word(0, 'logo_map_0', 'logo_map_1', 'zero_word', 'logo_map_2')
    a.label('logo_dma'); a.word(0, 0x01, 0x01, 0x09, 0x01)   # 9 = fonte fixa (zera)
    a.label('lvl_gate'); a.word(*['open_gate_%d' % i for i in range(n)])
    a.label('lvl_bridge')
    a.word(*['open_bridge_%d_%s' % (i, c) for i in range(n) for c in COLORS])
    a.label('lvl_pal'); a.word(*[1 if getattr(L, 'NIGHT', False) else 0 for L in ALL])
    a.label('lvl_spawn_ofs'); a.word(*[i * 24 for i in range(n)])
    a.label('lvl_spawn')
    maps = []
    for L in ALL:
        data, spawns = level_bytes(L)
        maps.append(data)
        for k in range(3):
            a.word(*(spawns[k] if k < len(spawns) else (0xFF, 0xFF, 0, 0)))
    for i, data in enumerate(maps):
        a.label('level_data_%d' % i)
        a.byte(data)
    a.align(2)

    # mensagens
    a.label('msg_tsrc'); a.word(*[src for _, src, _, _ in msg_src])
    a.label('msg_tbank'); a.word(*[bank for bank, _, _, _ in msg_src])
    a.label('msg_tsize'); a.word(*[size for _, _, size, _ in msg_src])
    a.label('msg_map_src'); a.word(*[m for _, _, _, m in msg_src])
    a.label('msg_next_tbl')
    a.word(*[MSG[nxt] if nxt else 0xFF for _, _, nxt in MESSAGES])
    a.label('box_template'); a.word(*box_template())
    a.label('palettes'); a.byte(palettes())


# ------------------------------------------------------------------ auxiliares
def dma(a, ch, mode, breg, src, count, bank=0):
    """DMA canal `ch`. Espera A em 16 bits."""
    base = 0x4300 + ch * 0x10
    a.a8()
    a.lda('#', mode); a.sta(base)
    a.lda('#', breg); a.sta(base + 1)
    if bank:
        a.lda('#', bank); a.sta(base + 4)
    else:
        a.stz(base + 4)
    a.rep(0x20)
    a.lda('#', src); a.sta(base + 2)
    a.lda('#', count & 0xFFFF); a.sta(base + 5)
    a.a8()
    a.lda('#', 1 << ch); a.sta(0x420B)
    a.rep(0x20)


def vram_upload(a, vaddr, src, size, bank=0):
    a.lda('#', vaddr); a.sta(0x2116)
    dma(a, 0, 0x01, 0x18, src, size, bank)


def metatile_rules():
    """Por metatile: sólido?, ação ao encostar, argumento, ação ao pisar."""
    rules = {
        'grass': (0, None, 0), 'flowers': (0, None, 0), 'path': (0, None, 0),
        'star': (1, 'star', 0),
        'bush': (1, 'leaves', 0),
        'bush_1': (1, 'hide', MT['rabbit']), 'bush_2': (1, 'hide', MT['bird']),
        'bush_3': (1, 'hide', MT['hedgehog']),
        'rabbit': (1, 'friend', 0), 'bird': (1, 'friend', 0), 'hedgehog': (1, 'friend', 0),
        'mother': (1, 'mother', 0), 'mother_1': (1, 'mother', 1),
        'mother_2': (1, 'mother', 2), 'mother_3': (1, 'mother', 3),
    }
    for i, (_, m) in enumerate(ITEMS):
        if m != 'grass':
            rules[m] = (1, 'ball', i + 1)
    for i, n in enumerate(['basket_r', 'basket_b', 'basket_y', 'hole_c', 'hole_s', 'hole_t']):
        rules[n] = (1, 'basket', i + 1)
    rules.update({
        'rabbit_h': (1, 'basket', ITEM['carrot']), 'hen_h': (1, 'basket', ITEM['corn']),
        'dog_h': (1, 'basket', ITEM['bone']), 'lantern': (1, 'basket', ITEM['firefly']),
        'nest_0': (1, 'basket', ITEM['egg']), 'nest_1': (1, 'basket', ITEM['egg']),
        'nest_2': (1, 'basket', ITEM['egg']),
        'rabbit_f': (1, 'friend', 0), 'hen_f': (1, 'friend', 0), 'dog_f': (1, 'friend', 0),
        'hen': (1, 'friend', 0), 'lantern_on': (1, 'friend', 0),
        'hay': (1, 'leaves', 0), 'hay_egg': (1, 'reveal', MT['egg']),
    })
    for k in '123':
        rules['sprout_' + k] = (1, 'use', ITEM['can'])
        rules['bloom_' + k] = (1, 'friend', 0)
        rules['mflower_' + k] = (1, 'bell', sound.SFX['note' + k])
    for k, c in zip('123', COLORS):
        rules['bell_' + c] = (1, 'bell', sound.SFX['bell' + k])
        rules['bellr_' + c] = (1, 'bell', sound.SFX['bell' + k])
    for i, c in enumerate(COLORS):
        rules['bridge_' + c] = (0, None, 0)
        rules['button_' + c] = (0, None, i + 1)
        rules['buttonp_' + c] = (0, None, 0)
    # trilha do Pato Pateta: casinhas, cartões de bolinhas, botões numerados e o pato
    for sy in A.SYMBOLS:
        rules['slot_' + sy] = (1, 'basket', ITEM['blk_' + sy])
        rules['slotf_' + sy] = (1, 'friend', 0)
    for k in range(1, 6):
        rules['dots_%d' % k] = (1, 'basket', ITEM['blk_%d' % k])
        rules['dotsf_%d' % k] = (1, 'friend', 0)
    for k in (1, 2, 3):
        rules['nbutton_%d' % k] = (0, None, k)
        rules['nbuttonp_%d' % k] = (0, None, 0)
    rules['pato'] = (1, 'quack', 0)
    solid, action, arg, step = [], [], [], []
    for name, _, _ in A.METATILES:
        s, act, ar = rules.get(name, (1, None, 0))   # o resto é só obstáculo
        solid.append(s)
        action.append('act_' + (act or 'none'))
        arg.append(ar)
        step.append('step_button' if name.startswith(('button_', 'nbutton_')) else 'step_none')
    return solid, action, arg, step


CHAR_MT = {
    'T': 'tree', '.': 'grass', ',': 'flowers', '=': 'path', 'W': 'water', 'F': 'frog',
    'B': 'bush', 'f': 'fence', 'G': 'gate', 'r': 'ball_r', 'b': 'ball_b', 'y': 'ball_y',
    '1': 'basket_r', '2': 'basket_b', '3': 'basket_y', 'S': 'sign', 'O': 'rock',
    '*': 'star', 'P': 'flowerbig',
    # fase 3: formas e buracos
    'c': 'shape_c', 'q': 'shape_s', 't': 'shape_t', '4': 'hole_c', '5': 'hole_s', '6': 'hole_t',
    # fase 4: arbustos com amigo
    'h': 'bush_1', 'j': 'bush_2', 'k': 'bush_3',
    # fase 5: água que vira ponte e botões
    'x': 'water_r', 'v': 'water_b', 'z': 'water_y', '7': 'button_r', '8': 'button_b', '9': 'button_y',
    # fase 6: mamãe pata
    'M': 'mother',
    # fase 7: regador (R), brotinhos (s)
    'R': 'can', 's': 'sprout_1', 'i': 'sprout_2', 'l': 'sprout_3',
    # fase 8: comidas e bichinhos com fome (o balão fica no bloco de cima)
    'C': 'carrot', 'K': 'corn', 'o': 'bone', 'a': 'rabbit_h', 'g': 'hen_h', 'D': 'dog_h',
    'A': 'bubble_carrot', 'E': 'bubble_corn', 'J': 'bubble_bone',
    # fase 9: lanternas
    'L': 'lantern',
    # fase 10: sinos e flores musicais
    'X': 'bell_r', 'Y': 'bell_b', 'Z': 'bell_y', 'm': 'mflower_1', 'n': 'mflower_2', 'p': 'mflower_3',
    # fase 11: feno, feno com ovo, ninho, galinha
    'H': 'hay', 'e': 'hay_egg', 'N': 'nest_0', 'Q': 'hen',
    # tela final
    '(': 'bloom_1', ')': 'bloom_2', '[': 'bloom_3', '&': 'rabbit_f', '%': 'dog_f',
    '$': 'bubble_heart', '@': 'nest_3',
}


def stage_for(i):
    """Tamanho do Pipo no começo da fase i (0 = pintinho no começo de cada trilha)."""
    t, k = trail_pos(i)
    return round(k * (growth.STAGES - 1) / len(TRAILS[t]))


def stage_after(i):
    """Tamanho do Pipo depois da estrela da fase i (depois da última da trilha = galo)."""
    t, k = trail_pos(i)
    return round((k + 1) * (growth.STAGES - 1) / len(TRAILS[t]))


def menu_heart_pos():
    """Posição (byte no TXTBUF) do coração ao lado de cada opção do menu, na
    ordem [idioma][página][opção]; $FFFF onde a opção não existe."""
    font = A._font()
    out = []
    for lang in (LANG_PT, LANG_EN):
        for page in title.MENU[:4]:           # a tela da fase não tem coração
            lines = MESSAGES[MSG['%d_%s' % (TITLE, page)] + (NPT if lang else 0)][1]
            for i in range(3):
                if i >= len(lines):
                    out.append(0xFFFF); continue
                x = 120 - font.getlength(lines[i]) / 2 - 12   # 120 = centro da área de texto
                col = max(0, int(x // 8))
                row = 1 + (3 - len(lines)) + 2 * i            # linha da caixa (igual a render_message)
                out.append((row * 32 + 1 + col) * 2)
    return out


def stage_tiles(stage):
    """Gráficos de um estágio do Pipo: 128 tiles 4bpp na ordem da VRAM."""
    sheet = growth.stage_sheet(stage)
    return b''.join(A.tile_4bpp(sheet, tx * 8, ty * 8) for ty in range(8) for tx in range(16))


def level_bytes(L):
    """Retorna (mapa em bytes, [(x, y, tipo, item)] dos atores)."""
    lv = L.LEVEL
    assert len(lv) == 14 and all(len(r) == 16 for r in lv), 'mapa deve ser 16x14: %s' % L.__name__
    bouncy = getattr(L, 'BOUNCY', False)
    local = getattr(L, 'CHARS', {})           # letras só desta fase (valem antes das outras)
    out, spawns = bytearray(), []
    for y, row in enumerate(lv):
        for x, c in enumerate(row):
            if c in local:
                out.append(MT[local[c]])
                continue
            if bouncy and c in 'rby':
                spawns.append(((x, y, KIND_BALL, 'rby'.index(c) + 1), 'rby'.index(c)))
                c = '.'
            elif c == 'd':
                spawns.append(((x, y, KIND_DUCK, 0), len(spawns)))
                c = '.'
            elif c == 'u':
                spawns.append(((x, y, KIND_FLY, ITEM['firefly']), len(spawns)))
                c = '.'
            assert c in CHAR_MT, 'letra desconhecida %r em %s' % (c, L.__name__)
            out.append(MT[CHAR_MT[c]])
    # a mamãe pata é grande: o M é o canto de cima à esquerda de um bloco 2x2
    for y, row in enumerate(lv):
        for x, c in enumerate(row):
            if c == 'M' and 'M' not in local:
                for part, (dx, dy) in enumerate([(1, 0), (0, 1), (1, 1)], 1):
                    assert lv[y + dy][x + dx] == 'W', 'a mamãe pata precisa de 2x2 de água'
                    out[(y + dy) * 16 + x + dx] = MT['mother_%d' % part]
    assert len(spawns) <= 3
    # bolas na ordem vermelha, azul, amarela (o ator i carrega o item i+1)
    spawns = [s for s, _ in sorted(spawns, key=lambda t: t[1])]
    return bytes(out), spawns


def box_template():
    pal = 0x2400  # prioridade + paleta 1
    t = A.box_tile
    rows = []
    rows.append([t('tl')] + [t('top')] * 30 + [t('tr')])
    for _ in range(6):
        rows.append([t('left')] + [t('fill')] * 30 + [t('right')])
    rows.append([t('bl')] + [t('bottom')] * 28 + [t('arrow'), t('bottom'), t('br')])
    return [pal | v for r in rows for v in r]


def palettes():
    cg = [(0, 0, 0)] * 256
    cg[0] = A.rgb(A.GRASS)
    cg[4:8] = A.TEXT_PAL
    cg[16:32] = A.BG_PAL1
    cg[32:48] = A.BG_PAL2
    cg[128:144] = A.SPR_PAL
    cg[144:160] = A.SPR_PAL2
    cg[8:12] = A.LOGO_PAL
    return A.pal_bytes(cg)


def finish_rom(code, banks, a):
    rom = bytearray(NBANKS * 0x8000)  # 512 KB = bancos 0..15
    rom[0:len(code)] = code
    for b, data in banks.items():
        rom[b * 0x8000:b * 0x8000 + len(data)] = data
    h = 0x7FC0
    rom[h:h + 21] = b'PIPO NO JARDIM'.ljust(21)
    rom[h + 0x15] = 0x20   # LoROM
    rom[h + 0x16] = 0x00   # só ROM
    rom[h + 0x17] = 0x09   # 512 KB
    rom[h + 0x18] = 0x00   # sem SRAM
    rom[h + 0x19] = 0x01   # NTSC
    rom[h + 0x1A] = 0x00
    rom[h + 0x1B] = 0x00
    nmi, irq, reset = a.labels['nmi'], a.labels['irq'], a.labels['reset']
    vec = {0x7FE4: irq, 0x7FE6: irq, 0x7FE8: irq, 0x7FEA: nmi, 0x7FEE: irq,
           0x7FF4: irq, 0x7FF8: irq, 0x7FFA: nmi, 0x7FFC: reset, 0x7FFE: irq}
    for off, v in vec.items():
        rom[off:off + 2] = v.to_bytes(2, 'little')
    rom[h + 0x1C:h + 0x20] = b'\xFF\xFF\x00\x00'
    s = sum(rom) & 0xFFFF
    rom[h + 0x1C:h + 0x1E] = (s ^ 0xFFFF).to_bytes(2, 'little')
    rom[h + 0x1E:h + 0x20] = s.to_bytes(2, 'little')
    return bytes(rom)


if __name__ == '__main__':
    rom, a, end, usage = build()
    out = os.path.join(ROOT, 'pipo.sfc')
    with open(out, 'wb') as f:
        f.write(rom)
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    with open(os.path.join(ROOT, 'build', 'pipo.sym'), 'w') as f:
        for k, v in sorted(a.labels.items(), key=lambda kv: kv[1]):
            f.write('%04X %s\n' % (v, k))
    print('ok: %s' % out)
    print('  banco 0 (código): $8000-$%04X | bancos 1-%d: %s bytes de 32768'
          % (end, NBANKS - 1, ', '.join('%d' % usage[b] for b in range(1, NBANKS))))

#!/usr/bin/env python3
"""Gera pipo.sfc — "Pipo no Jardim", jogo de SNES para crianças pequenas.

    python3 build.py

Não precisa de nenhum assembler externo: o código 65816 é escrito com a DSL de
tools/asm65816.py e os gráficos são gerados por tools/assets.py.
As fases ficam em level1.py ... level6.py.
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
import level11  # noqa: E402
import title  # noqa: E402
import ending  # noqa: E402

# ordem das fases (depois da última volta para a primeira)
LEVELS = [level1, level2, level3, level4, level5, level6, level7, level8, level9, level10, level11]
SCREENS = [title, ending]          # abertura e tela final usam a mesma estrutura de mapa
ALL = LEVELS + SCREENS
TITLE, ENDING = len(LEVELS), len(LEVELS) + 1
MODE_PLAY, MODE_TITLE, MODE_END = 0, 1, 2

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
           'mode scr_t hide_player scene_on scene_x scene_y scene_tile logo_req lang menu_sel '
           'lptr lptr_bank').split():
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

MT = A.MT
COLORS = 'rby'
# itens carregáveis (número = posição + 1): (sprite, metatile no chão)
ITEMS = [('ball_r', 'ball_r'), ('ball_b', 'ball_b'), ('ball_y', 'ball_y'),
         ('shape_c', 'shape_c'), ('shape_s', 'shape_s'), ('shape_t', 'shape_t'),
         ('can', 'can'), ('carrot', 'carrot'), ('corn', 'corn'), ('bone', 'bone'),
         ('firefly', 'grass'), ('egg', 'egg')]
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
    banks = {b: bytearray() for b in range(1, 8)}
    gfx = {}
    for name, blob in (('bg_tiles', bg_tiles), ('box_tiles', box_tiles), ('spr_tiles', spr_tiles),
                       ('logo_tiles', logo_tiles)):
        gfx[name] = 0x8000 + len(banks[1])
        banks[1] += blob
    gfx['logo_size'] = len(logo_tiles)
    stage_src = []
    for st in range(growth.STAGES):
        blob = stage_tiles(st)
        bank = next(b for b in range(2, 8) if len(banks[b]) + len(blob) <= 0x8000)
        stage_src.append((bank, 0x8000 + len(banks[bank])))
        banks[bank] += blob
    msg_src = []
    for tiles, m in msgs:
        mapb = b''.join((0x2400 | t).to_bytes(2, 'little') for t in m)   # prioridade + paleta 1
        blob = mapb + tiles
        bank = next(b for b in range(1, 8) if len(banks[b]) + len(blob) <= 0x8000)
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
    a.stz(V['pslot']); a.stz(V['slot_stage'])
    a.lda('#', 0xFF); a.sta(V['slot_stage1'])

    a.jsr('spc_upload')
    a.lda('#', 0xACE1); a.sta(V['rng'])
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
    a.lda(V['happy']); a.beq('no_happy'); a.dec(V['happy'])
    a.label('no_happy')
    a.lda(V['fx_timer']); a.beq('no_fx'); a.dec(V['fx_timer'])
    a.label('no_fx')
    a.jsr('update_grow')
    a.lda(V['mode']); a.beq('ml_game')
    a.cmp('#', MODE_TITLE); a.bne('ml_end')
    a.jsr('update_title'); a.bra('ml_draw')
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
    a.lda('#', MSG['%d_lang' % TITLE]); a.jsr('show_msg_raw')
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])
    a.lda(V['lang']); a.sta(V['menu_sel'])
    a.jmp('draw_menu')
    a.label('ut_wait')
    a.lda(V['scr_t']); a.and_('#', 127); a.bne('ut_2')
    a.lda('#', 40); a.sta(V['happy'])
    a.label('ut_2')
    a.lda(V['scr_t']); a.cmp('#', 110); a.bcc('ut_ret')
    a.lda(V['msg_pending']); a.bne('ut_ret')
    # direcional: troca o idioma
    a.lda(V['joy_new']); a.and_('#', 0x0F00); a.beq('ut_btn')
    a.lda(V['menu_sel']); a.eor('#', 1); a.sta(V['menu_sel'])
    sfx(a, 'note1')
    a.jmp('draw_menu')
    a.label('ut_btn')
    # qualquer outro botão: confirma e começa a fase 1
    a.lda(V['joy_new']); a.and_('#', BTN_ANY); a.beq('ut_ret')
    a.lda(V['menu_sel']); a.sta(V['lang'])
    sfx(a, 'pick')
    a.stz(V['level'])
    a.jmp('reset_level')
    a.label('ut_ret')
    a.rts()

    # draw_menu: coração ao lado do idioma escolhido (dentro da caixa de texto)
    a.label('draw_menu')
    hx = menu_heart_cols()
    for sel in (0, 1):
        top = ((2 + 2 * sel) * 32 + 1 + hx[sel]) * 2
        lbl_off = 'dm_off_%d' % sel
        lbl_done = 'dm_done_%d' % sel
        a.lda(V['menu_sel']); a.cmp('#', sel); a.bne(lbl_off)
        a.lda('#', 0x2400 | A.box_tile('heart_t')); a.sta(TXTBUF + top)
        a.lda('#', 0x2400 | A.box_tile('heart_b')); a.sta(TXTBUF + top + 64)
        a.bra(lbl_done)
        a.label(lbl_off)
        a.lda('#', 0x2400 | A.box_tile('fill')); a.sta(TXTBUF + top); a.sta(TXTBUF + top + 64)
        a.label(lbl_done)
    a.a8(); a.lda('#', 1); a.sta(V['text_dirty']); a.rep(0x20)
    a.rts()

    # ---------------------------------------------------------- tela final
    a.label('update_ending')
    a.lda(V['msg_pending']); a.beq('ue_0'); a.jsr('update_msg')
    a.label('ue_0')
    a.inc(V['scr_t'])
    a.lda(V['scr_t']); a.cmp('#', 30000); a.bcc('ue_1')
    a.lda('#', 1000); a.sta(V['scr_t'])
    a.label('ue_1')
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
    a.lda(V['snd_req']); a.beq('ss_ret')
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
    a.lda(V['msg_timer']); a.beq('um_ready')
    a.dec(V['msg_timer']); a.rts()
    a.label('um_ready')
    a.lda(V['joy_new']); a.and_('#', BTN_ANY); a.beq('um_done')
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
    a.a8(); a.lda('#', TM_FIELD); a.sta(V['tm_val']); a.rep(0x20)  # esconde até carregar
    a.rts()


# ================================================================== JOGADOR
def emit_player(a):
    a.label('update_player')
    a.lda(V['move_cnt']); a.jeq('up_idle')
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

    # goal_reached: mais um objetivo cumprido; no 3º o portão abre
    a.label('goal_reached')
    sfx(a, 'yay')
    a.label('goal_quiet')
    a.inc(V['delivered'])
    a.lda('#', 120); a.sta(V['happy'])
    a.lda(V['delivered']); a.cmp('#', 3); a.bne('gr_ret')
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

    a.label('fx_at_target')
    a.lda(V['target']); a.and_('#', 0x0F); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(V['fx_x'])
    a.lda(V['target']); a.and_('#', 0xF0); a.sta(V['fx_y'])
    a.lda('#', 24); a.sta(V['fx_timer'])
    a.rts()

    a.label('act_mother')                     # mamãe pata recebe os patinhos da fila
    a.lda(V['target']); a.and_('#', 0x0F); a.asl(); a.asl(); a.asl(); a.asl(); a.sta(V['mother_x'])
    a.lda(V['target']); a.and_('#', 0xF0); a.sta(V['mother_y'])
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
    a.lda(V['level']); a.inc()
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
    a.clc(); a.adc('#', MT['buttonp_r'] - 1)
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
    # modo: jogo, abertura ou final
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])
    a.stz(V['scr_t']); a.stz(V['hide_player']); a.stz(V['scene_on'])
    a.lda(V['level']); a.asl(); a.tax()
    a.lda('lvl_mode', 'x'); a.sta(V['mode'])
    a.bne('rl_screen')
    a.lda('#', 3); a.sta(V['logo_req'])      # jogo: apaga o logotipo do BG3
    a.rts()
    a.label('rl_screen')
    a.cmp('#', MODE_TITLE); a.bne('rl_final')
    a.lda('#', 1); a.sta(V['hide_player']); a.sta(V['scene_on'])
    a.sta(V['logo_req'])                      # logotipo PIPO NO JARDIM
    a.rts()
    a.label('rl_final')
    a.lda(V['lang']); a.asl(); a.clc(); a.adc('#', 2); a.sta(V['logo_req'])   # FIM! / THE END!
    a.lda('#', MSG['%d_box' % ENDING]); a.jsr('show_msg')
    a.lda('#', 0x3FF); a.sta(V['txt_scroll'])
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
    a.lda(V['frame_ctr']); a.and_('#', 8); a.beq('db_d0')
    a.lda('#', A.spr_tile(A.SPR['duck1'])); a.bra('db_dt')
    a.label('db_d0')
    a.lda('#', A.spr_tile(A.SPR['duck0']))
    a.label('db_dt')
    a.sta(V['tmp0'])
    a.lda('#', 0x22); a.sta(V['tmp1'])         # paleta de sprites 1
    a.label('db_show')
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
    a.word(0, *[A.spr_tile(A.SPR[n]) for n, _ in ITEMS])
    a.label('item_attr')
    a.word(0, *[0x22 if n in A.SPR_PAL2_CELLS else 0x20 for n, _ in ITEMS])
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
    a.label('home_dy'); a.word(3, 7, 3)

    # por fase
    n = len(ALL)
    nl = len(LEVELS)
    a.label('lvl_data'); a.word(*['level_data_%d' % i for i in range(n)])
    a.label('lvl_start_x'); a.word(*[L.START[0] for L in ALL])
    a.label('lvl_start_y'); a.word(*[L.START[1] for L in ALL])
    a.label('lvl_star_msg'); a.word(*[MSG['%d_star1' % i] if i < nl else 0 for i in range(n)])
    a.label('lvl_next'); a.word(*[i + 1 if i < nl - 1 else (ENDING if i == nl - 1 else 0) for i in range(n)])
    a.label('lvl_mode'); a.word(*([MODE_PLAY] * nl + [MODE_TITLE, MODE_END]))
    a.label('lvl_stage'); a.word(*(list(range(nl)) + [0, growth.STAGES - 1]))
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
        'mother': (1, 'mother', 0),
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
    solid, action, arg, step = [], [], [], []
    for name, _, _ in A.METATILES:
        s, act, ar = rules.get(name, (1, None, 0))   # o resto é só obstáculo
        solid.append(s)
        action.append('act_' + (act or 'none'))
        arg.append(ar)
        step.append('step_button' if name.startswith('button_') else 'step_none')
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


def menu_heart_cols():
    """Coluna (dentro da área de texto) do coração ao lado de cada idioma."""
    font = A._font()
    cols = []
    for line in title.MESSAGES[0][1]:
        w = font.getlength(line)
        x = 120 - w / 2 - 12            # 120 = centro da área de texto (240 px)
        cols.append(max(0, int(x // 8)))
    return cols


def stage_tiles(stage):
    """Gráficos de um estágio do Pipo: 128 tiles 4bpp na ordem da VRAM."""
    sheet = growth.stage_sheet(stage)
    return b''.join(A.tile_4bpp(sheet, tx * 8, ty * 8) for ty in range(8) for tx in range(16))


def level_bytes(L):
    """Retorna (mapa em bytes, [(x, y, tipo, item)] dos atores)."""
    lv = L.LEVEL
    assert len(lv) == 14 and all(len(r) == 16 for r in lv), 'mapa deve ser 16x14: %s' % L.__name__
    bouncy = getattr(L, 'BOUNCY', False)
    out, spawns = bytearray(), []
    for y, row in enumerate(lv):
        for x, c in enumerate(row):
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
    rom = bytearray(0x40000)  # 256 KB = bancos 0..7
    rom[0:len(code)] = code
    for b, data in banks.items():
        rom[b * 0x8000:b * 0x8000 + len(data)] = data
    h = 0x7FC0
    rom[h:h + 21] = b'PIPO NO JARDIM'.ljust(21)
    rom[h + 0x15] = 0x20   # LoROM
    rom[h + 0x16] = 0x00   # só ROM
    rom[h + 0x17] = 0x08   # 256 KB
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
    print('  banco 0 (código): $8000-$%04X | bancos 1-7: %s bytes de 32768'
          % (end, ', '.join('%d' % usage[b] for b in range(1, 8))))

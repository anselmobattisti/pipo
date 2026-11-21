"""Joga todas as fases no mini-emulador e salva capturas em build/shots.

    python3 tools/test_play.py
"""
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from PIL import Image  # noqa: E402
from emu import SNES, BUTTONS  # noqa: E402
import build as B  # noqa: E402
import sound  # noqa: E402

OUT = os.path.join(ROOT, 'build', 'shots')
DIRS = dict(UP=(0, -1), DOWN=(0, 1), LEFT=(-1, 0), RIGHT=(1, 0))


class Player:
    SOLID = B.metatile_rules()[0]

    def __init__(self, rom):
        self.emu = SNES(rom)
        self.n = 0

    # ---- leitura de memória
    def var(self, name):
        a = B.V[name]
        return self.emu.wram[a] | (self.emu.wram[a + 1] << 8)

    def actor(self, i, field):
        a = getattr(B, 'B_' + field) + i * 2
        return self.emu.wram[a] | (self.emu.wram[a + 1] << 8)

    def tile(self, x, y):
        return self.emu.wram[B.MAPBUF + y * 16 + x]

    def solid(self, x, y):
        return self.SOLID[self.tile(x, y)]

    def sfx_notes(self, since):
        """Notas MIDI tocadas na voz de efeitos (7) desde o índice `since` do log."""
        inv = {sound.pitch_value(n): n for n in range(128)}
        return [inv[p] for _, bits, info in self.emu.spc.kon_log[since:]
                for v, p, _ in info if v == 7]

    def expect_sfx(self, since, name):
        first = sound.EFFECTS[name][0]
        notes = self.sfx_notes(since)
        assert first in notes, 'efeito %r não tocou (notas: %s)' % (name, notes)

    def pos(self):
        return self.var('tx'), self.var('ty')

    # ---- controle
    def frames(self, k, buttons=''):
        mask = 0
        for b in filter(None, buttons.split('+')):
            mask |= BUTTONS[b]
        for _ in range(k):
            self.emu.run_frame(mask)

    def shot(self, name):
        self.n += 1
        path = os.path.join(OUT, '%02d_%s.png' % (self.n, name))
        self.emu.render().resize((512, 448), Image.NEAREST).save(path)

    def go(self, d, n=1):
        dx, dy = DIRS[d]
        goal = (self.var('tx') + dx * n, self.var('ty') + dy * n)
        for _ in range(n * 24 + 8):
            if self.pos() == goal and self.var('move_cnt') == 0:
                break
            self.frames(1, d)
        self.frames(1)
        assert self.pos() == goal, 'não chegou em %s (está em %s)' % (goal, self.pos())

    def first_step(self, goals):
        """BFS até um dos blocos em `goals`; devolve a 1a direção (None se já está)."""
        start = self.pos()
        if start in goals:
            return None
        prev = {start: None}
        q = deque([start])
        while q:
            c = q.popleft()
            if c in goals:
                while prev[c][0] != start:
                    c = prev[c][0]
                return prev[c][1]
            for d, (dx, dy) in DIRS.items():
                n = (c[0] + dx, c[1] + dy)
                if n not in prev and not self.solid(*n):
                    prev[n] = (c, d); q.append(n)
        raise AssertionError('sem caminho de %s até %s' % (start, goals))

    def walk_to(self, x, y):
        while True:
            d = self.first_step({(x, y)})
            if d is None:
                return
            self.go(d)

    def bump(self, d, msg=False):
        self.frames(3, d)
        self.frames(12)
        assert bool(self.var('msg_active')) == msg, 'mensagem inesperada (%s)' % d

    def touch(self, x, y, msg=False):
        """Vai até um vizinho livre do bloco (x, y) e encosta nele."""
        goals = {(x - dx, y - dy): d for d, (dx, dy) in DIRS.items()
                 if not self.solid(x - dx, y - dy)}
        while True:
            d = self.first_step(set(goals))
            if d is None:
                break
            self.go(d)
        self.bump(goals[self.pos()], msg)

    def intro(self, name=None, wait=False):
        """Assiste o sapo Cururu bagunçar a fase e fecha a mensagem dele."""
        lv = self.var('level')
        assert self.var('mode') == B.MODE_INTRO, 'a fase deveria começar com o sapo'
        before = bytes(self.emu.wram[B.MAPBUF:B.MAPBUF + 224])
        who = '_pato' if getattr(B.ALL[lv], 'VISITOR', 'frog') == 'pato' else '_sapo'
        k = len(self.emu.spc.kon_log)
        n = 0
        while self.var('mode') == B.MODE_INTRO:
            self.frames(1); n += 1
            assert n < 3000, 'introdução não terminou'
            if name and n == 120:
                self.shot(name + who)
        assert self.var('msg_active'), 'mensagem do sapo'
        if B.intro_data(B.ALL[lv])[0]:
            assert before != bytes(self.emu.wram[B.MAPBUF:B.MAPBUF + 224]), 'o sapo não mudou nada'
        now = bytes(self.emu.wram[B.MAPBUF:B.MAPBUF + 224])
        if getattr(B.ALL[lv], 'HIDE_RANDOM', False):     # amigos sorteados: contam como arbusto
            hidden = {B.MT['bush_1'], B.MT['bush_2'], B.MT['bush_3']}
            assert sum(c in hidden for c in now) == 3, 'três amigos escondidos'
            now = bytes(B.MT['bush'] if c in hidden else c for c in now)
            assert all(self.emu.wram[B.R_ON + 2 * i] == 0 for i in range(3)), 'amigos sumiram nos arbustos'
        assert now == B.level_bytes(B.ALL[lv])[0], 'depois do sapo a fase deveria ficar como no mapa'
        self.expect_sfx(k, B.visitor(B.ALL[lv])['sfx'][2])     # a risada do sapo / o quá-quá do pato
        self.frames(25)
        if name:
            self.shot(name + who + '_fez')
        if wait:                                         # sem botão: passa sozinho em 5 s
            self.frames(B.MSG_AUTO_FRAMES - 30)
            assert self.var('msg_active'), 'cedo demais'
            self.frames(10)
        else:
            self.frames(2, 'A'); self.frames(3)
        assert not self.var('msg_active') and self.var('mode') == B.MODE_PLAY
        return n

    def stage(self):
        return self.emu.wram[B.V['slot_stage'] + 2 * self.var('pslot')]

    def chase(self, i, item=None):
        item = item or i + 1
        for _ in range(200):
            if self.var('carry'):          # pegou esta ou outra bola no caminho
                return
            d = self.first_step({(self.actor(i, 'TX'), self.actor(i, 'TY'))})
            if d is None:
                self.frames(4)
            else:
                self.go(d)
        raise AssertionError('não conseguiu pegar a bola %d (pipo %s, bola %s/%s px %s,%s, ativa %d, carry %d, modo %d, msg %d)' % (
            i, self.pos(), self.actor(i, 'TX'), self.actor(i, 'TY'), self.actor(i, 'X'), self.actor(i, 'Y'),
            self.actor(i, 'ACT'), self.var('carry'), self.var('mode'), self.var('msg_active')))

    def finish_star(self, level_mod, star, name):
        """Encosta na estrela, passa as mensagens e confere a troca de fase."""
        lv = self.var('level')
        k = len(self.emu.spc.kon_log)
        self.touch(*star, msg=True)
        self.expect_sfx(k, 'star')
        self.frames(12); self.shot(name)
        # o Pipo cresce durante a primeira mensagem
        for _ in range(400):
            if self.var('grow_t') == 0:
                break
            self.frames(1)
        assert self.stage() == B.stage_after(lv), 'não cresceu (estágio %d)' % self.stage()
        self.shot(name + '_cresceu')
        for _ in range(len([m for m in level_mod.MESSAGES if m[0] != 'intro'])):
            self.frames(25); self.frames(2, 'A'); self.frames(1)
        self.frames(8)
        nxt = B.level_next(lv)
        assert self.var('level') == nxt, (self.var('level'), nxt)
        assert self.var('delivered') == 0
        if nxt < len(B.LEVELS):
            assert self.pos() == B.ALL[nxt].START
            t, k = B.trail_pos(nxt)
            self.intro('%s%d' % ('fp'[t], k + 1))
            assert not self.var('msg_active')
        else:                                  # no final o galo já começa a passear
            assert self.var('ty') == B.ALL[nxt].START[1]
        self.frames(2)


def find(level_mod, ch):
    return [(x, y) for y, row in enumerate(level_mod.LEVEL) for x, c in enumerate(row) if c == ch]


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    rom = open(os.path.join(ROOT, 'pipo.sfc'), 'rb').read()
    p = Player(rom)
    MT = B.MT
    # ---------------- abertura
    p.frames(30); p.shot('abertura_ovo')
    assert p.var('mode') == B.MODE_TITLE
    p.frames(40); p.shot('abertura_rachou')
    p.frames(40); p.shot('abertura_titulo')
    assert p.var('msg_active') and not p.var('hide_player'), 'o Pipo deveria ter nascido'
    assert p.var('menu_sel') == B.LANG_PT
    p.frames(2, 'START'); p.frames(6)                   # idioma
    assert p.var('lang') == B.LANG_PT and p.var('menu_page') == 1
    p.shot('menu_som')
    p.frames(2, 'START'); p.frames(6)                   # som
    assert p.var('snd_off') == 0 and p.var('menu_page') == 2
    p.frames(2, 'UP'); p.frames(2)
    assert p.var('menu_sel') == B.SPEED_SLOW
    p.frames(2, 'UP'); p.frames(2)
    assert p.var('menu_sel') == B.SPEED_FAST, 'deveria dar a volta'
    p.frames(2, 'DOWN'); p.frames(2)
    assert p.var('menu_sel') == B.SPEED_SLOW
    p.frames(2, 'DOWN'); p.frames(2)
    assert p.var('menu_sel') == B.SPEED_NORMAL
    p.frames(2, 'LEFT'); p.frames(2); p.frames(2, 'RIGHT'); p.frames(2)
    p.shot('menu_velocidade')
    p.frames(2, 'START'); p.frames(40)                  # velocidade
    assert p.var('speed') == B.SPEED_NORMAL and p.var('menu_page') == 3
    # escolha da trilha: sapo ou Pato Pateta
    assert p.var('menu_sel') == 0
    p.shot('menu_trilha')
    p.frames(2, 'DOWN'); p.frames(4)
    assert p.var('menu_sel') == 1
    p.shot('menu_trilha_pato')
    p.frames(2, 'DOWN'); p.frames(4)
    assert p.var('menu_sel') == 0, 'deveria dar a volta'
    p.frames(2, 'START'); p.frames(40)
    assert p.var('trail') == 0 and p.var('menu_page') == 4
    # escolha da fase: começa na 1, o direcional troca o número e dá a volta
    assert p.var('menu_sel') == 0
    p.shot('menu_fase')
    p.frames(2, 'RIGHT'); p.frames(40); p.frames(2, 'DOWN'); p.frames(40)
    assert p.var('menu_sel') == 2
    p.shot('menu_fase_3')
    for _ in range(3):
        p.frames(2, 'LEFT'); p.frames(40)
    assert p.var('menu_sel') == len(B.TRAILS[0]) - 1, 'deveria dar a volta'
    p.shot('menu_fase_10')
    p.frames(2, 'UP'); p.frames(40); p.frames(2, 'RIGHT'); p.frames(40); p.frames(2, 'RIGHT'); p.frames(40)
    assert p.var('menu_sel') == 0
    p.frames(2, 'START'); p.frames(3)                   # fase 1
    p.intro('f1')
    assert p.var('mode') == B.MODE_PLAY and p.var('level') == 0
    assert not p.var('msg_active')
    p.shot('f1_inicio')
    hud_y = lambda i: p.emu.wram[B.OAM + 4 * (B.HUD_OAM + i) + 1]
    assert hud_y(0) == 2 and hud_y(1) == 0xF0, 'número "1" no canto superior direito'
    assert p.emu.wram[B.OAM + 4 * B.HUD_OAM + 2] == B.A.hud_tile('1') & 0xFF
    assert p.emu.spc.running, 'driver de som não foi carregado'
    p.frames(60)
    kons = p.emu.spc.kon_log
    assert any(info[0][0] == 0 for _, _, info in kons), 'música (melodia) não tocou'
    assert any(any(v == 1 for v, _, _ in info) for _, _, info in kons), 'música (baixo) não tocou'

    # ---------------- fase 1: bolas paradas
    L = B.level1
    k = len(p.emu.spc.kon_log)
    p.touch(*find(L, 'r')[0]); assert p.var('carry') == 1
    p.frames(5); p.expect_sfx(k, 'pick')
    p.touch(*find(L, '2')[0]); assert p.var('delivered') == 0 and p.var('carry') == 1  # cesta errada
    k = len(p.emu.spc.kon_log)
    p.touch(*find(L, '1')[0]); assert p.var('delivered') == 1
    p.frames(5); p.expect_sfx(k, 'yay')
    p.touch(*find(L, 'b')[0]); p.touch(*find(L, '2')[0])
    p.touch(*find(L, 'y')[0])
    k = len(p.emu.spc.kon_log)
    p.touch(*find(L, '3')[0])
    assert p.var('delivered') == 3
    p.frames(5); p.expect_sfx(k, 'gate')
    p.frames(6); p.shot('f1_portao')
    p.finish_star(L, find(L, '*')[0], 'f1_estrela')

    # ---------------- fase 2: bolas puladoras
    L = B.level2
    p.shot('f2_inicio')
    p.frames(90)
    assert any((p.actor(i, 'TX'), p.actor(i, 'TY')) != pos
               for i, pos in enumerate(find(L, 'r') + find(L, 'b') + find(L, 'y'))), 'bolas paradas?'
    p.shot('f2_pulando')
    while p.var('delivered') < 3:      # entrega a bola que estiver carregando
        n = p.var('delivered')
        if not p.var('carry'):
            p.chase(next(i for i in range(3) if p.actor(i, 'ACT')))
        p.touch(*find(L, '123'[p.var('carry') - 1])[0])
        assert p.var('delivered') == n + 1 and not p.var('carry')
    p.finish_star(L, find(L, '*')[0], 'f2_estrela')

    # ---------------- fase 3: formas
    L = B.level3
    p.shot('f3_inicio')
    for item, hole, n in (('c', '4', 4), ('q', '5', 5), ('t', '6', 6)):
        p.touch(*find(L, item)[0]); assert p.var('carry') == n
        if n == 4:
            p.touch(*find(L, '5')[0]); assert p.var('carry') == 4   # buraco errado: nada
            p.frames(4); p.shot('f3_carregando')
        p.touch(*find(L, hole)[0]); assert p.var('carry') == 0
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f3_portao')
    p.finish_star(L, find(L, '*')[0], 'f3_estrela')

    # ---------------- fase 4: esconde-esconde
    L = B.level4
    p.shot('f4_inicio')
    bx, by = next(xy for xy in find(L, 'B') if p.tile(*xy) == MT['bush'])   # arbusto vazio
    k = len(p.emu.spc.kon_log)
    p.touch(bx, by)
    assert p.var('delivered') == 0, 'arbusto vazio não conta'
    p.expect_sfx(k, 'leaves')
    spots = {p.tile(x, y): (x, y) for y in range(14) for x in range(16)}
    for n, friend in ((1, 'rabbit'), (2, 'bird'), (3, 'hedgehog')):
        x, y = spots[MT['bush_%d' % n]]
        p.touch(x, y)
        assert p.tile(x, y) == MT[friend]
        if n == 1:
            p.shot('f4_achou_coelho')
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f4_portao')
    p.finish_star(L, find(L, '*')[0], 'f4_estrela')

    # ---------------- fase 5: botões e pontes
    L = B.level5
    p.shot('f5_inicio')
    for btn, water, col in (('7', 'x', 'r'), ('8', 'v', 'b'), ('9', 'z', 'y')):
        p.walk_to(*find(L, btn)[0])
        p.frames(2)
        for (x, y) in find(L, water):
            assert p.tile(x, y) == MT['bridge_' + col], 'ponte %s não apareceu' % col
        if col == 'r':
            p.shot('f5_ponte_vermelha')
    p.shot('f5_pontes')
    p.finish_star(L, find(L, '*')[0], 'f5_estrela')

    # ---------------- fase 6: patinhos
    L = B.level6
    p.shot('f6_inicio')
    for i, (x, y) in enumerate(find(L, 'd')):
        p.walk_to(x, y)
        p.frames(2)
        assert p.actor(i, 'ACT') == B.DUCK_FOLLOW, 'patinho %d não veio' % i
        if i == 0:
            p.frames(5); p.expect_sfx(len(p.emu.spc.kon_log) - 3, 'piu')
    assert p.var('followers') == 3
    p.walk_to(9, 5); p.frames(10)
    p.shot('f6_fila')
    p.touch(*find(L, 'M')[0])
    assert all(p.actor(i, 'ACT') == B.DUCK_HOME for i in range(3))
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f6_com_a_mamae')
    p.finish_star(L, find(L, '*')[0], 'f6_estrela')

    # ---------------- fase 7: regar
    L = B.level7
    p.shot('f7_inicio')
    p.touch(*find(L, 'R')[0]); assert p.var('carry') == B.ITEM['can']
    for ch, bloom in (('s', 'bloom_1'), ('i', 'bloom_2'), ('l', 'bloom_3')):
        x, y = find(L, ch)[0]
        p.touch(x, y)
        assert p.tile(x, y) == MT[bloom] and p.var('carry') == B.ITEM['can']
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f7_flores')
    p.finish_star(L, find(L, '*')[0], 'f7_estrela')

    # ---------------- fase 8: lanche
    L = B.level8
    p.shot('f8_inicio')
    p.touch(*find(L, 'o')[0]); p.touch(*find(L, 'a')[0])      # osso no coelho: não quer
    assert p.var('delivered') == 0 and p.var('carry') == B.ITEM['bone']
    for food, animal, fed in (('o', 'D', 'dog_f'), ('C', 'a', 'rabbit_f'), ('K', 'g', 'hen_f')):
        if food != 'o':
            p.touch(*find(L, food)[0])
        x, y = find(L, animal)[0]
        p.touch(x, y)
        assert p.tile(x, y) == MT[fed], 'bicho não comeu'
        assert p.tile(x, y - 1) == MT['bubble_heart'], 'balão não virou coração'
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f8_felizes')
    p.finish_star(L, find(L, '*')[0], 'f8_estrela')

    # ---------------- fase 9: noite
    L = B.level9
    p.frames(2); p.shot('f9_noite')
    assert p.var('pal_id') == 1
    lanterns = find(L, 'L')
    for i in range(3):
        # persegue um vaga-lume ainda solto (o Pipo pode ter pego outro no caminho)
        p.chase(next(k for k in range(3) if p.actor(k, 'ACT')), B.ITEM['firefly'])
        if i == 0:
            p.frames(4); p.shot('f9_vagalume')
        p.touch(*lanterns[i])
        assert p.tile(*lanterns[i]) == MT['lantern_on']
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f9_lanternas')
    p.finish_star(L, find(L, '*')[0], 'f9_estrela')
    assert p.var('pal_id') == 0

    # ---------------- fase 10: ovos
    L = B.level10
    p.shot('f10_inicio')
    nest = find(L, 'N')[0]
    p.touch(*find(L, 'H')[0]); assert p.var('delivered') == 0       # feno vazio
    for n, (x, y) in enumerate(find(L, 'e')):
        p.touch(x, y)
        assert p.tile(x, y) == MT['egg'], 'ovo não apareceu'
        p.touch(x, y); assert p.var('carry') == B.ITEM['egg']
        p.touch(*nest)
        assert p.tile(*nest) == MT['nest_%d' % (n + 1)]
    assert p.var('delivered') == 3
    p.frames(6); p.shot('f10_ninho')
    k = len(p.emu.spc.kon_log)
    p.finish_star(L, find(L, '*')[0], 'f10_galo')
    p.expect_sfx(k, 'crow')

    # ---------------- tela final: papai, mamãe e a coberta do Cururu
    assert p.var('mode') == B.MODE_END and p.stage() == 11, 'final com o galo'
    w = p.emu.wram
    cut_t = lambda: w[B.CUT_T] | (w[B.CUT_T + 1] << 8)
    oam = lambda i: w[B.OAM + 4 * (B.CUT_OAM + i):B.OAM + 4 * (B.CUT_OAM + i) + 4]
    for t, name in ((230, 'final_papai_mamae'), (400, 'final_coberta'), (530, 'final_cururu_frio'),
                    (640, 'final_cururu_quentinho')):
        while cut_t() < t:
            p.frames(1)
        p.shot(name)
    assert oam(1)[1] != 0xE0 and oam(2)[1] != 0xE0, 'papai e mamãe deveriam aparecer'
    assert oam(3)[2] == B.A.hud_tile('frog_wrap0') & 0xFF or oam(3)[2] == B.A.hud_tile('frog_wrap1') & 0xFF, \
        'o Cururu deveria estar enrolado na coberta'
    for _ in range(400):
        if w[B.CUT_DONE]:
            break
        p.frames(1)
    assert w[B.CUT_DONE], 'a cena final deveria terminar'
    p.frames(30); p.shot('final')
    x0 = p.var('px')
    p.frames(60)
    assert p.var('px') > x0, 'o galo deveria passear'
    k = len(p.emu.spc.kon_log)
    p.frames(80); p.shot('final_cantando'); p.expect_sfx(k, 'crow')
    txt0 = bytes(p.emu.wram[B.TXTBUF:B.TXTBUF + 512])
    p.frames(100); p.shot('final_autores')
    assert bytes(p.emu.wram[B.TXTBUF:B.TXTBUF + 512]) != txt0, 'deveria mostrar os autores'
    p.frames(2, 'A'); p.frames(3)
    assert p.var('mode') == B.MODE_TITLE, 'deveria voltar para a abertura'
    p.frames(120)
    assert p.stage() == 0, 'abertura com pintinho novo'
    p.shot('menu_pt')
    assert p.emu.wram[B.OAM + 4 * B.HUD_OAM + 1] == 0xF0, 'placar escondido na abertura'
    # ---------------- inglês
    p.frames(2, 'DOWN'); p.frames(4)
    assert p.var('menu_sel') == B.LANG_EN and p.var('mode') == B.MODE_TITLE
    p.shot('menu_en')
    p.frames(2, 'A'); p.frames(6)
    assert p.var('menu_page') == 1
    # sem som: o volume geral do SPC vai a zero na hora
    assert p.emu.spc.dsp[0x0C] == 0x7F
    p.frames(2, 'DOWN'); p.frames(6)
    assert p.var('snd_off') == 1 and p.emu.spc.dsp[0x0C] == 0 and p.emu.spc.dsp[0x1C] == 0
    p.shot('menu_sem_som_en')
    p.frames(2, 'UP'); p.frames(6)
    assert p.var('snd_off') == 0 and p.emu.spc.dsp[0x0C] == 0x7F, 'som deveria voltar'
    p.frames(2, 'DOWN'); p.frames(6)
    p.frames(2, 'A'); p.frames(6)
    assert p.var('snd_off') == 1 and p.var('menu_page') == 2
    p.frames(2, 'DOWN'); p.frames(2)                    # rápido
    p.shot('menu_rapido_en')
    p.frames(2, 'A'); p.frames(40)
    assert p.var('menu_page') == 3
    p.shot('menu_trilha_en')
    p.frames(2, 'A'); p.frames(40)
    assert p.var('menu_page') == 4 and p.var('trail') == 0
    p.shot('menu_fase_en')
    p.frames(2, 'A'); p.frames(3)
    assert p.var('mode') == B.MODE_INTRO and p.var('level') == 0 and p.var('lang') == B.LANG_EN
    assert p.var('speed') == B.SPEED_FAST and p.emu.spc.dsp[0x0C] == 0
    p.intro(wait=True)
    # quadros para andar um bloco em cada velocidade
    def step_frames():
        L = B.level1
        x, y = p.pos()
        for d, (dx, dy) in DIRS.items():
            if not p.solid(x + dx, y + dy) and not p.var('move_cnt'):
                n = 0
                while True:
                    p.frames(1, d if n == 0 else ''); n += 1
                    if not p.var('move_cnt'):
                        return n
        raise AssertionError('sem saída')
    p.frames(5)
    for sp in (B.SPEED_FAST, B.SPEED_SLOW, B.SPEED_NORMAL, B.SPEED_FAST):
        p.emu.wram[B.V['speed']] = sp
        n = step_frames()
        assert abs(n - B.SPEED_FRAMES[sp]) <= 1, 'velocidade %d: %d quadros por bloco' % (sp, n)
    p.emu.wram[B.V['speed']] = B.SPEED_FAST
    L = B.level1
    for item, basket in (('r', '1'), ('b', '2'), ('y', '3')):
        p.touch(*find(L, item)[0]); p.touch(*find(L, basket)[0])
    p.touch(*find(L, '*')[0], msg=True)
    p.frames(12)
    assert p.var('msg_next') == B.MSG['0_grow@en'], 'mensagem deveria estar em inglês'
    p.shot('f1_estrela_ingles')
    # ---------------- começar direto numa fase escolhida (fase 6)
    q = Player(rom)
    q.n = p.n
    q.frames(125)
    for _ in range(4):
        q.frames(2, 'START'); q.frames(40)
    assert q.var('menu_page') == 4
    for _ in range(5):
        q.frames(2, 'RIGHT'); q.frames(40)
    assert q.var('menu_sel') == 5
    q.frames(2, 'START'); q.frames(3)
    assert q.var('level') == 5 and q.var('mode') == B.MODE_INTRO
    q.intro()
    assert q.var('mode') == B.MODE_PLAY and q.stage() == B.stage_for(5), 'Pipo no tamanho da fase 6'
    q.frames(6); q.shot('escolheu_fase_6')
    n = pato_trail(rom, q.n)
    print('OK — abertura e menu, sapo Cururu + 10 fases, final, volta, fase 1 em inglês sem som e rápida, '
          'Pato Pateta + 5 fases e final (%d quadros emulados)' % (p.emu.frame + q.emu.frame + n))


def pato_trail(rom, shot_n):
    """Joga a trilha do Pato Pateta inteira (letras e números)."""
    MT = B.MT
    p = Player(rom)
    p.n = shot_n
    p.frames(125)
    for _ in range(3):
        p.frames(2, 'START'); p.frames(40)
    assert p.var('menu_page') == 3
    p.frames(2, 'RIGHT'); p.frames(4)
    assert p.var('menu_sel') == 1
    p.frames(2, 'START'); p.frames(40)
    assert p.var('trail') == 1 and p.var('menu_page') == 4 and p.var('menu_sel') == 0
    p.frames(2, 'LEFT'); p.frames(40)
    assert p.var('menu_sel') == len(B.TRAILS[1]) - 1, 'a trilha do pato tem 5 fases'
    p.shot('menu_fase_pato_5')
    p.frames(2, 'RIGHT'); p.frames(40)
    assert p.var('menu_sel') == 0
    k = k0 = len(p.emu.spc.kon_log)
    p.frames(2, 'START'); p.frames(3)
    first = B.TRAIL_BASE[1]
    assert p.var('level') == first and p.var('mode') == B.MODE_INTRO
    p.expect_sfx(k, 'quack')
    assert p.emu.wram[B.OAM + 4 * B.FROG_OAM + 2] == B.A.hud_tile('pato_sit') & 0xFF or \
        p.emu.wram[B.OAM + 4 * B.FROG_OAM + 2] == B.A.hud_tile('pato_laugh') & 0xFF, 'quem aparece é o pato'
    p.intro('p1')
    assert p.stage() == 0
    hud = B.OAM + 4 * B.HUD_OAM
    assert p.emu.wram[hud + 2] == B.A.hud_tile('1') & 0xFF and p.emu.wram[hud + 5] == 0xF0, 'placar "1"'
    # a música mudou: o lá agudo (A5) só existe na música do pato
    p.frames(60)
    inv = {sound.pitch_value(n): n for n in range(128)}
    mel = [inv[pt] for _, _, info in p.emu.spc.kon_log[k0:] for v, pt, _ in info if v == 0]
    assert sound.midi('A5') in mel, 'música do Pato Pateta não tocou (%s)' % mel

    def carry_all(L, pairs, goal):
        """pairs: [(letra do bloquinho, letra da casinha, símbolo)]."""
        for i, (blk, slot, sym) in enumerate(pairs):
            p.touch(*find(L, blk)[0])
            assert p.var('carry') == B.ITEM['blk_' + sym], 'não pegou o %s' % sym
            if i == 0:                                   # casinha errada: não aceita
                p.frames(4); p.shot('p%d_carregando' % (B.trail_pos(p.var('level'))[1] + 1))
                p.touch(*find(L, pairs[1][1])[0])
                assert p.var('carry') == B.ITEM['blk_' + sym] and p.var('delivered') == 0
            x, y = find(L, slot)[0]
            p.touch(x, y)
            assert p.var('carry') == 0 and p.var('delivered') == i + 1
            assert p.tile(x, y) == MT[B.MT_NEXT[B.char_mt(L, slot)]]
            gx, gy = find(L, 'G')[0]
            assert (p.tile(gx, gy) == MT['path']) == (i + 1 == goal), 'portão na hora errada'

    # ---------------- pato 1: vogais
    L = B.pato1
    p.shot('p1_inicio')
    k = len(p.emu.spc.kon_log)
    p.touch(*find(L, 'D')[0]); p.frames(5); p.expect_sfx(k, 'quack')
    carry_all(L, [(s, s.lower(), s) for s in 'AEIOU'], 5)
    p.frames(6); p.shot('p1_vogais')
    p.finish_star(L, find(L, '*')[0], 'p1_estrela')
    # ---------------- pato 2: números
    L = B.pato2
    p.shot('p2_inicio')
    carry_all(L, [(str(n), 'abcde'[n - 1], str(n)) for n in range(1, 6)], 5)
    p.frames(6); p.shot('p2_numeros')
    p.finish_star(L, find(L, '*')[0], 'p2_estrela')
    # ---------------- pato 3: botões 1, 2, 3
    L = B.pato3
    p.shot('p3_inicio')
    for btn, water, col in (('1', 'x', 'r'), ('2', 'v', 'b'), ('3', 'z', 'y')):
        x, y = find(L, btn)[0]
        p.walk_to(x, y)
        p.frames(2)
        assert p.tile(x, y) == MT['nbuttonp_' + btn], 'botão %s não afundou' % btn
        for (wx, wy) in find(L, water):
            assert p.tile(wx, wy) == MT['bridge_' + col], 'ponte do %s não apareceu' % btn
        if btn == '1':
            p.shot('p3_ponte_1')
    p.shot('p3_pontes')
    p.finish_star(L, find(L, '*')[0], 'p3_estrela')
    # ---------------- pato 4: contar as bolinhas
    L = B.pato4
    p.shot('p4_inicio')
    carry_all(L, [(str(n), 'abcde'[n - 1], str(n)) for n in range(1, 6)], 5)
    p.frames(6); p.shot('p4_bolinhas')
    p.finish_star(L, find(L, '*')[0], 'p4_estrela')
    # ---------------- pato 5: escrever PATO
    L = B.pato5
    p.shot('p5_inicio')
    carry_all(L, [('1234'[i], 'abcd'[i], s) for i, s in enumerate('PATO')], 4)
    p.frames(6); p.shot('p5_pato')
    k = len(p.emu.spc.kon_log)
    p.finish_star(L, find(L, '*')[0], 'p5_galo')
    p.expect_sfx(k, 'crow')
    # ---------------- tela final da trilha
    assert p.var('level') == B.ENDING2 and p.var('mode') == B.MODE_END and p.stage() == 11
    assert p.emu.wram[B.CUT_DONE], 'sem cena: o FIM! aparece logo'
    assert all(p.emu.wram[B.OAM + 4 * (B.CUT_OAM + i) + 1] >= 0xE0 for i in range(4)), 'sem papai/mamãe aqui'
    p.frames(40); p.shot('final_pato')
    assert p.var('px') > B.ending2.START[0] * 16, 'o galo deveria passear'
    txt0 = bytes(p.emu.wram[B.TXTBUF:B.TXTBUF + 512])
    p.frames(240); p.shot('final_pato_autores')
    assert bytes(p.emu.wram[B.TXTBUF:B.TXTBUF + 512]) != txt0, 'deveria mostrar os autores'
    p.frames(2, 'A'); p.frames(3)
    assert p.var('mode') == B.MODE_TITLE, 'deveria voltar para a abertura'
    return p.emu.frame


if __name__ == '__main__':
    if 'pato' in sys.argv[1:]:          # só a trilha do Pato Pateta (não apaga as outras capturas)
        os.makedirs(OUT, exist_ok=True)
        pato_trail(open(os.path.join(ROOT, 'pipo.sfc'), 'rb').read(), 100)
        print('OK — trilha do Pato Pateta')
    else:
        main()

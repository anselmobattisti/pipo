"""Gera todos os gráficos do jogo (paletas, tiles, sprites e fonte grande)
e converte para os formatos do SNES (BGR555, 2bpp e 4bpp planares)."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
]


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def bgr555(c):
    r, g, b = c
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def pal_bytes(cols):
    out = bytearray()
    for c in cols:
        out += bgr555(c).to_bytes(2, 'little')
    return out


# ---------------------------------------------------------------- paletas
GRASS = '#74C850'
BG_PAL1 = [rgb(x) for x in [
    GRASS,      # 0 (transparente)
    GRASS,      # 1 grama clara
    '#58A83C',  # 2 grama escura
    '#9A6430',  # 3 marrom
    '#5E3A18',  # 4 marrom escuro
    '#2F9A44',  # 5 folha
    '#1C6A2E',  # 6 folha escura
    '#FF7EB6',  # 7 rosa
    '#FFFFFF',  # 8 branco
    '#FFD83A',  # 9 amarelo
    '#E8403A',  # 10 vermelho
    '#3478E8',  # 11 azul
    '#8ED8FF',  # 12 azul claro
    '#28203A',  # 13 contorno
    '#D89A20',  # 14 laranja / amarelo escuro
    '#EED8A0',  # 15 areia
]]
# paleta 2: igual à 1 mas com cinzas, verde-sapo e dourado
BG_PAL2 = list(BG_PAL1)
BG_PAL2[7] = rgb('#C8C8D0')   # cinza claro
BG_PAL2[10] = rgb('#8C8C9C')  # cinza médio
BG_PAL2[11] = rgb('#5C5C6C')  # cinza escuro
BG_PAL2[12] = rgb('#A8F070')  # verde-sapo claro
BG_PAL2[14] = rgb('#FFA820')  # dourado

def night(cols, keep=()):
    """Versão noturna de uma paleta (escura e azulada); `keep` = cores que brilham."""
    out = []
    for i, (r, g, b) in enumerate(cols):
        if i in keep:
            out.append((r, g, b))
        else:
            out.append((int(r * 0.35), int(g * 0.42), min(255, int(b * 0.6 + 40))))
    return out


NIGHT_PAL1 = night(BG_PAL1, keep=(9,))      # o amarelo (lanterna acesa) continua aceso
NIGHT_PAL2 = night(BG_PAL2)
NIGHT_GRASS = night([rgb(GRASS)])[0]

# BG3 (texto) usa CGRAM 4..7 (paleta 2bpp nº 1)
TEXT_PAL = [rgb(x) for x in ['#000000', '#FFF8E0', '#1A2A6C', '#E07A2A']]

SPR_PAL = [rgb(x) for x in [
    '#000000',  # 0 transparente
    '#FFE040',  # 1 amarelo corpo
    '#E8A818',  # 2 amarelo sombra
    '#FF8A1E',  # 3 laranja bico/pés
    '#20182A',  # 4 preto
    '#FFFFFF',  # 5 branco
    '#FF90A8',  # 6 bochecha rosa
    '#E8403A',  # 7 vermelho
    '#A02020',  # 8 vermelho escuro
    '#3478E8',  # 9 azul
    '#1E46A0',  # 10 azul escuro
    '#FFD83A',  # 11 amarelo bola
    '#C08A10',  # 12 amarelo bola escuro
    '#FF5A8A',  # 13 coração
    '#FFF4A0',  # 14 brilho
    '#3A2A20',  # 15 contorno marrom
]]


SPR_PAL2 = [rgb(x) for x in [
    '#000000',  # 0 transparente
    '#4E9A36',  # 1 sombra
    '#3FB04A',  # 2 folha
    '#1C6A2E',  # 3 folha escura
    '#FFE860',  # 4 patinho amarelo
    '#E0B020',  # 5 patinho sombra
    '#FF8A1E',  # 6 bico laranja
    '#20182A',  # 7 olho
    '#FFFFFF',  # 8 branco
    '#C8C8D0',  # 9 cinza (ovo/osso)
    '#E07A2A',  # 10 laranja cenoura
    '#3478E8',  # 11 azul regador
    '#1E46A0',  # 12 azul escuro
    '#3A2A20',  # 13 contorno
    '#FFFFA0',  # 14 brilho do vaga-lume
    '#9A6430',  # 15 marrom
]]


# ---------------------------------------------------------------- conversão
def tile_4bpp(img, x0, y0):
    out = bytearray(32)
    for y in range(8):
        for x in range(8):
            c = img.getpixel((x0 + x, y0 + y)) & 15
            bit = 7 - x
            for p in range(4):
                if c & (1 << p):
                    off = y * 2 + (p & 1) + (16 if p >= 2 else 0)
                    out[off] |= 1 << bit
    return bytes(out)


def tile_2bpp(img, x0, y0):
    out = bytearray(16)
    for y in range(8):
        for x in range(8):
            c = img.getpixel((x0 + x, y0 + y)) & 3
            bit = 7 - x
            if c & 1: out[y * 2] |= 1 << bit
            if c & 2: out[y * 2 + 1] |= 1 << bit
    return bytes(out)


def new16(fill=1):
    return Image.new('P', (16, 16), fill)


# ---------------------------------------------------------------- metatiles
def grass(d, img, specks=True):
    if specks:
        for (x, y) in [(2, 3), (11, 2), (6, 9), (13, 12), (3, 13), (9, 6)]:
            d.point((x, y), 2); d.point((x + 1, y - 1), 2)


def mt_grass():
    im = new16(); grass(ImageDraw.Draw(im), im); return im


def mt_flowers():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im)
    for (x, y, c) in [(3, 4, 7), (11, 3, 8), (7, 11, 9), (13, 12, 7)]:
        d.point([(x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)], c)
        d.point((x, y), 9 if c != 9 else 14)
    return im


def mt_path():
    im = new16(15); d = ImageDraw.Draw(im)
    for (x, y) in [(3, 2), (12, 5), (7, 9), (2, 12), (13, 13)]:
        d.point((x, y), 14)
    return im


def mt_tree():
    im = new16(); d = ImageDraw.Draw(im)
    d.rectangle((6, 10, 9, 15), fill=3); d.line((6, 10, 6, 15), fill=4)
    d.ellipse((0, 0, 15, 12), fill=6)
    d.ellipse((1, 0, 14, 10), fill=5)
    d.ellipse((3, 2, 7, 5), fill=2)
    d.point([(10, 3), (11, 6), (4, 7)], 6)
    return im


def mt_bush():
    im = new16(); d = ImageDraw.Draw(im)
    d.ellipse((0, 2, 15, 15), fill=6)
    d.ellipse((1, 2, 14, 13), fill=5)
    for (x, y, c) in [(4, 5, 7), (10, 4, 8), (7, 9, 7), (12, 10, 9), (3, 10, 8)]:
        d.point([(x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)], c)
        d.point((x, y), 9 if c != 9 else 14)
    return im


def mt_water():
    im = new16(11); d = ImageDraw.Draw(im)
    for (x, y) in [(2, 3), (9, 8), (3, 12)]:
        d.line((x, y, x + 3, y), fill=12)
    return im


def mt_fence():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im)
    d.rectangle((0, 4, 15, 6), fill=3); d.line((0, 6, 15, 6), fill=4)
    d.rectangle((0, 10, 15, 12), fill=3); d.line((0, 12, 15, 12), fill=4)
    for x in (2, 11):
        d.rectangle((x, 1, x + 2, 15), fill=3); d.line((x + 2, 1, x + 2, 15), fill=4)
        d.point((x + 1, 1), 14)
    return im


BALL_COL = {'r': (10, 13), 'b': (11, 13), 'y': (9, 14)}


def draw_ball(d, cx, cy, r, col):
    c, _ = BALL_COL[col]
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=13)
    d.ellipse((cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1), fill=c)
    d.ellipse((cx - r + 2, cy - r + 2, cx - r + 4, cy - r + 4), fill=8)


def mt_ball(col):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((3, 12, 13, 15), fill=2)  # sombra
    draw_ball(d, 8, 8, 6, col)
    return im


def mt_basket(col, full):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    c, _ = BALL_COL[col]
    if full:
        draw_ball(d, 8, 5, 5, col)
    # cesta: trapézio colorido com trama
    d.polygon([(1, 7), (14, 7), (12, 15), (3, 15)], fill=13)
    d.polygon([(2, 8), (13, 8), (11, 14), (4, 14)], fill=c)
    d.line((1, 7, 14, 7), fill=4); d.line((1, 8, 14, 8), fill=3)
    for x in (5, 8, 11):
        d.line((x, 10, x, 13), fill=8)
    return im


def mt_rock():  # paleta 2
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((1, 4, 14, 15), fill=11)
    d.ellipse((2, 4, 13, 13), fill=10)
    d.ellipse((4, 6, 7, 8), fill=7)
    return im


def mt_sign():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im)
    d.rectangle((7, 9, 8, 15), fill=4)
    d.rectangle((1, 1, 14, 10), fill=4)
    d.rectangle((2, 2, 13, 9), fill=3)
    d.line((4, 4, 11, 4), fill=15); d.line((4, 7, 9, 7), fill=15)
    return im


def mt_frog():  # o sapo Cururu (marrom) na vitória-régia, sobre a água
    im = new16(11); d = ImageDraw.Draw(im)
    d.ellipse((0, 9, 15, 15), fill=5)       # vitória-régia
    d.ellipse((2, 4, 13, 13), fill=13); d.ellipse((3, 5, 12, 12), fill=3)
    d.ellipse((5, 9, 10, 12), fill=9)       # barriga
    for ex in (2, 8):
        d.ellipse((ex, 1, ex + 5, 6), fill=13)
        d.ellipse((ex + 1, 2, ex + 4, 5), fill=8)
        d.rectangle((ex + 2, 3, ex + 3, 4), fill=13)
    d.line([(4, 7), (5, 8), (10, 8), (11, 7)], fill=13)   # sorrisão
    return im


def mt_gate():
    im = mt_fence(); d = ImageDraw.Draw(im)
    d.rectangle((5, 3, 10, 13), fill=3)
    d.rectangle((5, 3, 10, 13), outline=4)
    d.line((5, 3, 10, 13), fill=4)
    d.rectangle((9, 7, 11, 9), fill=9)     # trinco amarelo
    return im


def mt_star():  # paleta 2
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    pts = []
    import math
    for i in range(10):
        r = 7.5 if i % 2 == 0 else 3.4
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((7.5 + r * math.cos(a), 8 + r * math.sin(a)))
    d.polygon(pts, fill=14, outline=13)
    d.point([(6, 7), (9, 7)], 13)
    d.point([(7, 10), (8, 10)], 13)
    d.point((5, 5), 8)
    return im


def mt_flowerbig():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.line((8, 8, 8, 15), fill=6); d.line((8, 12, 11, 10), fill=5)
    for (x, y) in [(8, 2), (4, 5), (12, 5), (5, 9), (11, 9)]:
        d.ellipse((x - 3, y - 3, x + 2, y + 2), fill=7)
    d.ellipse((5, 4, 10, 9), fill=9)
    d.point((6, 5), 8)
    return im


# ---------------------------------------------------------------- fase 3: formas
SHAPES = ['circle', 'square', 'triangle']


def shape_pts(kind, cx, cy, r):
    if kind == 'square':
        return [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    if kind == 'triangle':
        return [(cx, cy - r - 1), (cx + r + 1, cy + r), (cx - r - 1, cy + r)]
    return None


def draw_shape(d, kind, cx, cy, r, fill, outline=13, shine=8):
    if kind == 'circle':
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=outline)
        d.ellipse((cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1), fill=fill)
        d.point((cx - r + 2, cy - r + 2), shine)
    else:
        pts = shape_pts(kind, cx, cy, r)
        d.polygon(pts, fill=fill, outline=outline)
        d.point((cx - r + 2 if kind == 'square' else cx, cy - r + 2 if kind == 'square' else cy - 1), shine)


def mt_shape(kind):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((3, 12, 13, 15), fill=2)
    draw_shape(d, kind, 8, 7, 5, 7)
    return im


def mt_hole(kind, full):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((0, 1, 15, 15), fill=14)
    d.ellipse((1, 2, 14, 14), fill=15)
    if kind == 'circle':
        d.ellipse((3, 3, 12, 12), fill=4)
    else:
        d.polygon(shape_pts(kind, 8, 8, 5), fill=4)
    if full:
        draw_shape(d, kind, 8, 8, 5, 7)
    return im


# ---------------------------------------------------------------- fase 4: amigos
def mt_rabbit():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    for ex in (4, 9):
        d.ellipse((ex, 0, ex + 3, 8), fill=13); d.ellipse((ex + 1, 1, ex + 2, 7), fill=8)
        d.line((ex + 1, 2, ex + 1, 6), fill=7)
    d.ellipse((2, 5, 13, 15), fill=13); d.ellipse((3, 6, 12, 14), fill=8)
    d.point([(5, 9), (10, 9)], 13); d.point([(7, 11), (8, 11)], 7)
    d.point([(4, 11), (11, 11)], 7)
    return im


def mt_bird():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((2, 3, 13, 14), fill=13); d.ellipse((3, 4, 12, 13), fill=11)
    d.ellipse((5, 8, 11, 13), fill=12)
    d.point((5, 7), 8); d.point((6, 7), 13); d.point((9, 7), 8); d.point((10, 7), 13)
    d.polygon([(7, 8), (9, 8), (8, 10)], fill=14)
    d.line((12, 6, 15, 4), fill=13)
    d.line((6, 14, 6, 15), fill=14); d.line((9, 14, 9, 15), fill=14)
    return im


def mt_hedgehog():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.pieslice((1, 3, 14, 18), 180, 360, fill=4)
    for x in range(2, 14, 2):
        d.line((x, 5, x + 1, 2), fill=4)
    d.ellipse((4, 7, 11, 14), fill=15)
    d.point([(6, 9), (9, 9)], 13); d.point((7, 11), 13); d.point((8, 11), 13)
    d.line((5, 12, 10, 12), fill=14)
    return im


# ---------------------------------------------------------------- fase 5: pontes e botões
def mt_bridge(col):
    c = {'r': 10, 'b': 11, 'y': 9}[col]
    im = new16(11); d = ImageDraw.Draw(im)
    d.rectangle((0, 2, 15, 13), fill=3)
    for y in (4, 7, 10):
        d.line((0, y, 15, y), fill=4)
    d.rectangle((0, 0, 15, 1), fill=c); d.line((0, 1, 15, 1), fill=13)
    d.rectangle((0, 14, 15, 15), fill=c); d.line((0, 14, 15, 14), fill=13)
    return im


def mt_button(col, pressed):
    c = {'r': 10, 'b': 11, 'y': 9}[col]
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((1, 3, 14, 14), fill=13)
    if pressed:
        d.ellipse((3, 6, 12, 13), fill=c)
        d.ellipse((5, 8, 10, 11), fill=8)
    else:
        d.ellipse((3, 2, 12, 11), fill=c)
        d.ellipse((4, 3, 7, 5), fill=8)
        d.line((3, 9, 12, 9), fill=13)
    return im


# ---------------------------------------------------------------- fase 6: mamãe pata
def mt_mother():
    im = new16(11); d = ImageDraw.Draw(im)
    d.ellipse((1, 8, 15, 15), fill=12)
    d.ellipse((2, 6, 14, 14), fill=13); d.ellipse((3, 7, 13, 13), fill=8)
    d.ellipse((1, 1, 8, 8), fill=13); d.ellipse((2, 2, 7, 7), fill=8)
    d.point((4, 4), 13)
    d.polygon([(0, 5), (2, 4), (2, 6)], fill=14)
    d.line((8, 9, 12, 10), fill=12)
    return im


# ---------------------------------------------------------------- fase 7: regar
def mt_sprout():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((2, 9, 13, 15), fill=4); d.ellipse((3, 9, 12, 14), fill=3)
    d.line((8, 10, 8, 6), fill=6); d.line((8, 7, 6, 5), fill=14); d.line((8, 7, 10, 5), fill=14)
    return im


def mt_bloom(col):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((2, 10, 13, 15), fill=4); d.ellipse((3, 10, 12, 14), fill=3)
    d.line((8, 8, 8, 12), fill=6); d.line((8, 10, 11, 8), fill=5)
    for (x, y) in [(8, 1), (4, 4), (12, 4), (5, 8), (11, 8)]:
        d.ellipse((x - 3, y - 2, x + 2, y + 3), fill=col)
    d.ellipse((5, 3, 10, 8), fill=9 if col != 9 else 14)
    d.point((6, 4), 8)
    return im


def mt_can():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((3, 12, 13, 15), fill=2)
    d.rectangle((4, 6, 11, 13), fill=13); d.rectangle((5, 7, 10, 12), fill=11)
    d.line((11, 8, 15, 4), fill=13, width=2); d.point((15, 3), 12)
    d.arc((3, 2, 10, 10), 180, 360, fill=13); d.point((6, 8), 8)
    return im


# ---------------------------------------------------------------- fase 8: lanche
def draw_carrot(d, cx, cy):
    d.polygon([(cx - 3, cy - 2), (cx + 3, cy - 2), (cx, cy + 5)], fill=14, outline=13)
    d.line((cx - 1, cy - 3, cx - 2, cy - 5), fill=5); d.line((cx + 1, cy - 3, cx + 2, cy - 5), fill=5)


def draw_corn(d, cx, cy):
    d.ellipse((cx - 2, cy - 4, cx + 2, cy + 4), fill=9, outline=13)
    d.point([(cx - 1, cy - 2), (cx + 1, cy), (cx - 1, cy + 2)], 14)
    d.polygon([(cx - 3, cy + 4), (cx - 1, cy - 1), (cx, cy + 4)], fill=5)


def draw_bone(d, cx, cy):
    for c, g in ((13, 1), (8, 0)):      # contorno e depois o osso
        d.rectangle((cx - 3, cy - 1 - g, cx + 3, cy + 1 + g), fill=c)
        for x in (cx - 4, cx + 3):
            d.ellipse((x - 1 - g, cy - 3 - g, x + 2 + g, cy + g), fill=c)
            d.ellipse((x - 1 - g, cy - g, x + 2 + g, cy + 3 + g), fill=c)


FOOD_DRAW = {'carrot': draw_carrot, 'corn': draw_corn, 'bone': draw_bone}


def mt_food(kind):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((3, 12, 13, 15), fill=2)
    FOOD_DRAW[kind](d, 8, 8)
    return im


def mt_bubble(kind):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((1, 0, 14, 12), fill=13); d.ellipse((2, 1, 13, 11), fill=8)
    d.polygon([(6, 11), (9, 11), (7, 15)], fill=8); d.line((6, 12, 7, 15), fill=13)
    if kind == 'heart':
        d.ellipse((4, 3, 8, 7), fill=10); d.ellipse((7, 3, 11, 7), fill=10)
        d.polygon([(4, 6), (11, 6), (7.5, 10)], fill=10)
    else:
        FOOD_DRAW[kind](d, 7, 6)
    return im


def _heart(d, x, y):
    d.point([(x, y), (x + 2, y), (x - 1, y + 1), (x + 3, y + 1), (x, y + 2), (x + 2, y + 2),
             (x + 1, y + 1), (x + 1, y + 3)], 10)


def mt_hen(fed=False):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((2, 5, 14, 15), fill=13); d.ellipse((3, 6, 13, 14), fill=8)
    d.ellipse((3, 1, 9, 8), fill=13); d.ellipse((4, 2, 8, 7), fill=8)
    d.ellipse((4, 0, 7, 2), fill=10)
    d.point((5, 4), 13); d.polygon([(2, 4), (4, 4), (3, 6)], fill=14)
    d.point((4, 7), 10)
    d.line((12, 6, 15, 4), fill=13)
    if fed:
        _heart(d, 11, 0)
    return im


def mt_dog(fed=False):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((2, 7, 14, 15), fill=4); d.ellipse((3, 8, 13, 14), fill=3)
    d.ellipse((3, 1, 12, 10), fill=4); d.ellipse((4, 2, 11, 9), fill=3)
    d.ellipse((1, 2, 4, 8), fill=4); d.ellipse((11, 2, 14, 8), fill=4)
    d.ellipse((5, 5, 10, 9), fill=15)
    d.point([(6, 4), (9, 4)], 13); d.rectangle((7, 6, 8, 6), fill=13)
    if fed:
        d.line((7, 8, 8, 8), fill=10)
        _heart(d, 12, 0)
    return im


def mt_rabbit_fed():
    im = mt_rabbit(); d = ImageDraw.Draw(im)
    _heart(d, 12, 1)
    return im


# ---------------------------------------------------------------- fase 9: noite
def mt_lantern(on):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.rectangle((7, 10, 8, 15), fill=4)
    d.rectangle((4, 2, 11, 11), fill=4)
    d.rectangle((5, 3, 10, 10), fill=9 if on else 13)
    if on:
        d.rectangle((6, 4, 9, 9), fill=8)
        d.point([(7, 6), (8, 7)], 9)
    d.line((4, 1, 11, 1), fill=4); d.point((7, 0), 4); d.point((8, 0), 4)
    return im


# ---------------------------------------------------------------- fase 10: música
def mt_bell(col, rung):
    c = {'r': 10, 'b': 11, 'y': 9}[col]
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.rectangle((7, 11, 8, 15), fill=4)
    d.polygon([(8, 1), (12, 5), (13, 11), (2, 11), (3, 5)], fill=13)
    d.polygon([(8, 2), (11, 5), (12, 10), (3, 10), (4, 5)], fill=c)
    d.ellipse((6, 10, 9, 13), fill=4)
    d.point((5, 5), 8); d.point((5, 6), 8)
    if rung:
        for (x0, y0, x1, y1) in [(0, 3, 1, 5), (0, 8, 1, 7), (14, 3, 15, 5), (14, 8, 15, 7)]:
            d.line((x0, y0, x1, y1), fill=8)
    return im


def mt_mflower(col):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.line((8, 8, 8, 15), fill=6); d.line((8, 12, 11, 10), fill=5)
    for (x, y) in [(8, 2), (4, 5), (12, 5), (5, 9), (11, 9)]:
        d.ellipse((x - 3, y - 3, x + 2, y + 2), fill=col)
    d.ellipse((5, 4, 10, 9), fill=8)
    d.line((8, 5, 8, 8), fill=13); d.point([(6, 8), (7, 8)], 13); d.line((8, 5, 9, 6), fill=13)
    return im


# ---------------------------------------------------------------- fase 11: ovos
def mt_hay():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.pieslice((0, 3, 15, 22), 180, 360, fill=14)
    d.pieslice((1, 4, 14, 21), 180, 360, fill=15)
    for x in (3, 6, 9, 12):
        d.line((x, 8, x + 1, 12), fill=14)
    d.line((0, 12, 15, 12), fill=14)
    return im


def draw_egg(d, cx, cy):
    d.ellipse((cx - 3, cy - 4, cx + 3, cy + 4), fill=13)
    d.ellipse((cx - 2, cy - 3, cx + 2, cy + 3), fill=8)
    d.point((cx - 1, cy - 2), 15)


def mt_egg():
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((3, 12, 13, 15), fill=2)
    draw_egg(d, 8, 8)
    return im


def mt_nest(n):
    im = new16(); d = ImageDraw.Draw(im); grass(d, im, specks=False)
    d.ellipse((0, 5, 15, 15), fill=4); d.ellipse((2, 6, 13, 12), fill=3)
    for i, x in enumerate((4, 8, 11)[:n]):
        draw_egg(d, x, 7)
    d.arc((0, 7, 15, 15), 0, 180, fill=14)
    return im


# ordem = índice do metatile usado no mapa e no código
METATILES = [
    # nome, função, paleta
    ('grass', mt_grass, 1),
    ('flowers', mt_flowers, 1),
    ('path', mt_path, 1),
    ('tree', mt_tree, 1),
    ('bush', mt_bush, 1),
    ('water', mt_water, 1),
    ('fence', mt_fence, 1),
    ('ball_r', lambda: mt_ball('r'), 1),
    ('ball_b', lambda: mt_ball('b'), 1),
    ('ball_y', lambda: mt_ball('y'), 1),
    ('basket_r', lambda: mt_basket('r', False), 1),
    ('basket_b', lambda: mt_basket('b', False), 1),
    ('basket_y', lambda: mt_basket('y', False), 1),
    ('basketf_r', lambda: mt_basket('r', True), 1),
    ('basketf_b', lambda: mt_basket('b', True), 1),
    ('basketf_y', lambda: mt_basket('y', True), 1),
    ('rock', mt_rock, 2),
    ('sign', mt_sign, 1),
    ('frog', mt_frog, 1),
    ('star', mt_star, 2),
    ('flowerbig', mt_flowerbig, 1),
    ('gate', mt_gate, 1),
    # fase 3
    ('shape_c', lambda: mt_shape('circle'), 1), ('shape_s', lambda: mt_shape('square'), 1),
    ('shape_t', lambda: mt_shape('triangle'), 1),
    ('hole_c', lambda: mt_hole('circle', False), 1), ('hole_s', lambda: mt_hole('square', False), 1),
    ('hole_t', lambda: mt_hole('triangle', False), 1),
    ('holef_c', lambda: mt_hole('circle', True), 1), ('holef_s', lambda: mt_hole('square', True), 1),
    ('holef_t', lambda: mt_hole('triangle', True), 1),
    # fase 4 (arbustos com amigo têm o mesmo desenho do arbusto comum)
    ('bush_1', mt_bush, 1), ('bush_2', mt_bush, 1), ('bush_3', mt_bush, 1),
    ('rabbit', mt_rabbit, 1), ('bird', mt_bird, 1), ('hedgehog', mt_hedgehog, 1),
    # fase 5
    ('water_r', mt_water, 1), ('water_b', mt_water, 1), ('water_y', mt_water, 1),
    ('bridge_r', lambda: mt_bridge('r'), 1), ('bridge_b', lambda: mt_bridge('b'), 1),
    ('bridge_y', lambda: mt_bridge('y'), 1),
    ('button_r', lambda: mt_button('r', False), 1), ('button_b', lambda: mt_button('b', False), 1),
    ('button_y', lambda: mt_button('y', False), 1),
    ('buttonp_r', lambda: mt_button('r', True), 1), ('buttonp_b', lambda: mt_button('b', True), 1),
    ('buttonp_y', lambda: mt_button('y', True), 1),
    # fase 6
    ('mother', mt_mother, 1),
    # fase 7
    ('can', mt_can, 1),
    ('sprout_1', mt_sprout, 1), ('sprout_2', mt_sprout, 1), ('sprout_3', mt_sprout, 1),
    ('bloom_1', lambda: mt_bloom(10), 1), ('bloom_2', lambda: mt_bloom(11), 1),
    ('bloom_3', lambda: mt_bloom(9), 1),
    # fase 8 (os balões precisam ficar juntos e nesta ordem)
    ('carrot', lambda: mt_food('carrot'), 1), ('corn', lambda: mt_food('corn'), 1),
    ('bone', lambda: mt_food('bone'), 1),
    ('rabbit_h', mt_rabbit, 1), ('hen_h', mt_hen, 1), ('dog_h', mt_dog, 1),
    ('rabbit_f', mt_rabbit_fed, 1), ('hen_f', lambda: mt_hen(True), 1),
    ('dog_f', lambda: mt_dog(True), 1),
    ('bubble_carrot', lambda: mt_bubble('carrot'), 1), ('bubble_corn', lambda: mt_bubble('corn'), 1),
    ('bubble_bone', lambda: mt_bubble('bone'), 1), ('bubble_heart', lambda: mt_bubble('heart'), 1),
    # fase 9
    ('lantern', lambda: mt_lantern(False), 1), ('lantern_on', lambda: mt_lantern(True), 1),
    # fase 10
    ('bell_r', lambda: mt_bell('r', False), 1), ('bell_b', lambda: mt_bell('b', False), 1),
    ('bell_y', lambda: mt_bell('y', False), 1),
    ('bellr_r', lambda: mt_bell('r', True), 1), ('bellr_b', lambda: mt_bell('b', True), 1),
    ('bellr_y', lambda: mt_bell('y', True), 1),
    ('mflower_1', lambda: mt_mflower(7), 1), ('mflower_2', lambda: mt_mflower(12), 1),
    ('mflower_3', lambda: mt_mflower(14), 1),
    # fase 11
    ('hay', mt_hay, 1), ('hay_egg', mt_hay, 1), ('egg', mt_egg, 1),
    ('nest_0', lambda: mt_nest(0), 1), ('nest_1', lambda: mt_nest(1), 1),
    ('nest_2', lambda: mt_nest(2), 1), ('nest_3', lambda: mt_nest(3), 1),
    ('hen', mt_hen, 1),
]
MT = {name: i for i, (name, _, _) in enumerate(METATILES)}


def build_bg():
    """Retorna (tiles_4bpp, tabela_metatiles[4 palavras por metatile], imagens)."""
    tiles = [bytes(32)]  # tile 0 vazio
    index = {tiles[0]: 0}
    table = []
    images = []
    for name, fn, pal in METATILES:
        im = fn(); images.append((im, pal))
        for (x, y) in [(0, 0), (8, 0), (0, 8), (8, 8)]:
            t = tile_4bpp(im, x, y)
            if t not in index:
                index[t] = len(tiles); tiles.append(t)
            table.append(index[t] | (pal << 10))
    assert len(tiles) <= 768, 'tiles de cenário demais: %d' % len(tiles)
    return b''.join(tiles), table, images


# ---------------------------------------------------------------- sprites
def chick(direction, frame):
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    bob = 1 if frame else 0
    # pés
    if frame:
        d.rectangle((4, 14, 6, 15), fill=3); d.rectangle((10, 13, 12, 14), fill=3)
    else:
        d.rectangle((4, 14, 6, 15), fill=3); d.rectangle((9, 14, 11, 15), fill=3)
    # corpo
    d.ellipse((1, 1 + bob, 14, 14), fill=15)
    d.ellipse((2, 2 + bob, 13, 13), fill=1)
    d.ellipse((3, 9 + bob, 12, 13), fill=2)
    d.ellipse((4, 8 + bob, 11, 12), fill=1)
    d.line((7, 0 + bob, 8, 2 + bob), fill=15)  # topete
    d.point((6, 0 + bob), 15)
    if direction == 'down':
        for ex in (4, 9):
            d.rectangle((ex, 4 + bob, ex + 2, 7 + bob), fill=4)
            d.point((ex, 4 + bob), 5)
        d.polygon([(6, 8 + bob), (9, 8 + bob), (7.5, 10 + bob)], fill=3)
        d.point([(3, 9 + bob), (12, 9 + bob)], 6)
    elif direction == 'side':  # olhando para a direita
        d.rectangle((9, 4 + bob, 11, 7 + bob), fill=4)
        d.point((9, 4 + bob), 5)
        d.polygon([(12, 7 + bob), (15, 8 + bob), (12, 9 + bob)], fill=3)
        d.point((10, 9 + bob), 6)
        d.line((4, 7 + bob, 6, 9 + bob), fill=2)  # asinha
    else:  # costas
        d.line((4, 7 + bob, 6, 9 + bob), fill=2)
        d.line((11, 7 + bob, 9, 9 + bob), fill=2)
    return im


def spr_ball(col):
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    c, dark = {'r': (7, 8), 'b': (9, 10), 'y': (11, 12)}[col]
    d.ellipse((3, 3, 12, 12), fill=15)
    d.ellipse((4, 4, 11, 11), fill=c)
    d.ellipse((7, 8, 11, 11), fill=dark); d.ellipse((5, 5, 10, 10), fill=c)
    d.rectangle((5, 5, 6, 6), fill=5)
    return im


def spr_heart():
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    d.ellipse((2, 3, 8, 9), fill=13); d.ellipse((7, 3, 13, 9), fill=13)
    d.polygon([(2, 7), (13, 7), (7.5, 13)], fill=13)
    d.rectangle((4, 5, 5, 6), fill=5)
    return im


def spr_shadow():  # usa a paleta de sprites 1 (cor 1 = verde escuro)
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    d.ellipse((3, 12, 12, 15), fill=1)
    return im


def spr_shape(kind):
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    draw_shape(d, kind, 8, 8, 4, 13, outline=15, shine=5)
    return im


def spr_duckling(frame):  # paleta de sprites 1
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    b = frame
    d.ellipse((3, 7 + b, 13, 15), fill=5); d.ellipse((4, 7 + b, 12, 14), fill=4)
    d.ellipse((2, 2 + b, 9, 9 + b), fill=5); d.ellipse((3, 3 + b, 8, 8 + b), fill=4)
    d.point((4, 5 + b), 7)
    d.polygon([(0, 6 + b), (3, 5 + b), (3, 7 + b)], fill=6)
    d.line((11, 9 + b, 14, 8 + b), fill=5)
    return im


def spr_duckling_fb(view):  # paleta de sprites 1 — de frente ou de costas
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    d.line((5, 14, 5, 15), fill=6); d.line((10, 13, 10, 14), fill=6)   # pezinhos (um à frente: ginga)
    d.ellipse((3, 7, 12, 14), fill=5); d.ellipse((4, 7, 11, 13), fill=4)
    d.ellipse((4, 1, 11, 8), fill=5); d.ellipse((5, 2, 10, 7), fill=4)
    d.line((7, 0, 8, 1), fill=5)                                         # topete
    if view == 'front':
        d.point([(6, 4), (9, 4)], 7)
        d.polygon([(6, 6), (9, 6), (7.5, 8)], fill=6)
    else:
        d.line((7, 12, 8, 14), fill=5)                                   # rabinho
        d.line((4, 9, 5, 11), fill=5); d.line((11, 9, 10, 11), fill=5)   # asinhas
    return im


def spr_leaves():  # paleta de sprites 1
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    for (x, y) in [(2, 3), (10, 1), (6, 8), (12, 10), (1, 12)]:
        d.ellipse((x, y, x + 3, y + 2), fill=2); d.point((x + 3, y + 2), 3)
    return im


def spr_item(kind):  # paleta de sprites 1
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    if kind == 'can':
        d.rectangle((4, 6, 11, 13), fill=13); d.rectangle((5, 7, 10, 12), fill=11)
        d.line((11, 8, 15, 4), fill=13, width=2)
        d.arc((3, 2, 10, 10), 180, 360, fill=13); d.point((6, 8), 8)
    elif kind == 'carrot':
        d.polygon([(5, 5), (11, 5), (8, 13)], fill=10, outline=13)
        d.line((7, 4, 6, 2), fill=2); d.line((9, 4, 10, 2), fill=2)
    elif kind == 'corn':
        d.ellipse((6, 3, 10, 12), fill=4, outline=13)
        d.point([(7, 5), (9, 7), (7, 9)], 5)
        d.polygon([(5, 12), (7, 7), (8, 12)], fill=2)
    elif kind == 'bone':
        d.rectangle((5, 7, 11, 9), fill=8)
        for x in (4, 11):
            d.ellipse((x - 1, 5, x + 2, 8), fill=8); d.ellipse((x - 1, 8, x + 2, 11), fill=8)
        d.line((5, 9, 11, 9), fill=9)
    elif kind == 'firefly':
        d.ellipse((3, 3, 8, 7), fill=8); d.ellipse((8, 3, 13, 7), fill=8)
        d.ellipse((5, 6, 11, 13), fill=7)
        d.ellipse((6, 9, 10, 13), fill=14); d.point((8, 11), 4)
    elif kind == 'egg':
        d.ellipse((4, 3, 11, 13), fill=13); d.ellipse((5, 4, 10, 12), fill=8)
        d.point((6, 5), 9)
    elif kind == 'egg_crack':
        d.ellipse((4, 3, 11, 13), fill=13); d.ellipse((5, 4, 10, 12), fill=8)
        d.line([(5, 8), (6, 7), (7, 9), (8, 7), (9, 9), (10, 8)], fill=13)
        d.point((6, 5), 9)
    elif kind == 'egg_shell':
        d.chord((3, 6, 12, 15), 0, 180, fill=13); d.chord((4, 7, 11, 14), 0, 180, fill=8)
        d.line([(4, 11), (5, 9), (6, 11), (7, 9), (8, 11), (9, 9), (10, 11), (11, 10)], fill=13)
    return im


def spr_sparkle():
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    d.line((7, 1, 7, 13), fill=14); d.line((1, 7, 13, 7), fill=14)
    d.line((4, 4, 10, 10), fill=11); d.line((10, 4, 4, 10), fill=11)
    d.rectangle((6, 6, 8, 8), fill=5)
    return im


def spr_cururu(pose):  # paleta de sprites 1 — o sapo-cururu (marrom), o bagunceiro
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    BODY, BELLY, OUT, WH, EYE, TONGUE, HI = 15, 4, 13, 8, 7, 6, 10
    if pose == 'jump':
        for x0, x1 in ((4, 1), (11, 14)):            # pernas esticadas
            d.line((x0, 10, x1, 15), fill=OUT, width=3); d.line((x0, 10, x1, 15), fill=BODY)
        d.ellipse((2, 4, 13, 12), fill=OUT); d.ellipse((3, 5, 12, 11), fill=BODY)
        d.ellipse((5, 9, 10, 12), fill=BELLY)
        oy = -1
    else:
        d.ellipse((0, 12, 5, 15), fill=OUT); d.ellipse((10, 12, 15, 15), fill=OUT)   # pés
        d.ellipse((1, 13, 4, 15), fill=BODY); d.ellipse((11, 13, 14, 15), fill=BODY)
        d.ellipse((1, 4, 14, 14), fill=OUT); d.ellipse((2, 5, 13, 13), fill=BODY)
        d.ellipse((5, 11, 10, 14), fill=BELLY)
        d.point([(3, 10), (12, 11), (4, 12)], OUT)      # pintinhas de sapo-cururu
        oy = 0
    for ex in (1, 9):                                # olhos saltados
        d.ellipse((ex, 0 + oy, ex + 5, 6 + oy), fill=OUT)
    if pose == 'laugh':                              # olhinhos fechados: "hihi"
        for ex in (1, 9):
            d.ellipse((ex + 1, 1 + oy, ex + 4, 5 + oy), fill=BODY)
            d.line([(ex + 1, 4 + oy), (ex + 2, 2 + oy), (ex + 3, 2 + oy), (ex + 4, 4 + oy)], fill=OUT)
        d.polygon([(3, 7), (12, 7), (10, 10), (5, 10)], fill=EYE)
        d.line((6, 9, 9, 9), fill=HI)
    else:
        for ex in (1, 9):
            d.ellipse((ex + 1, 1 + oy, ex + 4, 5 + oy), fill=WH)
            d.rectangle((ex + 2, 2 + oy, ex + 3, 4 + oy), fill=EYE)
        my = 8 + oy
        d.line([(3, my - 1), (4, my), (11, my), (12, my - 1)], fill=OUT)   # sorrisão maroto
        d.point((10, my + 1), WH)                       # dentinho
    return im


# células 16x16 da folha de sprites (índice = célula)
SPRITES = [
    ('down0', lambda: chick('down', 0)), ('down1', lambda: chick('down', 1)),
    ('side0', lambda: chick('side', 0)), ('side1', lambda: chick('side', 1)),
    ('up0', lambda: chick('up', 0)), ('up1', lambda: chick('up', 1)),
    ('ball_r', lambda: spr_ball('r')), ('ball_b', lambda: spr_ball('b')),
    ('ball_y', lambda: spr_ball('y')), ('heart', spr_heart),
    ('sparkle', spr_sparkle), ('shadow', spr_shadow),
    ('shape_c', lambda: spr_shape('circle')), ('shape_s', lambda: spr_shape('square')),
    ('shape_t', lambda: spr_shape('triangle')),
    ('duck0', lambda: spr_duckling(0)), ('duck1', lambda: spr_duckling(1)),
    ('leaves', spr_leaves),
    ('can', lambda: spr_item('can')), ('carrot', lambda: spr_item('carrot')),
    ('corn', lambda: spr_item('corn')), ('bone', lambda: spr_item('bone')),
    ('firefly', lambda: spr_item('firefly')), ('egg', lambda: spr_item('egg')),
    ('egg_crack', lambda: spr_item('egg_crack')), ('egg_shell', lambda: spr_item('egg_shell')),
    ('frog_sit', lambda: spr_cururu('sit')), ('frog_jump', lambda: spr_cururu('jump')),
    ('frog_laugh', lambda: spr_cururu('laugh')),
    ('duck_front', lambda: spr_duckling_fb('front')), ('duck_back', lambda: spr_duckling_fb('back')),
]
assert len(SPRITES) <= 32, 'a folha de sprites tem 32 células (tiles 0-127)'
SPR = {name: i for i, (name, _) in enumerate(SPRITES)}
SPR_PAL2_CELLS = {'shadow', 'duck0', 'duck1', 'leaves', 'can', 'carrot', 'corn', 'bone', 'firefly', 'egg',
                  'egg_crack', 'egg_shell', 'frog_sit', 'frog_jump', 'frog_laugh',
                  'duck_front', 'duck_back'}   # usam a paleta de sprites 1


def spr_tile(cell):
    """Número do tile (canto sup. esquerdo) de uma célula 16x16."""
    return (cell % 8) * 2 + (cell // 8) * 32


def build_sprites():
    rows = (len(SPRITES) + 7) // 8
    sheet = Image.new('P', (128, rows * 16), 0)
    for i, (_, fn) in enumerate(SPRITES):
        sheet.paste(fn(), ((i % 8) * 16, (i // 8) * 16))
    out = bytearray()
    for ty in range(rows * 2):
        for tx in range(16):
            out += tile_4bpp(sheet, tx * 8, ty * 8)
    return bytes(out), sheet


# ---------------------------------------------------------------- placar (fase atual)
# Número da fase (canto superior direito) e outros desenhos extras.
# Ficam numa folha própria, nos tiles 384+ da área de sprites.
HUD_TILE_BASE = 384


def _star(fill, outline, shine=None):
    import math
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    pts = []
    for i in range(10):
        r = 7 if i % 2 == 0 else 3.2
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append((7.5 + r * math.cos(ang), 8 + r * math.sin(ang)))
    d.polygon(pts, fill=fill, outline=outline)
    if shine:
        d.point([(6, 6), (7, 5)], shine)
    return im


def _glyph(ch, fill=5, outline=15):
    """Um caractere grande e grosso, branco com contorno escuro."""
    font = ImageFont.truetype(next(p for p in FONT_CANDIDATES if os.path.exists(p)), 14)
    W = 16
    body = Image.new('L', (W, W), 0); edge = Image.new('L', (W, W), 0)
    w = ImageDraw.Draw(body).textlength(ch, font=font)
    pos = (W / 2 - w / 2, 13)
    ImageDraw.Draw(edge).text(pos, ch, font=font, fill=255, anchor='ls', stroke_width=1, stroke_fill=255)
    ImageDraw.Draw(body).text(pos, ch, font=font, fill=255, anchor='ls')
    im = Image.new('P', (W, W), 0)
    for y in range(W):
        for x in range(W):
            if body.getpixel((x, y)) >= 110:
                im.putpixel((x, y), fill)
            elif edge.getpixel((x, y)) >= 60:
                im.putpixel((x, y), outline)
    return im


def _slash():
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    d.line((10, 2, 5, 13), fill=15, width=4)
    d.line((10, 2, 5, 13), fill=5, width=2)
    return im


def _quilt(im, x0, y0, x1, y1):
    """Retalhos coloridos (paleta de sprites 1)."""
    d = ImageDraw.Draw(im)
    d.rectangle((x0, y0, x1, y1), fill=13)
    cols = [11, 4, 10, 2]
    for yy in range(y0 + 1, y1, 3):
        for xx in range(x0 + 1, x1, 3):
            c = cols[((xx - x0) // 3 + (yy - y0) // 3) % 4]
            d.rectangle((xx, yy, min(xx + 2, x1 - 1), min(yy + 2, y1 - 1)), fill=c)


def spr_blanket(full):
    im = Image.new('P', (16, 16), 0)
    if full:
        _quilt(im, 0, 3, 15, 13)
    else:
        _quilt(im, 3, 6, 12, 11)                 # metade: ainda costurando
    return im


def spr_frog_wrapped(frame):
    """O Cururu enroladinho na coberta, de olhos fechados e sorrindo."""
    im = Image.new('P', (16, 16), 0); d = ImageDraw.Draw(im)
    b = frame                                    # respira (sobe e desce 1 px)
    d.ellipse((1, 3 + b, 14, 13), fill=13); d.ellipse((2, 4 + b, 13, 12), fill=15)
    for ex in (1, 9):                            # olhos saltados, fechadinhos
        d.ellipse((ex, 1 + b, ex + 5, 6 + b), fill=13)
        d.ellipse((ex + 1, 2 + b, ex + 4, 5 + b), fill=15)
        d.line([(ex + 1, 4 + b), (ex + 2, 3 + b), (ex + 3, 3 + b), (ex + 4, 4 + b)], fill=13)
    d.line([(5, 7 + b), (6, 8 + b), (9, 8 + b), (10, 7 + b)], fill=13)   # sorriso
    _quilt(im, 0, 9, 15, 15)
    return im


HUD_SPRITES = [(str(n), (lambda n=n: _glyph(str(n)))) for n in range(10)] + [   # número da fase
    ('blanket_half', lambda: spr_blanket(False)),  # coberta do Cururu (paleta 1)
    ('blanket', lambda: spr_blanket(True)),
    ('frog_wrap0', lambda: spr_frog_wrapped(0)), ('frog_wrap1', lambda: spr_frog_wrapped(1)),
]
HUD = {name: i for i, (name, _) in enumerate(HUD_SPRITES)}
HUD_PAL2_CELLS = {'blanket_half', 'blanket', 'frog_wrap0', 'frog_wrap1'}


def hud_tile(name):
    return HUD_TILE_BASE + spr_tile(HUD[name])


def build_hud():
    rows = (len(HUD_SPRITES) + 7) // 8
    sheet = Image.new('P', (128, rows * 16), 0)
    for i, (_, fn) in enumerate(HUD_SPRITES):
        sheet.paste(fn(), ((i % 8) * 16, (i // 8) * 16))
    out = bytearray()
    for ty in range(rows * 2):
        for tx in range(16):
            out += tile_4bpp(sheet, tx * 8, ty * 8)
    return bytes(out), sheet


# ---------------------------------------------------------------- texto
# As mensagens são desenhadas já prontas (fonte proporcional) na hora de gerar
# a ROM: cada uma vira um bloco de 30x6 tiles 2bpp (240x48 px, 3 linhas de 16 px).
TEXT_SIZE = 13           # tamanho da fonte em pixels
TEXT_COLS, TEXT_ROWS = 30, 6
BOX_TILES = ['top', 'bottom', 'left', 'right', 'tl', 'tr', 'bl', 'br', 'arrow', 'fill', 'heart_t', 'heart_b']


def _font():
    path = next(p for p in FONT_CANDIDATES if os.path.exists(p))
    return ImageFont.truetype(path, TEXT_SIZE)


def render_message(lines):
    """Desenha até 3 linhas centralizadas numa imagem 'P' de 240x48."""
    font = _font()
    W, H = TEXT_COLS * 8, TEXT_ROWS * 8
    assert len(lines) <= 3, lines
    top = (3 - len(lines)) * 8           # centraliza na vertical
    gray = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(gray)
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=font)
        assert w <= W - 4, 'linha larga demais: %r (%d px)' % (ln, w)
        d.text((W / 2 - w / 2, top + i * 16 + 12), ln, font=font, fill=255, anchor='ls')
    img = Image.new('P', (W, H), 1)
    for y in range(H):
        for x in range(W):
            if gray.getpixel((x, y)) >= 100:
                img.putpixel((x, y), 2)
    return img


def _box(kind):
    p = Image.new('P', (8, 8), 1); d = ImageDraw.Draw(p)
    if kind == 'top': d.rectangle((0, 2, 7, 3), fill=3); d.rectangle((0, 0, 7, 1), fill=0)
    if kind == 'bottom': d.rectangle((0, 4, 7, 5), fill=3); d.rectangle((0, 6, 7, 7), fill=0)
    if kind == 'left': d.rectangle((2, 0, 3, 7), fill=3); d.rectangle((0, 0, 1, 7), fill=0)
    if kind == 'right': d.rectangle((4, 0, 5, 7), fill=3); d.rectangle((6, 0, 7, 7), fill=0)
    if kind == 'tl':
        d.rectangle((0, 0, 7, 7), fill=0); d.pieslice((2, 2, 13, 13), 180, 270, fill=3)
        d.pieslice((4, 4, 13, 13), 180, 270, fill=1)
    if kind == 'tr':
        d.rectangle((0, 0, 7, 7), fill=0); d.pieslice((-6, 2, 5, 13), 270, 360, fill=3)
        d.pieslice((-6, 4, 3, 13), 270, 360, fill=1)
    if kind == 'bl':
        d.rectangle((0, 0, 7, 7), fill=0); d.pieslice((2, -6, 13, 5), 90, 180, fill=3)
        d.pieslice((4, -6, 13, 3), 90, 180, fill=1)
    if kind == 'br':
        d.rectangle((0, 0, 7, 7), fill=0); d.pieslice((-6, -6, 5, 5), 0, 90, fill=3)
        d.pieslice((-6, -6, 3, 3), 0, 90, fill=1)
    if kind == 'arrow':
        d.polygon([(1, 1), (6, 1), (3.5, 5)], fill=3)
    if kind in ('heart_t', 'heart_b'):        # coração de 2 tiles (cursor do menu)
        big = Image.new('P', (8, 16), 1); hd = ImageDraw.Draw(big)
        hd.ellipse((0, 4, 4, 8), fill=3); hd.ellipse((3, 4, 7, 8), fill=3)
        hd.polygon([(0, 7), (7, 7), (3.5, 12)], fill=3)
        return big.crop((0, 0, 8, 8) if kind == 'heart_t' else (0, 8, 8, 16))
    return p


def box_tile(name):
    return 1 + BOX_TILES.index(name)


MSG_TILE_BASE = 16   # tiles das mensagens começam aqui (antes ficam a moldura)


LOGO_TILE_BASE = 200   # tiles dos logotipos (abertura/fim), sempre na VRAM
LOGO_PAL = [rgb(x) for x in ['#000000', '#3A2010', '#FFD83A', '#FF8A1E']]   # BG3 paleta 2


def render_logo(lines, width=240, height=64):
    """lines: [(texto, tamanho)]. Letras grandes com contorno; metade de baixo laranja."""
    path = next(p for p in FONT_CANDIDATES if os.path.exists(p))
    stroke = Image.new('L', (width, height), 0)
    fillm = Image.new('L', (width, height), 0)
    ds, df = ImageDraw.Draw(stroke), ImageDraw.Draw(fillm)
    boxes = []
    caps = [round(sz * 0.72) for _, sz in lines]
    gap = 9
    base = (height - (sum(caps) + gap * (len(lines) - 1))) // 2
    for (text, sz), cap in zip(lines, caps):
        font = ImageFont.truetype(path, sz)
        w = ds.textlength(text, font=font)
        x = (width - w) / 2
        base += cap
        ds.text((x, base), text, font=font, fill=255, stroke_width=3, stroke_fill=255, anchor='ls')
        df.text((x, base), text, font=font, fill=255, anchor='ls')
        boxes.append(df.textbbox((x, base), text, font=font, anchor='ls'))
        base += gap
    img = Image.new('P', (width, height), 0)
    for yy in range(height):
        for xx in range(width):
            if fillm.getpixel((xx, yy)) > 110:
                c = 2
                for (x0, y0, x1, y1) in boxes:
                    if y0 <= yy <= y1 and yy > y0 + (y1 - y0) * 0.55:
                        c = 3
                img.putpixel((xx, yy), c)
            elif stroke.getpixel((xx, yy)) > 90:
                img.putpixel((xx, yy), 1)
    return img


def build_logos(logos):
    """logos: lista de imagens 'P'. Retorna (tiles 2bpp, [mapa 32x8 de cada logo])."""
    tiles, index, maps = [], {}, []
    empty = bytes(16)
    for img in logos:
        cols, rows = img.size[0] // 8, img.size[1] // 8
        x0 = (32 - cols) // 2
        m = [0] * (32 * 8)
        for ty in range(rows):
            for tx in range(cols):
                t = tile_2bpp(img, tx * 8, ty * 8)
                if t == empty:
                    continue
                if t not in index:
                    index[t] = len(tiles); tiles.append(t)
                m[ty * 32 + x0 + tx] = (LOGO_TILE_BASE + index[t]) | 0x2800   # prioridade + paleta 2
        maps.append(m)
    assert LOGO_TILE_BASE + len(tiles) <= 512, 'logotipos grandes demais'
    return b''.join(tiles), maps


def build_box_tiles():
    """Tile 0 transparente + tiles da moldura da caixa."""
    out = bytearray(16)
    for k in BOX_TILES:
        out += tile_2bpp(_box(k), 0, 0)
    return bytes(out)


def build_text(messages):
    """Para cada mensagem: (tiles 2bpp sem repetição, mapa 30x6 com nº de tile na VRAM).
    Cada mensagem é carregada na VRAM só quando aparece, a partir de MSG_TILE_BASE."""
    result, imgs = [], []
    for lines in messages:
        img = render_message(lines)
        imgs.append(img)
        tiles, index, m = [], {}, []
        for ty in range(TEXT_ROWS):
            for tx in range(TEXT_COLS):
                t = tile_2bpp(img, tx * 8, ty * 8)
                if t not in index:
                    index[t] = len(tiles); tiles.append(t)
                m.append(MSG_TILE_BASE + index[t])
        result.append((b''.join(tiles), m))
    return result, imgs


if __name__ == '__main__':  # pré-visualização
    out = os.path.join(HERE, '..', 'build')
    os.makedirs(out, exist_ok=True)
    _, _, imgs = build_bg()
    sheet = Image.new('RGB', (16 * 8 * 4, 16 * ((len(imgs) + 7) // 8) * 4))
    for i, (im, pal) in enumerate(imgs):
        pal_cols = BG_PAL1 if pal == 1 else BG_PAL2
        rgbim = Image.new('RGB', (16, 16))
        for y in range(16):
            for x in range(16):
                rgbim.putpixel((x, y), pal_cols[im.getpixel((x, y))])
        sheet.paste(rgbim.resize((64, 64), Image.NEAREST), ((i % 8) * 64, (i // 8) * 64))
    sheet.save(os.path.join(out, 'preview_tiles.png'))
    _, ss = build_sprites()
    rgbim = Image.new('RGB', ss.size)
    for y in range(ss.size[1]):
        for x in range(ss.size[0]):
            c = ss.getpixel((x, y))
            cell = (y // 16) * 8 + x // 16
            pal = SPR_PAL2 if cell < len(SPRITES) and SPRITES[cell][0] in SPR_PAL2_CELLS else SPR_PAL
            rgbim.putpixel((x, y), (255, 0, 255) if c == 0 else pal[c])
    rgbim.resize((ss.size[0] * 4, ss.size[1] * 4), Image.NEAREST).save(os.path.join(out, 'preview_sprites.png'))
    _, imgs = build_text([['PARABÉNS!', 'VOCÊ ACHOU A', 'ESTRELA!'], ['AÇÃO É ÔNIBUS Ç']])
    for i, im in enumerate(imgs):
        rgbim = Image.new('RGB', im.size)
        for y in range(im.size[1]):
            for x in range(im.size[0]):
                rgbim.putpixel((x, y), TEXT_PAL[im.getpixel((x, y))])
        rgbim.resize((im.size[0] * 3, im.size[1] * 3), Image.NEAREST).save(
            os.path.join(out, 'preview_text%d.png' % i))
    print('ok')

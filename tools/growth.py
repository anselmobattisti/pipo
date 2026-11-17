"""Os 12 estágios do Pipo: de pintinho (0) a galo (11), em sprites 32x32.

Cores = índices da paleta de sprites 0 (assets.SPR_PAL).
Cada estágio tem 6 quadros: baixo0, baixo1, cima0, cima1, lado0, lado1
(o lado esquerdo é o direito espelhado).
"""
from PIL import Image, ImageDraw

STAGES = 12
YEL, YSH, ORG, BLK, WHT, PNK, RED, DRED, BLU, DBLU = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
CREAM, OUT = 14, 15


def _colors(stage):
    if stage <= 5:
        return YEL, YSH
    if stage <= 8:
        return CREAM, YSH
    return WHT, CREAM


def bird(stage, direction, frame, acc=None):
    s = stage / (STAGES - 1)
    im = Image.new('P', (32, 32), 0)
    d = ImageDraw.Draw(im)
    body, shade = _colors(stage)
    bob = 1 if frame else 0
    legs = 1 + round(4 * s)
    bw = round(13 + 7 * s)                  # largura do corpo
    bh = round(bw * 0.88)
    chick = stage < 4
    hr = 0 if chick else round(4 + 2.4 * s)  # raio da cabeça
    cx = 16
    by1 = 31 - legs                          # base do corpo
    by0 = by1 - bh + bob                     # topo do corpo
    side = direction == 'side'
    if side:
        cx = 15

    # ---- cauda (penas curvas atrás do corpo; de costas fica por cima)
    feathers = []
    if stage >= 6:
        n = 1 + (stage - 6) // 2 + (1 if stage >= 10 else 0)
        tcols = [DBLU, BLU, RED, BLU] if stage >= 9 else [YSH, CREAM]
        L0 = 4 + (stage - 6) * 1.6
        for i in range(n):
            col = tcols[i % len(tcols)]
            L = L0 - i * 1.5
            if side:
                bx0, by0_ = cx - bw // 2 + 3, by0 + bh // 3
                feathers.append((bx0, by0_, -1, L, col))
            else:
                for sgn in (-1, 1):
                    feathers.append((cx + sgn * 2, by0 + bh // 3, sgn, L * 0.9, col))

    def draw_feathers():
        for bx0, by0_, sgn, L, col in feathers:
            L = min(L, by0_ - 1)
            pts = []
            for t in [i / 6 for i in range(7)]:
                x = bx0 + sgn * (L * 0.9 * t + L * 0.3 * t * t)
                y = by0_ - L * (2 * t - t * t) * 1.1 + L * 0.35 * t * t * t
                pts.append((x, y))
            d.line(pts, fill=OUT, width=4)
            d.line(pts, fill=col, width=2)

    if direction != 'up':
        draw_feathers()
    # ---- pernas
    lc = ORG
    if side:
        fx = [cx - 2, cx + 2] if not frame else [cx - 3, cx + 3]
    else:
        fx = [cx - bw // 4 - 1, cx + bw // 4] if not frame else [cx - bw // 4, cx + bw // 4 - 1]
    for x in fx:
        d.line((x, by1 - 1, x, 30), fill=lc, width=1 + (stage >= 6))
        d.line((x - 1, 31, x + 2, 31), fill=lc)
    # ---- corpo
    d.ellipse((cx - bw // 2, by0, cx + bw // 2, by1), fill=OUT)
    d.ellipse((cx - bw // 2 + 1, by0 + 1, cx + bw // 2 - 1, by1 - 1), fill=body)
    d.ellipse((cx - bw // 2 + 2, by0 + bh // 2, cx + bw // 2 - 2, by1 - 1), fill=shade)
    d.ellipse((cx - bw // 2 + 3, by0 + bh // 2 - 1, cx + bw // 2 - 3, by1 - 2), fill=body)
    # asa
    if side:
        d.ellipse((cx - bw // 4 - 2, by0 + bh // 3, cx + bw // 4, by0 + bh // 3 + bh // 2), fill=shade)
    elif direction == 'down' and stage >= 2:
        d.line((cx - bw // 2 + 2, by0 + bh // 2 - 1, cx - bw // 2 + 4, by0 + bh // 2 + 3), fill=shade)
        d.line((cx + bw // 2 - 2, by0 + bh // 2 - 1, cx + bw // 2 - 4, by0 + bh // 2 + 3), fill=shade)

    if direction == 'up':
        draw_feathers()

    # ---- cabeça
    if chick:
        hx, hy, r = cx, by0 + bh // 3, bw // 2       # rosto no próprio corpo
        d.line((cx, by0 - 1, cx + 1, by0 + 1), fill=OUT)  # topete
    else:
        hx = cx + (bw // 3 if side else 0)
        hy = by0 + 1
        r = hr
        if stage >= 4:   # crista (atrás da cabeça)
            ch = 1 + round(3 * s)
            cw = max(2, r - 1)
            for i in range(-1, 2):
                x = hx + i * (cw // 2 + 1) - (1 if side else 0)
                d.ellipse((x - 2, hy - r - ch, x + 2, hy - r + 2), fill=RED)
        d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=OUT)
        d.ellipse((hx - r + 1, hy - r + 1, hx + r - 1, hy + r - 1), fill=body)

    # ---- rosto
    if direction == 'down':
        ey = hy - (1 if not chick else 2)
        ex = max(2, (r * 2) // 5)
        for sx in (-ex - 1, ex):
            d.rectangle((hx + sx, ey, hx + sx + 1, ey + 2), fill=BLK)
            d.point((hx + sx, ey), WHT)
        by = ey + 3
        d.polygon([(hx - 2, by), (hx + 1, by), (hx - 0.5, by + 2 + (stage >= 6))], fill=ORG)
        if stage >= 7:   # barbela
            d.ellipse((hx - 1, by + 2, hx + 1, by + 4 + (stage >= 10)), fill=RED)
        if chick:
            d.point([(hx - ex - 3, ey + 3), (hx + ex + 2, ey + 3)], PNK)
    elif side:
        ey = hy - 1
        ex = hx + max(1, r // 3)
        d.rectangle((ex, ey, ex + 1, ey + 2), fill=BLK)
        d.point((ex, ey), WHT)
        bx = hx + r - (0 if not chick else 1)
        d.polygon([(bx, ey + 1), (bx + 3 + (stage >= 6), ey + 2), (bx, ey + 3)], fill=ORG)
        if stage >= 7:
            d.ellipse((bx - 1, ey + 3, bx + 1, ey + 6), fill=RED)
        if chick:
            d.point((ex - 1, ey + 3), PNK)
    else:   # costas: só a nuca
        pass
    if acc:                                  # enfeites (papai e mamãe do Pipo)
        acc(d, hx, hy, r, direction, cx, by0, bw)
    return im


FRAMES = [('down', 0), ('down', 1), ('up', 0), ('up', 1), ('side', 0), ('side', 1)]


def stage_sheet(stage):
    """Bloco de 16x8 tiles (128x64 px) como fica na VRAM: quadros 0-3 na
    linha de cima, 4-5 na de baixo."""
    sheet = Image.new('P', (128, 64), 0)
    for k, (dr, fr) in enumerate(FRAMES):
        sheet.paste(bird(stage, dr, fr), ((k % 4) * 32, (k // 4) * 32))
    return sheet


def frame_tile(k):
    """Deslocamento do tile (canto sup. esq.) do quadro k dentro do bloco."""
    return (k // 4) * 64 + (k % 4) * 4


def head_top(stage):
    """Primeira linha não transparente (para posicionar o item carregado)."""
    im = bird(stage, 'down', 0)
    for y in range(32):
        if any(im.getpixel((x, y)) for x in range(32)):
            return y
    return 16


# ---------------------------------------------------------------- papai e mamãe
def _popi_acc(d, hx, hy, r, direction, cx, by0, bw):
    """Seu Popi: óculos e gravata-borboleta azul."""
    BLUE, DBLUE_ = 9, 10
    ny = hy + r + 1
    if direction == 'down':
        ex = max(2, (r * 2) // 5)
        ey = hy - 1
        for x in (hx - ex - 1, hx + ex):
            d.ellipse((x - 2, ey - 1, x + 3, ey + 4), outline=BLK)
        d.line((hx - ex + 3, ey + 1, hx + ex - 2, ey + 1), fill=BLK)
        d.polygon([(hx - 4, ny - 2), (hx, ny), (hx - 4, ny + 2)], fill=BLUE, outline=DBLUE_)
        d.polygon([(hx + 4, ny - 2), (hx, ny), (hx + 4, ny + 2)], fill=BLUE, outline=DBLUE_)
    elif direction == 'side':
        ex = hx + max(1, r // 3)
        d.ellipse((ex - 2, hy - 2, ex + 3, hy + 3), outline=BLK)
        d.line((ex - 2, hy, hx - r + 1, hy - 1), fill=BLK)
        d.polygon([(hx - 3, ny - 2), (hx + 1, ny), (hx - 3, ny + 2)], fill=BLUE, outline=DBLUE_)


def _pipa_acc(d, hx, hy, r, direction, cx, by0, bw):
    """Senhora Pipa: laço cor-de-rosa na cabeça."""
    bx, by = hx + (r - 2 if direction != 'side' else -r + 3), hy - r + 1
    d.polygon([(bx - 4, by - 3), (bx, by), (bx - 4, by + 3)], fill=PNK, outline=OUT)
    d.polygon([(bx + 4, by - 3), (bx, by), (bx + 4, by + 3)], fill=PNK, outline=OUT)
    d.rectangle((bx - 1, by - 1, bx + 1, by + 1), fill=RED)


PARENT_FRAMES = [('down', 0), ('down', 1), ('side', 0), ('side', 1)]


def parents_sheet():
    """Bloco 128x64 (como uma área de estágio): Seu Popi na linha de cima,
    Senhora Pipa na de baixo; quadros baixo0 baixo1 lado0 lado1."""
    sheet = Image.new('P', (128, 64), 0)
    for row, (stage, acc) in enumerate(((11, _popi_acc), (8, _pipa_acc))):
        for k, (dr, fr) in enumerate(PARENT_FRAMES):
            sheet.paste(bird(stage, dr, fr, acc), (k * 32, row * 32))
    return sheet


def parent_tile(who, k):
    """Tile (dentro da área) do quadro k do papai (0) ou da mamãe (1)."""
    return who * 64 + k * 4

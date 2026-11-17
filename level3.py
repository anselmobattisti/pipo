# Fase 3 — "Formas no lugar"
# Igual à fase 1, mas com formas: cada forma vai no buraco do mesmo formato.
#   c círculo   q quadrado   t triângulo     4 5 6  buracos (círculo, quadrado, triângulo)
#   (demais letras: veja level1.py)
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..,......B..,.T',
    'T.c....O....q..T',
    'T..............T',
    'T..B..4.5.6..P.T',
    'T..............T',
    'T.,.....,......T',
    'TWWW...........T',
    'TWWF......fffffT',
    'TWW....t..f....T',
    'T.........G.*..T',
    'T..P......f....T',
    'T...,.B...f..,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (5, 10)

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['4', 'c', '5', 'q', '6', 't']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'TIROU AS FORMAS', 'DO LUGAR!'], None),
    ('star1', ['MUITO BEM!', 'CADA FORMA NO', 'SEU LUGAR!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'BRINCAR DE', 'ESCONDE-ESCONDE!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'TOOK THE SHAPES', 'OUT!'],
    'star1': ['GREAT JOB!', 'EVERY SHAPE IN', 'ITS PLACE!'],
    'next': ["NOW LET'S PLAY", 'HIDE-AND-SEEK!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

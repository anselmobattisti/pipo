# Fase 2 — "As bolas puladoras"
# Mesmas letras da fase 1. Aqui as bolas (r b y) não ficam paradas: ficam
# quicando e de vez em quando pulam para um bloco vizinho. É só encostar nelas.
BOUNCY = True

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T,....B......,.T',
    'T..r........b..T',
    'T.....,..O.....T',
    'T.P............T',
    'T......y.....,.T',
    'T..,........B..T',
    'T.......P......T',
    'Tffff..........T',
    'T...G..1..2..3.T',
    'T.*.f..........T',
    'T,..f...WWWW...T',
    'T...f...WWWF..,T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 11)

MESSAGES = [
    ('star1', ['VIVA!', 'VOCÊ PEGOU AS', 'BOLAS PULADORAS!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'BRINCAR COM', 'AS FORMAS!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'star1': ['HOORAY!', 'YOU CAUGHT THE', 'BOUNCY BALLS!'],
    'next': ["NOW LET'S PLAY", 'WITH SHAPES!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

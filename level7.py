# Fase 7 — "Regar as flores"
# Pegue o regador (R) e encoste nos brotinhos secos: eles viram flores.
#   R regador   s i l  brotinhos (viram flor vermelha, azul, amarela)

# sem outras plantas no cenário (só os brotinhos), para não confundir a criança
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..............T',
    'T..s.......O...T',
    'T..............T',
    'T.......R....i.T',
    'T..............T',
    'T..............T',
    'T......l.......T',
    'T..............T',
    'TffGff.....WWW.T',
    'T....f.....WWW.T',
    'T.*..f.....WFW.T',
    'T....f.........T',
    'TTTTTTTTTTTTTTTT',
]

START = (8, 6)

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['s', 'i', 'l']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'AMASSOU', 'AS FLORES!'], None),
    ('star1', ['QUE JARDIM', 'LINDO!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA É HORA', 'DO LANCHE!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'SQUASHED', 'THE FLOWERS!'],
    'star1': ['WHAT A PRETTY', 'GARDEN!'],
    'next': ["NOW IT'S", 'SNACK TIME!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

# (FORA DO JOGO) Fase "Jardim musical" — removida a pedido; para voltar, importe no
# build.py e coloque na lista LEVELS.
# Fase "Jardim musical"
# Encoste nos 3 sinos (X Y Z) para tocar as notas e abrir o portão.
#   m n p  flores musicais (só tocam notas, por diversão)

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..m.....,...X.T',
    'T..............T',
    'T.B....n....B..T',
    'T..............T',
    'T.Y.....O....p.T',
    'T..............T',
    'T..,....Z......T',
    'Tfffff.........T',
    'T....f...m..n..T',
    'T.*..G.........T',
    'T....f...WWW...T',
    'T,...f...WWW.,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (8, 10)

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['X', 'Y', 'Z']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'DESAFINOU', 'OS SINOS!'], None),
    ('star1', ['QUE MÚSICA', 'BONITA!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA ACHE OS', 'OVOS DA GALINHA!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'MESSED UP', 'THE BELLS!'],
    'star1': ['WHAT LOVELY', 'MUSIC!'],
    'next': ['NOW FIND THE', "HEN'S EGGS!"],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

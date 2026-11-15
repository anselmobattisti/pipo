# Fase 10 — "Jardim musical"
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

MESSAGES = [
    ('star1', ['QUE MÚSICA', 'BONITA!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA ACHE OS', 'OVOS DA GALINHA!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'star1': ['WHAT LOVELY', 'MUSIC!'],
    'next': ['NOW FIND THE', "HEN'S EGGS!"],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

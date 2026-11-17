# Fase 9 — "Noite dos vaga-lumes"
# Fase noturna: pegue os vaga-lumes (u, voam por aí) e leve até as lanternas (L).
NIGHT = True

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.u......B.....T',
    'T....L.......u.T',
    'T.P.......O....T',
    'T..........L...T',
    'T.B..u.........T',
    'T.......,...B..T',
    'T..L...........T',
    'T.........fffffT',
    'TWWW......f....T',
    'TWWW......G.*..T',
    'TWFW......f....T',
    'T,........f..,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 11)

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['L', 'u', 'L', 'u', 'L', 'u']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'APAGOU', 'AS LANTERNAS!'], None),
    ('star1', ['AS LANTERNAS', 'ACENDERAM!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA ACHE OS', 'OVOS DA GALINHA!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'TURNED OFF', 'THE LANTERNS!'],
    'star1': ['THE LANTERNS', 'ARE LIT!'],
    'next': ['NOW FIND THE', "HEN'S EGGS!"],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

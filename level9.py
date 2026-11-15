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

MESSAGES = [
    ('star1', ['AS LANTERNAS', 'ACENDERAM!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'FAZER MÚSICA!'], None),
]

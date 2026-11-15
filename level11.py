# Fase 11 — "Os ovos da galinha"
# Os ovos estão escondidos no feno (H vazio, e com ovo). Leve cada ovo ao ninho (N).
#   Q galinha

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.H......e...H.T',
    'T..............T',
    'T.e...H....O...T',
    'T........,.....T',
    'T.H..QN.....H..T',
    'T..............T',
    'T.P......e.....T',
    'T.........fffffT',
    'T..H......f....T',
    'T.........G.*..T',
    'T.,...B...f....T',
    'TH........f..,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 10)

MESSAGES = [
    ('star1', ['ACHOU TODOS', 'OS OVOS!'], 'grow'),
    ('grow', ['O PIPO VIROU', 'UM GALO!'], 'crow'),
    ('crow', ['CÓ-CÓ-RI-CÓ!'], 'end1'),
    ('end1', ['VOCÊ É', 'INCRÍVEL!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'star1': ['YOU FOUND ALL', 'THE EGGS!'],
    'grow': ['PIPO BECAME', 'A ROOSTER!'],
    'crow': ['COCK-A-', 'DOODLE-DOO!'],
    'end1': ['YOU ARE', 'AMAZING!'],
}

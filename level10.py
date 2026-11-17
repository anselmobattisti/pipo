# Fase 10 — "Os ovos da galinha" (a última)
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

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['N', 'e', 'e', 'e']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'ESCONDEU OS OVOS', 'NO FENO!'], None),
    ('star1', ['ACHOU TODOS', 'OS OVOS!'], 'grow'),
    ('grow', ['O PIPO VIROU', 'UM GALO!'], 'crow'),
    ('crow', ['CÓ-CÓ-RI-CÓ!'], 'end1'),
    ('end1', ['VOCÊ É', 'INCRÍVEL!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'HID THE EGGS', 'IN THE HAY!'],
    'star1': ['YOU FOUND ALL', 'THE EGGS!'],
    'grow': ['PIPO BECAME', 'A ROOSTER!'],
    'crow': ['COCK-A-', 'DOODLE-DOO!'],
    'end1': ['YOU ARE', 'AMAZING!'],
}

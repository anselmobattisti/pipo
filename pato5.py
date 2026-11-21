# Trilha do Pato Pateta, fase 5 — "Escrever PATO"
# As letras P, A, T, O vão para as casinhas ao lado do pato e formam o nome dele.
# (aqui as letras do mapa são números porque T, P e O já são árvore, flor e pedra)
#   1 2 3 4  bloquinhos P, A, T, O     a b c d  casinhas P, A, T, O     D  o Pato Pateta
VISITOR = 'pato'
GOAL = 4
CHARS = {'D': 'pato'}
CHARS.update({'1234'[i]: 'blk_' + s for i, s in enumerate('PATO')})
CHARS.update({'abcd'[i]: 'slot_' + s for i, s in enumerate('PATO')})

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.....fffff..,.T',
    'T.3...f.*.f....T',
    'T.....f...f..1.T',
    'T.....ffGff....T',
    'T..............T',
    'T....Dabcd.....T',
    'T..............T',
    'T.,............T',
    'T..4.......2...T',
    'T..............T',
    'T......,.....,.T',
    'T..............T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 8)

CURURU = ['a1', 'b2', 'c3', 'd4']

MESSAGES = [
    ('intro', ['ATCHIM! AS LETRAS', 'DO NOME DO PATO', 'VOARAM!'], None),
    ('star1', ['P, A, T, O', 'VOCÊ ESCREVEU', 'PATO!'], 'grow'),
    ('grow', ['O PIPO VIROU', 'UM GALO!'], 'crow'),
    ('crow', ['CÓ-CÓ-RI-CÓ!'], 'end1'),
    ('end1', ['VOCÊ É', 'INCRÍVEL!'], None),
]

MESSAGES_EN = {
    'intro': ['ACHOO! THE LETTERS', "OF PATO'S NAME", 'FLEW AWAY!'],
    'star1': ['P, A, T, O', 'YOU SPELLED', 'PATO!'],
    'grow': ['PIPO BECAME', 'A ROOSTER!'],
    'crow': ['COCK-A-', 'DOODLE-DOO!'],
    'end1': ['YOU ARE', 'AMAZING!'],
}

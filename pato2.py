# Trilha do Pato Pateta, fase 2 — "Os números"
# Cada número (bloquinho vermelho) atravessa a ponte e vai para a casinha com o mesmo número.
#   1 2 3 4 5  bloquinhos     a b c d e  casinhas do 1 ao 5     D  o Pato Pateta
VISITOR = 'pato'
GOAL = 5
CHARS = {'D': 'pato'}
CHARS.update({str(n): 'blk_%d' % n for n in range(1, 6)})
CHARS.update({'abcde'[n - 1]: 'slot_%d' % n for n in range(1, 6)})

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.....,WW....1.T',
    'T.a....WW......T',
    'T......WW....2.T',
    'T.b....WW......T',
    'T......==....3.T',
    'T.c....WW..D...T',
    'T......WW....4.T',
    'T.d....WW......T',
    'T......WW....5.T',
    'T.e....WW......T',
    'TffGff.==..,...T',
    'T.*..f.WW......T',
    'TTTTTTTTTTTTTTTT',
]

START = (10, 8)

CURURU = ['a1', 'b2', 'c3', 'd4', 'e5']

MESSAGES = [
    ('intro', ['XI! O PATO PATETA', 'DERRUBOU', 'OS NÚMEROS!'], None),
    ('star1', ['VIVA!', '1, 2, 3, 4, 5', 'CADA UM NO LUGAR!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'CONTAR PARA', 'ATRAVESSAR!'], None),
]

MESSAGES_EN = {
    'intro': ['UH-OH! THE GOOFY DUCK', 'DROPPED', 'THE NUMBERS!'],
    'star1': ['HOORAY!', '1, 2, 3, 4, 5', 'ALL IN PLACE!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
    'next': ["NOW LET'S COUNT", 'TO CROSS!'],
}

# Trilha do Pato Pateta, fase 4 — "Contar as bolinhas"
# Cada número vai para o cartão com a mesma quantidade de bolinhas.
#   1 2 3 4 5  bloquinhos     a b c d e  cartões com 1 a 5 bolinhas     D  o Pato Pateta
VISITOR = 'pato'
GOAL = 5
CHARS = {'D': 'pato'}
CHARS.update({str(n): 'blk_%d' % n for n in range(1, 6)})
CHARS.update({'abcde'[n - 1]: 'dots_%d' % n for n in range(1, 6)})

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T,......f....f.T',
    'T.3.....f.*..f.T',
    'T.....1.f....f.T',
    'T.......ffGfff.T',
    'T.5............T',
    'T....D.....,...T',
    'T.2...4........T',
    'T..............T',
    'T.,............T',
    'T.a.b.c.d.e..P.T',
    'T..............T',
    'T......,.......T',
    'TTTTTTTTTTTTTTTT',
]

START = (9, 7)

CURURU = ['a1', 'b2', 'c3', 'd4', 'e5']

MESSAGES = [
    ('intro', ['O PATO PATETA', 'MISTUROU', 'OS NÚMEROS!'], None),
    ('star1', ['PARABÉNS!', 'VOCÊ SABE', 'CONTAR ATÉ 5!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'ESCREVER', 'PATO!'], None),
]

MESSAGES_EN = {
    'intro': ['THE GOOFY DUCK', 'MIXED UP', 'THE NUMBERS!'],
    'star1': ['WELL DONE!', 'YOU CAN COUNT', 'TO 5!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
    'next': ["NOW LET'S SPELL", 'PATO!'],
}

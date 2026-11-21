# Trilha do Pato Pateta, fase 1 — "As vogais"
# Cada vogal (bloquinho azul) vai para a casinha com a mesma letra, do outro lado do caminho.
#   A E I O U  bloquinhos     a e i o u  casinhas     D  o Pato Pateta
#   (demais letras: veja level1.py)
VISITOR = 'pato'      # quem bagunça a fase no começo (em vez do sapo Cururu)
GOAL = 5              # quantas entregas abrem o portão
CHARS = {'D': 'pato'}
CHARS.update({s: 'blk_' + s for s in 'AEIOU'})
CHARS.update({s.lower(): 'slot_' + s for s in 'AEIOU'})

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T,.......f....fT',
    'T.A......f..*.fT',
    'T....,...f....fT',
    'T.E......ffGfffT',
    'T......=.......T',
    'T.I..D.=..a.e..T',
    'T......=.......T',
    'T.O....=.i.o.u.T',
    'T......=.......T',
    'T.U....=..,....T',
    'T..,...=.....P.T',
    'T......=.......T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 9)

# o Pato Pateta tropeça em cada casinha (1ª letra) e o bloquinho vai parar longe (2ª letra)
CURURU = ['aA', 'eE', 'iI', 'oO', 'uU']

MESSAGES = [
    ('intro', ['OPA! O PATO PATETA', 'TROPEÇOU E ESPALHOU', 'AS VOGAIS!'], None),
    ('star1', ['MUITO BEM!', 'A, E, I, O, U', 'SÃO AS VOGAIS!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'BRINCAR COM', 'OS NÚMEROS!'], None),
]

MESSAGES_EN = {
    'intro': ['OOPS! THE GOOFY DUCK', 'TRIPPED AND SCATTERED', 'THE VOWELS!'],
    'star1': ['GREAT JOB!', 'A, E, I, O, U', 'ARE THE VOWELS!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
    'next': ["NOW LET'S PLAY", 'WITH NUMBERS!'],
}

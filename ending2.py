# Tela final da trilha do Pato Pateta: as vogais, os números e a palavra PATO no
# lugar; o Pipo, já galo, passeia e canta.
#   a e i o u  vogais   1 2 3 4 5  números   p q r s  P, A, T, O   D  o Pato Pateta
CHARS = {'D': 'pato'}
CHARS.update({s.lower(): 'slotf_' + s for s in 'AEIOU'})
CHARS.update({str(n): 'slotf_%d' % n for n in range(1, 6)})
CHARS.update({'pqrs'[i]: 'slotf_' + s for i, s in enumerate('PATO')})

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..............T',
    'T..............T',
    'T..............T',
    'T.,..........,.T',
    'T..a.e.i.o.u...T',
    'T..............T',
    'T..............T',
    'T..============T',
    'T..............T',
    'T..1.2.3.4.5...T',
    'T..............T',
    'T.....Dpqrs..,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (4, 8)

MESSAGES = [
    ('box', ['PARABÉNS! VOCÊ', 'APRENDEU AS VOGAIS', 'E OS NÚMEROS!'], None),
    ('credits', ['FEITO POR', 'PAPAI ANSELMO', 'E FILHO OLIVER'], None),   # autores (alterna com a de cima)
]

MESSAGES_EN = {
    'box': ['WELL DONE! YOU', 'LEARNED THE VOWELS', 'AND THE NUMBERS!'],
    'credits': ['MADE BY', 'DADDY ANSELMO', 'AND SON OLIVER'],
}

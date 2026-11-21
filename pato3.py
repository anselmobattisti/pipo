# Trilha do Pato Pateta, fase 3 — "Contar para atravessar"
# Pisar nos botões 1, 2 e 3 (nessa ordem: cada ponte leva ao próximo botão) faz as pontes aparecerem.
#   1 2 3  botões numerados     x v z  água que vira ponte (do 1, do 2, do 3)     D  o Pato Pateta
VISITOR = 'pato'
CHARS = {'D': 'pato', '1': 'nbutton_1', '2': 'nbutton_2', '3': 'nbutton_3'}

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..,.......*...T',
    'T..............T',
    'TWWWWWWWWWzWWWWT',
    'T.....,........T',
    'T..3.........P.T',
    'TWWWWvWWWWWWWWWT',
    'T..........2...T',
    'T.,............T',
    'TWWWWWWWxWWWWWWT',
    'T..............T',
    'T..1....D....,.T',
    'T..............T',
    'TTTTTTTTTTTTTTTT',
]

START = (6, 11)

CURURU = ['x', 'v', 'z']

MESSAGES = [
    ('intro', ['O PATO PATETA', 'DERRUBOU AS PONTES!', 'PISE NO 1, 2 E 3!'], None),
    ('star1', ['OBA!', 'VOCÊ CONTOU', '1, 2, 3!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'CONTAR', 'AS BOLINHAS!'], None),
]

MESSAGES_EN = {
    'intro': ['THE GOOFY DUCK BROKE', 'THE BRIDGES!', 'STEP ON 1, 2 AND 3!'],
    'star1': ['YAY!', 'YOU COUNTED', '1, 2, 3!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
    'next': ["NOW LET'S COUNT", 'THE DOTS!'],
}

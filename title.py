# Abertura: o ovo no ninho (N) racha e o Pipo nasce. Depois aparece o título.
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T,.....,....,..T',
    'T..P.......P...T',
    'T......,.......T',
    'T.B..........B.T',
    'T.....,..,.....T',
    'T..,.........,.T',
    'T......N.......T',
    'T.P..........P.T',
    'T....======....T',
    'T,..........,..T',
    'T..B....,...B..T',
    'T.,...P....,...T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 7)   # onde o ovo está (em cima do ninho)

# menu da abertura, uma tela de cada vez: o direcional troca a opção,
# qualquer outro botão confirma e vai para a próxima
MESSAGES = [
    ('lang', ['PORTUGUÊS', 'ENGLISH'], None),     # idioma
    ('sound', ['COM SOM', 'SEM SOM'], None),      # som ligado / desligado
    ('speed', ['DEVAGAR', 'NORMAL', 'RÁPIDO'], None),   # velocidade do Pipo
]

MESSAGES_EN = {
    'sound': ['SOUND ON', 'SOUND OFF'],
    'speed': ['SLOW', 'NORMAL', 'FAST'],
}

MENU = ['lang', 'sound', 'speed']   # ordem das telas do menu

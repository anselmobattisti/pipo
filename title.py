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
NLEVELS = 10      # fases da trilha mais comprida (as telas level0, level1, ... abaixo)

MESSAGES = [
    ('lang', ['PORTUGUÊS', 'ENGLISH'], None),     # idioma
    ('sound', ['COM SOM', 'SEM SOM'], None),      # som ligado / desligado
    ('speed', ['DEVAGAR', 'NORMAL', 'RÁPIDO'], None),   # velocidade do Pipo
    ('trail', ['TRILHA DO SAPO', 'TRILHA DO PATO PATETA'], None),   # qual trilha jogar
    # escolha da fase: o direcional troca o número (precisam ficar juntas e em ordem)
] + [('level%d' % i, ['QUAL FASE?', '<   %d   >' % (i + 1)], None) for i in range(NLEVELS)]

MESSAGES_EN = {
    'sound': ['SOUND ON', 'SOUND OFF'],
    'speed': ['SLOW', 'NORMAL', 'FAST'],
    'trail': ['TOAD TRAIL', 'GOOFY DUCK TRAIL'],
}
MESSAGES_EN.update({'level%d' % i: ['WHICH LEVEL?', '<   %d   >' % (i + 1)] for i in range(NLEVELS)})

MENU = ['lang', 'sound', 'speed', 'trail', 'level0']   # ordem das telas do menu (a última é a da fase)

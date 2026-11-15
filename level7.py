# Fase 7 — "Regar as flores"
# Pegue o regador (R) e encoste nos brotinhos secos: eles viram flores.
#   R regador   s i l  brotinhos (viram flor vermelha, azul, amarela)

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T,.....B......,T',
    'T..s.......O...T',
    'T.......,......T',
    'T.P.....R....i.T',
    'T..............T',
    'T..B.......P...T',
    'T,.....l.......T',
    'T..........,...T',
    'TffGff.....WWW.T',
    'T....f.....WWW.T',
    'T.*..f.....WFW.T',
    'T,...f......,..T',
    'TTTTTTTTTTTTTTTT',
]

START = (8, 6)

MESSAGES = [
    ('star1', ['QUE JARDIM', 'LINDO!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA É HORA', 'DO LANCHE!'], None),
]

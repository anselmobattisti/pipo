# Fase 8 — "Lanche dos bichinhos"
# Cada bichinho mostra no balão a comida que quer.
#   C cenoura  K milho  o osso      a coelho  g galinha  D cachorro (com fome)
#   A E J  balões (cenoura, milho, osso) — ficam logo acima do bichinho

LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.A...E...f...fT',
    'T.a...g...f.*.fT',
    'T.........f...fT',
    'T..J......ffGffT',
    'T..D...........T',
    'T.....,....C...T',
    'T.P............T',
    'T......K....B..T',
    'T..,...........T',
    'T.B.....o...P..T',
    'T.......,......T',
    'T,....B......,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 6)

MESSAGES = [
    ('star1', ['OS BICHINHOS', 'ESTÃO FELIZES!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAI', 'ANOITECER...'], None),
]

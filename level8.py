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

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['A', 'C', 'E', 'K', 'J', 'o']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'ESPALHOU O LANCHE', 'DOS BICHINHOS!'], None),
    ('star1', ['OS BICHINHOS', 'ESTÃO FELIZES!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAI', 'ANOITECER...'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'SCATTERED THE', "ANIMALS' SNACKS!"],
    'star1': ['THE ANIMALS', 'ARE HAPPY!'],
    'next': ["NOW IT'S", 'GETTING DARK...'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

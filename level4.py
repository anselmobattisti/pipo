# Fase 4 — "Esconde-esconde"
# Todos os arbustos parecem iguais. Encostar faz voar folhinhas; em três deles
# tem um amigo escondido:  h coelho   j passarinho   k ouriço   (B = arbusto vazio)
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.*.f....B....,T',
    'T...f..h....B..T',
    'TffGf.......,..T',
    'T.......B......T',
    'T.B..........j.T',
    'T.....,..B.....T',
    'T..k......,....T',
    'T.......P....B.T',
    'T.B....B.......T',
    'T....,.....B...T',
    'T.........WWWW.T',
    'T,....B...WWWW,T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 10)

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['h', 'j', 'k']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'ASSUSTOU OS AMIGOS', 'E ELES SE ESCONDERAM!'], None),
    ('star1', ['ACHOU TODOS', 'OS AMIGOS!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA APERTE', 'OS BOTÕES!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'SCARED THE FRIENDS', 'AND THEY HID!'],
    'star1': ['YOU FOUND ALL', 'YOUR FRIENDS!'],
    'next': ['NOW PRESS', 'THE BUTTONS!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

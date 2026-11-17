# Fase 4 — "Esconde-esconde"
# Todos os arbustos parecem iguais. Encostar faz voar folhinhas; em três deles
# tem um amigo escondido (coelho, passarinho, ouriço). Os três começam juntos
# brincando (FRIENDS); o sapo chega, eles se assustam e cada um corre para um
# arbusto (B) sorteado na hora — a cada vez os esconderijos mudam.
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T.*.f....B....,T',
    'T...f..B....B..T',
    'TffGf.......,..T',
    'T.......B......T',
    'T.B..........B.T',
    'T.....,..B.....T',
    'T..B......,....T',
    'T.......P....B.T',
    'T.B....B.......T',
    'T....,.....B...T',
    'T.........WWWW.T',
    'T,....B...WWWW,T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 10)

HIDE_RANDOM = True
FRIENDS = [(5, 8), (6, 8), (7, 8)]   # onde o coelho, o passarinho e o ouriço brincam juntos

# o sapo Cururu pula até perto dos amigos e os assusta
CURURU = [(6, 7, 'scare')]

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

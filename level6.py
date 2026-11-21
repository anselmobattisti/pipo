# Fase 6 — "Filhotes perdidos"
# Encostar num patinho faz ele seguir o Pipo em fila. Levando a fila até a
# mamãe pata, eles ficam com ela.   d patinho
# M mamãe pata (grande: ocupa 2x2 blocos de água; o M é o canto de cima à esquerda)
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..d......,....T',
    'T......B.....d.T',
    'T.P............T',
    'T....,....O....T',
    'T.B............T',
    'T.......d...B..T',
    'T..,...........T',
    'T.........fffffT',
    'TWWWMW....f....T',
    'TWWWWW....G.*..T',
    'TWWWWW....f....T',
    'TWWWWW..,.f..,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 11)

# o sapo Cururu bagunça a fase no começo: visita estas letras do mapa, nesta ordem
# (letras repetidas = a 1ª, 2ª, ... ocorrência, lendo o mapa linha por linha)
CURURU = ['d', 'd', 'd']

MESSAGES = [
    ('intro', ['O SAPO CURURU', 'ASSUSTOU', 'OS PATINHOS!'], None),
    ('star1', ['OS PATINHOS', 'ESTÃO COM', 'A MAMÃE!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA VAMOS', 'REGAR AS FLORES!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'intro': ['CURURU THE TOAD', 'SCARED', 'THE DUCKLINGS!'],
    'star1': ['THE DUCKLINGS', 'ARE WITH', 'THEIR MOM!'],
    'next': ["NOW LET'S WATER", 'THE FLOWERS!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

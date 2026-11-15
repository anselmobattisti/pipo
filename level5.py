# Fase 5 — "Botões e pontes"
# Pisar num botão faz aparecer a ponte da mesma cor.
#   7 8 9  botões (vermelho, azul, amarelo)
#   x v z  água onde aparece a ponte (vermelha, azul, amarela)
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T....W....W....T',
    'T.,..W..,.W.*..T',
    'T....W....W....T',
    'T.7..W....WWzWWT',
    'T....x..8.W....T',
    'T.P..W....v....T',
    'T....W....W....T',
    'T..,.W..B.W..9.T',
    'T....W....W....T',
    'T.B..W.,..W.,..T',
    'T....W....W....T',
    'T,...W....W..P.T',
    'TTTTTTTTTTTTTTTT',
]

START = (3, 9)

MESSAGES = [
    ('star1', ['OBA!', 'AS PONTES', 'APARECERAM!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA AJUDE', 'OS PATINHOS!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'star1': ['YAY!', 'THE BRIDGES', 'APPEARED!'],
    'next': ['NOW HELP', 'THE DUCKLINGS!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

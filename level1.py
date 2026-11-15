# Fase 1 — "O Jardim do Pipo"
BOUNCY = False
#
# Mapa 16x14 (cada letra = um bloco de 16x16 pixels)
#   T árvore   . grama   , florzinhas   = caminho   W água   F sapo
#   B arbusto  f cerca   G portão       S placa     O pedra  P flor grande
#   r b y  bolas (vermelha, azul, amarela)
#   1 2 3  cestas (vermelha, azul, amarela)
#   * estrela (prêmio)
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T..,....,.f...fT',
    'T.r...B...f.*.fT',
    'T.........f...fT',
    'T.S...====ffGffT',
    'T.....=======..T',
    'T.1...=..O...b.T',
    'T.....=.....P..T',
    'TWWWW.=..2...,.T',
    'TWWWF.=.......yT',
    'TWWW..=..,..3..T',
    'T.,...=....B...T',
    'T.P.....,.....,T',
    'TTTTTTTTTTTTTTTT',
]

START = (7, 7)  # coluna, linha do Pipo

# Mensagens: (nome, [até 3 linhas], próxima mensagem ou None)
# Só a estrela mostra texto; as outras ações têm só animação.
MESSAGES = [
    ('star1', ['PARABÉNS!', 'VOCÊ ACHOU A', 'ESTRELA!'], 'grow'),
    ('grow', ['OLHA SÓ!', 'O PIPO CRESCEU!'], 'next'),
    ('next', ['AGORA AS BOLAS', 'VÃO PULAR!'], None),
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'star1': ['WELL DONE!', 'YOU FOUND', 'THE STAR!'],
    'next': ['NOW THE BALLS', 'WILL BOUNCE!'],
    'grow': ['LOOK!', 'PIPO GREW UP!'],
}

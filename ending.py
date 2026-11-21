# Tela final: chegam o papai (Seu Popi) e a mamãe (Senhora Pipa) do Pipo; eles fazem
# uma coberta para o sapo Cururu, que estava com frio e por isso fazia bagunça.
# Depois: todos os amigos felizes; o Pipo, já galo, passeia e canta.
# (a cena é montada em build.py, ending_cutscene)
#   ( ) [  flores   & coelho feliz   % cachorro feliz   $ balão de coração   @ ninho cheio
LEVEL = [
    'TTTTTTTTTTTTTTTT',
    'T(.)..[..(.)..[T',
    'T..............T',
    'T.P..,....,..P.T',
    'T..............T',
    'T.$..$......$..T',
    'T.&..Q......%..T',
    'T..............T',
    'T..============T',
    'T..............T',
    'TWWWWMW........T',
    'TWWWWWW.....@.QT',
    'T,....P......,.T',
    'TTTTTTTTTTTTTTTT',
]

START = (4, 8)

MESSAGES = [
    ('parents', ['OLHA! CHEGARAM O', 'PAPAI SEU POPI E A', 'MAMÃE SENHORA PIPA!'], None),
    ('blanket', ['ELES ESTÃO FAZENDO', 'UMA COBERTA PARA', 'O SAPO CURURU!'], None),
    ('warm', ['AGORA O CURURU', 'ESTÁ QUENTINHO E', 'NÃO FAZ MAIS BAGUNÇA!'], None),
    ('box', ['TODOS OS AMIGOS', 'ESTÃO FELIZES!'], None),
    ('credits', ['FEITO POR', 'PAPAI ANSELMO', 'E FILHO OLIVER'], None),   # autores (alterna com a de cima)
]

# Inglês (o que não estiver aqui usa o texto em português)
MESSAGES_EN = {
    'parents': ['LOOK! HERE COME', 'DADDY MR. POPI AND', 'MOMMY MRS. PIPA!'],
    'blanket': ['THEY ARE MAKING', 'A BLANKET FOR', 'CURURU THE TOAD!'],
    'warm': ['NOW CURURU IS', 'NICE AND WARM.', 'NO MORE MESSES!'],
    'box': ['ALL THE FRIENDS', 'ARE HAPPY!'],
    'credits': ['MADE BY', 'DADDY ANSELMO', 'AND SON OLIVER'],
}

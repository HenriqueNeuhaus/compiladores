# Escopo léxico do subconjunto de Python

Este documento define **o que o scanner reconhece** (Etapa 3). A implementação está em [`backend/app/scanner.py`](../backend/app/scanner.py) e os testes em [`backend/tests/test_scanner.py`](../backend/tests/test_scanner.py).

## 1. Categorias de token

| Categoria | Padrão (regra de formação) | Exemplos válidos | Exemplos inválidos ou fora do subconjunto |
| --- | --- | --- | --- |
| `PALAVRA_RESERVADA` | Uma das palavras `if`, `elif`, `else`, `while`, `True`, `False` | `if`, `while`, `True` | `If`, `WHILE` (viram identificadores, pois Python diferencia maiúsculas) |
| `IDENTIFICADOR` | Letra ASCII ou `_`, seguida de letras ASCII, dígitos ou `_` | `nota`, `_x1`, `print`, `soma_total` | `preço` (acento); `1x` começa com dígito e gera `literal_numerico_malformado` |
| `LITERAL_INTEIRO` | Um ou mais dígitos decimais, sem zeros à esquerda (exceto o próprio `0`) | `0`, `42`, `1000` | `007`, `0x1F`, `1_000`, `0b10` |
| `LITERAL_REAL` | Dígitos, ponto e pelo menos um dígito | `3.14`, `0.5`, `10.0` | `3.`, `.5`, `1e5`, `2.5e-3` |
| `LITERAL_STRING` | Texto entre aspas simples ou duplas, na mesma linha; aceita escapes como `\"` e `\n` | `"Aprovado"`, `'x'`, `"diz \"oi\""` | `"sem fechar`, `"""três aspas"""`, `f"oi {x}"` |
| `OPERADOR_ARITMETICO` | `+` `-` `*` `/` `%` | `a + b`, `n % 2` | `**`, `//`, `+=` |
| `OPERADOR_RELACIONAL` | `==` `!=` `<` `<=` `>` `>=` | `x >= 7`, `a != b` | `<>` e `=<` não existem: são lidos como dois operadores separados (`<` `>` e `=` `<`), e o erro aparece na análise sintática |
| `OPERADOR_ATRIBUICAO` | `=` | `x = 1` | `:=`, `+=` |
| `DELIMITADOR` | `(` `)` `:` `,` | `print(a, b)`, `if x:` | `[`, `{`, `;`, `.` |
| `NOVA_LINHA` | Fim de uma linha lógica que contém pelo menos um token | `↵` depois de `x = 1` | Não é gerado para linhas em branco, linhas só com comentário nem quebras dentro de parênteses |
| `INDENT` | O recuo da linha é **maior** que o topo da pilha de indentação | 4 espaços depois de `if x:` | Recuo com tabulação |
| `DEDENT` | O recuo da linha é **menor** que o topo da pilha (um por nível fechado) | volta à coluna 1 depois de um bloco | Recuo que não corresponde a nenhum nível aberto |
| `FIM_DE_ARQUIVO` | Fim do código | sempre o último token | — |

Elementos lidos e **descartados** (não geram token):

| Elemento | Regra | Onde aparece na resposta |
| --- | --- | --- |
| Espaços entre tokens | Espaço e tabulação no meio da linha | Não aparecem |
| Comentário | De `#` até o fim da linha | Lista `comentarios` e passo do tipo `ignorado` |
| Linha em branco | Linha vazia ou só com espaços ou comentário | Passo do tipo `ignorado` |

## 2. Decisões de projeto

| Decisão | Justificativa |
| --- | --- |
| `print` é `IDENTIFICADOR` | Em Python 3, `print` é uma função, não palavra reservada. Manter essa classificação evita ensinar um conceito errado. |
| `True` e `False` são `PALAVRA_RESERVADA` | Em Python 3 são palavras reservadas (não podem ser usadas como nomes de variável). |
| Palavras reservadas de Python fora do subconjunto (`for`, `def`, `and` etc.) geram **aviso**, não erro | Elas são lexicamente válidas; quem deve rejeitá-las é a análise sintática (Etapa 4). O token sai como `PALAVRA_RESERVADA` com `fora_do_subconjunto: true`. |
| Operadores de Python fora do subconjunto (`**`, `//`, `+=`...) geram **erro** com explicação | Sem essa regra, `//` viraria dois `/` válidos e o estudante não entenderia o problema. O scanner usa o casamento mais longo e reconhece o operador inteiro antes de recusar. |
| Identificadores apenas ASCII | Python aceita `preço`, mas muitos materiais de ensino e linguagens não. A mensagem mostra o caractere e o nome Unicode dele. |
| Casamento mais longo (*maximal munch*) | `>=` é um token, não `>` seguido de `=`. O passo a passo mostra quando o scanner olhou um caractere à frente. |
| Dentro de parênteses, a quebra de linha não gera `NOVA_LINHA` nem mexe na indentação | Mesmo comportamento do Python (junção implícita de linhas). |
| `NOVA_LINHA` implícita no fim do arquivo | Se a última linha não termina com quebra, o scanner gera uma `NOVA_LINHA` sem texto, como o `tokenize` do Python. |
| Largura da tabulação = 8 | Igual ao Python, para o cálculo da coluna de tabulações no meio da linha. Na indentação, tabulação é erro. |
| `)` sem par vira token normal | Parênteses desbalanceados são um problema sintático. Só `(` não fechado até o fim do código gera erro léxico, porque impede o scanner de decidir onde termina a linha lógica. |
| Erros não interrompem a análise | O scanner registra o erro, pula o trecho inválido e continua, para mostrar todos os problemas de uma vez (limite de 100 erros). |
| Erro léxico retorna HTTP 200 com `sucesso: false` | O pedido foi atendido: o servidor analisou o código. O erro é do programa analisado, não da requisição. |

## 3. Erros e avisos léxicos

| Código | Tipo | Exemplo de entrada | Mensagem (resumo) |
| --- | --- | --- | --- |
| `caractere_nao_reconhecido` | Erro | `x = 1 ? 2` | caractere não reconhecido `'?'` (para caracteres não ASCII, inclui o nome Unicode, por exemplo *en dash*) |
| `operador_fora_do_subconjunto` | Erro | `x **= 2`, `a // b`, `lista[0]` | `'**='` existe em Python (atribuição com potência), mas não faz parte do subconjunto |
| `identificador_com_caractere_nao_ascii` | Erro | `preço = 1` | o identificador `'preço'` contém `'ç'` |
| `string_nao_fechada` | Erro | `x = "oi` | a string não foi fechada antes do fim da linha |
| `string_com_tres_aspas` | Erro | `x = """oi"""` | strings com três aspas não fazem parte do subconjunto |
| `prefixo_de_string` | Erro | `f"oi"`, `r"\d"` | strings com prefixo não fazem parte do subconjunto |
| `literal_real_incompleto` | Erro | `x = 1.` ou `x = .5` | deve haver dígito depois (e antes) do ponto |
| `literal_numerico_malformado` | Erro | `0x1F`, `1e5`, `1_000`, `12abc` | explica a causa: outra base, notação científica, separador `_` ou formato inválido |
| `zeros_a_esquerda` | Erro | `x = 007` | Python não permite zeros à esquerda |
| `indentacao_com_tabulacao` | Erro | linha recuada com Tab | indente apenas com espaços |
| `indentacao_inconsistente` | Erro | recuo de 2 espaços entre blocos de 0 e 4 | o recuo não corresponde a nenhum nível aberto |
| `continuacao_com_barra` | Erro | `x = 1 + \` | use parênteses para quebrar a expressão |
| `parentese_nao_fechado` | Erro | `print(x` | o `(` aberto aqui não foi fechado até o fim do código |
| `palavra_reservada_fora_do_subconjunto` | Aviso | `for x:` | `'for'` é palavra reservada de Python, mas não faz parte do subconjunto |

Formato das mensagens: `Erro léxico na linha L, coluna C: ...` e `Aviso na linha L, coluna C: ...`. Linhas e colunas começam em 1. A coluna conta caracteres (não bytes), então `ç` ocupa uma coluna.

## 4. Como a indentação é tratada

O scanner mantém uma **pilha de níveis de recuo**, que começa com `[0]`. No início de cada linha lógica:

1. Mede o recuo (número de espaços).
2. Se for **maior** que o topo, empilha o novo nível e gera `INDENT`.
3. Se for **menor**, desempilha e gera um `DEDENT` para cada nível removido até chegar a um nível igual. Se não encontrar um nível igual, gera o erro `indentacao_inconsistente`.
4. No fim do código, gera um `DEDENT` para cada nível que ainda está aberto.

A interface mostra essa pilha a cada passo, em **Pilha de indentação**.

## 5. Validação contra o Python

O teste `TestComparacaoComTokenizeDoPython` compara, token a token (categoria, texto, linha e coluna), a saída do scanner com a do módulo `tokenize` da biblioteca padrão do Python em todos os exemplos da interface, em programas de referência e em **300 programas gerados aleatoriamente** (semente fixa 2026). Como o `tokenize` conta colunas a partir de 0, a comparação soma 1 às colunas dele.

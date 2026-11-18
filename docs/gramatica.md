# Gramática do subconjunto de Python

Este documento define **o que o parser reconhece** (Etapa 4). A implementação está em [`backend/app/parser.py`](../backend/app/parser.py), e as produções abaixo são as mesmas da constante `GRAMATICA` desse arquivo: o teste `TestGramaticaDocumentada` falha se o código e este documento divergirem.

## 1. Gramática formal (EBNF)

Notação: `{ x }` repete x zero ou mais vezes; `[ x ]` torna x opcional; `|` separa alternativas; `( )` agrupa; texto entre aspas é um terminal escrito exatamente assim; nomes em MAIÚSCULAS são categorias de token do scanner; nomes em minúsculas são não terminais; `;` encerra a regra.

```ebnf
programa = { instrucao } FIM_DE_ARQUIVO ;
instrucao = atribuicao | chamada_simples | condicional | repeticao ;
atribuicao = IDENTIFICADOR "=" expressao NOVA_LINHA ;
chamada_simples = chamada NOVA_LINHA ;
condicional = "if" expressao ":" bloco { "elif" expressao ":" bloco } [ "else" ":" bloco ] ;
repeticao = "while" expressao ":" bloco ;
bloco = NOVA_LINHA INDENT instrucao { instrucao } DEDENT ;
expressao = comparacao ;
comparacao = soma [ OPERADOR_RELACIONAL soma ] ;
soma = termo { ( "+" | "-" ) termo } ;
termo = fator { ( "*" | "/" | "%" ) fator } ;
fator = ( "+" | "-" ) fator | primario ;
primario = LITERAL_INTEIRO | LITERAL_REAL | LITERAL_STRING | "True" | "False" | chamada | IDENTIFICADOR | "(" expressao ")" ;
chamada = IDENTIFICADOR "(" [ argumentos ] ")" ;
argumentos = expressao { "," expressao } ;
```

- **Símbolo inicial:** `programa`.
- **Não terminais (15):** `programa`, `instrucao`, `atribuicao`, `chamada_simples`, `condicional`, `repeticao`, `bloco`, `expressao`, `comparacao`, `soma`, `termo`, `fator`, `primario`, `chamada`, `argumentos`.
- **Terminais:** os tokens da Etapa 3 (tabela da seção 2).

### Como ler a gramática

- Um **programa** é uma sequência de instruções. Cada instrução simples termina com `NOVA_LINHA`, o token que o scanner gera no fim de cada linha lógica. É o equivalente ao `;` de C.
- Um **bloco** não usa chaves: ele começa com `NOVA_LINHA INDENT` e termina com `DEDENT`. Esses tokens vêm do scanner, que já transformou a indentação em estrutura. Por isso a gramática não precisa tratar espaços.
- As regras de expressão formam uma **escada de precedência**: `comparacao → soma → termo → fator → primario`. Quanto mais abaixo na escada, mais forte o operador "gruda" nos operandos.

## 2. Correspondência entre terminais e tokens da Etapa 3

| Terminal na gramática | Categoria de token (Etapa 3) | Lexemas |
| --- | --- | --- |
| `IDENTIFICADOR` | `IDENTIFICADOR` | `nota`, `print`, `_x1` |
| `LITERAL_INTEIRO` | `LITERAL_INTEIRO` | `0`, `42` |
| `LITERAL_REAL` | `LITERAL_REAL` | `3.14` |
| `LITERAL_STRING` | `LITERAL_STRING` | `"texto"`, `'x'` |
| `"if"`, `"elif"`, `"else"`, `"while"`, `"True"`, `"False"` | `PALAVRA_RESERVADA` | o próprio lexema |
| `"+"`, `"-"`, `"*"`, `"/"`, `"%"` | `OPERADOR_ARITMETICO` | o próprio lexema |
| `OPERADOR_RELACIONAL` | `OPERADOR_RELACIONAL` | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| `"="` | `OPERADOR_ATRIBUICAO` | `=` |
| `"("`, `")"`, `":"`, `","` | `DELIMITADOR` | o próprio lexema |
| `NOVA_LINHA` | `NOVA_LINHA` | fim de linha lógica |
| `INDENT` / `DEDENT` | `INDENT` / `DEDENT` | início e fim de bloco |
| `FIM_DE_ARQUIVO` | `FIM_DE_ARQUIVO` | fim do código |

**O scanner não precisou mudar.** Todos os terminais da gramática já eram produzidos na Etapa 3, e o teste `test_mesmos_tokens_da_etapa_3` confirma que a saída do scanner continua igual. Comentários e espaços continuam descartados pelo scanner e não aparecem na gramática.

## 3. Precedência e associatividade

| Nível (do mais fraco ao mais forte) | Regra | Operadores | Associatividade |
| --- | --- | --- | --- |
| 1 | `comparacao` | `==` `!=` `<` `<=` `>` `>=` | **não associativa**: no máximo um operador por comparação |
| 2 | `soma` | `+` `-` (binários) | à esquerda |
| 3 | `termo` | `*` `/` `%` | à esquerda |
| 4 | `fator` | `+` `-` (unários) | à direita (`- - x` = `-(-x)`) |
| 5 | `primario` | parênteses, chamada, literais e nomes | — |

Exemplos (todos verificados nos testes e comparados com o módulo `ast` do Python):

| Código | Organização reconhecida | AST |
| --- | --- | --- |
| `r = 10 + 5 * 2` | `10 + (5 * 2)` | `ADICAO(10, MULTIPLICACAO(5, 2))` |
| `r = 20 - 5 - 3` | `(20 - 5) - 3` | `SUBTRACAO(SUBTRACAO(20, 5), 3)` |
| `r = (10 + 5) * 2` | parênteses mudam a ordem | `MULTIPLICACAO(ADICAO(10, 5), 2)` |
| `r = -a * b` | `(-a) * b` | `MULTIPLICACAO(OPERACAO_UNARIA(a), b)` |
| `r = a + 1 > b * 2` | `(a + 1) > (b * 2)` | `COMPARACAO(ADICAO(a, 1), MULTIPLICACAO(b, 2))` |

**Por que a associatividade à esquerda aparece com `{ }`:** a regra `soma = termo { ("+" | "-") termo }` é a forma sem recursão à esquerda de `soma = soma "+" termo | termo`. Um parser descendente recursivo entraria em laço infinito com a versão recursiva à esquerda. O laço `{ }` lê os operandos da esquerda para a direita, e o parser monta cada novo nó com **o que já foi lido à esquerda**. É isso que produz `(20 - 5) - 3`.

**Por que a comparação não é associativa:** em Python, `a < b < c` significa `a < b and b < c` (comparação encadeada), e não `(a < b) < c`. Como `and` não faz parte do subconjunto, a gramática aceita um único operador relacional por comparação. `a < b < c` gera o erro `comparacao_encadeada`, que explica isso. Já `(a < b) == True` é aceito, porque os parênteses formam um novo `primario`.

## 4. Decisões que tornam a gramática LL

O parser é descendente recursivo e decide cada regra olhando o próximo token (*lookahead*):

| Ponto de decisão | Conjuntos FIRST | Como o parser decide |
| --- | --- | --- |
| `instrucao` | `condicional`: `if`; `repeticao`: `while`; `atribuicao` e `chamada_simples`: `IDENTIFICADOR` | `if` e `while` decidem com 1 token. Atribuição e chamada começam com o mesmo token, então o parser olha também o segundo: `=` indica atribuição e `(` indica chamada (LL(2) nesse ponto) |
| `primario` | `chamada` e `IDENTIFICADOR` começam com `IDENTIFICADOR` | Mesmo critério: se o segundo token é `(`, é chamada |
| `fator` | `+`/`-` ou FIRST(`primario`) | Operador aditivo no início de um fator é sinal unário |
| `condicional` | depois do bloco, `elif` ou `else` | `elif` repete o laço; `else` fecha a estrutura; qualquer outro token encerra o `if` |
| Laços `{ }` de `soma` e `termo` | FOLLOW inclui `)`, `,`, `:`, `NOVA_LINHA` e operadores relacionais | O laço continua apenas enquanto o próximo token for um operador do próprio nível |

Não há recursão à esquerda, e todas as alternativas se distinguem com no máximo dois tokens. Nada precisa ser desfeito (*backtracking*).

## 5. Construções suportadas e fora do escopo

| Suportado | Exemplo |
| --- | --- |
| Atribuição simples | `media = (a + b) / 2` |
| Chamada de função como instrução ou dentro de expressão | `print("x", y)`, `z = f(1) * 2` |
| Expressões aritméticas com `+ - * / %`, sinais unários e parênteses | `-(a + 1) % 3` |
| Uma comparação com `== != < <= > >=` | `nota >= 7` |
| Literais inteiros, reais, strings e `True`/`False` | `3.5`, `"oi"`, `True` |
| `if` com quantos `elif` forem necessários e `else` opcional | ver exemplos |
| `while` | `while i < 10:` |
| Blocos aninhados em qualquer profundidade (até o limite de 200 regras abertas) | `while` dentro de `if` dentro de `while` |
| Programa vazio ou só com comentários | gera `PROGRAMA` sem filhos |

| Fora do escopo | Exemplo | O que acontece |
| --- | --- | --- |
| Operadores lógicos `and`, `or`, `not` | `if a and b:` | erro `operador_logico_fora_do_subconjunto` (o scanner também avisa) |
| Comparações encadeadas | `0 < x < 10` | erro `comparacao_encadeada` |
| `for`, `def`, `return`, `import`, `class` e demais palavras de Python | `for i in x:` | erro `palavra_fora_do_subconjunto` |
| Atribuição composta, múltipla ou desempacotamento | `a = b = 1`, `a, b = 1, 2` | erro `fim_de_instrucao_esperado` |
| Expressão sozinha como instrução (só chamadas são aceitas) | `x + 1` | erro `expressao_sem_efeito` |
| Bloco na mesma linha do `if` | `if x: y = 1` | erro `bloco_na_mesma_linha` |
| Tuplas, listas, dicionários, índices e atributos | `()`, `[1]`, `a.b` | erro léxico (`[`, `.`) ou sintático (`()`) |
| Verificar se a função chamada existe, ou se a variável foi definida antes | `y = z + 1` com `z` indefinido | aceito pela sintaxe; será tratado na **análise semântica (Etapa 5)** |

## 6. Exemplos de programas

### Válidos

```python
# 1. Precedência
resultado = 10 + 5 * 2

# 2. Condicional completo
nota = 7.5
if nota >= 7:
    print("Aprovado")
elif nota >= 5:
    print("Recuperação")
else:
    print("Reprovado")

# 3. Laço com bloco aninhado
contador = 1
while contador <= 5:
    if contador % 2 == 0:
        print(contador, "é par")
    contador = contador + 1
```

### Inválidos (erros sintáticos intencionais)

Todos os códigos abaixo têm tokens válidos, ou seja, nenhum erro léxico. O problema está na ordem dos tokens.

| Código | Erro (`codigo`) | Mensagem do parser (resumida) |
| --- | --- | --- |
| `if x > 5` + bloco | `dois_pontos_ausente` | era esperado ':' no fim da linha do if, mas foi encontrado o fim da linha |
| `x = 5 +` | `operando_ausente` | o operador '+' precisa de um valor à direita |
| `x = 5 + * 2` | `operadores_consecutivos` | dois operadores seguidos: '+' e '*' |
| `x = 1 2` | `fim_de_instrucao_esperado` | era esperado o fim da instrução, mas foi encontrado '2'. Falta um operador entre '1' e '2'? |
| `print("a" "b")` | `parentese_nao_fechado` | era esperado ')' para fechar a chamada de 'print'… Faltou uma vírgula entre os argumentos? |
| `else:` sem `if` | `else_sem_if` | 'else' só pode aparecer logo depois do bloco de um if… |
| `True = 1` | `palavra_reservada_como_identificador` | 'True' é uma palavra reservada e não pode ser usada como nome de variável |
| `5 = x` | `atribuicao_invalida` | o lado esquerdo de '=' deve ser apenas o nome de uma variável |
| `if x = 1:` | `atribuicao_na_condicao` | '=' guarda um valor e não pode ser usado em uma condição. Para comparar use '==' |
| `x == 1` | `expressao_sem_efeito` | a comparação '==' sozinha não faz nada. Para guardar um valor use '=' |
| `if x:` + linha sem recuo | `bloco_ausente` | o if da linha 1 precisa de um bloco: a linha seguinte deve estar recuada |
| `while x < 3:` no fim do código | `fim_inesperado` | o código terminou antes do bloco do while aberto na linha 1 |
| `x = 1` + linha recuada | `indentacao_inesperada` | esta linha está recuada, mas não há um if, elif, else ou while… |

A lista completa dos 26 códigos de erro, com as regras de recuperação, está na seção 8 do README.

## 7. AST e árvore de derivação

O parser produz duas árvores para o mesmo programa:

- **Árvore de derivação (concreta):** registra **todas** as regras aplicadas e **todos** os tokens consumidos. Para `x = 1`, o valor `1` fica no fim da cadeia `expressao → comparacao → soma → termo → fator → primario → LITERAL_INTEIRO`.
- **AST (abstrata):** guarda só o que importa para as próximas fases: `ATRIBUICAO(IDENTIFICADOR x, LITERAL_INTEIRO 1)`. Regras que só repassam o resultado (como `expressao` e `termo` sem operador), parênteses, `:` e tokens de estrutura desaparecem. A hierarquia da árvore já expressa a precedência.

A interface mostra as duas, com uma explicação dessa diferença. Os tipos de nó da AST estão na seção 9 do README.

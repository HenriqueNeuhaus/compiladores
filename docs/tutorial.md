# Tutorial: sua primeira análise léxica

Este roteiro leva cerca de 20 minutos e mostra como usar o Visualizador para entender o que fazem o **scanner** (analisador léxico) e o **parser** (analisador sintático). Antes de começar, suba a aplicação (`docker compose up --build -d --wait`) e abra **http://localhost:8080**.

![Tela inicial com o tutorial "Como usar"](interface/tela-inicial.png)

## 1. Analise um programa pronto

1. No campo **Exemplo**, escolha **Estrutura condicional**.
2. Clique em **Analisar código**.

O painel **Resultado** informa quantos tokens foram reconhecidos e mostra a contagem por categoria. Abaixo do editor aparece o painel **Análise léxica passo a passo**, com o código colorido e a tabela de tokens.

![Resultado da análise do exemplo condicional](interface/tela-principal.png)

> **Para pensar:** o programa tem 7 linhas, mas o scanner gerou 41 tokens. De onde vêm tantos?

## 2. Leia o código colorido e a tabela

Cada cor é uma categoria de token (a legenda fica embaixo do código):

- roxo: palavra reservada (`if`, `elif`, `else`);
- azul: identificador (`nota`, `print`);
- laranja: número; verde: string;
- vermelho: operador; cinza: delimitador;
- faixas amarelas: recuo que gerou `INDENT`;
- `↵` marca uma `NOVA_LINHA` e `⇤` marca um `DEDENT`.

A tabela lista os mesmos tokens com **tipo, lexema, linha e coluna**. O lexema é o trecho exato do código; o tipo é a categoria que o scanner atribuiu a ele.

> **Para pensar:** por que `print` aparece como IDENTIFICADOR e não como palavra reservada? (Resposta: em Python 3, `print` é uma função comum.)

## 3. Acompanhe o scanner passo a passo

1. Clique em **⏮** para voltar ao primeiro passo.
2. Use **▶** (ou a seta para a direita do teclado) para avançar um token por vez. Também é possível clicar em **Reproduzir**, arrastar a barra ou clicar em um token do código ou no número dele na tabela.

A cada passo, o token atual fica destacado, o que ainda não foi lido fica esmaecido e uma frase explica a decisão do scanner, por exemplo:

- "Leu 'if': tem a forma de um identificador, mas está na lista de palavras reservadas → PALAVRA_RESERVADA."
- "Leu '>=': o scanner olhou um caractere à frente e escolheu o operador mais longo..."

![Passo a passo no meio da linha 2](interface/passo-a-passo.png)

## 4. Observe a pilha de indentação

Avance até a linha 3 (`    print("Aprovado")`). Repare na **Pilha de indentação**: ela passa de `0` para `0 4`, e o scanner gera um `INDENT`. Na linha 4 (`elif`), o recuo volta a 0: o nível 4 sai da pilha e o scanner gera um `DEDENT`.

> **Exercício:** escolha o exemplo **Repetição com blocos aninhados** e descubra quantos `DEDENT` o scanner gera na linha 8 e por quê.

## 5. Provoque erros léxicos

1. Escolha o exemplo **Erros léxicos** e clique em **Analisar código**.
2. Leia a lista de erros. Cada mensagem diz a linha, a coluna e o motivo.
3. Clique em **Mostrar no código** em um dos erros: o trecho fica selecionado no editor e o passo a passo vai até ele.

![Lista de erros léxicos](interface/erros-lexicos.png)

Repare que o scanner **não para no primeiro erro**: ele pula o trecho inválido e continua, então os tokens válidos continuam na tabela.

> **Exercício:** corrija os erros um por um (troque `preço` por `preco`, apague o `$`, feche as aspas e troque `//` por `/`) e analise de novo a cada correção.

## 6. Erro léxico × erro sintático

Escolha o exemplo **Erro sintático (tokens válidos)**. Falta o `:` depois de `if x > 5`, mas a análise léxica termina **sem erros**: todos os lexemas são tokens válidos. O problema está na **ordem** dos tokens, e quem verifica a ordem é a análise sintática. O resultado fica roxo, com o selo "Erro sintático", e mostra o que foi encontrado (fim da linha), o que era esperado (`:`) e a regra da gramática que exige o `:`.

Agora volte ao exemplo **Erros léxicos**: o painel da análise sintática avisa que o parser **não foi executado**. Com um token faltando, ele acusaria erros que você não cometeu.

## 7. Experimente

Algumas ideias para escrever no editor:

| Escreva | O que observar |
| --- | --- |
| `x = 3.` | número real incompleto |
| `if x>=1:` (sem espaços) | o scanner separa os tokens mesmo sem espaços |
| `y = 2 ** 3` | operador de Python fora do subconjunto |
| `for i in x:` | aviso: palavra reservada fora do subconjunto |
| um bloco recuado com 2 espaços e outro com 4 | erro de indentação inconsistente |
| `print("a",` e uma quebra de linha antes de `"b")` | dentro de parênteses a quebra de linha não gera `NOVA_LINHA` |

A lista completa de categorias, decisões e erros está em [`escopo-lexico.md`](escopo-lexico.md).

## 8. Leia a árvore sintática (AST)

1. Escolha o exemplo **Precedência e associatividade** e clique em **Analisar código**.
2. Desça até **Análise sintática e árvore sintática abstrata (AST)**. Cada linha da árvore é um nó; o símbolo e a cor indicam a categoria (◆ instrução, ● operação, ■ valor, ▲ nome, ⑂ controle de fluxo, ▣ estrutura).
3. Compare as atribuições `r1` e `r3`. Em `r1 = 10 + 5 * 2`, a `MULTIPLICACAO` fica **dentro** da `ADICAO`: é calculada primeiro. Em `r3 = (10 + 5) * 2`, os parênteses invertem a posição.
4. Clique na `MULTIPLICACAO`. O trecho `5 * 2` fica destacado no código e o painel ao lado mostra a regra (`termo = fator { ... } ;`), o papel do nó (`direita`), a posição e os tokens que o formam.

![Árvore com o nó MULTIPLICACAO selecionado](interface/ast-arvore.png)

> **Para pensar:** em `r2 = 20 - 5 - 3`, qual `SUBTRACAO` fica mais acima na árvore? O que isso diz sobre a ordem do cálculo?

Experimente também o teclado (setas para navegar, ← e → para recolher e expandir), o filtro por tipo e **Exportar JSON**.

## 9. Veja o parser trabalhar, passo a passo

1. Clique em **⏮** no reprodutor da análise sintática e avance com **▶**.
2. Observe a **pilha de regras abertas**: para ler o `10`, o parser entra em `programa → instrucao → atribuicao → expressao → comparacao → soma → termo → fator → primario`. Cada regra é uma função chamando a próxima: é isso que significa **descendente recursivo**.
3. A **fita de tokens** mostra o próximo token a ser lido. Os nós ainda não construídos ficam esmaecidos: as folhas (`10`, `5`, `2`) aparecem antes das operações, porque o parser só monta um nó depois de ter os filhos.
4. Troque para **Árvore de derivação** e compare o tamanho com a AST: a derivação guarda todas as regras e todos os tokens; a AST guarda só o essencial.

![Passo a passo do parser](interface/ast-passo-a-passo.png)

## 10. Provoque erros sintáticos

Escolha **Erros sintáticos (vários)**. O parser encontra quatro erros diferentes e continua depois de cada um (recuperação de erros). Use **Mostrar no código** para ir a cada erro.

| Escreva | O que observar |
| --- | --- |
| `x = 5 + * 2` | dois operadores seguidos |
| `True = 1` | palavra reservada usada como nome |
| `x == 1` | o parser sugere usar `=` |
| `if a and b:` | operador lógico fora do subconjunto |
| `a < b < c` | comparação encadeada |
| `else:` sozinho | `else` sem `if` |

## 11. Pergunte ao assistente de IA (opcional)

Se o assistente estiver disponível (o selo no painel **Assistente de IA** fica verde), selecione um nó e clique em **Explicar este nó com IA**, ou clique em **Entender erro com IA** em um erro sintático. Também é possível escolher uma das perguntas sugeridas. A resposta é gerada pelo Llama 3.2 a partir dos resultados reais do compilador, mas **pode conter erros**: confira sempre com a árvore e as mensagens do parser.

A gramática completa está em [`gramatica.md`](gramatica.md).

# Casos de teste (Etapa 4 / Tarefa 4)

> Arquivo gerado por `scripts/casos_de_teste.py` a partir de [`backend/tests/casos_de_teste.json`](../backend/tests/casos_de_teste.json). Não edite à mão: altere o JSON e gere de novo. Voltar ao [README](../README.md).

São **45 casos**: 40 verificam comportamento já implementado e 5 descrevem erros semânticos previstos para a Etapa 5. Todos são executados por `backend/tests/test_casos_de_teste.py`:

```bash
docker compose --profile testes run --rm testes-backend \
  python -m unittest tests.test_casos_de_teste -v
```

Nos casos semânticos previstos, o teste confere hoje apenas que o programa passa pelas análises léxica e sintática (condição para a análise semântica ser executada); a verificação semântica aparece como teste ignorado até a Etapa 5.

Os critérios C1–C12 estão em [`materiais-e-metodos.md`](materiais-e-metodos.md#36-método-de-avaliação). Nas entradas, `→` representa uma tabulação.

## Programas válidos (13)

| Identificador | Categoria | Entrada | Resultado esperado | Análise envolvida | Critérios |
| --- | --- | --- | --- | --- | --- |
| CT-01 | válido | <code>x&nbsp;=&nbsp;5</code> | Tokens IDENTIFICADOR, OPERADOR_ATRIBUICAO, LITERAL_INTEIRO, NOVA_LINHA, FIM_DE_ARQUIVO; AST com um nó ATRIBUICAO. | léxica, sintática | C1, C2 |
| CT-02 | válido | <code>r&nbsp;=&nbsp;2&nbsp;+&nbsp;3&nbsp;*&nbsp;4</code> | MULTIPLICACAO é filha de ADICAO (3 * 4 agrupado primeiro). | léxica, sintática | C2 |
| CT-03 | válido | <code>r&nbsp;=&nbsp;10&nbsp;-&nbsp;3&nbsp;-&nbsp;2</code> | (10 - 3) - 2: a subtração mais interna fica à esquerda. | léxica, sintática | C2 |
| CT-04 | válido | <code>r&nbsp;=&nbsp;(10&nbsp;+&nbsp;5)&nbsp;*&nbsp;2</code> | ADICAO passa a ser filha de MULTIPLICACAO. | léxica, sintática | C2 |
| CT-05 | válido | <code>r&nbsp;=&nbsp;-x&nbsp;%&nbsp;3</code> | OPERACAO_UNARIA liga mais forte que %. | léxica, sintática | C2 |
| CT-06 | válido | <code>print(&quot;soma:&quot;,&nbsp;a&nbsp;+&nbsp;b)</code> | CHAMADA_FUNCAO com dois argumentos, o segundo uma expressão. | léxica, sintática | C2 |
| CT-07 | válido | <code>print()</code> | CHAMADA_FUNCAO sem filhos. | léxica, sintática | C2 |
| CT-08 | válido | <code>nota&nbsp;=&nbsp;7.5<br>if&nbsp;nota&nbsp;&gt;=&nbsp;7:<br>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;Aprovado&quot;)<br>elif&nbsp;nota&nbsp;&gt;=&nbsp;5:<br>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;Recuperacao&quot;)<br>else:<br>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;Reprovado&quot;)</code> | INDENT e DEDENT em cada bloco; AST com CONDICIONAL e três ramos. | léxica, sintática | C1, C2 |
| CT-09 | válido | <code>while&nbsp;a&nbsp;&lt;&nbsp;3:<br>&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;a&nbsp;%&nbsp;2&nbsp;==&nbsp;0:<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;while&nbsp;b&nbsp;&lt;&nbsp;2:<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;b&nbsp;=&nbsp;b&nbsp;+&nbsp;1<br>&nbsp;&nbsp;&nbsp;&nbsp;a&nbsp;=&nbsp;a&nbsp;+&nbsp;1</code> | Três INDENT e três DEDENT balanceados; REPETICAO &gt; CONDICIONAL &gt; REPETICAO. | léxica, sintática | C1, C2 |
| CT-10 | válido | <code>ok&nbsp;=&nbsp;nome&nbsp;==&nbsp;&quot;Ana&quot;<br>ativo&nbsp;=&nbsp;True</code> | COMPARACAO com LITERAL_STRING; True como LITERAL_LOGICO. | léxica, sintática | C2 |
| CT-11 | válido | <code>#&nbsp;só&nbsp;comentário<br>#&nbsp;outro</code> | Comentários descartados pelo scanner; AST só com PROGRAMA. | léxica, sintática | C1, C5 |
| CT-12 | válido | <code>print(x)</code> | O scanner gera NOVA_LINHA antes de FIM_DE_ARQUIVO; programa aceito. | léxica, sintática | C1, C5 |
| CT-13 | válido | <code>print(&quot;ação&nbsp;✓&quot;)&nbsp;&nbsp;#&nbsp;comentário&nbsp;com&nbsp;acento</code> | Caracteres não ASCII aceitos dentro de string e comentário. | léxica, sintática | C1, C5 |

## Erros léxicos (8)

| Identificador | Categoria | Entrada | Resultado esperado | Análise envolvida | Critérios |
| --- | --- | --- | --- | --- | --- |
| CT-14 | erro léxico | <code>total&nbsp;=&nbsp;2&nbsp;$&nbsp;1</code> | Erro léxico na linha 1 apontando '$'; parser não executado, com motivo. | léxica | C3 |
| CT-15 | erro léxico | <code>preço&nbsp;=&nbsp;10</code> | Erro léxico: o subconjunto só aceita identificadores ASCII. | léxica | C3 |
| CT-16 | erro léxico | <code>m&nbsp;=&nbsp;&quot;sem&nbsp;fechar</code> | Erro léxico na linha 1, coluna da aspa de abertura. | léxica | C3 |
| CT-17 | erro léxico | <code>x&nbsp;=&nbsp;7&nbsp;//&nbsp;2</code> | Erro léxico: '//' existe em Python, mas não no subconjunto. | léxica | C3 |
| CT-18 | erro léxico | <code>x&nbsp;=&nbsp;(1&nbsp;+&nbsp;2</code> | Erro léxico: o scanner controla o balanceamento de parênteses (junção implícita de linhas). | léxica | C3 |
| CT-19 | erro léxico | <code>if&nbsp;x:<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;a&nbsp;=&nbsp;1<br>&nbsp;&nbsp;&nbsp;&nbsp;b&nbsp;=&nbsp;2</code> | Erro léxico na linha 3: o recuo não corresponde a nenhum nível aberto. | léxica | C3 |
| CT-20 | erro léxico | <code>if&nbsp;x:<br>&rarr;a&nbsp;=&nbsp;1<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;b&nbsp;=&nbsp;2</code> | Erro léxico na linha 2: tabulação na indentação. | léxica | C3 |
| CT-21 | erro léxico | <code>#&nbsp;Programa&nbsp;com&nbsp;erros&nbsp;léxicos<br>preço&nbsp;=&nbsp;10<br>total&nbsp;=&nbsp;preço&nbsp;*&nbsp;2&nbsp;$&nbsp;1<br>mensagem&nbsp;=&nbsp;&quot;sem&nbsp;fechar<br>if&nbsp;total&nbsp;&gt;=&nbsp;20:<br>&nbsp;&nbsp;&nbsp;&nbsp;print(total&nbsp;//&nbsp;2)</code> | Cinco erros léxicos; o scanner continua depois de cada um; parser não executado. | léxica | C3, C4 |

## Erros sintáticos (12)

| Identificador | Categoria | Entrada | Resultado esperado | Análise envolvida | Critérios |
| --- | --- | --- | --- | --- | --- |
| CT-22 | erro sintático | <code>x&nbsp;=&nbsp;5&nbsp;+</code> | Erro sintático na linha 1; esperado um valor depois de '+'; regra soma. | léxica, sintática | C3 |
| CT-23 | erro sintático | <code>x&nbsp;=&nbsp;10<br>if&nbsp;x&nbsp;&gt;&nbsp;5<br>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;x&quot;)</code> | Erro na linha 2: esperado ':'; regra condicional; recuperação por inserção sem erro em cascata no bloco. | léxica, sintática | C3, C4 |
| CT-24 | erro sintático | <code>else:<br>&nbsp;&nbsp;&nbsp;&nbsp;x&nbsp;=&nbsp;1</code> | Erro na linha 1: else sem if correspondente. | léxica, sintática | C3 |
| CT-25 | erro sintático | <code>5&nbsp;=&nbsp;x</code> | Erro: só um nome pode receber valor. | léxica, sintática | C3 |
| CT-26 | erro sintático | <code>x&nbsp;=&nbsp;5&nbsp;+&nbsp;*&nbsp;2</code> | Erro na coluna 9: dois operadores seguidos. | léxica, sintática | C3 |
| CT-27 | erro sintático | <code>print(a,)</code> | Erro: esperado um argumento depois de ','. | léxica, sintática | C3 |
| CT-28 | erro sintático | <code>ok&nbsp;=&nbsp;a&nbsp;&lt;&nbsp;b&nbsp;&lt;&nbsp;c</code> | Erro: a comparação é não associativa no subconjunto. | léxica, sintática | C3 |
| CT-29 | erro sintático | <code>if&nbsp;x:<br>y&nbsp;=&nbsp;1</code> | Erro na linha 2: esperado INDENT (bloco recuado). | léxica, sintática | C3 |
| CT-30 | erro sintático | <code>if&nbsp;x&nbsp;=&nbsp;1:<br>&nbsp;&nbsp;&nbsp;&nbsp;y&nbsp;=&nbsp;2</code> | Erro: '=' na condição; sugere '=='. | léxica, sintática | C3 |
| CT-31 | erro sintático | <code>for&nbsp;i&nbsp;in&nbsp;x:<br>&nbsp;&nbsp;&nbsp;&nbsp;print(i)</code> | Aviso léxico (palavra reservada fora do subconjunto) e erro sintático; regra instrucao. | léxica, sintática | C3 |
| CT-32 | erro sintático | <code>while&nbsp;x&nbsp;&lt;&nbsp;3:</code> | Erro: o código terminou antes do bloco do while. | léxica, sintática | C3 |
| CT-33 | erro sintático | <code>#&nbsp;Programa&nbsp;com&nbsp;erros&nbsp;sintáticos<br>total&nbsp;=&nbsp;10&nbsp;+<br>if&nbsp;total&nbsp;&gt;&nbsp;5<br>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;maior&quot;,&nbsp;total)<br>elif:<br>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;menor&quot;)<br>5&nbsp;=&nbsp;total</code> | Quatro erros, nas linhas 2, 3, 5 e 7, sem erros em cascata; AST nula. | léxica, sintática | C3, C4 |

## Erros semânticos previstos (Etapa 5, ainda não implementados) (5)

| Identificador | Categoria | Entrada | Resultado esperado | Análise envolvida | Critérios |
| --- | --- | --- | --- | --- | --- |
| CT-34 | erro semântico (previsto) | <code>print(y)</code> | Etapa 5: erro semântico 'y' não definida; a tabela de símbolos não contém 'y'. Hoje: aceito pelas análises léxica e sintática. | léxica, sintática, semântica | C6 |
| CT-35 | erro semântico (previsto) | <code>soma(1,&nbsp;2)</code> | Etapa 5: erro semântico 'soma' não é função conhecida (apenas funções embutidas previstas). Hoje: aceito sintaticamente. | léxica, sintática, semântica | C6 |
| CT-36 | erro semântico (previsto) | <code>x&nbsp;=&nbsp;&quot;a&quot;&nbsp;-&nbsp;1</code> | Etapa 5: erro semântico, '-' entre texto e número. Hoje: aceito sintaticamente. | léxica, sintática, semântica | C6 |
| CT-37 | erro semântico (previsto) | <code>if&nbsp;a&nbsp;&gt;&nbsp;0:<br>&nbsp;&nbsp;&nbsp;&nbsp;b&nbsp;=&nbsp;1<br>print(b)</code> | Etapa 5: 'a' não definida (erro) e 'b' possivelmente não definida (aviso). Hoje: aceito sintaticamente. | léxica, sintática, semântica | C6 |
| CT-38 | erro semântico (previsto) | <code>x&nbsp;=&nbsp;10&nbsp;/&nbsp;0</code> | Etapa 5: aviso de divisão por zero detectável em tempo de compilação. Hoje: aceito sintaticamente. | léxica, sintática, semântica | C6 |

## Casos de borda (7)

| Identificador | Categoria | Entrada | Resultado esperado | Análise envolvida | Critérios |
| --- | --- | --- | --- | --- | --- |
| CT-39 | caso de borda | <i>(texto vazio)</i> | HTTP 400 com mensagem 'Informe um código-fonte…'; nenhuma análise executada. | validação | C5 |
| CT-40 | caso de borda | <code>&nbsp;&nbsp;&nbsp;<br>&nbsp;<br>&nbsp;&nbsp;</code> | HTTP 400 com mensagem sobre código só com espaços. | validação | C5 |
| CT-41 | caso de borda | <code>x = 1</code> repetido 3334 vezes | HTTP 413; o limite é informado ao estudante. | validação | C5 |
| CT-42 | caso de borda | <code>x = </code> + 25 × <code>(</code> + <code>1</code> + 25 × <code>)</code> | Aceito; AST com o literal no fundo. | léxica, sintática | C5 |
| CT-43 | caso de borda | <code>x = </code> + 300 × <code>(</code> + <code>1</code> + 300 × <code>)</code> | Erro controlado 'aninhamento_excessivo' (limite de 200 regras abertas), sem estouro de pilha nem HTTP 500. | léxica, sintática | C5 |
| CT-44 | caso de borda | <code>x = 5 +</code> repetido 55 vezes | Exatamente 50 erros relatados (limite), sem travamento. | léxica, sintática | C4, C5 |
| CT-45 | caso de borda | <code>x = x + 1</code> repetido 1500 vezes | Aceito; AST completa; passo a passo limitado a 20 000 passos e marcado como truncado. | léxica, sintática | C5 |

# Registros para o artigo: Materiais e Métodos (Etapa 4)

Este documento reúne as decisões técnicas, o fluxograma e os critérios de avaliação do software. O objetivo é que sirvam de base para a seção **Materiais e Métodos** do artigo. Ele descreve só o que foi implementado e testado até a versão 0.4.0.

## 1. Fluxograma do sistema

![Fluxograma: entrada, análise léxica, análise sintática, análise semântica (futura) e apresentação](figuras/fluxograma.png)

A fonte do fluxograma está em [`figuras/fluxograma.mmd`](figuras/fluxograma.mmd), no formato Mermaid, e a versão vetorial em [`figuras/fluxograma.svg`](figuras/fluxograma.svg). A análise semântica (Etapa 5) e o assistente de IA aparecem tracejados: a primeira ainda não existe, e o segundo é opcional, sem influência nos resultados das análises.

## 2. Materiais

| Componente | Tecnologia e versão | Papel |
| --- | --- | --- |
| Linguagem analisada | Subconjunto de Python 3 (15 regras EBNF) | Objeto de estudo do estudante |
| Backend | Python 3.12, Starlette 1.6, Uvicorn 0.53 | API HTTP com scanner e parser |
| Scanner | Código próprio (`backend/app/scanner.py`) | Etapa 3; reaproveitado sem alterações |
| Parser | Código próprio, descendente recursivo (`backend/app/parser.py`) | Etapa 4 |
| Frontend | HTML, CSS e JavaScript (módulos ES, sem build), Nginx 1.27 | Interface web responsiva |
| Assistente (opcional) | Ollama (`ollama/ollama:latest`) com Llama 3.2 3B | Explicações didáticas dos resultados |
| Infraestrutura | Docker Compose: serviços `backend`, `frontend` e `ollama`, mais o perfil `testes` | Ambiente reproduzível |
| Testes | `unittest` (Python), `node --test` (Node 22), Playwright 1.56 com Chromium | Unitários, endpoints, interface, regressão |
| Oráculos de validação | Módulos `tokenize` e `ast` da biblioteca padrão do Python | Referência para conferir scanner e parser |

## 3. Métodos: decisões técnicas do parser

1. **Gramática antes do código.** A gramática foi definida em EBNF ([`gramatica.md`](gramatica.md)), sem recursão à esquerda e com decisões resolvidas por no máximo dois tokens à frente. Os terminais são exatamente as categorias de token da Etapa 3, e o scanner não precisou mudar.
2. **Estratégia descendente recursiva, escrita à mão.** Há uma função por não terminal. A escolha é didática: a pilha de chamadas do parser é a pilha de regras exibida ao estudante, e cada função conhece o contexto para explicar o erro com a regra violada. Nenhum gerador (Yacc/Bison, ANTLR, PLY) foi usado.
3. **Precedência pela estrutura da gramática:** `comparacao → soma → termo → fator → primario`. A associatividade à esquerda vem dos laços `{ }`; a comparação é não associativa.
4. **AST com formato único.** Cada nó tem `id`, `tipo`, `regra`, `papel`, posição inicial e final, `atributos`, `passo` e `filhos`. A árvore de derivação é registrada ao mesmo tempo, para comparar as duas representações.
5. **Erros léxicos bloqueiam o parser.** Com tokens faltando, o parser produziria diagnósticos falsos. O motivo é informado na resposta e na interface.
6. **Recuperação de erros** em modo pânico (sincronização no fim da linha) e por inserção (`:` ausente). Acumula até 50 erros, sem cascata nos casos testados.
7. **Registro de passos** (entrar em regra, consumir token, construir nó, erro, recuperação) para a construção passo a passo na interface.
8. **Assistente de IA isolado.** O backend reanalisa o código e envia ao modelo só os resultados reais, delimitados como dados. A análise não depende do Ollama.
9. **Desenvolvimento incremental com testes a cada construção.** A ordem foi expressões → atribuições → chamadas → `if/elif/else` → `while` → erros → recuperação. A cada passo foram executados também os testes anteriores (regressão).

## 4. Critérios de avaliação (definidos antes dos resultados)

| Critério | Como é medido | Meta |
| --- | --- | --- |
| C1. Correção da AST | Comparação da estrutura e das posições com o módulo `ast` do Python em programas de referência e em 300 programas aleatórios (semente fixa) | 100% de concordância |
| C2. Precedência e associatividade | Casos `2 + 3 * 4`, `10 - 3 - 2`, `(10 + 5) * 2`, unário, relacional | AST igual à esperada |
| C3. Rejeição de programas inválidos | Programas que o próprio Python rejeita (`compile`) também devem ser rejeitados | 100% |
| C4. Qualidade do diagnóstico | Cada erro com linha, coluna, `encontrado`, `esperado`, regra e mensagem sem detalhes internos | Todos os casos de teste |
| C5. Recuperação | Vários erros em um programa são relatados sem erros em cascata | Casos de teste de recuperação |
| C6. Robustez | Entradas vazias, só comentários, grandes, aninhadas demais e com caracteres especiais não derrubam a aplicação | Nenhum erro 500 ou travamento |
| C7. Consistência entre visualizações | Tokens consumidos pelo parser são os da tabela; posições na árvore iguais às da tabela | Testes de interface |
| C8. Regressão | Testes das Etapas 1 a 3 continuam passando; scanner produz os mesmos tokens | 100% |
| C9. Reprodutibilidade | Fluxo completo validado com Docker Compose em ambiente limpo | `scripts/testar.ps1` aprovado |
| C10. Assistente (diferencial) | Explicações geradas pelo modelo com o contexto do compilador e tratamento de indisponibilidade | `scripts/testar-ia.ps1` |

## 5. Casos de teste (válidos e inválidos)

| Grupo | Exemplos |
| --- | --- |
| Válidos | atribuição com cada tipo de literal; chamadas com 0, 1 e vários argumentos; `if`, `if/else`, `if/elif/elif/else`; `while`; blocos aninhados em três níveis; condições com parênteses e `%`; código vazio; só comentários; um comando sem quebra final |
| Incompletos | `x = 5 +`; `total =`; `if x > 5` sem `:`; `x = (1 + 2 3)`; `print("a" "b")`; `print(a,)`; `x = ()`; `if:`; `if x:` + linha sem recuo; `while x < 3:` no fim |
| Combinações inválidas | `else:` e `elif` sem `if`; `else` com recuo diferente do `if`; `x = 5 + * 2`; `x = = 2`; `True = 1`; `x = 1 + while`; `for i in x:`; `5 = x`; `if x = 1:`; `x == 1`; `x + 1`; `x = 1 2`; `a < b < c`; `x = 5)`; `if x: y = 1`; `if a and b:` |
| Robustez | 300 parênteses aninhados; 500 sinais unários; 1 500 linhas; 55+ erros no mesmo programa |

Os resultados estão em [`testes.md`](testes.md) (seção da Etapa 4).

## 6. Comparação com ferramentas da literatura

| Trabalho | Como o parser é obtido | O que mostra da análise sintática | Mensagens de erro | Diferença em relação a este trabalho |
| --- | --- | --- | --- | --- |
| VAST (ALMEIDA-MARTÍNEZ; URQUIZA-FUENTES; VELÁZQUEZ-ITURBIDE, 2009) | Parser do aluno gerado com ANTLR ou CUP | Árvore sintática e animação da sua construção; interface para árvores grandes | Não é o foco | Aqui o parser é fixo e escrito à mão; em troca, mostra a pilha de regras, a regra de cada nó e a AST ao lado da árvore de derivação |
| LP_Tools (GOLEMANOV; GOLEMANOVA, 2020) | Gera o código-fonte de um parser descendente recursivo a partir da gramática; simula análise ascendente | Simulação passo a passo e ações semânticas | Não é o foco | Aqui o estudante escreve programas, não gramáticas; o foco é ler a árvore e entender os erros do próprio código |
| ITT (DEL VADO VÍRSEDA, 2023) | Ferramentas de geração (Flex/Bison, JFlex/CUP) | Explora autômatos e grafos gerados pelas ferramentas | Usa mensagens de erro de compiladores como recurso de ensino | Aqui as mensagens foram escritas para ensinar: dizem o que era esperado e citam a regra violada |
| Conejo et al. (2024) | Exercícios de LL(1) e LR(1) gerados automaticamente | Tabelas e passos dos algoritmos, com correção automática | Retorno sobre a resposta do estudante | Aqui não há exercícios de construção de tabelas; o foco é o resultado da análise de um programa |
| Graciano Junior et al. (2022) | JFlex na análise léxica; árvore de derivação gerada pela ferramenta | Árvore de derivação passo a passo, com animação | Não informado em detalhe | Aqui há AST e árvore de derivação, posições ligadas ao código e recuperação de vários erros |
| Borela et al. (2025) | ANTLR 4 gera os analisadores | Lista de tokens e árvore, além das fases seguintes até o código-alvo | Não informado em detalhe | Cobre mais fases; não mostra a construção passo a passo nem explica as regras violadas |

**Lacunas observadas nos artigos lidos** (sem afirmar novidade absoluta): nenhum dos seis trabalhos descreve, ao mesmo tempo:

- mensagens de erro sintático que citam a regra gramatical violada;
- AST e árvore de derivação lado a lado;
- seleção de um nó com destaque no código;
- explicações geradas por um modelo de linguagem a partir dos resultados do compilador.

A gramática formal explícita e documentada também não aparece, para o subconjunto analisado, nas ferramentas baseadas em geradores. Essas são as contribuições que o artigo pode sustentar, dentro dos limites desta amostra.

## Referências

ALMEIDA-MARTÍNEZ, F. J.; URQUIZA-FUENTES, J.; VELÁZQUEZ-ITURBIDE, J. Á. Visualization of syntax trees for language processing courses. **Journal of Universal Computer Science**, v. 15, n. 7, p. 1546-1561, 2009.

BORELA, R. et al. Uma ferramenta educacional de apoio ao ensino de compiladores. In: WORKSHOP SOBRE EDUCAÇÃO EM COMPUTAÇÃO (WEI), 2025. **Anais** [...]. Porto Alegre: SBC, 2025.

CONEJO MUÑOZ, R. et al. Teaching compilers: automatic question generation and intelligent assessment of grammars' parsing. **IEEE Transactions on Learning Technologies**, v. 17, p. 1734-1744, 2024.

DEL VADO VÍRSEDA, R. Visualizing compiler design theory from implementation through an interactive tutoring tool: experiences and results. In: INTERNATIONAL CONFERENCE ON COMPUTER SUPPORTED EDUCATION (CSEDU), 2023. **Proceedings** [...]. Setúbal: SciTePress, 2023. v. 2, p. 333-340.

GOLEMANOV, T.; GOLEMANOVA, E. A set of tools to teach language processors construction. In: INTERNATIONAL CONFERENCE ON COMPUTER SYSTEMS AND TECHNOLOGIES (CompSysTech '20), 2020. **Proceedings** [...]. New York: ACM, 2020.

GRACIANO JUNIOR, A. et al. Ferramenta interativa para o ensino de compiladores. In: SIMPÓSIO BRASILEIRO DE EDUCAÇÃO EM COMPUTAÇÃO (EDUCOMP), 2022. **Anais** [...]. Porto Alegre: SBC, 2022.

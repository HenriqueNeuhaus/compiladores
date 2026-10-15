# Revisão de Literatura — Definição do Problema

> Documento da etapa de definição do problema e revisão inicial de literatura. Voltar ao [README](../README.md).

## 1. Definição do Problema de Estudo

O software proposto é um visualizador interativo, voltado a graduandos de Ciência da Computação, que mostra passo a passo as análises léxica e sintática de programas escritos em um subconjunto da linguagem Python.

### 1.1 Fronteira tecnológica

A linguagem-alvo é **Python**, escolhida por três razões:

- É a linguagem com que muitos estudantes iniciam a graduação, o que reduz a barreira de entrada: o aluno analisa um código que já sabe ler.
- Sua sintaxe enxuta permite definir um subconjunto pequeno (atribuições, expressões, `if`, `while`, `def`) sem perder realismo.
- Python tem uma particularidade léxica pouco explorada no ensino: a indentação gera os tokens `INDENT` e `DEDENT`, o que torna a análise léxica mais interessante do que em linguagens delimitadas por chaves.

O próprio software também será implementado em Python, com interface web, aproveitando os módulos nativos `tokenize` e `ast` como referência para validar os resultados exibidos.

**Público-alvo:** estudantes de graduação em Ciência da Computação e cursos afins que estejam cursando ou revisando a disciplina de Compiladores.

### 1.2 Fronteira pedagógica

| Aspecto | Definição |
| --- | --- |
| Fases abordadas | Análise léxica (autômatos finitos) e análise sintática (árvore de derivação e AST) |
| Tipo de ferramenta | Visualizador interativo |
| Abordagem | Híbrida: breve explicação teórica seguida de prática guiada |

O aluno digita o próprio código, avança e retrocede cada passo da análise e observa o estado do autômato, a lista de tokens e o crescimento da árvore. Erros inseridos pelo aluno são destacados no ponto exato em que foram detectados.

---

## 2. Objetivo Geral e Justificativa Inicial

O presente trabalho tem como objetivo desenvolver um software educacional web para o ensino das análises léxica e sintática, usando um subconjunto da linguagem Python, voltado a estudantes de graduação em Ciência da Computação.

A justificativa baseia-se na dificuldade recorrente dos alunos em visualizar, na prática, o funcionamento das fases de um compilador. Graciano Junior et al. (2022) apontam que esse é um dos principais entraves da disciplina: livros e aulas costumam mostrar apenas a árvore final ou figuras estáticas de exemplos pequenos, sem permitir que o aluno teste o próprio código. Borela et al. (2025) reforçam que professores enfrentam escassez de recursos didáticos com recursos gráficos e interativos.

Há evidências de que ferramentas visuais ajudam. No estudo de Sangal et al. (2018), 89% dos estudantes afirmaram que um visualizador de algoritmos de parsing os ajudou a compreender o conteúdo. Ainda assim, as ferramentas existentes trabalham com pseudolinguagens (Portugol), linguagens próprias inspiradas em C ou gramáticas abstratas, e nenhuma das analisadas usa Python como linguagem-fonte.

Diante disso, propõe-se uma ferramenta interativa que conecte a teoria de autômatos e gramáticas a uma linguagem que o aluno já conhece e usa. Os beneficiados são:

- **Alunos**, que poderão experimentar com o próprio código, inclusive provocando erros, e acompanhar cada passo da análise;
- **Professores**, que terão um recurso gratuito para aulas expositivas, laboratórios ou sala de aula invertida;
- **Instituições**, que ganham um material reutilizável, acessível pelo navegador e sem necessidade de instalação.

---

## 3. Fichamento dos Artigos

A busca foi feita em três bases, com os termos sugeridos para a tarefa, priorizando trabalhos publicados a partir de 2016:

| Base | Termos de busca | Artigos selecionados encontrados |
| --- | --- | --- |
| SBC OpenLib (SOL) | *ensino de compiladores* | Artigos 1 e 3 |
| Google Acadêmico | *"teaching compilers" OR "ensino de compiladores" tool* (a partir de 2016) | Artigos 1 e 3 |
| Springer Link | *parsing algorithm visualizer compiler construction teaching* | Artigo 2 |

Dos resultados, foram lidos os resumos e escolhidos os três trabalhos mais alinhados ao escopo: ferramentas visuais e interativas para as fases de análise léxica e sintática, com algum tipo de avaliação com estudantes.

### Artigo 1 — Ferramenta Interativa para o Ensino de Compiladores (2022)

**Referência:** GRACIANO JUNIOR, W.; GROSSERT, I. T. S.; CASTELLO BRANCO NETO, W.; AVILA, A. J. Ferramenta Interativa para o ensino de compiladores. In: Simpósio Brasileiro de Educação em Computação (EduComp), 2., 2022, on-line. *Anais* [...]. Porto Alegre: SBC, 2022. p. 224–233. [Link](https://sol.sbc.org.br/index.php/educomp/article/view/19217)

- **Objetivo:** apresentar uma aplicação web interativa para apoiar o ensino-aprendizagem das análises léxica e sintática.
- **Metodologia:** pesquisa aplicada e qualitativa, com levantamento bibliográfico e estudo de caso. Frontend em Angular e backend em **Python**. A linguagem analisada é uma pseudolinguagem baseada em Portugol, reconhecida por um autômato finito determinístico e por um analisador sintático preditivo (FIRST, FOLLOW e tabela M).
- **Resultados:** a ferramenta anima o autômato token a token e constrói a árvore de derivação passo a passo, com explicação textual e destaque de erros em vermelho. Cinco alunos testaram uma versão preliminar; pelo número reduzido, os resultados não foram publicados.
- **Contribuições para o meu trabalho:** é o trabalho mais próximo da proposta. Inspira a interface em três colunas (tokens, visualização e explicação), o controle de avançar/voltar e a combinação de teoria com prática.
- **Limitações:** não houve avaliação com alunos que tivesse resultados mensuráveis. O uso de pseudolinguagem afasta a ferramenta das linguagens reais que o aluno usa.

### Artigo 2 — PAVT: a tool to visualize and teach parsing algorithms (2018)

**Referência:** SANGAL, S.; KATARIA, S.; TYAGI, T. et al. PAVT: a tool to visualize and teach parsing algorithms. *Education and Information Technologies*, v. 23, p. 2737–2764, 2018. DOI: [10.1007/s10639-018-9739-x](https://doi.org/10.1007/s10639-018-9739-x)

- **Objetivo:** apresentar um visualizador capaz de mostrar a construção e a execução de seis algoritmos de análise sintática: preditivo LL(1), SLR, LR canônico, LALR, Earley e CYK.
- **Metodologia:** desenvolvimento de uma aplicação para desktop, distribuída para download no SourceForge, que recebe uma gramática livre de contexto e uma cadeia de entrada. A ferramenta foi usada em disciplinas de Compiladores de graduação e pós-graduação, com coleta de opinião dos estudantes.
- **Resultados:** 89% dos estudantes disseram que a ferramenta ajudou a entender os algoritmos de parsing, e 88% a usaram para comparar algoritmos entre si.
- **Contribuições para o meu trabalho:** oferece evidência quantitativa do benefício de visualizar a análise sintática. Mostra também quais artefatos são didaticamente úteis: conjuntos FIRST/FOLLOW, tabela de parsing, pilha, árvore e derivação.
- **Limitações:** trabalha apenas com gramáticas abstratas e cadeias curtas, sem ligação com uma linguagem de programação real. Não aborda a análise léxica.

### Artigo 3 — Uma Ferramenta Educacional de Apoio ao Ensino de Compiladores (2025)

**Referência:** BORELA, E. P. S.; OLIVEIRA, A. L.; CASTELLO BRANCO NETO, W.; SOUZA, A. P. Uma Ferramenta Educacional de Apoio ao Ensino de Compiladores. In: Workshop sobre Educação em Computação (WEI), 33., 2025, Maceió. *Anais* [...]. Porto Alegre: SBC, 2025. p. 171–181. DOI: [10.5753/wei.2025.7407](https://doi.org/10.5753/wei.2025.7407)

- **Objetivo:** apresentar uma ferramenta web que compila uma linguagem inspirada em C e exibe todos os artefatos da compilação.
- **Metodologia:** compilador construído com ANTLR 4 (análises léxica e sintática) e LLVM (otimização e código-alvo), com backend Java/Spring Boot. A avaliação usou questionário on-line com escala Likert, respondido por 27 participantes (74,1% alunos e 18,5% professores).
- **Resultados:** avaliação geral média de 4,81 em 5. A lista de tokens teve 96,3% de respostas positivas e a árvore sintática, 88,89%.
- **Contribuições para o meu trabalho:** mostra um modelo de avaliação replicável (questionário Likert com perguntas abertas). Indica que a árvore sintática é o recurso que mais precisa de cuidado na apresentação, segundo as sugestões dos participantes.
- **Limitações:** a árvore é mostrada pronta, sem passo a passo. A avaliação mede aceitação, não ganho de aprendizagem. Os autores reconhecem que a ferramenta exige conhecimento prévio e não substitui o ensino.

---

## 4. Análise Comparativa (Quadro de Síntese)

Nenhum dos três trabalhos combina análise léxica e sintática passo a passo com uma linguagem real conhecida pelo aluno; é nessa lacuna que a proposta se posiciona.

| Critério | Graciano Junior et al. (2022) | Sangal et al. (2018) | Borela et al. (2025) | **Proposta deste trabalho** |
| --- | --- | --- | --- | --- |
| Plataforma | Web responsiva | Desktop (download) | Web | Web |
| Fases abordadas | Léxica, sintática | Sintática | Todas (até código-alvo e execução) | Léxica, sintática |
| Recursos visuais | Autômato animado, árvore de derivação passo a passo | Tabelas FIRST/FOLLOW, tabela de parsing, pilha, árvore, derivação | Lista de tokens, árvore sintática, tabela de símbolos, LLVM IR, Assembly | Autômato animado, tokens com INDENT/DEDENT, árvore de derivação e AST passo a passo |
| Passo a passo | Sim | Sim | Não | Sim |
| Validação com alunos | Preliminar, 5 alunos, sem resultados publicados | Sim, em turmas de graduação e pós (89% aprovação) | Sim, 27 participantes (média 4,81/5) | Planejada |
| Linguagem-alvo | Pseudolinguagem (Portugol) | Gramáticas livres de contexto abstratas | Linguagem própria inspirada em C | Subconjunto de Python |
| Ano | 2022 | 2018 | 2025 | — |

**Convergências.** Os três trabalhos partem do mesmo diagnóstico: compiladores é uma disciplina abstrata, e ver o processo acontecer facilita a compreensão. Há também uma tendência clara à plataforma web, mais acessível que o desktop, e ao uso do código digitado pelo próprio usuário.

**Diferenças e lacunas.** Os trabalhos oscilam entre dois extremos. Sangal et al. (2018) aprofundam os algoritmos, mas com gramáticas abstratas; Borela et al. (2025) usam uma linguagem realista, mas sem passo a passo; Graciano Junior et al. (2022) oferecem o passo a passo, mas sobre Portugol e sem avaliação concluída. Além disso, só um dos estudos mede algo próximo de aprendizagem, e ainda por autorrelato.

**Onde este trabalho se encaixa.** A proposta une o passo a passo de Graciano Junior et al. (2022) a uma linguagem real e familiar, Python, que traz o desafio léxico da indentação, ausente em todos os trabalhos analisados. Para a avaliação, pretende-se adotar um questionário Likert semelhante ao de Borela et al. (2025), complementado por um pré-teste e pós-teste de conteúdo, para medir também o ganho de aprendizagem.

---

## 5. Anexos

Os artigos estão disponíveis nos links abaixo. O Anexo B é de acesso pago (Springer), por isso aparece apenas como link.

| Anexo | Artigo | Acesso |
| --- | --- | --- |
| A | Graciano Junior et al. (2022) — [PDF](https://sol.sbc.org.br/index.php/educomp/article/download/19217/19046) | Aberto (CC BY-NC 4.0) |
| B | Sangal et al. (2018) — [página do artigo](https://doi.org/10.1007/s10639-018-9739-x) | Portal de Periódicos CAPES / rede da instituição |
| C | Borela et al. (2025) — [PDF](https://sol.sbc.org.br/index.php/wei/article/download/36164/35951) | Aberto |

---

## Referências

BORELA, E. P. S.; OLIVEIRA, A. L.; CASTELLO BRANCO NETO, W.; SOUZA, A. P. Uma Ferramenta Educacional de Apoio ao Ensino de Compiladores. In: WORKSHOP SOBRE EDUCAÇÃO EM COMPUTAÇÃO (WEI), 33., 2025, Maceió. *Anais* [...]. Porto Alegre: SBC, 2025. p. 171–181. DOI: 10.5753/wei.2025.7407.

GRACIANO JUNIOR, W.; GROSSERT, I. T. S.; CASTELLO BRANCO NETO, W.; AVILA, A. J. Ferramenta Interativa para o ensino de compiladores. In: SIMPÓSIO BRASILEIRO DE EDUCAÇÃO EM COMPUTAÇÃO (EDUCOMP), 2., 2022, on-line. *Anais* [...]. Porto Alegre: SBC, 2022. p. 224–233.

SANGAL, S.; KATARIA, S.; TYAGI, T. et al. PAVT: a tool to visualize and teach parsing algorithms. *Education and Information Technologies*, v. 23, p. 2737–2764, 2018. DOI: 10.1007/s10639-018-9739-x.

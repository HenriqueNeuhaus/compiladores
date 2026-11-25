# Plano de avaliação e formulário (Tarefa 4)

> Detalha a seção 3.6 de [`materiais-e-metodos.md`](materiais-e-metodos.md#36-método-de-avaliação). Situação: formulário criado e em aplicação desde a apresentação parcial de 25/11/2026. Voltar ao [README](../README.md).

## 1. Visão geral

| Pergunta de avaliação | Tipo | Instrumento | Critérios |
| --- | --- | --- | --- |
| O software produz resultados corretos? | Técnica | Testes automatizados e oráculos `tokenize`/`ast`; casos CT-01 a CT-45 | C1, C2, C4, C5, C7, C8 |
| Os erros são relatados de forma correta e compreensível? | Técnica + inspeção | Campos dos erros testados automaticamente; mensagens inspecionadas por dois avaliadores | C3 |
| As explicações da IA são corretas? | Inspeção | Sete aspectos de Leinonen et al. (2023), dois avaliadores, kappa de Cohen | C9 |
| A interface é usável? | Percepção | Formulário, bloco B | C10 |
| O software e seus diferenciais ajudam a entender as análises? | Percepção | Formulário, blocos C e D, tarefa T2 | C11, C12 |
| A análise semântica funciona? | Técnica | CT-34 a CT-38 | C6 — pendente (Etapa 5) |

## 2. Ordem de execução

1. Rodar `scripts\testar.ps1` em máquina limpa e registrar o resultado em `testes.md` (C8).
2. Executar o roteiro manual da seção 3.6 (navegadores, teclado, celular, assistente) e registrar.
3. Gerar as explicações da IA para os exemplos e os casos de erro e fazer a classificação dupla (C9).
4. Aplicar a avaliação por pares (seções 3 e 4 abaixo).
5. Consolidar os resultados nas seções "Resultados" e "Discussão" do artigo.

## 3. Roteiro de tarefas para os participantes (20 a 30 minutos)

| Tarefa | Instrução ao participante | O que observa |
| --- | --- | --- |
| T1 | Carregue o exemplo "Atribuição e expressões aritméticas", clique em Analisar e localize na tabela os tokens da primeira linha de código. | Uso básico, tabela de tokens |
| T2 | Digite `r = 2 + 3 * 4`, analise e responda no formulário: qual operação fica mais perto da raiz da AST? | Leitura da árvore (resposta objetiva) |
| T3 | Carregue "Erros sintáticos (vários)" e corrija o código usando apenas as mensagens de erro, até a análise terminar sem erros. | Diagnóstico e recuperação |
| T4 | Carregue "Erros léxicos". Por que não aparece árvore sintática? | Separação entre erro léxico e sintático |
| T5 (opcional) | Selecione um nó da AST e peça ao assistente de IA uma explicação. | Assistente de IA |

## 4. Formulário (Google Forms)

**Link para responder:** https://forms.gle/Rew1G5XDrc7Gd8Dw8

**Configuração:** coleta de e-mails desativada; sem login obrigatório; uma resposta por pessoa não exigida (para não pedir conta Google); nenhuma pergunta obrigatória além do consentimento.

**Texto de abertura (consentimento).** "Este formulário avalia um software educacional de análise léxica e sintática desenvolvido na disciplina de Compiladores. A participação é voluntária, anônima e não vale nota. Não pedimos nome, e-mail nem matrícula. As respostas serão apresentadas apenas de forma agregada em um trabalho acadêmico. Você pode parar a qualquer momento." — [ ] Li e concordo em participar.

**Escala dos blocos B, C e D:** 1 = discordo totalmente; 2 = discordo; 3 = neutro; 4 = concordo; 5 = concordo totalmente; e a opção "não usei / não se aplica".

### Bloco A — Perfil (sem dados pessoais)

- A1. Curso: Ciência da Computação / Inteligência Artificial / Outro.
- A2. Situação em Compiladores: cursando / já cursei / sou professor(a).
- A3. Dispositivo usado nesta avaliação: computador / celular / os dois.
- A4. Familiaridade com Python: nenhuma / básica / intermediária / avançada.

### Bloco B — Usabilidade (C10)

- B1. Foi fácil escrever ou escolher um programa e obter a análise.
- B2. A interface é intuitiva: encontrei as funções sem precisar de ajuda.
- B3. Os textos, rótulos e cores da interface são claros.
- B4. Consegui realizar as tarefas T1 a T4.
- B5. (Se usou celular) A ferramenta funcionou bem no celular.
- B6. (Se tentou) Consegui usar as principais funções só com o teclado.

### Bloco C — Utilidade para aprender (C11)

- C1. A tabela de tokens e o código colorido ajudaram a entender a análise léxica.
- C2. Ver os tokens `INDENT` e `DEDENT` ajudou a entender como a indentação do Python vira estrutura.
- C3. A árvore sintática ajudou a entender a análise sintática.
- C4. As mensagens de erro me ajudaram a encontrar e corrigir os erros.
- C5. Eu usaria a ferramenta para estudar para a disciplina.
- C6. Gostaria de ter usado a ferramenta no início da disciplina.

### Bloco D — Diferenciais do software (C12)

- D1. Ver a AST e a árvore de derivação do mesmo programa ajudou a entender a diferença entre elas.
- D2. O passo a passo do parser (entrar em regra, consumir token, construir nó) ajudou a entender como a árvore é construída.
- D3. Selecionar um nó e ver o trecho correspondente destacado no código ajudou a relacionar a árvore com o programa.
- D4. As mensagens que mostram o que era esperado e citam a regra da gramática ajudaram a entender o erro.
- D5. A separação entre erros léxicos e sintáticos (e o aviso de que o parser não foi executado) ficou clara.
- D6. (Se usou) As explicações do assistente de IA foram corretas e úteis.
- D7. (Se usou) Ficou claro que as explicações da IA podem conter erros e que o resultado oficial é o do compilador.
- D8. Analisar um subconjunto de Python, linguagem que já conheço, facilitou o entendimento.

### Bloco E — Respostas objetivas e abertas

- E1. (Tarefa T2) Em `r = 2 + 3 * 4`, qual operação fica mais perto da raiz da AST? Adição / Multiplicação / As duas no mesmo nível / Não sei.
- E2. O que mais ajudou? (opcional)
- E3. O que dificultou ou faltou? (opcional)
- E4. Você encontrou algum resultado que parecia errado? Se sim, descreva o código usado. (opcional)

## 5. Análise dos dados

- Por item: mediana, moda e distribuição percentual; média e desvio-padrão só como complemento. "Não usei" fica fora do cálculo e é relatado à parte.
- Por bloco (B, C, D): alfa de Cronbach, se houver pelo menos 10 respostas completas, como em Ortin et al. (2022).
- Por perfil (cursando, já cursou, professor; computador ou celular): comparação descritiva, sem teste de hipótese.
- E1: porcentagem de acertos (resposta correta: adição).
- Abertas: agrupamento por tema (o que ajudou, problemas de uso, erros relatados). Todo erro relatado em E4 vira caso de teste novo, se confirmado.
- C9 (IA): porcentagem de "sim" por aspecto para cada avaliador e kappa de Cohen.

## 6. Ameaças e cuidados

Ver a seção 3.7 de [`materiais-e-metodos.md`](materiais-e-metodos.md#37-limitações-do-método): percepção não é aprendizagem; amostra pequena e de conveniência; participantes conhecem o autor; sem cegamento; assistente não determinístico.

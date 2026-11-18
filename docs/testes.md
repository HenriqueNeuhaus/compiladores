# Registro de testes

Registro das execuções de teste do projeto, em ordem cronológica. Cada etapa traz o que foi testado, os comandos usados, os resultados, as falhas encontradas e o que ainda falta.

## Etapa 4 — Análise sintática e AST (18/11/2026)

**Ambiente das execuções:** Linux, Python 3.13, Starlette 1.6.0, Uvicorn 0.53.0, Node.js 22, Playwright 1.56.0 com Chromium, servidor local `tests/e2e/servidor_local.py` (frontend + backend real, sem Ollama). A execução no Docker é feita no Windows com `scripts\testar.ps1` e `scripts\testar-ia.ps1`, e fica registrada abaixo, em seções próprias.

A gramática e os testes do parser foram escritos juntos, construção por construção: expressões, atribuições, chamadas, `if/elif/else`, `while`, erros e recuperação. A cada passo todas as suítes foram executadas de novo.

### Execuções por funcionalidade

| # | Funcionalidade | Tipo | Comando | Resultado |
| --- | --- | --- | --- | --- |
| 1 | Construções válidas e AST esperada (atribuição, literais, chamadas, `if/elif/else`, `while`, aninhamento, comentários, exemplos da interface) | Unitário | `cd backend && python -m unittest tests.test_parser -v` | Aprovado |
| 2 | Precedência e associatividade (`2 + 3 * 4`, `10 - 3 - 2`, `100 / 10 / 2`, `(10 + 5) * 2`, unário, relacional, 6 operadores relacionais) | Unitário | idem | Aprovado |
| 3 | Posições dos nós, nó pai cobrindo os parênteses, ids em pré-ordem, regra e passo de cada nó, posições iguais às dos tokens | Unitário | idem | Aprovado |
| 4 | Construções incompletas (operando, valor, `:`, `)`, vírgula, argumento, parênteses vazios, condição, bloco, fim do código) com `encontrado`, `esperado`, `regra`, `producao` e mensagem | Unitário | idem | Aprovado |
| 5 | Combinações inválidas (`else`/`elif` sem `if`, operadores seguidos, palavra reservada como nome, `for`, `and/or/not/in`, atribuição inválida, `=` na condição, expressão sem efeito, valores seguidos, comparação encadeada, `)` sem abertura, recuo inesperado, bloco na mesma linha) | Unitário | idem | Aprovado |
| 6 | Recuperação de erros: vários erros acumulados, sem cascata depois de `:` ausente, erros dentro de bloco com cabeçalho inválido, limite de 50 erros, passos de erro e de recuperação | Unitário | idem | Aprovado |
| 7 | Casos de borda: vazio, só comentários, comando sem quebra final, fim no meio, 300 parênteses, 500 sinais, 1 500 linhas (passos limitados, AST completa) | Unitário | idem | Aprovado |
| 8 | Integração com o scanner: parser não executado com erro léxico, aviso léxico não impede o parser, parser consome exatamente os tokens do scanner, tokens iguais aos da Etapa 3 | Unitário | idem | Aprovado |
| 9 | Árvore de derivação: folhas = tokens em ordem; cadeia de regras; ausente com erro | Unitário | idem | Aprovado |
| 10 | Gramática do código idêntica à de `docs/gramatica.md`; todo tipo de nó tem regra | Unitário | idem | Aprovado |
| 11 | **Oráculo:** estrutura e posições da AST iguais às do módulo `ast` do Python em 8 programas de referência e em 300 programas aleatórios (semente 2026); 13 programas que o Python rejeita também rejeitados | Diferencial | idem | Aprovado: nenhuma divergência |
| 12 | Endpoint: campos da Etapa 3 preservados + `lexico` e `sintatico`; AST e sucesso; erro sintático com AST nula e objeto de erro completo; erro léxico sem parser e com `motivo`; plural; só comentários; falha do parser como 500 genérico; entrada no limite | Endpoints | `python -m unittest tests.test_api -v` | 36 aprovados (29 anteriores, 2 atualizados de propósito, + 7 novos) |
| 13 | Assistente de IA com Ollama falso: status, `/api/chat`, `message.content`, resposta vazia ou inválida, modelo ausente, indisponível com nova tentativa, tempo limite, sem detalhes internos, contexto do nó/token/erro/pergunta vindo do parser, dados delimitados, pedidos inválidos, análise sem IA, variáveis de ambiente | Endpoints | `python -m unittest tests.test_ia -v` | 21 aprovados |
| 14 | Frontend: preparação da AST (`sintatico.js`) e cliente do assistente (`api.js`) | Unitário (frontend) | `cd frontend && node --test "tests/unit/*.test.js"` | 74 aprovados (53 anteriores, 6 gerados pelos 2 exemplos novos, + 15 novos) |
| 15 | Interface: árvore, precedência e parênteses, seleção com trecho e regra, posições iguais às da tabela, expandir/recolher e teclado, filtro, exportação JSON, derivação, explicação, legenda com forma, passo a passo do parser, erros sintáticos, vários erros, distinção léxico × sintático, entrada grande, aviso de desatualizado, celular, assistente simulado | Interface | `BASE_URL=http://localhost:8090 python -m unittest tests.e2e.test_interface -v` | 77 aprovados (48 anteriores, alguns atualizados de propósito, + 29 novos) |
| 16 | Sensibilidade dos testes do parser | Mutação manual | Associatividade trocada para a direita em `_binaria` | 204 casos reprovados; restaurado |
| 17 | Idem | Mutação manual | Nó pai sem cobrir os parênteses | 229 casos reprovados (oráculo); restaurado |
| 18 | Revisão visual em 1366 px e 390 px | Capturas com Playwright | `docs/interface/ast-*.png`, `erros-sintaticos.png`, `celular-ast.png` | Sem rolagem horizontal; problemas listados abaixo e corrigidos |

### Testes que mudaram de propósito (regressão)

| Teste | Antes (Etapa 3) | Agora (Etapa 4) |
| --- | --- | --- |
| Contrato de `POST /api/analisar` | 10 campos | os mesmos 10 campos **mais** `lexico` e `sintatico` |
| Mensagem geral | "Análise léxica concluída sem erros: N tokens reconhecidos." | "Análises léxica e sintática concluídas sem erros: N tokens reconhecidos e AST com M nós." (o resumo léxico continua em `lexico.mensagem`) |
| Mensagem com erro léxico | resumo léxico | resumo léxico + "A análise sintática não foi executada." |
| Estado do resultado na interface | `lexico_ok` | `analise_ok` (ou `sintatico_erros`) |
| Exemplo "Erro sintático (tokens válidos)" e `if x > 5` sem `:` | aceitos (sem erro léxico) | sem erro léxico, mas **recusados pelo parser** |
| `for x:` (aviso léxico) | aceito | aviso léxico mantido + erro `palavra_fora_do_subconjunto` |
| Teste das ligaduras | código `x >= 1 != 2` | `x = a >= 1` e `y = b != 2` (o código antigo é uma comparação encadeada, agora recusada) |
| Fase atual no cabeçalho | Tokens | Árvore sintática (próxima: Semântica, "em breve") |

Os testes de regressão das etapas anteriores continuam passando: `/api/health`, `/api/hello`, validações (400, 413, 422), 404/405/500, falhas de comunicação, tokens iguais aos da Etapa 3, tabela, cores, passo a passo léxico e celular.

### Execução final de regressão

| Suíte | Aprovados | Reprovados |
| --- | --- | --- |
| Backend (validação 20, endpoints 36, scanner 58, parser 72, assistente 21) | 207 | 0 |
| Frontend (unitários) | 74 | 0 |
| Interface e ponta a ponta | 77 | 0 |
| **Total** | **358** | **0** |

### Falhas encontradas e correções

| Falha | Como apareceu | Causa | Correção |
| --- | --- | --- | --- |
| 50 erros iguais ("foi encontrado o fim do bloco") para uma única linha recuada | Teste manual de recuperação | A sincronização parava em `DEDENT` sem consumi-lo e o laço do programa tentava a mesma posição de novo | Bloco órfão analisado e descartado (`_bloco_orfao`) e garantia de progresso de pelo menos um token por recuperação; testes `test_indentacao_inesperada` e `test_programa_com_muitos_erros_para_no_limite` |
| Dezenas de programas aleatórios "válidos" recusados | Oráculo | **Erro no gerador de testes**: criava `a < b > c`, que no Python é comparação encadeada, fora do subconjunto | Gerador refeito: comparações só no nível de cima, entre parênteses ou como argumento |
| `x = ()` esperado como inválido também no Python | Oráculo | **Erro no teste**: em Python `()` é uma tupla vazia | Caso retirado da lista "o Python rejeita"; continua testado como fora do subconjunto |
| 2 testes de endpoint reprovados | `test_api` | **Erro no teste**: contagem feita de cabeça (7 nós e 16 tokens); o certo é 6 nós e 17 tokens | Expectativas corrigidas depois de contar nó a nó e token a token |
| `if a and b:` dava "era esperado ':'" | Revisão das mensagens | `and` não era tratado | Novo código `operador_logico_fora_do_subconjunto` (`and`, `or`, `not`, `in`, `is`) e teste |
| "Recolher tudo" não escondia os nós | Teste de interface `test_expandir_recolher_e_teclado` | Faltava a regra CSS que esconde grupos recolhidos | `li[aria-expanded="false"] > ul { display: none }` |
| Teste de posição falhava para "coluna 18" | Teste de interface | **Erro no teste**: `\b` não separa "18" de "Atributos" no texto concatenado | Expressão regular trocada por `(?!\d)` |
| `:` ausente no fim da linha não aparecia no código | Captura de tela | A marca ficava depois do último caractere da linha | Marcador `↵` visível no ponto do erro |
| Caixa vazia da árvore quando não há AST | Captura de tela | A lista era exibida mesmo sem nós | Árvore, legenda e texto escondidos; fica só o aviso explicativo |

### Execução no Docker

Pendente: rodar `scripts\testar.ps1` e `scripts\testar-ia.ps1` no Windows com a versão 0.4.0 e registrar aqui.

## Etapa 3 — Análise léxica (scanner) (27/10/2026)

**Ambiente das execuções:** Linux, Python 3.13, Starlette 1.6.0, Uvicorn 0.53.0, Node.js 22.22, Playwright 1.56.0 com Chromium, servidor local `tests/e2e/servidor_local.py` (frontend + backend real). A execução no Docker é feita no Windows com `scripts\testar.ps1` e está registrada abaixo, em seção própria.

### Execuções por funcionalidade

| # | Funcionalidade | Tipo de teste | Comando | Resultado |
| --- | --- | --- | --- | --- |
| 1 | Scanner: palavras reservadas, identificadores, literais, operadores (inclusive compostos e casamento mais longo), delimitadores, comentários, espaços, indentação, posições, erros léxicos e casos de borda (código vazio, sem quebra final, CRLF, tabulação no meio da linha, parênteses em várias linhas) | Unitário | `cd backend && python -m unittest tests.test_scanner -v` | 58 aprovados, 0 reprovados |
| 2 | Scanner comparado ao `tokenize` do Python (categoria, texto, linha e coluna) nos exemplos da interface, em programas de referência e em 300 programas aleatórios | Oráculo (diferencial) | incluído no comando anterior (`TestComparacaoComTokenizeDoPython`) | Aprovado: nenhuma divergência |
| 3 | `POST /api/analisar` com tokens, erros, avisos, comentários, contagem e passos; erro léxico com 200 e `sucesso: false`; entrada vazia sem chamar o scanner; falha do scanner como 500 genérico | Endpoints | `cd backend && python -m unittest tests.test_api -v` | 29 aprovados (21 da Etapa 2, alguns atualizados, + 8 novos) |
| 4 | Preparação dos tokens para a tela (`frontend/js/lexico.js`): nomes e classes das 13 categorias, lexemas visíveis, contagem, segmentação do código, erros sobre tokens e em várias linhas, CRLF | Unitário (frontend) | `cd frontend && node --test "tests/unit/*.test.js"` | 53 aprovados (39 da Etapa 2, 3 gerados automaticamente para o novo exemplo e 11 novos de `lexico.test.js`) |
| 5 | Tabela de tokens, código colorido, contagem, lista de erros com "Mostrar no código", avisos, passo a passo (botões, teclado, reprodução, pilha, esmaecimento, clique no token), aviso de código alterado, celular com toque | Interface e ponta a ponta | `BASE_URL=http://localhost:8090 python -m unittest tests.e2e.test_interface -v` | 48 aprovados (31 da Etapa 2, alguns atualizados, + 17 novos) |
| 6 | Sensibilidade do oráculo | Mutação manual | Coluna do `DEDENT` alterada de propósito em `scanner.py` | Dezenas de subtestes reprovaram; arquivo restaurado e testes aprovados de novo |
| 7 | Sensibilidade dos testes de interface | Mutação manual | Esmaecimento dos tokens futuros desligado em `interface.js` | 1 teste do passo a passo reprovou; arquivo restaurado e testes aprovados de novo |
| 8 | Revisão visual em 1366 px e 390 px | Capturas de tela com Playwright | `docs/interface/*.png` | Sem rolagem horizontal; problemas encontrados listados abaixo e corrigidos |

### Testes que mudaram de propósito (regressão)

Mudanças intencionais de comportamento entre a Etapa 2 e a Etapa 3, refletidas nos testes:

| Teste | Antes (Etapa 2) | Agora (Etapa 3) |
| --- | --- | --- |
| Contrato de `POST /api/analisar` | `recebido`, `mensagem`, `estatisticas` | os mesmos campos **mais** `sucesso`, `tokens`, `erros`, `avisos`, `comentarios`, `contagem`, `passos` |
| Mensagem de sucesso | "Código recebido com sucesso..." | "Análise léxica concluída sem erros: N tokens reconhecidos." |
| Estado do resultado na interface | `sucesso` | `lexico_ok` ou `lexico_erros` |
| Texto do botão durante o envio | "Enviando…" | "Analisando…" |
| Estado inicial | frase de orientação | tutorial "Como usar" com 4 passos |
| Fase atual no cabeçalho | Código-fonte | Tokens |
| Exemplo com erro | "Programa com erro intencional" | "Erro sintático (tokens válidos)", que deve terminar **sem** erro léxico; novo exemplo "Erros léxicos" |

Os testes de regressão das etapas anteriores continuam passando: `/api/health`, `/api/hello`, validação de entrada (400, 413, 422), erros 404/405/500, falhas de comunicação, edição, exemplos e layout no celular.

### Execução final de regressão

| Suíte | Aprovados | Reprovados |
| --- | --- | --- |
| Backend (scanner + validação + endpoints) | 107 | 0 |
| Frontend (unitário) | 53 | 0 |
| Interface e ponta a ponta | 48 | 0 |
| **Total** | **208** | **0** |

### Falhas encontradas e correções

| Falha | Como apareceu | Causa | Correção |
| --- | --- | --- | --- |
| Coluna do `DEDENT` diferente da do Python | Teste de oráculo | O scanner usava a largura do recuo + 1 | Passou a usar a coluna real do primeiro caractere da linha |
| 2 testes de endpoint reprovados | `test_api` | **Erro no teste**: esperava 9 tokens para `x = 10\nprint(x)`, mas o certo é 10 (há a `NOVA_LINHA` implícita do fim do arquivo e o `FIM_DE_ARQUIVO`) | Expectativa corrigida para 10, conferida com o `tokenize` |
| `.5` gerava "'.' é acesso a atributo" | Revisão manual das mensagens | O ponto era tratado como operador | Novo caso: `.5` gera `literal_real_incompleto` sugerindo `0.5`; teste `test_real_sem_digito_antes_do_ponto` |
| Painel da análise visível antes da primeira análise | Captura de tela | `display: flex` do painel anulava o atributo `hidden` | Regra `[hidden] { display: none !important; }` |
| Texto "null" no fim do resultado | Captura de tela | Lista de avisos vazia era passada como `null` ao DOM | Itens vazios são filtrados antes de montar o resultado |
| Rótulo `INDENT` invisível na tabela e na contagem | Captura de tela | A classe da categoria deixa o texto transparente (para desenhar o recuo no código) | Cor própria para os rótulos; teste de regressão na tabela |
| `>=`, `<=`, `!=` e `==` desenhados como um único símbolo (≥, ≤, ≠) | Prints da validação no Docker (no ambiente local a fonte do Google não carregava, por isso não apareceu antes) | Ligaduras da fonte JetBrains Mono: o estudante via um caractere onde o lexema tem dois | Ligaduras desligadas em toda a página (`font-variant-ligatures: none`); teste de regressão `test_operadores_compostos_sem_ligaduras`, que reprova se a regra for removida |
| Coluna "Coluna" cortada na tabela e controles quebrados em duas linhas no celular | Captura de tela em 390 px | Nomes de tipo longos e botões largos | Quebra dos nomes depois de `_`, grade 1:1 no desktop e botões menores no celular |

### Execução no Docker (Windows, Docker 29.8.2, 27/10/2026)

Comandos: `git pull` e `powershell -ExecutionPolicy Bypass -File scripts\testar.ps1`

| Etapa do script | Resultado |
| --- | --- |
| 1. Implantação (build + healthcheck) | Aprovada |
| 2. Testes do backend no contêiner | Aprovados |
| 3. Testes do frontend no contêiner | Aprovados |
| 4. Testes de interface (Playwright contra o Nginx) | 47 aprovados, 0 reprovados, em 46,3 s |

Evidências: [`validacao/06-etapa3-testes-docker.png`](validacao/06-etapa3-testes-docker.png) (resumo do script) e [`validacao/07-etapa3-interface-docker.png`](validacao/07-etapa3-interface-docker.png) (interface 0.3.0 em http://localhost:8080, com a fase Tokens disponível). Todas as suítes passaram no Docker. Os prints da interface com o exemplo "Erros léxicos" analisado ([`validacao/08-etapa3-erros-lexicos-docker.png`](validacao/08-etapa3-erros-lexicos-docker.png) e [`validacao/09-etapa3-passo-a-passo-docker.png`](validacao/09-etapa3-passo-a-passo-docker.png)) mostraram um defeito visual que os testes não pegavam: com a fonte JetBrains Mono carregada da internet, `>=` aparecia como `≥` (ligadura tipográfica). O defeito foi corrigido e ganhou um teste de regressão (ver "Falhas encontradas e correções"); a suíte de interface passou a ter 48 testes. Depois de `git pull` e `docker compose up -d --build`, a correção foi conferida no Docker: a linha 5 do exemplo mostra `>=` com dois caracteres ([`validacao/10-etapa3-ligaduras-corrigidas-docker.png`](validacao/10-etapa3-ligaduras-corrigidas-docker.png)).

### Pendências

- Testes de interface em Firefox e WebKit.

## Etapa 2 — Interface web e entrada de código-fonte (15/10/2026)

**Ambiente das execuções:** Linux, Python 3.13, Starlette 1.6.0, Uvicorn 0.53.0, Node.js 22.22, Playwright 1.56.0 com Chromium. Os testes de interface usaram o `tests/e2e/servidor_local.py`, que reúne o frontend e o backend real em um único servidor, porque o Docker Hub não estava acessível no ambiente de desenvolvimento.

### Execuções por funcionalidade

| # | Funcionalidade | Tipo de teste | Comando | Resultado |
| --- | --- | --- | --- | --- |
| 1 | Regras de validação da entrada | Unitário (backend) | `cd backend && python -m unittest tests.test_validacao -v` | 20 aprovados, 0 reprovados |
| 2 | Endpoint `POST /api/analisar`, erros 400/404/405/413/422/500 e regressão de `/api/health` e `/api/hello` | Endpoints (backend) | `cd backend && python -m unittest discover -s tests -t . -v` | 41 aprovados, 0 reprovados (20 + 21 novos) |
| 3 | Endpoint rodando no servidor real (Uvicorn) | Fumaça manual com `curl` | `curl -X POST localhost:8765/api/analisar -d '{"codigo":"x = 1"}'` e casos de espaços e JSON inválido | 200, 400 e 400, como no contrato |
| 4 | Validação no navegador, exemplos e cliente da API | Unitário (frontend) | `cd frontend && node --test "tests/unit/*.test.js"` | 39 aprovados, 0 reprovados |
| 5 | Tela, edição, exemplos, envio, mensagens e falhas de comunicação | Interface e ponta a ponta | `BASE_URL=http://localhost:8090 python -m unittest tests.e2e.test_interface -v` | 31 aprovados, 0 reprovados |
| 6 | Sensibilidade dos testes (prova de que detectam defeitos) | Mutação manual | Mensagem de entrada vazia alterada de propósito em `frontend/js/validacao.js` | 1 unitário e 1 de interface reprovaram, como esperado; arquivo restaurado e testes aprovados de novo |
| 7 | Arquivo do Docker Compose, incluindo o perfil `testes` | Verificação de configuração | `docker compose config --quiet` e `docker compose --profile testes config --services` | Válido; 5 serviços (backend, frontend, testes-backend, testes-frontend, testes-e2e) |

### Execução final de regressão

Todas as suítes foram executadas juntas depois da última alteração de código:

| Suíte | Aprovados | Reprovados |
| --- | --- | --- |
| Backend (unitário + endpoints) | 41 | 0 |
| Frontend (unitário) | 39 | 0 |
| Interface e ponta a ponta | 31 | 0 |
| **Total** | **111** | **0** |

### Falhas encontradas e correções

| Problema | Como apareceu | Correção |
| --- | --- | --- |
| `node --test tests/unit/` não encontrava os testes | O Node 22 interpretou a pasta como um módulo e terminou com `MODULE_NOT_FOUND` | O comando passou a usar o padrão `"tests/unit/*.test.js"` (em `package.json` e no Compose) |
| Rolagem horizontal no celular | Inspeção com Playwright em 320 e 390 px: a página ficava com 417 px de largura | A coluna da grade passou de `1fr` para `minmax(0, 1fr)` e o seletor de exemplos passou a ocupar a largura disponível. Foi criado o teste `test_sem_rolagem_horizontal_em_tela_de_celular` para evitar regressão |
| Resultado fora da tela no celular | Na tela estreita, a resposta aparecia abaixo da área visível depois do clique | O resultado passou a rolar para a vista quando é atualizado |
| Configuração do Nginx com risco | Revisão: um bloco `types` extra substituiria a tabela de tipos MIME padrão | Bloco removido; o Nginx já serve `.js` como `application/javascript` |

Nenhum teste foi alterado para esconder uma falha.

### Execução no Docker (Windows, Docker 29.8.2)

Comando: `powershell -ExecutionPolicy Bypass -File scripts\testar.ps1`

| Etapa do script | Resultado |
| --- | --- |
| 1. Implantação (`docker compose up -d --build --wait`) | Aprovada: imagens construídas, backend e frontend saudáveis |
| 2. Testes do backend no contêiner | Aprovados |
| 3. Testes do frontend no contêiner | Aprovados |
| 4. Testes de interface no contêiner | Falharam antes de executar: `ModuleNotFoundError: No module named 'playwright'` |

**Causa:** a imagem oficial `mcr.microsoft.com/playwright/python` traz o Python e os navegadores, mas não o pacote `playwright` do Python. **Correção:** criada a imagem `tests/e2e/Dockerfile`, que parte da oficial e instala `playwright==1.56.0`. Também foi incluído `--build` nos comandos `docker compose run`, para que os testes sempre usem o código atual, e as mensagens do script passaram a ser exibidas sem acentos, que apareciam embaralhados no PowerShell ISE.

### Nova execução no Docker após a correção (Windows, Docker 29.8.2)

Comando: `powershell -ExecutionPolicy Bypass -File scripts\testar.ps1`

| Etapa do script | Resultado |
| --- | --- |
| 1. Implantação (build + healthcheck) | Aprovada |
| 2. Testes do backend | Aprovados |
| 3. Testes do frontend | Aprovados |
| 4. Testes de interface (Playwright contra o Nginx) | 31 aprovados, 0 reprovados, em 22,5 s |

Evidências: [`validacao/04-etapa2-testes-docker.png`](validacao/04-etapa2-testes-docker.png) (testes) e [`validacao/05-etapa2-interface-docker.png`](validacao/05-etapa2-interface-docker.png) (interface em http://localhost:8080 recebendo um programa). Com isso, todas as suítes passaram tanto no ambiente local quanto nos contêineres.

### Pendências

- Testes de interface em outros navegadores (Firefox e WebKit).

## Etapa 1 — Estrutura inicial e Docker (15/10/2026)

Validação manual de instalação limpa no Windows com Docker 29.8.2: `docker compose up --build -d`, backend `healthy`, `GET /api/hello` com "Hello, World!", página no navegador e `docker compose down`. As evidências estão em [`validacao/`](validacao/).

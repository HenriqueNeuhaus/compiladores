# Registro de testes

Registro das execuções de teste do projeto, em ordem cronológica. Cada etapa traz o que foi testado, os comandos usados, os resultados, as falhas encontradas e o que ainda falta.

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

Evidências: [`validacao/06-etapa3-testes-docker.png`](validacao/06-etapa3-testes-docker.png) (resumo do script) e [`validacao/07-etapa3-interface-docker.png`](validacao/07-etapa3-interface-docker.png) (interface 0.3.0 em http://localhost:8080, com a fase Tokens disponível). Todas as suítes passaram no Docker. Os prints da interface com o exemplo "Erros léxicos" analisado ([`validacao/08-etapa3-erros-lexicos-docker.png`](validacao/08-etapa3-erros-lexicos-docker.png) e [`validacao/09-etapa3-passo-a-passo-docker.png`](validacao/09-etapa3-passo-a-passo-docker.png)) mostraram um defeito visual que os testes não pegavam: com a fonte JetBrains Mono carregada da internet, `>=` aparecia como `≥` (ligadura tipográfica). O defeito foi corrigido e ganhou um teste de regressão (ver "Falhas encontradas e correções"); a suíte de interface passou a ter 48 testes.

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

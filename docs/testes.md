# Registro de testes

Registro das execuções de teste do projeto, em ordem cronológica. Cada etapa traz o que foi testado, os comandos usados, os resultados, as falhas encontradas e o que ainda falta.

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

### Pendências

- **Testes de interface no Docker:** executar novamente `scripts/testar.ps1` depois da correção acima e registrar o resultado.
- Testes de interface em outros navegadores (Firefox e WebKit).

## Etapa 1 — Estrutura inicial e Docker (15/10/2026)

Validação manual de instalação limpa no Windows com Docker 29.8.2: `docker compose up --build -d`, backend `healthy`, `GET /api/hello` com "Hello, World!", página no navegador e `docker compose down`. As evidências estão em [`validacao/`](validacao/).

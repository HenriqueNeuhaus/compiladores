# Compiladores — Visualizador Educacional

Software educacional web para estudar as **análises léxica e sintática** com programas escritos em um subconjunto da linguagem **Python**. É voltado a estudantes de graduação em Computação que cursam a disciplina de Compiladores.

> **Etapa atual: 2 — interface web e entrada de código-fonte.** O estudante escreve ou escolhe um programa, solicita a análise e recebe a resposta do servidor. Nesta versão o servidor **recebe e valida** o código; ele **ainda não** faz análise léxica, sintática nem semântica, que serão implementadas nas próximas etapas.
>
> A definição do problema e a revisão de literatura estão em [`docs/revisao-literatura.md`](docs/revisao-literatura.md).

![Tela principal do Visualizador de Compiladores](docs/interface/tela-principal.png)

## Sumário

1. [Objetivo](#1-objetivo)
2. [Linguagem escolhida e subconjunto](#2-linguagem-escolhida-e-subconjunto)
3. [Tecnologias](#3-tecnologias)
4. [Estrutura do repositório](#4-estrutura-do-repositório)
5. [Pré-requisitos](#5-pré-requisitos)
6. [Como executar e acessar](#6-como-executar-e-acessar)
7. [Como encerrar](#7-como-encerrar)
8. [Usando a interface](#8-usando-a-interface)
9. [Exemplos disponíveis](#9-exemplos-disponíveis)
10. [Comunicação entre frontend e backend](#10-comunicação-entre-frontend-e-backend)
11. [Testes](#11-testes)
12. [Limitações conhecidas](#12-limitações-conhecidas)
13. [Histórico das etapas](#13-histórico-das-etapas)

---

## 1. Objetivo

Ajudar estudantes a compreender como um compilador lê um programa, mostrando passo a passo o reconhecimento de tokens por autômatos finitos e a construção da árvore sintática, a partir de um código que o próprio estudante escreve. A ferramenta usa Python porque muitos alunos já conhecem a linguagem, o que permite concentrar o esforço nos conceitos de compilação.

## 2. Linguagem escolhida e subconjunto

### Por que Python

| Motivo | Explicação |
| --- | --- |
| Familiaridade | É a linguagem com que muitos alunos começam a graduação; o estudante analisa um código que já sabe ler. |
| Sintaxe enxuta | Permite definir um subconjunto pequeno sem perder realismo. |
| Desafio léxico próprio | A indentação gera os tokens `INDENT` e `DEDENT`, conceito ausente em linguagens delimitadas por chaves e pouco explorado nas ferramentas existentes. |
| Validação | Os módulos nativos `tokenize` e `ast` poderão servir de referência para conferir os resultados dos analisadores. |

### Subconjunto previsto

O projeto **não** cobre o Python inteiro. Os analisadores das próximas etapas tratarão:

| Categoria | Construções incluídas | Exemplo |
| --- | --- | --- |
| Literais | Inteiros, números de ponto flutuante, strings entre aspas, `True`, `False` | `42`, `3.14`, `"oi"` |
| Identificadores e atribuição | Nomes de variáveis e atribuição simples | `x = 10` |
| Operadores aritméticos | `+`, `-`, `*`, `/`, `%` e parênteses | `(a + b) * 2` |
| Operadores relacionais | `==`, `!=`, `<`, `<=`, `>`, `>=` | `x >= 0` |
| Condicional | `if` / `elif` / `else` com blocos indentados | `if x > 0:` |
| Repetição | `while` com bloco indentado | `while i < 10:` |
| Saída | Chamada a `print(...)` | `print(x)` |
| Estrutura de bloco | Tokens `NEWLINE`, `INDENT`, `DEDENT` e comentários `#` | — |

**Fora do escopo inicial:** funções (`def`), `for`, listas, dicionários, classes, `import` e operadores lógicos (`and`, `or`, `not`).

## 3. Tecnologias

| Parte | Tecnologia | Observação |
| --- | --- | --- |
| Frontend | HTML, CSS e JavaScript (módulos ES, sem etapa de build) | Servido pelo **Nginx 1.27** |
| Backend | **Python 3.12** com **Starlette 1.6** e **Uvicorn 0.53** | Na Etapa 2 a API passou de FastAPI para Starlette, a base do próprio FastAPI, por ser mais leve; o contrato da Etapa 1 foi mantido |
| Orquestração | **Docker Compose** | Serviços `frontend` e `backend`, mais o perfil `testes` |
| Testes do backend | `unittest` (biblioteca padrão do Python) | Sem dependências extras |
| Testes do frontend | `node --test` (Node.js 22) | Sem dependências extras |
| Testes de interface e ponta a ponta | **Playwright 1.56** (Python) com Chromium | Imagem `tests/e2e/Dockerfile`, baseada na oficial `mcr.microsoft.com/playwright/python:v1.56.0-noble` |

Não há banco de dados: o projeto ainda não precisa guardar informações.

## 4. Estrutura do repositório

```
compiladores/
├── backend/
│   ├── app/
│   │   ├── main.py            # rotas da API e tratamento de erros
│   │   └── validacao.py       # regras de validação da entrada (sem dependência do framework)
│   ├── tests/
│   │   ├── cliente_asgi.py    # cliente HTTP em processo para os testes
│   │   ├── test_api.py        # testes dos endpoints
│   │   └── test_validacao.py  # testes unitários das regras
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html             # tela principal
│   ├── css/estilo.css
│   ├── js/
│   │   ├── app.js             # ponto de entrada
│   │   ├── interface.js       # liga a tela ao comportamento
│   │   ├── api.js             # comunicação com o backend
│   │   ├── validacao.js       # validação no navegador
│   │   └── exemplos.js        # programas de exemplo
│   ├── tests/unit/            # testes unitários (node --test)
│   ├── nginx.conf             # serve o frontend e repassa /api/ ao backend
│   ├── package.json
│   └── Dockerfile
├── tests/e2e/
│   ├── test_interface.py      # testes de interface e ponta a ponta (Playwright)
│   ├── servidor_local.py      # frontend + backend juntos para testar sem Docker
│   └── Dockerfile             # imagem dos testes de interface
├── scripts/
│   ├── testar.ps1             # roda todos os testes no Docker (Windows)
│   └── testar.sh              # idem (Linux/macOS)
├── docs/
│   ├── testes.md              # registro das execuções de teste
│   ├── interface/             # capturas de tela da interface
│   ├── validacao/             # evidências da validação da Etapa 1
│   └── revisao-literatura.md
├── docker-compose.yml
└── README.md
```

## 5. Pré-requisitos

| Ferramenta | Versão mínima | Como verificar |
| --- | --- | --- |
| Git | 2.30 | `git --version` |
| Docker Engine (ou Docker Desktop) | 24.0 | `docker --version` |
| Docker Compose (plugin v2) | 2.20 | `docker compose version` |

A porta **8080** precisa estar livre. Não é necessário instalar Python nem Node.js: tudo, inclusive os testes, roda em contêineres. Na primeira execução dos testes, o Docker baixa as imagens do Node e do Playwright (cerca de 2 GB no total).

> No Windows e no macOS, instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/), que já inclui o Docker Compose. No Linux, instale o [Docker Engine](https://docs.docker.com/engine/install/) e o plugin `docker-compose-plugin`.

## 6. Como executar e acessar

```bash
git clone https://github.com/HenriqueNeuhaus/compiladores.git
cd compiladores
docker compose up --build -d --wait
```

O `--wait` faz o comando só terminar quando o backend e o frontend estiverem saudáveis. Depois, abra **http://localhost:8080** no navegador.

Para conferir pelo terminal:

```bash
docker compose ps                               # backend e frontend como "healthy"
curl http://localhost:8080/api/health            # {"status":"ok","versao":"0.2.0"}
```

No PowerShell do Windows, use `curl.exe` no lugar de `curl`.

## 7. Como encerrar

```bash
docker compose down              # para e remove os contêineres e a rede
docker compose down --rmi local  # também remove as imagens construídas pelo projeto
```

## 8. Usando a interface

| Elemento | O que faz |
| --- | --- |
| Cabeçalho | Mostra o nome do sistema, a linguagem analisada (Python, subconjunto) e as fases do compilador. A fase **Código-fonte** está disponível; **Tokens** e **Árvore sintática** aparecem como "em breve". |
| **Exemplo** | Lista os programas prontos. Ao escolher um, o código **substitui** o conteúdo do editor e uma linha explica quais construções ele demonstra. O código carregado pode ser editado normalmente. |
| Editor de código | Campo com fonte monoespaçada e numeração de linhas, para escrever, colar ou editar o programa. **Tab** insere quatro espaços; para sair do editor pelo teclado, pressione **Esc** e depois **Tab**. Abaixo há um contador de linhas e caracteres. |
| **Analisar código** | Envia o código ao backend. Durante o envio o botão fica desabilitado e mostra "Enviando…". O código continua no editor depois da resposta. |
| **Limpar** | Esvazia o editor e o resultado. |
| **Resultado** | Mostra a resposta do servidor ou o motivo de o código não ter sido aceito. |

O sistema **não** presume que o código é válido: programas com erros são aceitos, pois serão usados nas próximas etapas para mostrar como o compilador encontra problemas.

### Mensagens apresentadas

| Situação | Onde é detectada | Mensagem |
| --- | --- | --- |
| Editor vazio | Navegador (e backend) | Informe um código-fonte antes de solicitar a análise. |
| Só espaços ou quebras de linha | Navegador (e backend) | O código informado contém apenas espaços ou quebras de linha. Escreva um programa ou escolha um exemplo. |
| Mais de 20 000 caracteres | Navegador (e backend) | O código informado ultrapassa o limite de 20000 caracteres. |
| Requisição fora do contrato | Backend | Mensagem específica do problema (JSON inválido, campo ausente etc.) |
| Servidor fora do ar, rede indisponível ou mais de 10 s sem resposta | Navegador | Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente. |
| Erro inesperado no servidor | Backend e navegador | Ocorreu um erro inesperado ao processar a solicitação. Tente novamente. |

As mensagens de entrada aparecem em amarelo e as falhas de comunicação e erros inesperados, em vermelho. Nenhuma mensagem expõe rastreamentos, caminhos internos ou variáveis do servidor.

## 9. Exemplos disponíveis

| Exemplo | Construções que pretende demonstrar |
| --- | --- |
| Atribuição e expressões aritméticas | Atribuição, números inteiros e decimais, operadores `+ - * /`, parênteses, comentário e `print` |
| Estrutura condicional | `if`, `elif` e `else`, operadores relacionais, strings e blocos indentados (`INDENT`/`DEDENT`) |
| Repetição com blocos aninhados | `while`, `if` dentro de `while`, operador `%`, comparação `==` e vários níveis de indentação |
| Programa com erro intencional | `if` sem os dois-pontos no fim da linha, para demonstrar a detecção de erros sintáticos nas próximas etapas |

O código de cada exemplo está em [`frontend/js/exemplos.js`](frontend/js/exemplos.js).

## 10. Comunicação entre frontend e backend

O navegador sempre chama a API no mesmo endereço da página (`/api/...`). O Nginx do contêiner `frontend` repassa essas requisições para `http://backend:8000`, nome que só existe dentro da rede do Docker. Assim, o navegador nunca precisa conhecer o endereço interno do backend.

```
Navegador ──► frontend (Nginx, porta 8080) ──/api/──► backend (Starlette, porta 8000)
```

### `POST /api/analisar`

Requisição (`Content-Type: application/json`):

```json
{ "codigo": "x = 10\nprint(x)" }
```

Resposta de sucesso, **200**:

```json
{
  "recebido": true,
  "mensagem": "Código recebido com sucesso. A análise léxica e sintática será implementada nas próximas etapas do projeto.",
  "estatisticas": { "linhas": 2, "caracteres": 15 }
}
```

Respostas de erro, sempre no mesmo formato:

```json
{ "recebido": false, "erro": { "tipo": "entrada_vazia", "mensagem": "Informe um código-fonte antes de solicitar a análise." } }
```

| Código HTTP | `erro.tipo` | Quando ocorre |
| --- | --- | --- |
| 400 | `json_invalido` | Corpo vazio, que não é JSON ou que não está em UTF-8 |
| 400 | `entrada_vazia` | `codigo` é um texto vazio |
| 400 | `entrada_em_branco` | `codigo` tem só espaços, tabulações ou quebras de linha |
| 413 | `entrada_muito_grande` | `codigo` com mais de 20 000 caracteres |
| 422 | `corpo_nao_objeto` | O JSON não é um objeto (por exemplo, uma lista) |
| 422 | `campo_ausente` | Falta o campo `codigo` |
| 422 | `tipo_invalido` | `codigo` não é texto (número, nulo, lista…) |
| 404 | `rota_inexistente` | Endereço da API que não existe |
| 405 | `metodo_nao_permitido` | Método errado, por exemplo `GET /api/analisar` |
| 500 | `erro_interno` | Erro inesperado; o detalhe fica só no log do servidor |

### Outros endpoints

| Endpoint | Resposta | Uso |
| --- | --- | --- |
| `GET /api/health` | `{"status": "ok", "versao": "0.2.0"}` | Healthcheck do Docker Compose |
| `GET /api/hello` | `{"message": "Hello, World!"}` | Mantido da Etapa 1, por compatibilidade |

## 11. Testes

Os testes cresceram junto com cada funcionalidade e cobrem quatro níveis:

| Tipo | O que verifica | Ferramenta | Arquivos | Quantidade |
| --- | --- | --- | --- | --- |
| Unitário (backend) | Regras de validação e estatísticas | `unittest` | `backend/tests/test_validacao.py` | 20 |
| Endpoints (backend) | Respostas válidas, contrato JSON, códigos HTTP, campos ausentes ou inválidos, erro 500 sem detalhes, regressão da Etapa 1 | `unittest` | `backend/tests/test_api.py` | 21 |
| Unitário (frontend) | Validação no navegador, exemplos e classificação das respostas do servidor (inclusive falha de rede e tempo limite) | `node --test` | `frontend/tests/unit/*.test.js` | 39 |
| Interface e ponta a ponta | Elementos da tela, edição, seleção de cada exemplo, envio real ao backend, mensagens de erro, falha de comunicação simulada, tela de celular e API pelo mesmo endereço | Playwright | `tests/e2e/test_interface.py` | 31 |
| Implantação | Build das imagens e healthcheck dos dois serviços | Docker Compose (`--wait`) | `docker-compose.yml` | — |

### Rodar tudo no Docker (recomendado)

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\testar.ps1
```

```bash
# Linux ou macOS
bash scripts/testar.sh
```

Os scripts sobem a aplicação com `--wait` (teste de implantação), rodam as três suítes e mostram um resumo. Também é possível rodar cada suíte separadamente:

```bash
docker compose up -d --build --wait
docker compose --profile testes run --build --rm testes-backend    # backend
docker compose --profile testes run --build --rm testes-frontend   # frontend (unitários)
docker compose --profile testes run --build --rm testes-e2e        # interface (Playwright contra o Nginx)
```

### Rodar sem Docker

Requer Python 3.12+, Starlette, Uvicorn, Playwright para Python com Chromium e Node.js 22.

```bash
cd backend && python -m unittest discover -s tests -t . -v && cd ..
cd frontend && node --test "tests/unit/*.test.js" && cd ..
python tests/e2e/servidor_local.py --porta 8090 &
BASE_URL=http://localhost:8090 python -m unittest tests.e2e.test_interface -v
```

### Resultados

| Data | Ambiente | Backend | Frontend | Interface | Implantação no Docker |
| --- | --- | --- | --- | --- | --- |
| 15/10/2026 | Linux, Python 3.13, Node 22, servidor local | 41 de 41 | 39 de 39 | 31 de 31 | não executada nesse ambiente |
| 15/10/2026 | Windows, Docker 29.8.2 (`scripts/testar.ps1`) | aprovado | aprovado | falhou: pacote `playwright` ausente na imagem (corrigido, aguardando nova execução) | aprovada (build + healthcheck) |

O registro completo, com os comandos, as falhas encontradas e as correções, está em [`docs/testes.md`](docs/testes.md).

## 12. Limitações conhecidas

- O sistema **ainda não** faz análise léxica, sintática nem semântica: ele recebe o código, valida a entrada e confirma o recebimento.
- A validação não verifica se o programa pertence ao subconjunto de Python; qualquer texto não vazio é aceito.
- O editor é um campo de texto simples, sem realce de sintaxe.
- As fontes Atkinson Hyperlegible e JetBrains Mono vêm do Google Fonts; sem internet, a página usa fontes do sistema.
- Os testes de interface usam apenas o Chromium.

## 13. Histórico das etapas

| Etapa | Entrega | Situação |
| --- | --- | --- |
| 1 | Linguagem, estrutura inicial, Docker e "Hello, World!" | Concluída; validação limpa no Windows em 15/10/2026, com evidências em [`docs/validacao/`](docs/validacao/) |
| 2 | Interface web, entrada de código, exemplos, comunicação, validações e testes automatizados | Esta versão |
| 3 | Analisador léxico do subconjunto, com visualização do autômato e dos tokens `INDENT`/`DEDENT` | Prevista |
| 4 | Analisador sintático com construção passo a passo da árvore | Prevista |

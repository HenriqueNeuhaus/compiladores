# Compiladores — Visualizador Educacional

Software educacional web que mostra, passo a passo, as **análises léxica e sintática** de programas escritos em um subconjunto da linguagem **Python**. É voltado a estudantes de graduação em Ciência da Computação que cursam a disciplina de Compiladores.

> **Etapa atual:** 1 — escolha da linguagem, estrutura inicial e ambiente Docker. A aplicação exibe "Hello, World!" vindo do backend.
>
> A definição do problema e a revisão de literatura estão em [`docs/revisao-literatura.md`](docs/revisao-literatura.md).

## Sumário

1. [Linguagem escolhida e subconjunto](#1-linguagem-escolhida-e-subconjunto)
2. [Estrutura do repositório](#2-estrutura-do-repositório)
3. [Arquitetura](#3-arquitetura)
4. [Pré-requisitos](#4-pré-requisitos)
5. [Como executar](#5-como-executar)
6. [Como encerrar](#6-como-encerrar)
7. [Validação de instalação limpa](#7-validação-de-instalação-limpa)
8. [Próximas etapas](#8-próximas-etapas)

---

## 1. Linguagem escolhida e subconjunto

### Linguagem analisada: Python

| Motivo | Explicação |
| --- | --- |
| Familiaridade | É a linguagem com que muitos alunos começam a graduação; o estudante analisa um código que já sabe ler. |
| Sintaxe enxuta | Permite definir um subconjunto pequeno sem perder realismo. |
| Desafio léxico próprio | A indentação gera os tokens `INDENT` e `DEDENT`, conceito ausente em linguagens delimitadas por chaves e pouco explorado nas ferramentas existentes. |
| Validação | Os módulos nativos `tokenize` e `ast` servem de referência para conferir os resultados do analisador. |

### Subconjunto inicial

O projeto **não** cobre o Python inteiro. A primeira versão do analisador tratará apenas:

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

**Fora do escopo inicial:** funções (`def`), `for`, listas, dicionários, classes, `import` e operadores lógicos (`and`, `or`, `not`). Esses itens poderão ser adicionados em etapas posteriores.

**Por que esse recorte?** Ele contém o suficiente para exercitar todas as categorias de token (palavras-chave, identificadores, literais, operadores, delimitadores e indentação) e gerar árvores sintáticas com aninhamento real, mantendo a gramática pequena o bastante para ser visualizada passo a passo.

---

## 2. Estrutura do repositório

```
compiladores/
├── backend/                 # API em Python (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py          # endpoints /api/health e /api/hello
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Interface web estática servida pelo Nginx
│   ├── Dockerfile
│   ├── index.html           # exibe a mensagem recebida do backend
│   └── nginx.conf           # serve o HTML e repassa /api/ ao backend
├── docs/
│   └── revisao-literatura.md
├── docker-compose.yml       # orquestra frontend e backend
├── .gitignore
└── README.md
```

Não há banco de dados nesta etapa, pois o projeto ainda não precisa guardar informações.

---

## 3. Arquitetura

```
Navegador ──► frontend (Nginx, porta 8080) ──/api/──► backend (FastAPI, porta 8000)
```

- O **frontend** serve a página `index.html` e repassa toda requisição que começa com `/api/` para o backend.
- O **backend** responde em `/api/hello` com `{"message": "Hello, World!"}`.
- A página busca essa mensagem e a exibe. Se aparecer **Hello, World!**, os dois serviços estão no ar e se comunicando.
- O backend só é acessível pela rede interna do Docker; apenas a porta **8080** do frontend é exposta.

---

## 4. Pré-requisitos

| Ferramenta | Versão mínima | Como verificar |
| --- | --- | --- |
| Git | 2.30 | `git --version` |
| Docker Engine (ou Docker Desktop) | 24.0 | `docker --version` |
| Docker Compose (plugin v2) | 2.20 | `docker compose version` |

A porta **8080** precisa estar livre. Não é necessário instalar Python nem Node.js na máquina: tudo roda dentro dos contêineres.

> No Windows e no macOS, instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/), que já inclui o Docker Compose. No Linux, instale o [Docker Engine](https://docs.docker.com/engine/install/) e o plugin `docker-compose-plugin`.

---

## 5. Como executar

```bash
# 1. Clonar o repositório
git clone https://github.com/HenriqueNeuhaus/compiladores.git
cd compiladores

# 2. Construir as imagens e subir os contêineres em segundo plano
docker compose up --build -d

# 3. Conferir se os dois serviços estão rodando (backend deve aparecer como "healthy")
docker compose ps
```

Depois, abra **http://localhost:8080** no navegador. A página deve exibir **Hello, World!**.

Para testar pelo terminal:

```bash
curl http://localhost:8080/api/hello
# {"message":"Hello, World!"}
```

A documentação automática da API fica em **http://localhost:8080/api/docs**.

Comandos úteis durante o desenvolvimento:

```bash
docker compose logs -f            # acompanhar os logs dos dois serviços
docker compose logs -f backend    # logs só do backend
docker compose up --build -d      # reconstruir após alterar o código
```

---

## 6. Como encerrar

```bash
# Parar e remover os contêineres e a rede criada pelo Compose
docker compose down

# (Opcional) remover também as imagens construídas pelo projeto
docker compose down --rmi local
```

---

## 7. Validação de instalação limpa

Para garantir que o projeto não depende de nada configurado só na máquina do autor, os passos das seções 5 e 6 devem ser executados a partir de um clone novo, sem imagens nem contêineres do projeto:

```bash
# Partir do zero: apagar clones antigos e imagens do projeto
docker compose down --rmi local 2>/dev/null
cd .. && rm -rf compiladores
git clone https://github.com/HenriqueNeuhaus/compiladores.git
cd compiladores
docker compose up --build -d
```

| Verificação | Resultado esperado | Status |
| --- | --- | --- |
| `docker compose up --build -d` | Imagens construídas e dois contêineres iniciados | ✅ |
| `docker compose ps` | `backend` com estado `healthy`, `frontend` em execução | ✅ |
| `curl http://localhost:8080/api/hello` | `{"message":"Hello, World!"}` | ✅ |
| http://localhost:8080 no navegador | Página exibe "Hello, World!" | ✅ |
| `docker compose down` | Contêineres e rede removidos | ⬜ |

Data da validação: 15/10/2026 · Sistema operacional: Windows (x64) · Docker: Docker Desktop

---

## 8. Próximas etapas

- [x] Etapa 1 — linguagem, estrutura inicial, Docker e "Hello, World!"
- [ ] Analisador léxico do subconjunto, com visualização do autômato e dos tokens `INDENT`/`DEDENT`
- [ ] Analisador sintático com construção passo a passo da árvore de derivação e da AST
- [ ] Explicações teóricas integradas e avaliação com estudantes

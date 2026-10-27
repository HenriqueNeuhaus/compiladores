"""API do visualizador educacional de compiladores (subconjunto de Python).

Etapa 3: a API recebe o código-fonte, valida a entrada e executa a análise
léxica (scanner), devolvendo tokens, erros léxicos e o passo a passo. A
análise sintática será adicionada na Etapa 4, no mesmo endpoint.

Endpoints:
- GET  /api/health   -> verificação de saúde usada pelo Docker Compose;
- GET  /api/hello    -> mensagem da Etapa 1, mantida por compatibilidade;
- POST /api/analisar -> recebe {"codigo": "..."} e devolve o resultado da
                        análise léxica em JSON.
"""

import json
import logging

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import scanner
from .validacao import LIMITE_CARACTERES, ErroValidacao, estatisticas, validar_corpo

logger = logging.getLogger("compiladores")

VERSAO = "0.3.0"

# Limite do corpo bruto da requisição, em bytes. Um caractere UTF-8 ocupa até
# 4 bytes; a folga cobre as aspas e o nome do campo no JSON.
LIMITE_BYTES = LIMITE_CARACTERES * 4 + 1024

def mensagem_lexica(resultado: scanner.ResultadoLexico) -> str:
    """Resumo da análise léxica para a área de resultados."""
    total = len(resultado.tokens)
    if resultado.sucesso:
        return f"Análise léxica concluída sem erros: {total} tokens reconhecidos."
    erros = len(resultado.erros)
    plural = "erro léxico encontrado" if erros == 1 else "erros léxicos encontrados"
    return (f"Análise léxica concluída com {erros} {plural}. "
            f"Os trechos válidos foram reconhecidos como {total} tokens.")
MENSAGEM_ERRO_INTERNO = (
    "Ocorreu um erro inesperado ao processar a solicitação. Tente novamente."
)


def resposta_erro(tipo: str, mensagem: str, status: int) -> JSONResponse:
    """Formato único para todas as respostas de erro da API."""
    return JSONResponse(
        {"recebido": False, "erro": {"tipo": tipo, "mensagem": mensagem}},
        status_code=status,
    )


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "versao": VERSAO})


async def hello(request: Request) -> JSONResponse:
    return JSONResponse({"message": "Hello, World!"})


async def analisar(request: Request) -> JSONResponse:
    corpo_bruto = await request.body()
    if len(corpo_bruto) > LIMITE_BYTES:
        erro = ErroValidacao("entrada_muito_grande", 413)
        return resposta_erro(erro.tipo, erro.mensagem, erro.status)

    try:
        corpo = json.loads(corpo_bruto.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        erro = ErroValidacao("json_invalido", 400)
        return resposta_erro(erro.tipo, erro.mensagem, erro.status)

    try:
        codigo = validar_corpo(corpo)
    except ErroValidacao as erro:
        return resposta_erro(erro.tipo, erro.mensagem, erro.status)

    resultado = scanner.analisar(codigo)
    return JSONResponse(
        {
            "recebido": True,
            "mensagem": mensagem_lexica(resultado),
            "estatisticas": estatisticas(codigo),
            **resultado.como_dict(),
        }
    )


async def erro_http(request: Request, exc: HTTPException) -> JSONResponse:
    """Rotas inexistentes (404) e métodos não permitidos (405) em JSON."""
    tipos = {
        404: ("rota_inexistente", "O recurso solicitado não existe."),
        405: ("metodo_nao_permitido", "Método HTTP não permitido para este recurso."),
    }
    tipo, mensagem = tipos.get(
        exc.status_code, ("erro_http", "A requisição não pôde ser atendida.")
    )
    return resposta_erro(tipo, mensagem, exc.status_code)


async def erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    """Erro não previsto: registra no log do servidor e devolve mensagem genérica,
    sem expor rastreamento, caminhos internos ou variáveis de ambiente."""
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
    return resposta_erro("erro_interno", MENSAGEM_ERRO_INTERNO, 500)


rotas = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/hello", hello, methods=["GET"]),
    Route("/api/analisar", analisar, methods=["POST"]),
]

app = Starlette(
    routes=rotas,
    exception_handlers={HTTPException: erro_http, Exception: erro_inesperado},
)

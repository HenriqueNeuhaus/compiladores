"""Servidor local para os testes de interface sem Docker.

Reproduz o que o Nginx faz no Docker Compose: serve os arquivos do frontend
e encaminha /api/ para o backend. Aqui o backend real (backend/app/main.py)
roda no mesmo processo, então as respostas são as mesmas da aplicação.

Uso:
    python tests/e2e/servidor_local.py --porta 8090
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

import uvicorn  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.routing import Mount  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

from app import main as backend  # noqa: E402


def criar_app() -> Starlette:
    return Starlette(
        routes=[
            *backend.rotas,
            Mount("/", StaticFiles(directory=RAIZ / "frontend", html=True)),
        ],
        exception_handlers={
            backend.HTTPException: backend.erro_http,
            Exception: backend.erro_inesperado,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--porta", type=int, default=8090)
    args = parser.parse_args()
    uvicorn.run(criar_app(), host="127.0.0.1", port=args.porta, log_level="warning")

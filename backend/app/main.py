"""API do software educacional de compiladores.

Nesta primeira etapa, a API expõe apenas dois endpoints:
- GET /api/health -> verifica se o serviço está no ar;
- GET /api/hello  -> devolve a mensagem exibida pelo frontend.

Os analisadores léxico e sintático serão adicionados nas próximas etapas.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Compiladores — Visualizador Educacional",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/hello")
def hello() -> dict:
    return {"message": "Hello, World!"}

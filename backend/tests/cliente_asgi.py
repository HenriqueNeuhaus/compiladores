"""Cliente HTTP mínimo para testar a aplicação ASGI em processo.

Usa apenas a biblioteca padrão (asyncio), de modo que os testes do backend
rodam sem instalar dependências extras como pytest ou httpx.
"""

import asyncio
import json as jsonlib
from dataclasses import dataclass, field


@dataclass
class Resposta:
    status: int
    cabecalhos: dict = field(default_factory=dict)
    corpo: bytes = b""
    excecao: BaseException | None = None

    def json(self):
        return jsonlib.loads(self.corpo.decode("utf-8"))

    @property
    def texto(self) -> str:
        return self.corpo.decode("utf-8", errors="replace")


async def _requisitar(app, metodo, caminho, corpo, cabecalhos):
    enviado = False
    mensagens = []

    async def receive():
        nonlocal enviado
        if not enviado:
            enviado = True
            return {"type": "http.request", "body": corpo, "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(mensagem):
        mensagens.append(mensagem)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": metodo,
        "scheme": "http",
        "path": caminho,
        "raw_path": caminho.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in cabecalhos.items()],
        "client": ("127.0.0.1", 12345),
        "server": ("teste", 80),
    }

    excecao = None
    try:
        await app(scope, receive, send)
    except Exception as exc:  # o servidor real também registra e segue
        excecao = exc

    inicio = next(m for m in mensagens if m["type"] == "http.response.start")
    corpo_resposta = b"".join(
        m.get("body", b"") for m in mensagens if m["type"] == "http.response.body"
    )
    hdrs = {k.decode().lower(): v.decode() for k, v in inicio["headers"]}
    return Resposta(inicio["status"], hdrs, corpo_resposta, excecao)


class ClienteASGI:
    def __init__(self, app):
        self.app = app

    def requisitar(self, metodo, caminho, *, json=None, dados=None, cabecalhos=None):
        cabecalhos = dict(cabecalhos or {})
        if json is not None:
            dados = jsonlib.dumps(json).encode("utf-8")
            cabecalhos.setdefault("content-type", "application/json")
        corpo = dados if isinstance(dados, bytes) else (dados or "").encode("utf-8")
        cabecalhos.setdefault("content-length", str(len(corpo)))
        return asyncio.run(_requisitar(self.app, metodo, caminho, corpo, cabecalhos))

    def get(self, caminho, **kw):
        return self.requisitar("GET", caminho, **kw)

    def post(self, caminho, **kw):
        return self.requisitar("POST", caminho, **kw)

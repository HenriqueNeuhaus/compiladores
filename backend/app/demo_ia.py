"""Demonstração e teste da integração com o Llama 3.2 de verdade.

Executado dentro do contêiner do backend (veja scripts/testar-ia.ps1):

    docker compose exec backend python -m app.demo_ia

Faz as chamadas pela própria API (http://localhost:8000), como o navegador
faria, e grava o que foi enviado e recebido em /tmp/ia-demo.json, que o
script copia para docs/validacao/. Termina com código 0 só se todas as
explicações vierem do modelo.
"""

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://localhost:8000"
CODIGO = "resultado = 10 + 5 * 2\n"
CODIGO_COM_ERRO = "x = 1\nif x > 5\n    print(x)\n"


def chamar(metodo: str, caminho: str, corpo: dict | None = None) -> tuple[int, dict]:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(API + caminho, data=dados, method=metodo,
                                    headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read())


def main() -> int:
    registro = {"data": time.strftime("%Y-%m-%d %H:%M:%S"), "casos": []}
    status_http, status = chamar("GET", "/api/ia/status")
    registro["status"] = status
    print(f"Status do assistente: {status}")
    if not status.get("disponivel"):
        print("O modelo nao esta disponivel; veja a mensagem acima.")
        json.dump(registro, open("/tmp/ia-demo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return 1

    _, analise = chamar("POST", "/api/analisar", {"codigo": CODIGO})
    ast = analise["sintatico"]["ast"]
    multiplicacao = ast["filhos"][0]["filhos"][1]["filhos"][1]
    _, analise_erro = chamar("POST", "/api/analisar", {"codigo": CODIGO_COM_ERRO})

    casos = [
        ("No MULTIPLICACAO da AST", {
            "tipo": "no", "codigo": CODIGO, "referencia": multiplicacao["id"],
            "pergunta": "Por que a multiplicacao aparece abaixo da adicao?"}),
        ("Erro sintatico (':' ausente)", {
            "tipo": "erro", "codigo": CODIGO_COM_ERRO, "referencia": 0}),
        ("Token 'resultado'", {"tipo": "token", "codigo": CODIGO, "referencia": 0}),
        ("Pergunta conceitual", {
            "tipo": "pergunta", "codigo": "",
            "pergunta": "Qual a diferenca entre arvore de derivacao e AST?"}),
    ]
    falhas = 0
    for nome, corpo in casos:
        inicio = time.time()
        codigo_http, resposta = chamar("POST", "/api/ia/explicar", corpo)
        segundos = round(time.time() - inicio, 1)
        ok = codigo_http == 200 and resposta.get("gerado_por_ia") and resposta.get("resposta")
        falhas += 0 if ok else 1
        print(f"\n=== {nome}: HTTP {codigo_http} em {segundos} s ===")
        print(resposta.get("resposta") or resposta.get("erro", {}).get("mensagem"))
        registro["casos"].append({"nome": nome, "pedido": corpo, "http": codigo_http,
                                  "segundos": segundos, "resposta": resposta})
    registro["erro_do_parser_usado"] = analise_erro["sintatico"]["erros"][0]["mensagem"]
    with open("/tmp/ia-demo.json", "w", encoding="utf-8") as arquivo:
        json.dump(registro, arquivo, ensure_ascii=False, indent=2)
    print(f"\n{len(casos) - falhas} de {len(casos)} explicacoes geradas pelo modelo.")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

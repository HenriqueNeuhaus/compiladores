"""Gera docs/casos-de-teste.md a partir de backend/tests/casos_de_teste.json.

Uso (na raiz do repositório):
    python scripts/casos_de_teste.py           # escreve o arquivo
    python scripts/casos_de_teste.py --checar  # só confere se está atualizado

O JSON é a fonte única: os mesmos casos são executados por
backend/tests/test_casos_de_teste.py.
"""

import html
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "backend" / "tests" / "casos_de_teste.json"
DESTINO = RAIZ / "docs" / "casos-de-teste.md"

ORDEM = ["válido", "erro léxico", "erro sintático", "erro semântico (previsto)", "caso de borda"]
TITULOS = {
    "válido": "Programas válidos",
    "erro léxico": "Erros léxicos",
    "erro sintático": "Erros sintáticos",
    "erro semântico (previsto)": "Erros semânticos previstos (Etapa 5, ainda não implementados)",
    "caso de borda": "Casos de borda",
}


def entrada(caso: dict) -> str:
    if "entrada" in caso:
        texto = caso["entrada"]
        if texto == "":
            return "<i>(texto vazio)</i>"
        linhas = texto.split("\n")
        if linhas[-1] == "":
            linhas.pop()
        corpo = "<br>".join(html.escape(l).replace(" ", "&nbsp;").replace("\t", "&rarr;") or "&nbsp;" for l in linhas)
        return f"<code>{corpo}</code>".replace("|", "&#124;")
    g = caso["gerador"]
    if g["tipo"] == "repetir":
        linha = html.escape(g["texto"].rstrip("\n"))
        return f"<code>{linha}</code> repetido {g['vezes']} vezes"
    return (f"<code>{html.escape(g['prefixo'])}</code> + {g['n']} × <code>{g['abre']}</code> + "
            f"<code>{g['miolo']}</code> + {g['n']} × <code>{g['fecha']}</code>")


def gerar() -> str:
    dados = json.loads(FONTE.read_text(encoding="utf-8"))
    casos = dados["casos"]
    total = len(casos)
    previstos = sum(c["status"] != "implementado" for c in casos)
    partes = [
        "# Casos de teste (Etapa 4 / Tarefa 4)",
        "",
        "> Arquivo gerado por `scripts/casos_de_teste.py` a partir de "
        "[`backend/tests/casos_de_teste.json`](../backend/tests/casos_de_teste.json). "
        "Não edite à mão: altere o JSON e gere de novo. Voltar ao [README](../README.md).",
        "",
        f"São **{total} casos**: {total - previstos} verificam comportamento já implementado e "
        f"{previstos} descrevem erros semânticos previstos para a Etapa 5. Todos são executados por "
        "`backend/tests/test_casos_de_teste.py`:",
        "",
        "```bash",
        "docker compose --profile testes run --rm testes-backend \\",
        "  python -m unittest tests.test_casos_de_teste -v",
        "```",
        "",
        "Nos casos semânticos previstos, o teste confere hoje apenas que o programa passa pelas análises "
        "léxica e sintática (condição para a análise semântica ser executada); a verificação semântica "
        "aparece como teste ignorado até a Etapa 5.",
        "",
        "Os critérios C1–C12 estão em [`materiais-e-metodos.md`](materiais-e-metodos.md#36-método-de-avaliação). "
        "Nas entradas, `→` representa uma tabulação.",
    ]
    for categoria in ORDEM:
        grupo = [c for c in casos if c["categoria"] == categoria]
        partes += ["", f"## {TITULOS[categoria]} ({len(grupo)})", "",
                   "| Identificador | Categoria | Entrada | Resultado esperado | Análise envolvida | Critérios |",
                   "| --- | --- | --- | --- | --- | --- |"]
        for c in grupo:
            resultado = html.escape(c["resultado_esperado"], quote=False).replace("|", "&#124;")
            partes.append(
                f"| {c['id']} | {c['categoria']} | {entrada(c)} | {resultado} | "
                f"{', '.join(c['analise'])} | {', '.join(c['criterios'])} |"
            )
    return "\n".join(partes) + "\n"


if __name__ == "__main__":
    texto = gerar()
    if "--checar" in sys.argv:
        atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if atual != texto:
            print("docs/casos-de-teste.md está desatualizado; rode scripts/casos_de_teste.py")
            sys.exit(1)
        print("docs/casos-de-teste.md atualizado.")
    else:
        DESTINO.write_text(texto, encoding="utf-8")
        print(f"Escrito {DESTINO.relative_to(RAIZ)}")

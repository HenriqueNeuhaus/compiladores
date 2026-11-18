"""Executa os casos de teste documentados (CT-01, CT-02, ...).

Os casos ficam em `casos_de_teste.json`, a mesma fonte que gera
`docs/casos-de-teste.md`. Cada caso informa a categoria, a entrada (ou um
gerador para entradas grandes), as análises envolvidas e o resultado esperado.

- Casos `implementado`: o resultado das análises léxica e sintática (ou da
  validação da API) deve ser exatamente o esperado.
- Casos `previsto_etapa5` (erros semânticos): hoje só se verifica que o
  programa passa pelas análises léxica e sintática, condição para que a
  análise semântica da Etapa 5 seja executada. A verificação semântica
  aparece como teste ignorado (skip) até a Etapa 5.
"""

import json
import unittest
from pathlib import Path

from app import parser
from app.main import app
from tests.cliente_asgi import ClienteASGI
from tests.test_parser import resumo

ARQUIVO = Path(__file__).with_name("casos_de_teste.json")
CASOS = json.loads(ARQUIVO.read_text(encoding="utf-8"))["casos"]


def entrada_de(caso: dict) -> str:
    if "entrada" in caso:
        return caso["entrada"]
    g = caso["gerador"]
    if g["tipo"] == "repetir":
        return g["texto"] * g["vezes"]
    if g["tipo"] == "aninhar":
        return g["prefixo"] + g["abre"] * g["n"] + g["miolo"] + g["fecha"] * g["n"] + g["sufixo"]
    raise ValueError(f"gerador desconhecido: {g['tipo']}")


class TestCasosDocumentados(unittest.TestCase):
    def test_ids_sequenciais_e_campos(self):
        for i, caso in enumerate(CASOS, start=1):
            self.assertEqual(caso["id"], f"CT-{i:02d}")
            for campo in ("categoria", "titulo", "analise", "resultado_esperado", "esperado", "criterios", "status"):
                self.assertIn(campo, caso, caso["id"])
            self.assertIn(caso["status"], ("implementado", "previsto_etapa5"))

    def test_todas_as_categorias_presentes(self):
        categorias = {c["categoria"] for c in CASOS}
        self.assertEqual(categorias, {
            "válido", "erro léxico", "erro sintático", "erro semântico (previsto)", "caso de borda",
        })

    def test_casos_lexicos_e_sintaticos(self):
        for caso in CASOS:
            if caso.get("via") == "api":
                continue
            with self.subTest(caso["id"], titulo=caso["titulo"]):
                esperado = caso["esperado"]
                lexico, sintatico = parser.analisar(entrada_de(caso))
                self.assertEqual(lexico.sucesso, esperado["lexico_sucesso"])
                if "erros_lexicos" in esperado:
                    self.assertEqual([e.codigo for e in lexico.erros], esperado["erros_lexicos"])
                if esperado.get("avisos_lexicos"):
                    self.assertTrue(lexico.avisos)
                self.assertEqual(sintatico["executado"], esperado["sintatico_executado"])
                if not esperado["sintatico_executado"]:
                    self.assertIn("motivo", sintatico)
                    continue
                self.assertEqual(sintatico["sucesso"], esperado["sintatico_sucesso"])
                if "erros_sintaticos" in esperado:
                    self.assertEqual([e["codigo"] for e in sintatico["erros"]], esperado["erros_sintaticos"])
                    self.assertIsNone(sintatico["ast"])
                    for erro in sintatico["erros"]:
                        for campo in ("linha", "coluna", "encontrado", "esperado", "regra", "mensagem"):
                            self.assertIn(campo, erro)
                if "regra" in esperado:
                    self.assertEqual(sintatico["erros"][0]["regra"], esperado["regra"])
                if "ast" in esperado:
                    self.assertEqual(resumo(sintatico["ast"]), esperado["ast"])
                if "passos_truncados" in esperado:
                    self.assertEqual(sintatico["passos_truncados"], esperado["passos_truncados"])

    def test_casos_da_api(self):
        for caso in CASOS:
            if caso.get("via") != "api":
                continue
            with self.subTest(caso["id"], titulo=caso["titulo"]):
                resposta = ClienteASGI(app).post("/api/analisar", json={"codigo": entrada_de(caso)})
                self.assertEqual(resposta.status, caso["esperado"]["http"])
                self.assertEqual(resposta.json()["erro"]["tipo"], caso["esperado"]["tipo"])

    @unittest.skip("Análise semântica e tabela de símbolos: Etapa 5 (ainda não implementadas)")
    def test_casos_semanticos(self):
        """Será preenchido na Etapa 5: verificar os erros e avisos semânticos
        descritos em `resultado_esperado` dos casos `previsto_etapa5`."""


if __name__ == "__main__":
    unittest.main()

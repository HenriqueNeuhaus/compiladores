"""Testes dos endpoints da API, executando a aplicação em processo."""

import json
import unittest
from unittest import mock

from app import main
from app.main import MENSAGEM_ERRO_INTERNO, MENSAGEM_RECEBIDO, app
from app.validacao import LIMITE_CARACTERES, MENSAGENS
from tests.cliente_asgi import ClienteASGI

cliente = ClienteASGI(app)


class TestAnalisarRequisicoesValidas(unittest.TestCase):
    def test_codigo_valido_retorna_200_e_contrato(self):
        r = cliente.post("/api/analisar", json={"codigo": "x = 10\nprint(x)"})
        self.assertEqual(r.status, 200)
        self.assertIn("application/json", r.cabecalhos["content-type"])
        self.assertEqual(
            r.json(),
            {
                "recebido": True,
                "mensagem": MENSAGEM_RECEBIDO,
                "estatisticas": {"linhas": 2, "caracteres": 15},
            },
        )

    def test_codigo_com_erro_sintatico_e_recebido(self):
        r = cliente.post("/api/analisar", json={"codigo": "if x > 5\n    print(x)"})
        self.assertEqual(r.status, 200)
        self.assertTrue(r.json()["recebido"])

    def test_caracteres_especiais_e_unicode(self):
        codigo = 'texto = "ação ✓ <b> & \\"aspas\\""  # çãõ'
        r = cliente.post("/api/analisar", json={"codigo": codigo})
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json()["estatisticas"]["caracteres"], len(codigo))

    def test_campos_extras_sao_ignorados(self):
        r = cliente.post("/api/analisar", json={"codigo": "x = 1", "extra": True})
        self.assertEqual(r.status, 200)

    def test_codigo_no_limite_exato(self):
        r = cliente.post("/api/analisar", json={"codigo": "x" * LIMITE_CARACTERES})
        self.assertEqual(r.status, 200)


class TestAnalisarErrosDeEntrada(unittest.TestCase):
    def assertErro(self, r, status, tipo):
        self.assertEqual(r.status, status)
        corpo = r.json()
        self.assertEqual(corpo["recebido"], False)
        self.assertEqual(corpo["erro"]["tipo"], tipo)
        self.assertEqual(corpo["erro"]["mensagem"], MENSAGENS[tipo])

    def test_texto_vazio_400(self):
        self.assertErro(
            cliente.post("/api/analisar", json={"codigo": ""}), 400, "entrada_vazia"
        )

    def test_apenas_espacos_400(self):
        self.assertErro(
            cliente.post("/api/analisar", json={"codigo": "   \n\t  "}),
            400,
            "entrada_em_branco",
        )

    def test_acima_do_limite_413(self):
        r = cliente.post("/api/analisar", json={"codigo": "x" * (LIMITE_CARACTERES + 1)})
        self.assertErro(r, 413, "entrada_muito_grande")

    def test_corpo_bruto_gigante_413_sem_decodificar(self):
        dados = b'{"codigo": "' + b"x" * (main.LIMITE_BYTES + 10) + b'"}'
        self.assertErro(cliente.post("/api/analisar", dados=dados), 413, "entrada_muito_grande")


class TestAnalisarRequisicoesInvalidas(unittest.TestCase):
    def assertErro(self, r, status, tipo):
        self.assertEqual(r.status, status)
        self.assertEqual(r.json()["erro"]["tipo"], tipo)
        self.assertFalse(r.json()["recebido"])

    def test_json_malformado_400(self):
        r = cliente.post(
            "/api/analisar", dados='{"codigo": "x = 1"', cabecalhos={"content-type": "application/json"}
        )
        self.assertErro(r, 400, "json_invalido")

    def test_corpo_vazio_400(self):
        self.assertErro(cliente.post("/api/analisar", dados=b""), 400, "json_invalido")

    def test_bytes_que_nao_sao_utf8_400(self):
        self.assertErro(cliente.post("/api/analisar", dados=b"\xff\xfe\x00"), 400, "json_invalido")

    def test_campo_ausente_422(self):
        self.assertErro(cliente.post("/api/analisar", json={"code": "x"}), 422, "campo_ausente")

    def test_codigo_nao_texto_422(self):
        self.assertErro(cliente.post("/api/analisar", json={"codigo": 123}), 422, "tipo_invalido")

    def test_codigo_nulo_422(self):
        self.assertErro(cliente.post("/api/analisar", json={"codigo": None}), 422, "tipo_invalido")

    def test_corpo_lista_422(self):
        self.assertErro(cliente.post("/api/analisar", json=["x = 1"]), 422, "corpo_nao_objeto")

    def test_metodo_get_405_em_json(self):
        r = cliente.get("/api/analisar")
        self.assertErro(r, 405, "metodo_nao_permitido")

    def test_rota_inexistente_404_em_json(self):
        self.assertErro(cliente.get("/api/nao-existe"), 404, "rota_inexistente")


class TestErroInesperado(unittest.TestCase):
    def test_erro_interno_500_generico_sem_detalhes(self):
        segredo = "/srv/caminho/interno SENHA=123"
        with mock.patch.object(main, "estatisticas", side_effect=RuntimeError(segredo)), \
                self.assertLogs("compiladores", level="ERROR"):
            r = cliente.post("/api/analisar", json={"codigo": "x = 1"})
        self.assertEqual(r.status, 500)
        self.assertEqual(
            r.json(),
            {"recebido": False, "erro": {"tipo": "erro_interno", "mensagem": MENSAGEM_ERRO_INTERNO}},
        )
        self.assertNotIn("Traceback", r.texto)
        self.assertNotIn(segredo, r.texto)
        self.assertNotIn("RuntimeError", r.texto)


class TestRegressaoEtapa1(unittest.TestCase):
    """Endpoints da Etapa 1 continuam funcionando."""

    def test_health(self):
        r = cliente.get("/api/health")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_hello(self):
        r = cliente.get("/api/hello")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json(), {"message": "Hello, World!"})


if __name__ == "__main__":
    unittest.main()

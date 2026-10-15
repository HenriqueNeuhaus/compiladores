"""Testes de interface e de ponta a ponta (Playwright + unittest).

Abrem a aplicação em um navegador real (Chromium) e simulam o uso pelo
estudante. A URL vem da variável BASE_URL:
- sem Docker:  python tests/e2e/servidor_local.py e BASE_URL=http://localhost:8090
- no Docker:   o serviço de testes usa BASE_URL=http://frontend (Nginx + backend)

Falhas de comunicação e erros do servidor são simulados interceptando a
requisição no navegador (page.route), sem alterar o backend.
"""

import json
import os
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8090").rstrip("/")

# Lê os exemplos diretamente do módulo do frontend, para não duplicar dados.
RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_EXEMPLOS = RAIZ / "frontend" / "js" / "exemplos.js"

MSG_VAZIA = "Informe um código-fonte antes de solicitar a análise."
MSG_BRANCO = (
    "O código informado contém apenas espaços ou quebras de linha. "
    "Escreva um programa ou escolha um exemplo."
)
MSG_COMUNICACAO = (
    "Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente."
)
MSG_INESPERADO = "Ocorreu um erro inesperado ao processar a solicitação. Tente novamente."


def setUpModule():
    global _pw, _navegador
    _pw = sync_playwright().start()
    _navegador = _pw.chromium.launch()


def tearDownModule():
    _navegador.close()
    _pw.stop()


class BaseInterface(unittest.TestCase):
    def setUp(self):
        self.contexto = _navegador.new_context(viewport={"width": 1280, "height": 900})
        self.pagina = self.contexto.new_page()
        self.erros_js = []
        self.pagina.on("pageerror", lambda e: self.erros_js.append(str(e)))
        self.requisicoes = []
        self.pagina.on(
            "request",
            lambda r: self.requisicoes.append(r) if r.url.endswith("/api/analisar") else None,
        )
        self.pagina.goto(BASE_URL + "/")
        self.codigo = self.pagina.locator("#codigo")
        self.botao = self.pagina.locator("#analisar")
        self.resultado = self.pagina.locator("#resultado")
        self.mensagem = self.pagina.locator("#mensagem")

    def tearDown(self):
        self.contexto.close()
        self.assertEqual(self.erros_js, [], "a página gerou erros de JavaScript")

    def preencher(self, texto):
        self.codigo.fill(texto)

    def analisar_e_esperar(self, estado):
        self.botao.click()
        expect(self.resultado).to_have_attribute("data-estado", estado)


class TestTelaPrincipal(BaseInterface):
    def test_identificacao_do_sistema_e_da_linguagem(self):
        expect(self.pagina).to_have_title("Visualizador de Compiladores — Python")
        expect(self.pagina.locator("h1")).to_have_text("Visualizador de Compiladores")
        expect(self.pagina.locator("#linguagem")).to_contain_text("Python")

    def test_elementos_obrigatorios_visiveis(self):
        for seletor in ("#codigo", "#analisar", "#resultado", "#exemplo", "#limpar"):
            expect(self.pagina.locator(seletor)).to_be_visible()
        expect(self.botao).to_have_text("Analisar código")
        expect(self.codigo).to_have_attribute("aria-label", "Código-fonte em Python")

    def test_area_de_codigo_monoespacada(self):
        fonte = self.codigo.evaluate("e => getComputedStyle(e).fontFamily")
        self.assertRegex(fonte.lower(), "mono|consolas|courier")

    def test_estado_inicial_do_resultado(self):
        expect(self.resultado).to_have_attribute("data-estado", "vazio")
        expect(self.resultado).to_contain_text("Escreva um programa ou escolha um exemplo")

    def test_fases_futuras_indicadas_como_em_breve(self):
        expect(self.pagina.locator(".fase.atual")).to_contain_text("Código-fonte")
        expect(self.pagina.locator(".fase").nth(1)).to_contain_text("em breve")

    def test_sem_rolagem_horizontal_em_tela_de_celular(self):
        self.pagina.set_viewport_size({"width": 360, "height": 780})
        largura = self.pagina.evaluate("document.documentElement.scrollWidth")
        self.assertLessEqual(largura, 360)


class TestEdicaoDoCodigo(BaseInterface):
    def test_digitar_editar_e_preservar_o_conteudo(self):
        self.codigo.click()
        self.pagina.keyboard.type("x = 1\nprint(x)")
        self.pagina.keyboard.press("Backspace")
        self.pagina.keyboard.type(")")
        expect(self.codigo).to_have_value("x = 1\nprint(x)")
        self.pagina.locator("h1").click()  # perder o foco não apaga o texto
        expect(self.codigo).to_have_value("x = 1\nprint(x)")

    def test_tab_insere_quatro_espacos(self):
        self.codigo.click()
        self.pagina.keyboard.type("if x:\n")
        self.pagina.keyboard.press("Tab")
        self.pagina.keyboard.type("y = 1")
        expect(self.codigo).to_have_value("if x:\n    y = 1")

    def test_contador_de_linhas_e_caracteres(self):
        self.preencher("a = 1\nb = 2")
        expect(self.pagina.locator("#contador")).to_have_text("2 linhas, 11 caracteres")
        expect(self.pagina.locator("#numeros-linha")).to_have_text("1\n2")

    def test_limpar_esvazia_o_editor_e_o_resultado(self):
        self.preencher("x = 1")
        self.analisar_e_esperar("sucesso")
        self.pagina.locator("#limpar").click()
        expect(self.codigo).to_have_value("")
        expect(self.codigo).to_be_focused()
        expect(self.resultado).to_have_attribute("data-estado", "vazio")


class TestExemplos(BaseInterface):
    def exemplos(self):
        """Lê id e código de cada exemplo a partir do próprio módulo JS."""
        return self.pagina.evaluate(
            "async () => (await import('/js/exemplos.js')).EXEMPLOS"
            ".map(e => ({id: e.id, titulo: e.titulo, codigo: e.codigo}))"
        )

    def test_ha_pelo_menos_tres_exemplos_no_seletor(self):
        opcoes = self.pagina.locator("#exemplo option:not([value=''])")
        self.assertGreaterEqual(opcoes.count(), 3)

    def test_cada_exemplo_carrega_o_codigo_correspondente(self):
        for exemplo in self.exemplos():
            with self.subTest(exemplo=exemplo["id"]):
                self.pagina.select_option("#exemplo", exemplo["id"])
                expect(self.codigo).to_have_value(exemplo["codigo"])
                expect(self.pagina.locator("#descricao-exemplo")).to_contain_text("Demonstra:")

    def test_novo_exemplo_substitui_o_conteudo_anterior(self):
        self.preencher("texto digitado antes")
        a, b = self.exemplos()[0], self.exemplos()[1]
        self.pagina.select_option("#exemplo", a["id"])
        self.pagina.select_option("#exemplo", b["id"])
        expect(self.codigo).to_have_value(b["codigo"])

    def test_exemplo_pode_ser_editado_e_o_texto_editado_e_enviado(self):
        exemplo = self.exemplos()[0]
        self.pagina.select_option("#exemplo", exemplo["id"])
        self.codigo.press("End")
        self.codigo.press("Control+End")
        self.pagina.keyboard.type("total = 1\n")
        with self.pagina.expect_request("**/api/analisar") as info:
            self.botao.click()
        enviado = json.loads(info.value.post_data)["codigo"]
        self.assertEqual(enviado, exemplo["codigo"] + "total = 1\n")
        expect(self.resultado).to_have_attribute("data-estado", "sucesso")

    def test_cada_exemplo_e_aceito_pelo_backend(self):
        for exemplo in self.exemplos():
            with self.subTest(exemplo=exemplo["id"]):
                self.pagina.select_option("#exemplo", exemplo["id"])
                self.analisar_e_esperar("sucesso")


class TestEnvioEComunicacao(BaseInterface):
    def test_envio_valido_mostra_a_resposta_do_backend(self):
        self.preencher("x = 10\nprint(x)")
        with self.pagina.expect_response("**/api/analisar") as info:
            self.botao.click()
        self.assertEqual(info.value.status, 200)
        expect(self.resultado).to_have_attribute("data-estado", "sucesso")
        expect(self.mensagem).to_contain_text("Código recebido com sucesso")
        expect(self.resultado).to_contain_text("Linhas recebidas")
        expect(self.resultado.locator("dd").first).to_have_text("2")
        expect(self.codigo).to_have_value("x = 10\nprint(x)")  # código preservado

    def test_requisicao_segue_o_contrato_json(self):
        self.preencher("x = 1")
        with self.pagina.expect_request("**/api/analisar") as info:
            self.botao.click()
        req = info.value
        self.assertEqual(req.method, "POST")
        self.assertIn("application/json", req.headers["content-type"])
        self.assertEqual(json.loads(req.post_data), {"codigo": "x = 1"})

    def test_caracteres_especiais_chegam_intactos_e_nao_viram_html(self):
        codigo = 'msg = "<b>ação</b> & ✓"\n# <script>alert(1)</script>'
        self.preencher(codigo)
        with self.pagina.expect_request("**/api/analisar") as info:
            self.botao.click()
        self.assertEqual(json.loads(info.value.post_data)["codigo"], codigo)
        expect(self.resultado).to_have_attribute("data-estado", "sucesso")
        self.assertEqual(self.pagina.locator("#resultado b, #resultado script").count(), 0)

    def test_codigo_com_erro_sintatico_e_aceito_nesta_etapa(self):
        self.preencher('if x > 5\n    print("x")')
        self.analisar_e_esperar("sucesso")

    def test_botao_fica_desabilitado_durante_o_envio(self):
        def atrasar(rota):
            self.pagina.wait_for_timeout(600)
            rota.continue_()

        self.pagina.route("**/api/analisar", atrasar)
        self.preencher("x = 1")
        self.botao.click()
        expect(self.botao).to_be_disabled()
        expect(self.botao).to_have_text("Enviando…")
        expect(self.resultado).to_have_attribute("data-estado", "sucesso")
        expect(self.botao).to_be_enabled()
        expect(self.botao).to_have_text("Analisar código")


class TestValidacoesEMensagens(BaseInterface):
    def test_entrada_vazia_mostra_mensagem_e_nao_envia(self):
        self.analisar_e_esperar("entrada")
        expect(self.mensagem).to_have_text(MSG_VAZIA)
        self.assertEqual(self.requisicoes, [])

    def test_apenas_espacos_mostra_orientacao_e_nao_envia(self):
        self.preencher("   \n\t  \n")
        self.analisar_e_esperar("entrada")
        expect(self.mensagem).to_have_text(MSG_BRANCO)
        self.assertEqual(self.requisicoes, [])

    def test_falha_de_rede_mostra_mensagem_de_comunicacao(self):
        self.pagina.route("**/api/analisar", lambda rota: rota.abort("connectionrefused"))
        self.preencher("x = 1")
        self.analisar_e_esperar("comunicacao")
        expect(self.mensagem).to_have_text(MSG_COMUNICACAO)
        expect(self.botao).to_be_enabled()  # interface não fica travada
        expect(self.codigo).to_have_value("x = 1")

    def test_servidor_indisponivel_502_mostra_mensagem_de_comunicacao(self):
        self.pagina.route(
            "**/api/analisar",
            lambda rota: rota.fulfill(status=502, content_type="text/html", body="<h1>502 Bad Gateway</h1>"),
        )
        self.preencher("x = 1")
        self.analisar_e_esperar("comunicacao")
        expect(self.mensagem).to_have_text(MSG_COMUNICACAO)

    def test_erro_500_mostra_mensagem_generica_sem_detalhes(self):
        corpo = {"recebido": False, "erro": {"tipo": "erro_interno", "mensagem": "Traceback /srv/segredo"}}
        self.pagina.route(
            "**/api/analisar",
            lambda rota: rota.fulfill(status=500, content_type="application/json", body=json.dumps(corpo)),
        )
        self.preencher("x = 1")
        self.analisar_e_esperar("inesperado")
        expect(self.mensagem).to_have_text(MSG_INESPERADO)
        expect(self.resultado).not_to_contain_text("segredo")

    def test_erro_de_entrada_do_backend_mostra_a_mensagem_do_servidor(self):
        # Garante que a validação do backend é exibida mesmo se a do navegador deixar passar.
        corpo = {"recebido": False, "erro": {"tipo": "campo_ausente", "mensagem": "Mensagem vinda do backend."}}
        self.pagina.route(
            "**/api/analisar",
            lambda rota: rota.fulfill(status=422, content_type="application/json", body=json.dumps(corpo)),
        )
        self.preencher("x = 1")
        self.analisar_e_esperar("entrada")
        expect(self.mensagem).to_have_text("Mensagem vinda do backend.")

    def test_depois_de_um_erro_um_novo_envio_funciona(self):
        self.analisar_e_esperar("entrada")
        self.preencher("x = 1")
        self.analisar_e_esperar("sucesso")


class TestApiPeloMesmoEndereco(unittest.TestCase):
    """A API responde pelo mesmo endereço da interface (proxy do frontend)."""

    def setUp(self):
        self.req = _pw.request.new_context(base_url=BASE_URL)

    def tearDown(self):
        self.req.dispose()

    def test_health(self):
        r = self.req.get("/api/health")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_hello_da_etapa_1(self):
        r = self.req.get("/api/hello")
        self.assertEqual(r.json(), {"message": "Hello, World!"})

    def test_backend_valida_mesmo_sem_o_navegador(self):
        r = self.req.post("/api/analisar", data=json.dumps({"codigo": "  "}),
                          headers={"content-type": "application/json"})
        self.assertEqual(r.status, 400)
        self.assertEqual(r.json()["erro"]["tipo"], "entrada_em_branco")

    def test_json_invalido(self):
        r = self.req.post("/api/analisar", data="isto não é json",
                          headers={"content-type": "application/json"})
        self.assertEqual(r.status, 400)
        self.assertEqual(r.json()["erro"]["tipo"], "json_invalido")


if __name__ == "__main__":
    print(f"Testando {BASE_URL}", file=sys.stderr)
    unittest.main(verbosity=2)

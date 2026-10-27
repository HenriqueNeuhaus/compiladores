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
        # Etapa 3: o estado vazio virou um pequeno tutorial "Como usar".
        expect(self.resultado).to_contain_text("Como usar")
        expect(self.resultado.locator(".como-usar li")).to_have_count(4)
        expect(self.pagina.locator("#analise-lexica")).to_be_hidden()

    def test_fase_de_tokens_disponivel_e_arvore_em_breve(self):
        # Etapa 3: a fase atual passou de "Código-fonte" para "Tokens".
        expect(self.pagina.locator(".fase.atual")).to_contain_text("Tokens")
        expect(self.pagina.locator(".fase.atual")).to_contain_text("disponível")
        expect(self.pagina.locator(".fase").nth(2)).to_contain_text("em breve")

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
        self.analisar_e_esperar("lexico_ok")
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
        expect(self.resultado).to_have_attribute("data-estado", "lexico_ok")

    def test_cada_exemplo_tem_o_resultado_lexico_esperado(self):
        # Só o exemplo "erros-lexicos" deve ter erros léxicos; o de erro
        # sintático é formado apenas por tokens válidos.
        for exemplo in self.exemplos():
            with self.subTest(exemplo=exemplo["id"]):
                self.pagina.select_option("#exemplo", exemplo["id"])
                esperado = "lexico_erros" if exemplo["id"] == "erros-lexicos" else "lexico_ok"
                self.analisar_e_esperar(esperado)


class TestEnvioEComunicacao(BaseInterface):
    def test_envio_valido_mostra_a_resposta_do_backend(self):
        self.preencher("x = 10\nprint(x)")
        with self.pagina.expect_response("**/api/analisar") as info:
            self.botao.click()
        self.assertEqual(info.value.status, 200)
        expect(self.resultado).to_have_attribute("data-estado", "lexico_ok")
        # Etapa 3: a mensagem e os detalhes passaram a ser os da análise léxica.
        expect(self.mensagem).to_have_text("Análise léxica concluída sem erros: 10 tokens reconhecidos.")
        expect(self.pagina.locator("#total-tokens")).to_have_text("10")
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
        expect(self.resultado).to_have_attribute("data-estado", "lexico_ok")
        self.assertEqual(self.pagina.locator("#resultado b, #resultado script").count(), 0)

    def test_codigo_com_erro_sintatico_nao_tem_erro_lexico(self):
        self.preencher('if x > 5\n    print("x")')
        self.analisar_e_esperar("lexico_ok")

    def test_botao_fica_desabilitado_durante_o_envio(self):
        def atrasar(rota):
            self.pagina.wait_for_timeout(600)
            rota.continue_()

        self.pagina.route("**/api/analisar", atrasar)
        self.preencher("x = 1")
        self.botao.click()
        expect(self.botao).to_be_disabled()
        expect(self.botao).to_have_text("Analisando…")
        expect(self.resultado).to_have_attribute("data-estado", "lexico_ok")
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
        self.analisar_e_esperar("lexico_ok")


PROGRAMA_BLOCO = "x = 1\nif x >= 1:\n    print(x)\n"


class TestTabelaDeTokens(BaseInterface):
    def test_tabela_tem_colunas_e_uma_linha_por_token(self):
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("lexico_ok")
        cabecalho = self.pagina.locator("#tabela-tokens th")
        expect(cabecalho).to_have_text(["#", "Tipo", "Lexema", "Linha", "Coluna"])
        linhas = self.pagina.locator("#tabela-tokens tbody tr")
        # x = 1 ↵ if x >= 1 : ↵ INDENT print ( x ) ↵ DEDENT FIM
        expect(linhas).to_have_count(18)
        expect(linhas.nth(4).locator("td")).to_have_text(["5", "PALAVRA_RESERVADA", "if", "2", "1"])
        expect(linhas.nth(10).locator("td")).to_have_text(["11", "INDENT", "4 espaços", "3", "1"])
        expect(linhas.nth(17).locator("td")).to_have_text(["18", "FIM_DE_ARQUIVO", "(fim)", "4", "1"])

    def test_contagem_por_categoria(self):
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("lexico_ok")
        chip = self.pagina.locator('#contagem [data-tipo="IDENTIFICADOR"]')
        expect(chip).to_contain_text("Identificador")
        expect(chip.locator(".chip-qtd")).to_have_text("4")

    def test_lexema_com_html_e_exibido_como_texto(self):
        self.preencher('s = "<img src=x onerror=alert(1)>"')
        self.analisar_e_esperar("lexico_ok")
        expect(self.pagina.locator("#tabela-tokens tbody")).to_contain_text("<img src=x onerror=alert(1)>")
        self.assertEqual(self.pagina.locator("#analise-lexica img").count(), 0)


class TestCodigoDestacado(BaseInterface):
    def test_cada_categoria_recebe_sua_cor(self):
        self.preencher('if nota >= 7:\n    print("ok")  # fim\n')
        self.analisar_e_esperar("lexico_ok")
        area = self.pagina.locator("#codigo-destacado")
        for texto, classe in [("if", "cat-palavra"), ("nota", "cat-identificador"), (">=", "cat-operador"),
                              ("7", "cat-numero"), ('"ok"', "cat-string"), ("# fim", "cat-comentario")]:
            with self.subTest(texto=texto):
                expect(area.locator(f".{classe}", has_text=texto).first).to_be_visible()
        expect(area.locator(".marcador-nova-linha")).to_have_count(2)
        expect(area.locator(".marcador-dedent")).to_have_count(1)
        cores = {area.locator(f".{c}").first.evaluate("e => getComputedStyle(e).backgroundColor")
                 for c in ("cat-palavra", "cat-identificador", "cat-numero", "cat-string")}
        self.assertEqual(len(cores), 4, "categorias diferentes devem ter cores diferentes")

    def test_texto_do_codigo_destacado_e_igual_ao_do_editor(self):
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("lexico_ok")
        linhas = self.pagina.locator("#codigo-destacado .linha-codigo:not(.linha-fim) .conteudo")
        textos = linhas.evaluate_all(
            "ls => ls.map(l => [...l.children].filter(s => !s.classList.contains('marcador'))"
            ".map(s => s.textContent).join(''))")
        self.assertEqual(textos, PROGRAMA_BLOCO.split("\n"))


class TestErrosLexicosNaInterface(BaseInterface):
    def test_varios_erros_sao_listados_com_linha_e_coluna(self):
        self.preencher('a = 1 $ 2\nb = "aberta\nc = a // 2\n')
        self.analisar_e_esperar("lexico_erros")
        expect(self.pagina.locator("#resultado-titulo")).to_have_text("Erros léxicos encontrados")
        expect(self.mensagem).to_contain_text("3 erros léxicos encontrados")
        itens = self.pagina.locator("#lista-erros li p")
        expect(itens).to_have_count(3)
        expect(itens.nth(0)).to_have_text(
            "Erro léxico na linha 1, coluna 7: caractere não reconhecido '$'. "
            "Verifique se ele faz parte do subconjunto suportado.")
        expect(itens.nth(1)).to_contain_text("linha 2, coluna 5")
        expect(itens.nth(2)).to_contain_text("'//'")
        # Os trechos válidos continuam na tabela (o scanner não para no primeiro erro).
        expect(self.pagina.locator("#tabela-tokens tbody")).to_contain_text("IDENTIFICADOR")
        expect(self.pagina.locator("#codigo-destacado .cat-erro")).to_have_count(3)
        self.assertNotIn("Traceback", self.resultado.inner_text())

    def test_mostrar_no_codigo_seleciona_o_trecho_no_editor(self):
        self.preencher("x = 1\ny = 2 $ 3\n")
        self.analisar_e_esperar("lexico_erros")
        self.pagina.locator("#lista-erros button").click()
        expect(self.codigo).to_be_focused()
        selecao = self.codigo.evaluate("e => e.value.slice(e.selectionStart, e.selectionEnd)")
        self.assertEqual(selecao, "$")
        expect(self.pagina.locator("#passo-descricao")).to_contain_text("'$'")

    def test_palavra_fora_do_subconjunto_gera_aviso(self):
        self.preencher("for x:\n    y = 1\n")
        self.analisar_e_esperar("lexico_ok")
        expect(self.pagina.locator("#lista-avisos li")).to_have_count(1)
        expect(self.pagina.locator("#lista-avisos")).to_contain_text("for")


class TestPassoAPasso(BaseInterface):
    def setUp(self):
        super().setUp()
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("lexico_ok")
        self.contador = self.pagina.locator("#passo-contador")
        self.descricao = self.pagina.locator("#passo-descricao")

    def test_comeca_no_ultimo_passo_e_navega_pelos_botoes(self):
        total = self.pagina.locator("#passo-barra").get_attribute("max")
        expect(self.contador).to_have_text(f"Passo {int(total) + 1} de {int(total) + 1}")
        expect(self.pagina.locator("#passo-proximo")).to_be_disabled()
        self.pagina.locator("#passo-inicio").click()
        expect(self.contador).to_contain_text("Passo 1 de")
        expect(self.descricao).to_contain_text("'x'")
        expect(self.descricao).to_contain_text("IDENTIFICADOR")
        expect(self.pagina.locator("#passo-anterior")).to_be_disabled()
        self.pagina.locator("#passo-proximo").click()
        expect(self.contador).to_contain_text("Passo 2 de")
        expect(self.descricao).to_contain_text("'='")

    def test_tokens_futuros_ficam_esmaecidos_e_o_atual_destacado(self):
        self.pagina.locator("#passo-inicio").click()
        atual = self.pagina.locator("#codigo-destacado .seg.atual")
        expect(atual).to_have_count(1)
        expect(atual).to_have_text("x")
        self.assertGreater(self.pagina.locator("#codigo-destacado .seg.futuro").count(), 10)
        expect(self.pagina.locator("#tabela-tokens tr.atual td").nth(2)).to_have_text("x")

    def test_pilha_de_indentacao_acompanha_os_blocos(self):
        self.pagina.locator('#tabela-tokens tbody tr:nth-child(11) button').click()  # INDENT
        expect(self.pagina.locator("#pilha li")).to_have_text(["0", "4"])
        expect(self.descricao).to_contain_text("INDENT")
        self.pagina.locator("#passo-fim").click()
        expect(self.pagina.locator("#pilha li")).to_have_text(["0"])

    def test_clicar_em_um_token_do_codigo_vai_ao_passo(self):
        self.pagina.locator("#codigo-destacado .cat-palavra", has_text="if").click()
        expect(self.descricao).to_contain_text("'if'")
        expect(self.descricao).to_contain_text("PALAVRA_RESERVADA")

    def test_teclado_e_reproducao_automatica(self):
        self.pagina.locator("#passo-inicio").click()
        self.pagina.locator("#passo-reproduzir").focus()
        self.pagina.keyboard.press("ArrowRight")
        expect(self.contador).to_contain_text("Passo 2 de")
        self.pagina.locator("#passo-reproduzir").click()
        expect(self.pagina.locator("#passo-reproduzir")).to_have_attribute("aria-pressed", "true")
        expect(self.contador).to_contain_text("Passo 4 de", timeout=5000)
        self.pagina.locator("#passo-reproduzir").click()
        expect(self.pagina.locator("#passo-reproduzir")).to_have_text("Reproduzir")

    def test_editar_o_codigo_avisa_que_a_analise_esta_desatualizada(self):
        expect(self.pagina.locator("#aviso-desatualizado")).to_be_hidden()
        self.codigo.press("End")
        self.pagina.keyboard.type(" ")
        expect(self.pagina.locator("#aviso-desatualizado")).to_be_visible()
        self.analisar_e_esperar("lexico_ok")
        expect(self.pagina.locator("#aviso-desatualizado")).to_be_hidden()

    def test_limpar_esconde_a_analise(self):
        self.pagina.locator("#limpar").click()
        expect(self.pagina.locator("#analise-lexica")).to_be_hidden()


class TestCelular(BaseInterface):
    def test_analise_completa_sem_rolagem_horizontal_e_com_toque(self):
        contexto = _navegador.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        pagina = contexto.new_page()
        try:
            pagina.goto(BASE_URL + "/")
            pagina.select_option("#exemplo", "erros-lexicos")
            pagina.locator("#analisar").tap()
            expect(pagina.locator("#resultado")).to_have_attribute("data-estado", "lexico_erros")
            self.assertLessEqual(pagina.evaluate("document.documentElement.scrollWidth"), 390)
            pagina.locator("#passo-inicio").tap()
            expect(pagina.locator("#passo-contador")).to_contain_text("Passo 1 de")
            for seletor in ("#passo-inicio", "#passo-anterior", "#passo-proximo", "#passo-fim"):
                caixa = pagina.locator(seletor).bounding_box()
                self.assertGreaterEqual(caixa["height"], 40, f"{seletor} pequeno demais para toque")
        finally:
            contexto.close()


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

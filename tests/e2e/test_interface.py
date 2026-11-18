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
import re
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
        # Etapa 4: a fase atual passou de "Tokens" para "Árvore sintática".
        expect(self.pagina.locator(".fase.atual")).to_contain_text("Árvore sintática")
        expect(self.pagina.locator(".fase.atual")).to_contain_text("disponível")
        expect(self.pagina.locator(".fase").nth(1)).to_contain_text("disponível")
        expect(self.pagina.locator(".fase").nth(3)).to_contain_text("em breve")

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
        self.analisar_e_esperar("analise_ok")
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
        expect(self.resultado).to_have_attribute("data-estado", "analise_ok")

    def test_cada_exemplo_tem_o_resultado_lexico_esperado(self):
        # Só o exemplo "erros-lexicos" tem erros léxicos; o de erro sintático
        # tem só tokens válidos e agora é recusado pelo parser (Etapa 4).
        resultado_esperado = {"erros-lexicos": "lexico_erros", "erro-sintatico": "sintatico_erros"}
        for exemplo in self.exemplos():
            with self.subTest(exemplo=exemplo["id"]):
                self.pagina.select_option("#exemplo", exemplo["id"])
                esperado = resultado_esperado.get(exemplo["id"], "analise_ok")
                self.analisar_e_esperar(esperado)


class TestEnvioEComunicacao(BaseInterface):
    def test_envio_valido_mostra_a_resposta_do_backend(self):
        self.preencher("x = 10\nprint(x)")
        with self.pagina.expect_response("**/api/analisar") as info:
            self.botao.click()
        self.assertEqual(info.value.status, 200)
        expect(self.resultado).to_have_attribute("data-estado", "analise_ok")
        # Etapa 4: a mensagem resume as análises léxica e sintática.
        expect(self.mensagem).to_have_text(
            "Análises léxica e sintática concluídas sem erros: 10 tokens reconhecidos e AST com 6 nós.")
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
        expect(self.resultado).to_have_attribute("data-estado", "analise_ok")
        self.assertEqual(self.pagina.locator("#resultado b, #resultado script").count(), 0)

    def test_codigo_com_erro_sintatico_nao_tem_erro_lexico(self):
        # Etapa 4: o código continua sem erro léxico, mas o parser o recusa.
        self.preencher('if x > 5\n    print("x")')
        self.analisar_e_esperar("sintatico_erros")
        expect(self.pagina.locator("#lista-erros")).to_have_count(0)
        expect(self.pagina.locator("#lista-erros-sintaticos li")).to_have_count(1)

    def test_botao_fica_desabilitado_durante_o_envio(self):
        def atrasar(rota):
            self.pagina.wait_for_timeout(600)
            rota.continue_()

        self.pagina.route("**/api/analisar", atrasar)
        self.preencher("x = 1")
        self.botao.click()
        expect(self.botao).to_be_disabled()
        expect(self.botao).to_have_text("Analisando…")
        expect(self.resultado).to_have_attribute("data-estado", "analise_ok")
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
        self.analisar_e_esperar("analise_ok")


PROGRAMA_BLOCO = "x = 1\nif x >= 1:\n    print(x)\n"


class TestTabelaDeTokens(BaseInterface):
    def test_tabela_tem_colunas_e_uma_linha_por_token(self):
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("analise_ok")
        cabecalho = self.pagina.locator("#tabela-tokens th")
        expect(cabecalho).to_have_text(["#", "Tipo", "Lexema", "Linha", "Coluna"])
        linhas = self.pagina.locator("#tabela-tokens tbody tr")
        # x = 1 ↵ if x >= 1 : ↵ INDENT print ( x ) ↵ DEDENT FIM
        expect(linhas).to_have_count(18)
        expect(linhas.nth(4).locator("td")).to_have_text(["5", "PALAVRA_RESERVADA", "if", "2", "1"])
        expect(linhas.nth(10).locator("td")).to_have_text(["11", "INDENT", "4 espaços", "3", "1"])
        expect(linhas.nth(17).locator("td")).to_have_text(["18", "FIM_DE_ARQUIVO", "(fim)", "4", "1"])
        # Regressão: o rótulo INDENT herdava a cor transparente do destaque do código.
        cor = linhas.nth(10).locator(".tipo").evaluate("e => getComputedStyle(e).color")
        self.assertNotEqual(cor, "rgba(0, 0, 0, 0)")

    def test_contagem_por_categoria(self):
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("analise_ok")
        chip = self.pagina.locator('#contagem [data-tipo="IDENTIFICADOR"]')
        expect(chip).to_contain_text("Identificador")
        expect(chip.locator(".chip-qtd")).to_have_text("4")

    def test_lexema_com_html_e_exibido_como_texto(self):
        self.preencher('s = "<img src=x onerror=alert(1)>"')
        self.analisar_e_esperar("analise_ok")
        expect(self.pagina.locator("#tabela-tokens tbody")).to_contain_text("<img src=x onerror=alert(1)>")
        self.assertEqual(self.pagina.locator("#analise-lexica img").count(), 0)


class TestCodigoDestacado(BaseInterface):
    def test_cada_categoria_recebe_sua_cor(self):
        self.preencher('if nota >= 7:\n    print("ok")  # fim\n')
        self.analisar_e_esperar("analise_ok")
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

    def test_operadores_compostos_sem_ligaduras(self):
        # Regressão (validação no Docker): com a fonte JetBrains Mono carregada,
        # ">=" aparecia como um único símbolo "≥" no editor, no código e na tabela.
        self.preencher("x = a >= 1\ny = b != 2\n")
        self.analisar_e_esperar("analise_ok")
        for seletor in ("#codigo", "#codigo-destacado .cat-operador", "#tabela-tokens .lexema code",
                        "#explicacao code"):
            with self.subTest(seletor=seletor):
                estilo = self.pagina.locator(seletor).first.evaluate(
                    "e => [getComputedStyle(e).fontVariantLigatures, getComputedStyle(e).fontFeatureSettings]")
                self.assertEqual(estilo[0], "none")
                self.assertIn('"calt" 0', estilo[1])

    def test_texto_do_codigo_destacado_e_igual_ao_do_editor(self):
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("analise_ok")
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
        # Etapa 4: o aviso léxico continua e o parser recusa o 'for'.
        self.analisar_e_esperar("sintatico_erros")
        expect(self.pagina.locator("#lista-avisos li")).to_have_count(1)
        expect(self.pagina.locator("#lista-avisos")).to_contain_text("for")


class TestPassoAPasso(BaseInterface):
    def setUp(self):
        super().setUp()
        self.preencher(PROGRAMA_BLOCO)
        self.analisar_e_esperar("analise_ok")
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
        self.analisar_e_esperar("analise_ok")
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


# ---------------------------------------------------------------------------
# Etapa 4: análise sintática e AST
# ---------------------------------------------------------------------------

PROGRAMA_PRECEDENCIA = "resultado = 10 + 5 * 2\n"


class TestArvoreSintatica(BaseInterface):
    def setUp(self):
        super().setUp()
        self.arvore = self.pagina.locator("#arvore")

    def no(self, tipo):
        return self.arvore.locator(f'[role="treeitem"][data-tipo="{tipo}"]')

    def test_arvore_exibida_para_codigo_valido_com_precedencia(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        expect(self.pagina.locator("#analise-sintatica")).to_be_visible()
        expect(self.arvore.locator('[role="treeitem"]')).to_have_count(8)
        # A multiplicação fica dentro (abaixo) da adição: é calculada primeiro.
        adicao = self.no("ADICAO")
        expect(adicao.locator('[data-tipo="MULTIPLICACAO"]')).to_have_count(1)
        expect(adicao.locator(":scope > .no-linha")).to_contain_text("valor")
        texto = self.pagina.locator("#arvore-texto")
        self.assertIn("└── ADICAO: + (valor)", texto.text_content())
        self.assertIn("    └── MULTIPLICACAO: * (direita)", texto.text_content())

    def test_parenteses_e_associatividade_mudam_a_arvore(self):
        self.preencher("a = (10 + 5) * 2\nb = 20 - 5 - 3\n")
        self.analisar_e_esperar("analise_ok")
        expect(self.no("MULTIPLICACAO").locator('[data-tipo="ADICAO"]')).to_have_count(1)
        subtracoes = self.no("SUBTRACAO")
        expect(subtracoes).to_have_count(2)
        # (20 - 5) - 3: a primeira subtração contém a segunda, à esquerda.
        expect(subtracoes.first.locator('[data-tipo="SUBTRACAO"] .no-papel').first).to_have_text("esquerda")

    def test_selecionar_no_destaca_o_trecho_e_mostra_a_regra(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        self.no("MULTIPLICACAO").locator(":scope > .no-linha").click()
        expect(self.no("MULTIPLICACAO")).to_have_attribute("aria-selected", "true")
        expect(self.pagina.locator("#sint-codigo .trecho-selecionado")).to_have_text("5 * 2")
        detalhes = self.pagina.locator("#no-detalhes")
        expect(detalhes).to_contain_text('termo = fator { ( "*" | "/" | "%" ) fator } ;')
        expect(detalhes).to_contain_text("linha 1, colunas 18–22")
        expect(detalhes.locator(".tokens-do-no li")).to_have_text(["5", "*", "2"])
        detalhes.get_by_role("button", name="Selecionar no editor").click()
        selecao = self.codigo.evaluate("e => e.value.slice(e.selectionStart, e.selectionEnd)")
        self.assertEqual(selecao, "5 * 2")

    def test_posicoes_da_arvore_coincidem_com_a_tabela_de_tokens(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        for valor, coluna in (("10", "13"), ("5", "18"), ("2", "22")):
            with self.subTest(valor=valor):
                linha_tabela = self.pagina.locator("#tabela-tokens tbody tr").filter(
                    has=self.pagina.locator(".lexema code", has_text=valor))
                expect(linha_tabela.locator("td").nth(4)).to_have_text(coluna)
                self.arvore.locator('[data-tipo="LITERAL_INTEIRO"]', has_text=valor).first.click()
                # "coluna 18" (um caractere) ou "colunas 13–14" (dois ou mais)
                expect(self.pagina.locator("#no-detalhes")).to_contain_text(
                    re.compile(rf"colunas? {coluna}(?!\d)"))

    def test_expandir_recolher_e_teclado(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        self.pagina.locator("#recolher-tudo").click()
        expect(self.arvore.locator('[role="treeitem"]:visible')).to_have_count(2)  # PROGRAMA e ATRIBUICAO
        self.pagina.locator("#expandir-tudo").click()
        expect(self.arvore.locator('[role="treeitem"]:visible')).to_have_count(8)
        raiz = self.arvore.locator('[role="treeitem"]').first
        raiz.focus()
        self.pagina.keyboard.press("ArrowDown")
        expect(self.no("ATRIBUICAO")).to_be_focused()
        self.pagina.keyboard.press("ArrowLeft")
        expect(self.no("ATRIBUICAO")).to_have_attribute("aria-expanded", "false")
        self.pagina.keyboard.press("ArrowRight")
        expect(self.no("ATRIBUICAO")).to_have_attribute("aria-expanded", "true")

    def test_filtro_por_tipo(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        self.pagina.select_option("#filtro-tipo", "LITERAL_INTEIRO")
        expect(self.arvore.locator(".no-linha.filtrado")).to_have_count(3)
        expect(self.pagina.locator("#filtro-info")).to_have_text("3 nó(s) LITERAL_INTEIRO destacado(s).")
        self.pagina.select_option("#filtro-tipo", "")
        expect(self.arvore.locator(".no-linha.filtrado")).to_have_count(0)

    def test_exportar_ast_em_json(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        with self.pagina.expect_download() as info:
            self.pagina.locator("#exportar-json").click()
        download = info.value
        self.assertEqual(download.suggested_filename, "ast.json")
        dados = json.loads(Path(download.path()).read_text(encoding="utf-8"))
        self.assertEqual(dados["codigo"], PROGRAMA_PRECEDENCIA)
        self.assertEqual(dados["ast"]["filhos"][0]["filhos"][1]["tipo"], "ADICAO")

    def test_arvore_de_derivacao_tem_regras_e_todos_os_tokens(self):
        self.preencher("x = 1\n")
        self.analisar_e_esperar("analise_ok")
        self.pagina.locator("#ver-derivacao").click()
        expect(self.pagina.locator("#ver-derivacao")).to_have_attribute("aria-pressed", "true")
        regras = self.arvore.locator(".deriv-regra")
        expect(regras).to_have_text(["programa", "instrucao", "atribuicao", "expressao", "comparacao",
                                     "soma", "termo", "fator", "primario"])
        terminais = self.arvore.locator(".deriv-terminal")
        expect(terminais).to_have_count(5)  # x, =, 1, NOVA_LINHA, FIM_DE_ARQUIVO
        expect(self.pagina.locator("#filtro-tipo")).to_be_disabled()
        self.pagina.locator("#ver-ast").click()
        expect(self.arvore.locator('[role="treeitem"]')).to_have_count(4)

    def test_explicacao_sobre_analise_sintatica_e_ast(self):
        self.preencher("x = 1\n")
        self.analisar_e_esperar("analise_ok")
        self.pagina.locator("#explicacao-ast summary").click()
        expect(self.pagina.locator("#explicacao-ast")).to_contain_text("descendente recursivo")
        expect(self.pagina.locator("#explicacao-ast")).to_contain_text("árvore de derivação")

    def test_legenda_usa_forma_alem_da_cor(self):
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        expect(self.pagina.locator("#legenda-nos li")).to_have_count(6)
        rotulo = self.no("ADICAO").get_attribute("aria-label")
        self.assertIn("operação", rotulo)


class TestPassoAPassoDoParser(BaseInterface):
    def setUp(self):
        super().setUp()
        self.preencher(PROGRAMA_PRECEDENCIA)
        self.analisar_e_esperar("analise_ok")
        self.descricao = self.pagina.locator("#sint-descricao")
        self.pilha = self.pagina.locator("#sint-pilha li")

    def test_primeiro_passo_entra_na_regra_inicial(self):
        self.pagina.locator("#sint-inicio").click()
        expect(self.pagina.locator("#sint-contador")).to_contain_text("Passo 1 de")
        expect(self.descricao).to_contain_text("Aplica a regra programa")
        expect(self.pilha).to_have_text(["programa"])
        expect(self.pagina.locator("#sint-tokens li.atual")).to_have_text("resultado")

    def test_pilha_de_regras_desce_ate_o_primario(self):
        self.pagina.locator("#sint-inicio").click()
        while "primario" not in (self.pilha.last.text_content() or ""):
            self.pagina.locator("#sint-proximo").click()
        expect(self.pilha).to_have_text(["programa", "instrucao", "atribuicao", "expressao", "comparacao",
                                         "soma", "termo", "fator", "primario"])
        expect(self.pagina.locator("#sint-tokens li.atual")).to_have_text("10")

    def test_nos_ainda_nao_construidos_ficam_esmaecidos(self):
        self.pagina.locator("#sint-inicio").click()
        expect(self.pagina.locator("#arvore .no-linha.futuro")).to_have_count(8)
        self.pagina.locator("#sint-fim").click()
        expect(self.pagina.locator("#arvore .no-linha.futuro")).to_have_count(0)

    def test_teclado_no_reprodutor_do_parser(self):
        self.pagina.locator("#sint-inicio").click()
        self.pagina.locator("#sint-reproduzir").focus()
        self.pagina.keyboard.press("ArrowRight")
        expect(self.pagina.locator("#sint-contador")).to_contain_text("Passo 2 de")
        self.pagina.keyboard.press("End")
        expect(self.pagina.locator("#sint-proximo")).to_be_disabled()


class TestErrosSintaticosNaInterface(BaseInterface):
    def test_erro_sintatico_com_encontrado_esperado_regra_e_localizacao(self):
        self.preencher("x = 1\nif x > 5\n    print(x)\n")
        self.analisar_e_esperar("sintatico_erros")
        expect(self.pagina.locator("#resultado-titulo")).to_have_text("Erros sintáticos encontrados")
        erro = self.pagina.locator("#lista-erros-sintaticos li")
        expect(erro).to_have_count(1)
        expect(erro.locator(".selo-erro")).to_have_text("Erro sintático")
        expect(erro.locator("p")).to_contain_text("Erro sintático na linha 2, coluna 9: era esperado ':'")
        expect(erro.locator(".erro-campos dd").nth(0)).to_have_text("fim da linha")
        expect(erro.locator(".erro-campos dd").nth(1)).to_have_text("':'")
        expect(erro.locator(".producao")).to_contain_text('condicional = "if" expressao ":" bloco')
        self.assertNotIn("Traceback", self.resultado.inner_text())
        # Sem AST: a interface explica por quê e marca o local no código.
        expect(self.pagina.locator("#arvore-aviso")).to_contain_text("A AST não foi construída")
        expect(self.pagina.locator("#sint-codigo .trecho-erro")).to_have_count(1)
        expect(self.pagina.locator("#exportar-json")).to_be_disabled()

    def test_mostrar_no_codigo_leva_ao_passo_do_erro(self):
        self.preencher("x = 5 + * 2\n")
        self.analisar_e_esperar("sintatico_erros")
        self.pagina.locator("#lista-erros-sintaticos button", has_text="Mostrar no código").click()
        expect(self.pagina.locator("#sint-descricao")).to_contain_text("dois operadores seguidos")
        selecao = self.codigo.evaluate("e => e.value.slice(e.selectionStart, e.selectionEnd)")
        self.assertEqual(selecao, "*")

    def test_varios_erros_sao_acumulados(self):
        self.preencher("a = 1 +\nb = 2\nelse:\n    c = 3\nd = (1 2)\n")
        self.analisar_e_esperar("sintatico_erros")
        codigos = self.pagina.locator("#lista-erros-sintaticos li").evaluate_all(
            "ls => ls.map(l => l.dataset.codigo)")
        self.assertEqual(codigos, ["operando_ausente", "else_sem_if", "parentese_nao_fechado"])

    def test_erro_lexico_e_sintatico_sao_distinguidos(self):
        self.preencher("x = 1 $ 2\n")
        self.analisar_e_esperar("lexico_erros")
        expect(self.pagina.locator("#lista-erros h4")).to_have_text("Erros léxicos (1)")
        expect(self.pagina.locator("#lista-erros-sintaticos")).to_have_count(0)
        expect(self.mensagem).to_contain_text("A análise sintática não foi executada.")
        motivo = self.pagina.locator("#sintatico-motivo")
        expect(motivo).to_be_visible()
        expect(motivo).to_contain_text("não foi executada porque o código tem 1 erro léxico")
        expect(self.pagina.locator("#sintatico-conteudo")).to_be_hidden()
        # A análise léxica continua sendo exibida normalmente.
        expect(self.pagina.locator("#analise-lexica")).to_be_visible()

    def test_entrada_grande_e_estranha_nao_quebra_a_interface(self):
        codigo = "x = " + "(" * 250 + "1" + ")" * 250 + "\n" + "y = 1 + 2 * 3\n" * 300
        self.preencher(codigo)
        self.analisar_e_esperar("sintatico_erros")
        expect(self.pagina.locator("#lista-erros-sintaticos li").first).to_contain_text("aninhadas demais")
        self.preencher("y = 1 + 2 * 3\n" * 400)
        self.analisar_e_esperar("analise_ok")
        expect(self.pagina.locator("#arvore")).to_be_visible()

    def test_editar_codigo_marca_a_arvore_como_desatualizada(self):
        self.preencher("x = 1\n")
        self.analisar_e_esperar("analise_ok")
        self.codigo.press("End")
        self.pagina.keyboard.type(" ")
        expect(self.pagina.locator("#aviso-desatualizado-sint")).to_be_visible()


class TestCelularSintatico(BaseInterface):
    def test_arvore_no_celular_sem_rolagem_horizontal_da_pagina(self):
        contexto = _navegador.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        pagina = contexto.new_page()
        try:
            pagina.goto(BASE_URL + "/")
            pagina.select_option("#exemplo", "repeticao")
            pagina.locator("#analisar").tap()
            expect(pagina.locator("#resultado")).to_have_attribute("data-estado", "analise_ok")
            pagina.locator('#arvore [data-tipo="REPETICAO"] > .no-linha').tap()
            expect(pagina.locator("#no-detalhes")).to_contain_text("repeticao")
            self.assertLessEqual(pagina.evaluate("document.documentElement.scrollWidth"), 390)
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

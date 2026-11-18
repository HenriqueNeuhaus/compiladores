"""Testes do analisador sintático (parser) e da AST.

Organização:
- construções válidas e a AST esperada (comparação com uma referência escrita
  à mão, no formato compacto de `resumo`);
- precedência e associatividade;
- posições (linha e coluna) dos nós;
- erros: construções incompletas, combinações inválidas, fim inesperado,
  campos encontrado/esperado/regra e recuperação de erros;
- casos de borda e integração com o scanner;
- oráculo: comparação com o módulo `ast` do próprio Python em programas de
  referência e em programas gerados aleatoriamente.
"""

import ast as ast_python
import random
import re
import unittest
from pathlib import Path

from app import parser, scanner


def analisar(codigo: str) -> dict:
    lexico, sintatico = parser.analisar(codigo)
    assert lexico.sucesso, [e.mensagem for e in lexico.erros]
    return sintatico


def resumo(no: dict) -> str:
    """AST em uma linha: TIPO(atributo, filhos...). Facilita comparar com a
    árvore esperada sem repetir posições."""
    tipo = no["tipo"]
    a = no["atributos"]
    rotulo = {
        "IDENTIFICADOR": lambda: a["nome"],
        "LITERAL_INTEIRO": lambda: a["valor"],
        "LITERAL_REAL": lambda: a["valor"],
        "LITERAL_STRING": lambda: a["valor"],
        "LITERAL_LOGICO": lambda: a["valor"],
    }
    if tipo in rotulo:
        return rotulo[tipo]()
    nome = tipo
    if "operador" in a:
        nome += f"[{a['operador']}]"
    if tipo == "CHAMADA_FUNCAO":
        nome += f"[{a['nome']}]"
    return f"{nome}(" + ", ".join(resumo(f) for f in no["filhos"]) + ")"


def ast_de(codigo: str) -> str:
    resultado = analisar(codigo)
    assert resultado["sucesso"], [e["mensagem"] for e in resultado["erros"]]
    return resumo(resultado["ast"])


def valor_de(codigo: str) -> str:
    """Resumo da expressão atribuída na primeira linha de 'x = ...'."""
    resultado = analisar(codigo)
    assert resultado["sucesso"], [e["mensagem"] for e in resultado["erros"]]
    return resumo(resultado["ast"]["filhos"][0]["filhos"][1])


def erros(codigo: str) -> list[dict]:
    resultado = analisar(codigo)
    assert not resultado["sucesso"], "era esperado erro sintático"
    assert resultado["ast"] is None
    return resultado["erros"]


def codigos(codigo: str) -> list[str]:
    return [e["codigo"] for e in erros(codigo)]


def todos_os_nos(no: dict):
    yield no
    for filho in no["filhos"]:
        yield from todos_os_nos(filho)


class TestConstrucoesValidas(unittest.TestCase):
    def test_atribuicao(self):
        self.assertEqual(ast_de("x = 10\n"), "PROGRAMA(ATRIBUICAO(x, 10))")

    def test_literais_de_todos_os_tipos(self):
        self.assertEqual(
            ast_de('a = 1\nb = 2.5\nc = "oi"\nd = True\ne = False\n'),
            'PROGRAMA(ATRIBUICAO(a, 1), ATRIBUICAO(b, 2.5), ATRIBUICAO(c, "oi"), '
            "ATRIBUICAO(d, True), ATRIBUICAO(e, False))")
        tipos = [n["tipo"] for n in todos_os_nos(analisar('a = 1\nb = 2.5\nc = "x"\nd = True\n')["ast"])]
        for tipo in ("LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING", "LITERAL_LOGICO"):
            self.assertIn(tipo, tipos)

    def test_chamada_sem_com_um_e_com_varios_argumentos(self):
        self.assertEqual(ast_de("print()\n"), "PROGRAMA(CHAMADA_FUNCAO[print]())")
        self.assertEqual(ast_de('print("a", x, 1 + 2)\n'),
                         'PROGRAMA(CHAMADA_FUNCAO[print]("a", x, ADICAO[+](1, 2)))')

    def test_chamada_dentro_de_expressao(self):
        self.assertEqual(valor_de("x = f(1) * 2\n"), "MULTIPLICACAO[*](CHAMADA_FUNCAO[f](1), 2)")

    def test_if_simples(self):
        self.assertEqual(ast_de("if x > 0:\n    y = 1\n"),
                         "PROGRAMA(CONDICIONAL(COMPARACAO[>](x, 0), BLOCO(ATRIBUICAO(y, 1))))")

    def test_if_elif_else(self):
        codigo = ("if n >= 7:\n    print(1)\nelif n >= 5:\n    print(2)\n"
                  "elif n >= 3:\n    print(3)\nelse:\n    print(4)\n")
        self.assertEqual(
            ast_de(codigo),
            "PROGRAMA(CONDICIONAL(COMPARACAO[>=](n, 7), BLOCO(CHAMADA_FUNCAO[print](1)), "
            "SENAO_SE(COMPARACAO[>=](n, 5), BLOCO(CHAMADA_FUNCAO[print](2))), "
            "SENAO_SE(COMPARACAO[>=](n, 3), BLOCO(CHAMADA_FUNCAO[print](3))), "
            "BLOCO(CHAMADA_FUNCAO[print](4))))")
        cond = analisar(codigo)["ast"]["filhos"][0]
        self.assertEqual([f["papel"] for f in cond["filhos"]],
                         ["condição", "então", "senão se", "senão se", "senão"])
        self.assertEqual(cond["atributos"], {"elif": 2, "else": True})

    def test_while(self):
        self.assertEqual(ast_de("while i < 3:\n    i = i + 1\n"),
                         "PROGRAMA(REPETICAO(COMPARACAO[<](i, 3), "
                         "BLOCO(ATRIBUICAO(i, ADICAO[+](i, 1)))))")

    def test_aninhamento_de_blocos(self):
        codigo = ("while a:\n    if b:\n        while c:\n            x = 1\n"
                  "    else:\n        y = 2\nz = 3\n")
        self.assertEqual(
            ast_de(codigo),
            "PROGRAMA(REPETICAO(a, BLOCO(CONDICIONAL(b, BLOCO(REPETICAO(c, "
            "BLOCO(ATRIBUICAO(x, 1)))), BLOCO(ATRIBUICAO(y, 2))))), ATRIBUICAO(z, 3))")

    def test_condicao_pode_ser_qualquer_expressao(self):
        self.assertEqual(ast_de("if True:\n    x = 1\n"),
                         "PROGRAMA(CONDICIONAL(True, BLOCO(ATRIBUICAO(x, 1))))")
        self.assertEqual(ast_de("while (a + 1) % 2 == 0:\n    a = a + 1\n").count("COMPARACAO[==]"), 1)

    def test_comentarios_e_linhas_em_branco_sao_ignorados(self):
        self.assertEqual(ast_de("# início\n\nx = 1  # um\n\n\n# fim\ny = 2\n"),
                         "PROGRAMA(ATRIBUICAO(x, 1), ATRIBUICAO(y, 2))")

    def test_exemplos_da_interface_sao_validos_exceto_os_de_erro(self):
        arquivo = Path(__file__).resolve().parents[2] / "frontend" / "js" / "exemplos.js"
        if not arquivo.exists():
            self.skipTest("frontend não disponível neste ambiente")
        texto = arquivo.read_text(encoding="utf-8")
        for bloco in re.findall(r'id: "([a-z-]+)".*?codigo: \[(.*?)\]\.join', texto, re.S):
            ident, linhas = bloco
            codigo = "\n".join(ast_python.literal_eval("[" + linhas + "]"))
            lexico, sintatico = parser.analisar(codigo)
            with self.subTest(exemplo=ident):
                if ident == "erros-lexicos":
                    self.assertFalse(sintatico["executado"])
                elif ident.startswith("erro"):
                    self.assertFalse(sintatico["sucesso"])
                else:
                    self.assertTrue(sintatico["sucesso"], sintatico["erros"])


class TestPrecedenciaEAssociatividade(unittest.TestCase):
    def test_multiplicacao_antes_da_adicao(self):
        self.assertEqual(valor_de("x = 2 + 3 * 4\n"), "ADICAO[+](2, MULTIPLICACAO[*](3, 4))")
        self.assertEqual(valor_de("x = 2 * 3 + 4\n"), "ADICAO[+](MULTIPLICACAO[*](2, 3), 4)")

    def test_subtracao_associativa_a_esquerda(self):
        self.assertEqual(valor_de("x = 10 - 3 - 2\n"),
                         "SUBTRACAO[-](SUBTRACAO[-](10, 3), 2)")

    def test_divisao_e_resto_associativos_a_esquerda(self):
        self.assertEqual(valor_de("x = 100 / 10 / 2\n"), "DIVISAO[/](DIVISAO[/](100, 10), 2)")
        self.assertEqual(valor_de("x = a % b * c\n"), "MULTIPLICACAO[*](RESTO[%](a, b), c)")

    def test_parenteses_alteram_a_organizacao(self):
        self.assertEqual(valor_de("x = (10 + 5) * 2\n"),
                         "MULTIPLICACAO[*](ADICAO[+](10, 5), 2)")
        self.assertEqual(valor_de("x = 10 - (3 - 2)\n"),
                         "SUBTRACAO[-](10, SUBTRACAO[-](3, 2))")
        self.assertEqual(valor_de("x = ((((1))))\n"), "1")

    def test_relacional_tem_a_menor_precedencia(self):
        self.assertEqual(valor_de("x = a + 1 > b * 2\n"),
                         "COMPARACAO[>](ADICAO[+](a, 1), MULTIPLICACAO[*](b, 2))")

    def test_menos_unario_liga_mais_forte_que_multiplicacao(self):
        self.assertEqual(valor_de("x = -a * b\n"),
                         "MULTIPLICACAO[*](OPERACAO_UNARIA[-](a), b)")
        self.assertEqual(valor_de("x = - - 3\n"),
                         "OPERACAO_UNARIA[-](OPERACAO_UNARIA[-](3))")
        self.assertEqual(valor_de("x = 2 * -3\n"), "MULTIPLICACAO[*](2, OPERACAO_UNARIA[-](3))")

    def test_todos_os_operadores_relacionais(self):
        for op in ("==", "!=", "<", "<=", ">", ">="):
            with self.subTest(op=op):
                self.assertEqual(valor_de(f"x = a {op} b\n"), f"COMPARACAO[{op}](a, b)")

    def test_papeis_esquerda_e_direita(self):
        valor = analisar("x = 1 + 2\n")["ast"]["filhos"][0]["filhos"][1]
        self.assertEqual([f["papel"] for f in valor["filhos"]], ["esquerda", "direita"])


class TestPosicoesENumeracao(unittest.TestCase):
    def test_posicoes_dos_nos(self):
        ast = analisar("resultado = 10 + 5 * 2\n")["ast"]
        atrib = ast["filhos"][0]
        self.assertEqual((atrib["linha"], atrib["coluna"], atrib["linha_final"], atrib["coluna_final"]),
                         (1, 1, 1, 22))
        soma = atrib["filhos"][1]
        self.assertEqual((soma["coluna"], soma["coluna_final"]), (13, 22))
        mult = soma["filhos"][1]
        self.assertEqual((mult["coluna"], mult["coluna_final"]), (18, 22))

    def test_no_pai_cobre_os_parenteses(self):
        mult = analisar("x = (10 + 5) * 2\n")["ast"]["filhos"][0]["filhos"][1]
        self.assertEqual(mult["coluna"], 5)            # inclui '('
        self.assertEqual(mult["filhos"][0]["coluna"], 6)  # a soma em si começa em 10

    def test_posicoes_em_varias_linhas(self):
        cond = analisar("if a:\n    x = 1\nelse:\n    y = 22\n")["ast"]["filhos"][0]
        self.assertEqual((cond["linha"], cond["coluna"], cond["linha_final"], cond["coluna_final"]),
                         (1, 1, 4, 10))
        bloco_else = cond["filhos"][2]
        self.assertEqual((bloco_else["linha"], bloco_else["coluna"]), (4, 5))

    def test_ids_em_pre_ordem_e_regra_e_passo_em_cada_no(self):
        resultado = analisar("x = 1 + 2\nprint(x)\n")
        nos = list(todos_os_nos(resultado["ast"]))
        self.assertEqual([n["id"] for n in nos], list(range(len(nos))))
        for no in nos:
            self.assertIn(no["regra"], parser.GRAMATICA)
            self.assertEqual(resultado["passos"][no["passo"]]["tipo"], "construir")

    def test_posicoes_coincidem_com_os_tokens(self):
        # Consistência entre a AST e a tabela de tokens da Etapa 3.
        codigo = 'nota = 7.5\nif nota >= 7:\n    print("ok", nota)\n'
        lexico, sintatico = parser.analisar(codigo)
        inicios = {(t.linha, t.coluna) for t in lexico.tokens}
        fins = {(t.linha_final, t.coluna_final) for t in lexico.tokens}
        for no in todos_os_nos(sintatico["ast"]):
            if no["tipo"] in ("PROGRAMA", "BLOCO"):
                continue
            with self.subTest(no=no["tipo"]):
                self.assertIn((no["linha"], no["coluna"]), inicios)
                self.assertIn((no["linha_final"], no["coluna_final"]), fins)


class TestConstrucoesIncompletas(unittest.TestCase):
    def test_operador_sem_operando_a_direita(self):
        e = erros("x = 5 +\n")[0]
        self.assertEqual(e["codigo"], "operando_ausente")
        self.assertEqual((e["linha"], e["coluna"]), (1, 8))
        self.assertEqual(e["encontrado"], "NOVA_LINHA")
        self.assertEqual(e["esperado"], ["expressao"])
        self.assertEqual(e["regra"], "soma")
        self.assertEqual(e["producao"], parser.GRAMATICA["soma"])
        self.assertTrue(e["mensagem"].startswith("Erro sintático na linha 1, coluna 8: "))
        self.assertIn("'+'", e["mensagem"])

    def test_atribuicao_sem_valor(self):
        e = erros("total =\n")[0]
        self.assertEqual(e["codigo"], "expressao_ausente")
        self.assertIn("'total'", e["mensagem"])

    def test_dois_pontos_ausente_no_if_e_no_while(self):
        for codigo, construcao in (("if x > 5\n    y = 1\n", "if"),
                                   ("while x\n    y = 1\n", "while"),
                                   ("if a:\n    y = 1\nelse\n    y = 2\n", "else")):
            with self.subTest(construcao=construcao):
                e = erros(codigo)
                self.assertEqual([x["codigo"] for x in e], ["dois_pontos_ausente"])
                self.assertEqual(e[0]["esperado"], [":"])
                self.assertIn(f"linha do {construcao}", e[0]["mensagem"])

    def test_parentese_nao_fechado(self):
        e = erros("x = (1 + 2 3)\n")[0]
        self.assertEqual(e["codigo"], "parentese_nao_fechado")
        self.assertEqual(e["esperado"], [")"])
        self.assertIn("coluna 5", e["mensagem"])

    def test_chamada_sem_virgula_entre_argumentos(self):
        e = erros('print("a" "b")\n')[0]
        self.assertEqual(e["codigo"], "parentese_nao_fechado")
        self.assertEqual(e["esperado"], [")", ","])
        self.assertIn("vírgula", e["mensagem"])

    def test_argumento_ausente(self):
        self.assertEqual(codigos("print(a,)\n"), ["argumento_ausente"])
        self.assertEqual(codigos("print(,a)\n"), ["argumento_ausente"])

    def test_parenteses_vazios(self):
        # Em Python "()" é uma tupla vazia; tuplas não fazem parte do subconjunto.
        self.assertEqual(codigos("x = ()\n"), ["expressao_ausente"])

    def test_condicao_ausente(self):
        self.assertEqual(codigos("if:\n    x = 1\n"), ["condicao_ausente"])
        self.assertEqual(codigos("while:\n    x = 1\n"), ["condicao_ausente"])

    def test_bloco_ausente(self):
        e = erros("if x:\nprint(1)\n")[0]
        self.assertEqual(e["codigo"], "bloco_ausente")
        self.assertEqual(e["esperado"], ["INDENT"])
        self.assertIn("linha 1", e["mensagem"])

    def test_fim_inesperado_do_codigo(self):
        e = erros("while x < 3:\n")[0]
        self.assertEqual(e["codigo"], "fim_inesperado")
        self.assertEqual(e["encontrado"], "FIM_DE_ARQUIVO")
        self.assertIn("terminou antes do bloco do while aberto na linha 1", e["mensagem"])
        e = erros("if a:\n    x = 1\nelif b:")[0]
        self.assertEqual(e["codigo"], "fim_inesperado")


class TestCombinacoesInvalidas(unittest.TestCase):
    def test_else_e_elif_sem_if(self):
        self.assertEqual(codigos("else:\n    x = 1\n"), ["else_sem_if"])
        self.assertEqual(codigos("x = 1\nelif x:\n    x = 2\n"), ["elif_sem_if"])

    def test_else_com_recuo_diferente_do_if(self):
        codigo = "if a:\n    x = 1\n    else:\n        x = 2\n"
        self.assertEqual(codigos(codigo), ["else_sem_if"])

    def test_operadores_consecutivos(self):
        e = erros("x = 5 + * 2\n")[0]
        self.assertEqual(e["codigo"], "operadores_consecutivos")
        self.assertEqual((e["coluna"], e["encontrado"]), (9, "*"))
        self.assertEqual(codigos("x = = 2\n"), ["operadores_consecutivos"])
        self.assertEqual(codigos("x = a < > b\n"), ["operadores_consecutivos"])

    def test_sinal_unario_depois_de_operador_e_valido(self):
        self.assertTrue(analisar("x = 5 + -2\ny = 3 * +1\n")["sucesso"])

    def test_palavra_reservada_onde_se_esperava_identificador(self):
        self.assertEqual(codigos("True = 1\n"), ["palavra_reservada_como_identificador"])
        self.assertEqual(codigos("x = 1 + while\n"), ["palavra_reservada_inesperada"])

    def test_palavra_reservada_fora_do_subconjunto(self):
        e = erros("for i in x:\n    y = 1\n")
        self.assertEqual(e[0]["codigo"], "palavra_fora_do_subconjunto")
        self.assertEqual(len(e), 1, "o bloco do for não deve gerar erros em cascata")

    def test_operadores_logicos_fora_do_subconjunto(self):
        for codigo in ("if a and b:\n    x = 1\n", "x = a or b\n", "x = not a\n",
                       "while x in y:\n    x = 1\n"):
            with self.subTest(codigo=codigo):
                e = erros(codigo)
                self.assertEqual([x["codigo"] for x in e], ["operador_logico_fora_do_subconjunto"])

    def test_atribuicao_invalida(self):
        self.assertEqual(codigos("5 = x\n"), ["atribuicao_invalida"])
        self.assertEqual(codigos("x + 1 = 2\n"), ["atribuicao_invalida"])

    def test_atribuicao_na_condicao(self):
        e = erros("if x = 1:\n    y = 2\n")[0]
        self.assertEqual(e["codigo"], "atribuicao_na_condicao")
        self.assertIn("'=='", e["mensagem"])

    def test_expressao_sem_efeito(self):
        e = erros("x == 1\n")[0]
        self.assertEqual(e["codigo"], "expressao_sem_efeito")
        self.assertIn("use '='", e["mensagem"])
        self.assertEqual(codigos("x + 1\n"), ["expressao_sem_efeito"])
        self.assertEqual(codigos("42\n"), ["expressao_sem_efeito"])

    def test_dois_valores_seguidos(self):
        e = erros("x = 1 2\n")[0]
        self.assertEqual(e["codigo"], "fim_de_instrucao_esperado")
        self.assertIn("Falta um operador entre '1' e '2'?", e["mensagem"])

    def test_comparacao_encadeada(self):
        self.assertEqual(codigos("x = a < b < c\n"), ["comparacao_encadeada"])

    def test_parentese_sem_abertura(self):
        self.assertEqual(codigos("x = 5)\n"), ["parentese_sem_abertura"])

    def test_indentacao_inesperada(self):
        self.assertEqual(codigos("x = 1\n    y = 2\n"), ["indentacao_inesperada"])

    def test_bloco_na_mesma_linha(self):
        self.assertEqual(codigos("if x: y = 1\n"), ["bloco_na_mesma_linha"])


class TestRecuperacaoDeErros(unittest.TestCase):
    def test_acumula_erros_de_linhas_diferentes(self):
        e = erros("x = 1 +\ny = 2\nz = * 3\nw = (1\n)\n")
        self.assertEqual([(x["codigo"], x["linha"]) for x in e],
                         [("operando_ausente", 1), ("operadores_consecutivos", 3)])

    def test_sem_erros_em_cascata_depois_de_dois_pontos_ausente(self):
        codigo = "if x > 5\n    y = 1\n    z = 2\nelse:\n    w = 3\n"
        self.assertEqual(codigos(codigo), ["dois_pontos_ausente"])

    def test_erros_dentro_de_bloco_com_cabecalho_invalido_continuam_aparecendo(self):
        codigo = "for i in x:\n    y = = 1\nz = 2\n"
        self.assertEqual(codigos(codigo), ["palavra_fora_do_subconjunto", "operadores_consecutivos"])

    def test_programa_com_muitos_erros_para_no_limite(self):
        codigo = "x = = 1\n" * (parser.LIMITE_ERROS + 20)
        self.assertEqual(len(erros(codigo)), parser.LIMITE_ERROS)

    def test_passos_registram_erro_e_recuperacao(self):
        passos = analisar("x = 1 +\ny = 2\n")["passos"]
        tipos = [p["tipo"] for p in passos]
        self.assertIn("erro", tipos)
        self.assertIn("recuperar", tipos)
        self.assertLess(tipos.index("erro"), tipos.index("recuperar"))


class TestCasosDeBorda(unittest.TestCase):
    def test_codigo_vazio_e_so_comentarios_sao_programas_validos(self):
        for codigo in ("", "# nada aqui\n", "\n\n\n"):
            with self.subTest(codigo=codigo):
                resultado = analisar(codigo)
                self.assertTrue(resultado["sucesso"])
                self.assertEqual(resultado["ast"]["tipo"], "PROGRAMA")
                self.assertEqual(resultado["ast"]["filhos"], [])

    def test_unico_comando_sem_quebra_de_linha_no_fim(self):
        self.assertEqual(ast_de("print(1)"), "PROGRAMA(CHAMADA_FUNCAO[print](1))")

    def test_fim_no_meio_de_uma_construcao(self):
        self.assertEqual(codigos("x = 1 +"), ["operando_ausente"])
        self.assertEqual(codigos("if a:"), ["fim_inesperado"])

    def test_aninhamento_excessivo_nao_derruba_o_parser(self):
        codigo = "x = " + "(" * 300 + "1" + ")" * 300 + "\n"
        self.assertEqual(codigos(codigo), ["aninhamento_excessivo"])
        self.assertEqual(codigos("x = " + "-" * 500 + "1\n"), ["aninhamento_excessivo"])

    def test_programa_grande_limita_os_passos(self):
        codigo = "x = 1 + 2 * 3\n" * 1500
        resultado = analisar(codigo)
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(len(resultado["passos"]), parser.LIMITE_PASSOS)
        self.assertTrue(resultado["passos_truncados"])
        self.assertEqual(len(resultado["ast"]["filhos"]), 1500)

    def test_lista_de_tokens_sem_fim_de_arquivo_e_recusada(self):
        with self.assertRaises(ValueError):
            parser.Parser([])


class TestIntegracaoComScanner(unittest.TestCase):
    def test_com_erro_lexico_o_parser_nao_e_executado(self):
        lexico, sintatico = parser.analisar("x = 1 $ 2\n")
        self.assertFalse(lexico.sucesso)
        self.assertFalse(sintatico["executado"])
        self.assertIsNone(sintatico["ast"])
        self.assertEqual(sintatico["erros"], [])
        self.assertIn("1 erro léxico", sintatico["motivo"])

    def test_aviso_lexico_nao_impede_o_parser(self):
        lexico, sintatico = parser.analisar("def f:\n    x = 1\n")
        self.assertTrue(lexico.sucesso)
        self.assertTrue(lexico.avisos)
        self.assertTrue(sintatico["executado"])
        self.assertEqual(sintatico["erros"][0]["codigo"], "palavra_fora_do_subconjunto")

    def test_parser_consome_exatamente_os_tokens_do_scanner(self):
        codigo = "x = (1 + 2) * 3\nif x > 1:\n    print(x)\n"
        lexico, sintatico = parser.analisar(codigo)
        consumidos = [p["token"] for p in sintatico["passos"] if p["tipo"] == "consumir"]
        self.assertEqual(consumidos, list(range(len(lexico.tokens))))

    def test_mesmos_tokens_da_etapa_3(self):
        # Regressão: a Etapa 4 não alterou o scanner.
        lexico = scanner.analisar("if x >= 1:\n    print(\"oi\")\n")
        self.assertEqual([t.tipo for t in lexico.tokens], [
            "PALAVRA_RESERVADA", "IDENTIFICADOR", "OPERADOR_RELACIONAL", "LITERAL_INTEIRO",
            "DELIMITADOR", "NOVA_LINHA", "INDENT", "IDENTIFICADOR", "DELIMITADOR",
            "LITERAL_STRING", "DELIMITADOR", "NOVA_LINHA", "DEDENT", "FIM_DE_ARQUIVO"])


class TestArvoreDeDerivacao(unittest.TestCase):
    def folhas(self, no):
        if "terminal" in no:
            return [no]
        return [f for filho in no["filhos"] for f in self.folhas(filho)]

    def test_folhas_sao_todos_os_tokens_em_ordem(self):
        codigo = "x = 2 + 3 * 4\n"
        lexico, sintatico = parser.analisar(codigo)
        folhas = self.folhas(sintatico["derivacao"])
        self.assertEqual([f["lexema"] for f in folhas], [t.lexema for t in lexico.tokens])

    def test_derivacao_mostra_as_regras_intermediarias(self):
        derivacao = analisar("x = 1\n")["derivacao"]
        caminho = []
        no = derivacao
        while "regra" in no:
            caminho.append(no["regra"])
            no = no["filhos"][0] if no["regra"] != "atribuicao" else no["filhos"][2]
        self.assertEqual(caminho, ["programa", "instrucao", "atribuicao", "expressao",
                                   "comparacao", "soma", "termo", "fator", "primario"])

    def test_derivacao_ausente_quando_ha_erro(self):
        self.assertIsNone(analisar("x = 1 +\n")["derivacao"])


class TestGramaticaDocumentada(unittest.TestCase):
    def test_todas_as_producoes_estao_em_docs_gramatica(self):
        arquivo = Path(__file__).resolve().parents[2] / "docs" / "gramatica.md"
        if not arquivo.exists():
            self.skipTest("docs não disponível neste ambiente")
        texto = arquivo.read_text(encoding="utf-8")
        for regra, producao in parser.GRAMATICA.items():
            with self.subTest(regra=regra):
                self.assertIn(producao, texto)

    def test_todo_tipo_de_no_tem_regra_da_gramatica(self):
        for tipo, regra in parser.TIPOS_DE_NO.items():
            self.assertIn(regra, parser.GRAMATICA, tipo)


# ---------------------------------------------------------------------------
# Oráculo: módulo ast do Python
# ---------------------------------------------------------------------------

OPS_PY = {ast_python.Add: "+", ast_python.Sub: "-", ast_python.Mult: "*", ast_python.Div: "/",
          ast_python.Mod: "%", ast_python.Eq: "==", ast_python.NotEq: "!=", ast_python.Lt: "<",
          ast_python.LtE: "<=", ast_python.Gt: ">", ast_python.GtE: ">=",
          ast_python.USub: "-", ast_python.UAdd: "+"}
TIPO_BIN = {"+": "ADICAO", "-": "SUBTRACAO", "*": "MULTIPLICACAO", "/": "DIVISAO", "%": "RESTO"}


def resumo_python(no, codigo_linhas) -> str:
    """Converte a AST do Python para o mesmo formato de `resumo`."""
    if isinstance(no, ast_python.Module):
        return "PROGRAMA(" + ", ".join(resumo_python(i, codigo_linhas) for i in no.body) + ")"
    if isinstance(no, ast_python.Assign):
        return f"ATRIBUICAO({no.targets[0].id}, {resumo_python(no.value, codigo_linhas)})"
    if isinstance(no, ast_python.Expr):
        return resumo_python(no.value, codigo_linhas)
    if isinstance(no, ast_python.While):
        return (f"REPETICAO({resumo_python(no.test, codigo_linhas)}, BLOCO("
                + ", ".join(resumo_python(i, codigo_linhas) for i in no.body) + "))")
    if isinstance(no, ast_python.If):
        partes = [resumo_python(no.test, codigo_linhas),
                  "BLOCO(" + ", ".join(resumo_python(i, codigo_linhas) for i in no.body) + ")"]
        senao = no.orelse
        # elif aparece no Python como um If sozinho dentro do orelse, na mesma coluna
        while (len(senao) == 1 and isinstance(senao[0], ast_python.If)
               and codigo_linhas[senao[0].lineno - 1].lstrip().startswith("elif")):
            ramo = senao[0]
            partes.append(f"SENAO_SE({resumo_python(ramo.test, codigo_linhas)}, BLOCO("
                          + ", ".join(resumo_python(i, codigo_linhas) for i in ramo.body) + "))")
            senao = ramo.orelse
        if senao:
            partes.append("BLOCO(" + ", ".join(resumo_python(i, codigo_linhas) for i in senao) + ")")
        return "CONDICIONAL(" + ", ".join(partes) + ")"
    if isinstance(no, ast_python.Call):
        return (f"CHAMADA_FUNCAO[{no.func.id}](" +
                ", ".join(resumo_python(a, codigo_linhas) for a in no.args) + ")")
    if isinstance(no, ast_python.BinOp):
        op = OPS_PY[type(no.op)]
        return (f"{TIPO_BIN[op]}[{op}]({resumo_python(no.left, codigo_linhas)}, "
                f"{resumo_python(no.right, codigo_linhas)})")
    if isinstance(no, ast_python.UnaryOp):
        return f"OPERACAO_UNARIA[{OPS_PY[type(no.op)]}]({resumo_python(no.operand, codigo_linhas)})"
    if isinstance(no, ast_python.Compare):
        return (f"COMPARACAO[{OPS_PY[type(no.ops[0])]}]({resumo_python(no.left, codigo_linhas)}, "
                f"{resumo_python(no.comparators[0], codigo_linhas)})")
    if isinstance(no, ast_python.Name):
        return no.id
    if isinstance(no, ast_python.Constant):
        return ast_python.get_source_segment("\n".join(codigo_linhas), no)
    raise AssertionError(f"nó fora do subconjunto: {type(no).__name__}")


def posicoes_python(arvore) -> list[tuple]:
    """(linha, coluna inicial, linha final, coluna final) das expressões, em
    colunas 1-based e coluna final inclusiva, como no nosso parser."""
    saida = []
    for no in ast_python.walk(arvore):
        if isinstance(no, ast_python.expr) and not isinstance(no, ast_python.Name) or \
                isinstance(no, ast_python.Name) and isinstance(no.ctx, ast_python.Load):
            saida.append((no.lineno, no.col_offset + 1, no.end_lineno, no.end_col_offset))
    return sorted(saida)


def posicoes_nossas(ast: dict) -> list[tuple]:
    expressoes = {"COMPARACAO", "ADICAO", "SUBTRACAO", "MULTIPLICACAO", "DIVISAO", "RESTO",
                  "OPERACAO_UNARIA", "LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING",
                  "LITERAL_LOGICO", "CHAMADA_FUNCAO"}
    saida = []
    for no in todos_os_nos(ast):
        if no["tipo"] in expressoes or (no["tipo"] == "IDENTIFICADOR" and no["papel"] != "alvo"):
            saida.append((no["linha"], no["coluna"], no["linha_final"], no["coluna_final"]))
    # O Python também guarda a posição do nome da função chamada.
    for no in todos_os_nos(ast):
        if no["tipo"] == "CHAMADA_FUNCAO":
            saida.append((no["linha"], no["coluna"], no["linha"],
                          no["coluna"] + len(no["atributos"]["nome"]) - 1))
    return sorted(saida)


PROGRAMAS_DE_REFERENCIA = [
    "resultado = 10 + 5 * 2\n",
    "resultado = 20 - 5 - 3\n",
    "resultado = (10 + 5) * 2\n",
    "x = -(a + b) * -c % 3\n",
    'print("soma:", a + b, (c))\n',
    "if a < b:\n    m = a\nelif a == b:\n    m = 0\nelse:\n    m = b\n",
    "while i <= 10:\n    if i % 2 == 0:\n        print(i)\n    i = i + 1\n",
    "ok = True\nif ok != False:\n    x = 1.5 / 3\n",
]


def programa_aleatorio(rng: random.Random, profundidade: int = 0, recuo: str = "") -> str:
    def aritmetica(n: int) -> str:
        """Expressão sem comparação no nível de cima (comparações só aparecem
        entre parênteses ou como argumento, como exige a gramática)."""
        if n <= 0 or rng.random() < 0.3:
            return rng.choice(["a", "b", "total", "1", "42", "3.5", '"txt"', "True", "False"])
        escolha = rng.random()
        if escolha < 0.5:
            return f"{aritmetica(n - 1)} {rng.choice('+-*/%')} {aritmetica(n - 1)}"
        if escolha < 0.7:
            return f"({expressao(n - 1)})"
        if escolha < 0.8:
            return f"-{aritmetica(n - 1)}"
        return f"f({', '.join(expressao(n - 1) for _ in range(rng.randint(0, 2)))})"

    def expressao(n: int) -> str:
        if rng.random() < 0.3:
            return (f"{aritmetica(n)} {rng.choice(['==', '!=', '<', '<=', '>', '>='])} "
                    f"{aritmetica(n - 1)}")
        return aritmetica(n)

    def condicao() -> str:
        e = expressao(2)
        return e if " " in e else f"{e} > 0"

    linhas = []
    for _ in range(rng.randint(1, 4)):
        tipo = rng.random()
        if tipo < 0.45 or profundidade >= 2:
            linhas.append(f"{recuo}{rng.choice(['a', 'b', 'x1'])} = {expressao(3)}")
        elif tipo < 0.6:
            linhas.append(f"{recuo}print({expressao(2)})")
        elif tipo < 0.8:
            linhas.append(f"{recuo}if {condicao()}:")
            linhas.append(programa_aleatorio(rng, profundidade + 1, recuo + "    ").rstrip("\n"))
            for _ in range(rng.randint(0, 2)):
                linhas.append(f"{recuo}elif {condicao()}:")
                linhas.append(programa_aleatorio(rng, profundidade + 1, recuo + "    ").rstrip("\n"))
            if rng.random() < 0.5:
                linhas.append(f"{recuo}else:")
                linhas.append(programa_aleatorio(rng, profundidade + 1, recuo + "    ").rstrip("\n"))
        else:
            linhas.append(f"{recuo}while {condicao()}:")
            linhas.append(programa_aleatorio(rng, profundidade + 1, recuo + "    ").rstrip("\n"))
    return "\n".join(linhas) + "\n"


class TestComparacaoComAstDoPython(unittest.TestCase):
    def comparar(self, codigo: str) -> None:
        esperado = resumo_python(ast_python.parse(codigo), codigo.split("\n"))
        resultado = analisar(codigo)
        self.assertTrue(resultado["sucesso"], resultado["erros"])
        self.assertEqual(resumo(resultado["ast"]), esperado)
        self.assertEqual(posicoes_nossas(resultado["ast"]), posicoes_python(ast_python.parse(codigo)))

    def test_programas_de_referencia(self):
        for codigo in PROGRAMAS_DE_REFERENCIA:
            with self.subTest(codigo=codigo):
                self.comparar(codigo)

    def test_programas_aleatorios(self):
        rng = random.Random(2026)
        for i in range(300):
            codigo = programa_aleatorio(rng)
            with self.subTest(i=i, codigo=codigo):
                self.comparar(codigo)

    def test_programas_que_o_python_rejeita_tambem_sao_rejeitados(self):
        invalidos = ["x = 5 +\n", "if x > 5\n    y = 1\n", "else:\n    x = 1\n", "True = 1\n",
                     "x = 1 2\n", "if x:\nprint(1)\n", "5 = x\n", "if x = 1:\n    y = 2\n",
                     "while:\n    y = 1\n", "x = 5)\n", "print(a,,b)\n",
                     "x = = 2\n", "if a:\n    x = 1\n    else:\n        x = 2\n"]
        for codigo in invalidos:
            with self.subTest(codigo=codigo):
                with self.assertRaises(SyntaxError):
                    compile(codigo, "<teste>", "exec")
                self.assertFalse(analisar(codigo)["sucesso"])


if __name__ == "__main__":
    unittest.main()

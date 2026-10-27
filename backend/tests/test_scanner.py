"""Testes unitários do analisador léxico (scanner)."""

import io
import random
import tokenize
import unittest

from app.scanner import (
    CATEGORIAS,
    OPERADORES_DO_SUBCONJUNTO,
    PALAVRAS_RESERVADAS,
    PALAVRAS_RESERVADAS_FORA,
    analisar,
)


def tipos(codigo):
    return [t.tipo for t in analisar(codigo).tokens]


def pares(codigo):
    """(tipo, lexema) dos tokens, sem os de estrutura."""
    estrutura = {"NOVA_LINHA", "INDENT", "DEDENT", "FIM_DE_ARQUIVO"}
    return [(t.tipo, t.lexema) for t in analisar(codigo).tokens if t.tipo not in estrutura]


def codigos_de_erro(codigo):
    return [e.codigo for e in analisar(codigo).erros]


class TestPalavrasReservadas(unittest.TestCase):
    def test_cada_palavra_do_subconjunto(self):
        for palavra in PALAVRAS_RESERVADAS:
            with self.subTest(palavra=palavra):
                r = analisar(palavra)
                self.assertEqual(pares(palavra), [("PALAVRA_RESERVADA", palavra)])
                self.assertFalse(r.tokens[0].fora_do_subconjunto)
                self.assertEqual(r.avisos, [])

    def test_palavras_de_python_fora_do_subconjunto_geram_aviso_e_nao_erro(self):
        for palavra in PALAVRAS_RESERVADAS_FORA:
            with self.subTest(palavra=palavra):
                r = analisar(palavra)
                self.assertTrue(r.sucesso)
                self.assertEqual(r.tokens[0].tipo, "PALAVRA_RESERVADA")
                self.assertTrue(r.tokens[0].fora_do_subconjunto)
                self.assertEqual(r.avisos[0].codigo, "palavra_reservada_fora_do_subconjunto")

    def test_palavras_reservadas_diferenciam_maiusculas(self):
        self.assertEqual(pares("If true WHILE"), [
            ("IDENTIFICADOR", "If"), ("IDENTIFICADOR", "true"), ("IDENTIFICADOR", "WHILE")])

    def test_print_e_identificador(self):
        self.assertEqual(pares("print"), [("IDENTIFICADOR", "print")])

    def test_prefixo_de_palavra_reservada_e_identificador(self):
        self.assertEqual(pares("iff elsewhere while_1"), [
            ("IDENTIFICADOR", "iff"), ("IDENTIFICADOR", "elsewhere"),
            ("IDENTIFICADOR", "while_1")])


class TestIdentificadores(unittest.TestCase):
    def test_formacoes_validas(self):
        for nome in ("x", "numero", "_x1", "__temp", "Valor2", "a_b_c", "_"):
            with self.subTest(nome=nome):
                self.assertEqual(pares(nome), [("IDENTIFICADOR", nome)])

    def test_identificador_comecando_com_digito_e_erro(self):
        r = analisar("2x = 1")
        self.assertEqual(r.erros[0].codigo, "literal_numerico_malformado")
        self.assertEqual(r.erros[0].lexema, "2x")

    def test_identificador_com_acento_e_erro(self):
        r = analisar("ação = 1")
        self.assertEqual(r.erros[0].codigo, "identificador_com_caractere_nao_ascii")
        self.assertEqual(r.erros[0].lexema, "ação")
        self.assertIn("'ç'", r.erros[0].mensagem)
        # o restante da linha continua sendo analisado
        self.assertEqual(pares("ação = 1"), [("OPERADOR_ATRIBUICAO", "="), ("LITERAL_INTEIRO", "1")])

    def test_identificador_comecando_com_letra_acentuada(self):
        self.assertEqual(codigos_de_erro("élan"), ["identificador_com_caractere_nao_ascii"])


class TestLiterais(unittest.TestCase):
    def test_inteiros(self):
        for lexema in ("0", "7", "42", "100000", "00"):
            with self.subTest(lexema=lexema):
                self.assertEqual(pares(lexema), [("LITERAL_INTEIRO", lexema)])

    def test_reais(self):
        for lexema in ("3.14", "0.5", "10.0", "007.5"):
            with self.subTest(lexema=lexema):
                self.assertEqual(pares(lexema), [("LITERAL_REAL", lexema)])

    def test_strings_com_aspas_duplas_e_simples(self):
        self.assertEqual(pares('"Aprovado"'), [("LITERAL_STRING", '"Aprovado"')])
        self.assertEqual(pares("'oi'"), [("LITERAL_STRING", "'oi'")])
        self.assertEqual(pares('""'), [("LITERAL_STRING", '""')])

    def test_strings_com_escapes_e_aspas_internas(self):
        for s in (r'"diz \"oi\""', r"'it\'s'", r'"a\\"', r'"tab\tfim"', "\"ele disse 'oi'\""):
            with self.subTest(s=s):
                self.assertEqual(pares(s), [("LITERAL_STRING", s)])

    def test_string_com_acentos_e_simbolos(self):
        s = '"ação ✓ @ $ # não é comentário"'
        r = analisar(s)
        self.assertTrue(r.sucesso)
        self.assertEqual(pares(s), [("LITERAL_STRING", s)])
        self.assertEqual(r.comentarios, [])

    def test_true_e_false_sao_palavras_reservadas(self):
        self.assertEqual(pares("True False"), [
            ("PALAVRA_RESERVADA", "True"), ("PALAVRA_RESERVADA", "False")])


class TestOperadoresEDelimitadores(unittest.TestCase):
    def test_cada_operador_e_delimitador_do_subconjunto(self):
        for op, tipo in OPERADORES_DO_SUBCONJUNTO.items():
            with self.subTest(op=op):
                self.assertEqual(pares(f"a {op} b") if op not in "()" else pares(op),
                                 [("IDENTIFICADOR", "a"), (tipo, op), ("IDENTIFICADOR", "b")]
                                 if op not in "()" else [(tipo, op)])

    def test_operadores_compostos_pelo_casamento_mais_longo(self):
        self.assertEqual(pares("a<=b>=c==d!=e"), [
            ("IDENTIFICADOR", "a"), ("OPERADOR_RELACIONAL", "<="),
            ("IDENTIFICADOR", "b"), ("OPERADOR_RELACIONAL", ">="),
            ("IDENTIFICADOR", "c"), ("OPERADOR_RELACIONAL", "=="),
            ("IDENTIFICADOR", "d"), ("OPERADOR_RELACIONAL", "!="),
            ("IDENTIFICADOR", "e")])

    def test_atribuicao_seguida_de_igualdade(self):
        self.assertEqual(pares("x = y == z"), [
            ("IDENTIFICADOR", "x"), ("OPERADOR_ATRIBUICAO", "="), ("IDENTIFICADOR", "y"),
            ("OPERADOR_RELACIONAL", "=="), ("IDENTIFICADOR", "z")])

    def test_operadores_de_python_fora_do_subconjunto_sao_erros_inteiros(self):
        for op in ("//", "**", "+=", ";", "[", "]", "{", "}", ".", "@", ":=", "->"):
            with self.subTest(op=op):
                r = analisar(f"a {op} b")
                self.assertEqual([e.codigo for e in r.erros], ["operador_fora_do_subconjunto"])
                self.assertEqual(r.erros[0].lexema, op)

    def test_exclamacao_sozinha_nao_e_operador(self):
        self.assertEqual(codigos_de_erro("a ! b"), ["caractere_nao_reconhecido"])


class TestComentariosEEspacos(unittest.TestCase):
    def test_comentario_de_linha_inteira_e_ignorado(self):
        r = analisar("# só um comentário\nx = 1\n")
        self.assertEqual(pares("# só um comentário\nx = 1\n"), [
            ("IDENTIFICADOR", "x"), ("OPERADOR_ATRIBUICAO", "="), ("LITERAL_INTEIRO", "1")])
        self.assertEqual(len(r.comentarios), 1)
        self.assertEqual(r.comentarios[0].lexema, "# só um comentário")

    def test_comentario_no_fim_da_linha(self):
        r = analisar("x = 1  # um\n")
        self.assertEqual(tipos("x = 1  # um\n"), [
            "IDENTIFICADOR", "OPERADOR_ATRIBUICAO", "LITERAL_INTEIRO", "NOVA_LINHA",
            "FIM_DE_ARQUIVO"])
        self.assertEqual((r.comentarios[0].linha, r.comentarios[0].coluna), (1, 8))

    def test_espacos_e_tabulacoes_no_meio_da_linha_nao_geram_tokens(self):
        self.assertEqual(pares("x\t=   1"), [
            ("IDENTIFICADOR", "x"), ("OPERADOR_ATRIBUICAO", "="), ("LITERAL_INTEIRO", "1")])

    def test_linhas_em_branco_nao_geram_nova_linha(self):
        self.assertEqual(tipos("\n\nx = 1\n\n\n"), [
            "IDENTIFICADOR", "OPERADOR_ATRIBUICAO", "LITERAL_INTEIRO", "NOVA_LINHA",
            "FIM_DE_ARQUIVO"])


class TestIndentacao(unittest.TestCase):
    def test_bloco_gera_indent_e_dedent(self):
        codigo = "if x:\n    y = 1\nz = 2\n"
        self.assertEqual(tipos(codigo), [
            "PALAVRA_RESERVADA", "IDENTIFICADOR", "DELIMITADOR", "NOVA_LINHA",
            "INDENT", "IDENTIFICADOR", "OPERADOR_ATRIBUICAO", "LITERAL_INTEIRO", "NOVA_LINHA",
            "DEDENT", "IDENTIFICADOR", "OPERADOR_ATRIBUICAO", "LITERAL_INTEIRO", "NOVA_LINHA",
            "FIM_DE_ARQUIVO"])

    def test_dois_niveis_fecham_com_dois_dedents(self):
        codigo = "while a:\n    if b:\n        c = 1\nd = 2\n"
        r = analisar(codigo)
        self.assertEqual([t.tipo for t in r.tokens].count("INDENT"), 2)
        dedents = [t for t in r.tokens if t.tipo == "DEDENT"]
        self.assertEqual(len(dedents), 2)
        self.assertTrue(all((t.linha, t.coluna) == (4, 1) for t in dedents))

    def test_blocos_abertos_no_fim_do_codigo_geram_dedent(self):
        r = analisar("if a:\n    if b:\n        c = 1")
        self.assertEqual([t.tipo for t in r.tokens][-4:],
                         ["NOVA_LINHA", "DEDENT", "DEDENT", "FIM_DE_ARQUIVO"])

    def test_pilha_registrada_nos_passos(self):
        r = analisar("if a:\n    b = 1\n")
        indent = next(p for p in r.passos if p.get("token") is not None
                      and r.tokens[p["token"]].tipo == "INDENT")
        self.assertEqual(indent["pilha"], [0, 4])
        self.assertEqual(r.passos[-1]["pilha"], [0])

    def test_lexema_do_indent_e_o_recuo(self):
        r = analisar("if a:\n    b = 1\n")
        indent = next(t for t in r.tokens if t.tipo == "INDENT")
        self.assertEqual((indent.lexema, indent.linha, indent.coluna, indent.coluna_final),
                         ("    ", 2, 1, 4))

    def test_indentacao_inconsistente_e_erro_e_a_analise_continua(self):
        r = analisar("if a:\n    b = 1\n  c = 2\nd = 3\n")
        self.assertEqual([e.codigo for e in r.erros], ["indentacao_inconsistente"])
        self.assertEqual(r.erros[0].linha, 3)
        self.assertIn("níveis: 0", r.erros[0].mensagem)
        self.assertIn(("IDENTIFICADOR", "d"), pares("if a:\n    b = 1\n  c = 2\nd = 3\n"))

    def test_tabulacao_na_indentacao_e_erro(self):
        r = analisar("if a:\n\tb = 1\n")
        self.assertEqual([e.codigo for e in r.erros], ["indentacao_com_tabulacao"])
        self.assertEqual((r.erros[0].linha, r.erros[0].coluna), (2, 1))

    def test_comentario_com_outra_indentacao_nao_altera_a_pilha(self):
        self.assertEqual(tipos("if a:\n    b = 1\n# fora\n    c = 2\n").count("DEDENT"), 1)

    def test_parenteses_ignoram_quebra_de_linha_e_indentacao(self):
        codigo = "x = (1 +\n        2)\ny = 3\n"
        r = analisar(codigo)
        self.assertTrue(r.sucesso)
        self.assertEqual([t.tipo for t in r.tokens].count("NOVA_LINHA"), 2)
        self.assertNotIn("INDENT", [t.tipo for t in r.tokens])

    def test_parentese_nao_fechado(self):
        r = analisar("print(1\n")
        self.assertEqual([e.codigo for e in r.erros], ["parentese_nao_fechado"])
        self.assertEqual((r.erros[0].linha, r.erros[0].coluna), (1, 6))


class TestPosicoes(unittest.TestCase):
    def test_linha_e_coluna_em_varias_posicoes(self):
        r = analisar("x = 10\nif x >= 5:\n    print(\"ok\")\n")
        posicoes = {(t.lexema, t.linha, t.coluna, t.coluna_final)
                    for t in r.tokens if t.tipo not in ("NOVA_LINHA", "INDENT", "DEDENT",
                                                         "FIM_DE_ARQUIVO")}
        for esperado in [("x", 1, 1, 1), ("10", 1, 5, 6), ("if", 2, 1, 2), (">=", 2, 6, 7),
                         ("5", 2, 9, 9), (":", 2, 10, 10), ("print", 3, 5, 9),
                         ('"ok"', 3, 11, 14), (")", 3, 15, 15)]:
            self.assertIn(esperado, posicoes)

    def test_crlf_do_windows(self):
        self.assertEqual(analisar("x = 1\r\ny = 2\r\n").tokens[4].linha, 2)

    def test_nova_linha_implicita_no_fim_sem_quebra(self):
        r = analisar("x = 1")
        nl = r.tokens[3]
        self.assertEqual((nl.tipo, nl.lexema, nl.linha, nl.coluna), ("NOVA_LINHA", "", 1, 6))
        fim = r.tokens[4]
        self.assertEqual((fim.tipo, fim.linha, fim.coluna), ("FIM_DE_ARQUIVO", 2, 1))


class TestErrosLexicos(unittest.TestCase):
    def test_caractere_nao_reconhecido_com_localizacao(self):
        r = analisar("x = 1\ny = 2 $ 3\n")
        e = r.erros[0]
        self.assertEqual((e.tipo, e.codigo, e.lexema, e.linha, e.coluna),
                         ("ERRO_LEXICO", "caractere_nao_reconhecido", "$", 2, 7))
        self.assertTrue(e.mensagem.startswith("Erro léxico na linha 2, coluna 7:"))
        self.assertFalse(r.sucesso)

    def test_varios_erros_sao_acumulados(self):
        r = analisar("a = 1 $ 2\nb = ? \nc = `x`\n")
        self.assertEqual(len(r.erros), 4)
        self.assertIn(("IDENTIFICADOR", "c"), pares("a = 1 $ 2\nb = ? \nc = `x`\n"))

    def test_string_nao_fechada(self):
        r = analisar('msg = "oi\nx = 1\n')
        self.assertEqual(r.erros[0].codigo, "string_nao_fechada")
        self.assertEqual((r.erros[0].linha, r.erros[0].coluna), (1, 7))
        self.assertIn(("IDENTIFICADOR", "x"), pares('msg = "oi\nx = 1\n'))

    def test_string_com_tres_aspas(self):
        r = analisar('x = """a\nb"""\ny = 1\n')
        self.assertEqual(r.erros[0].codigo, "string_com_tres_aspas")
        self.assertEqual(r.erros[0].linha_final, 2)
        self.assertIn(("IDENTIFICADOR", "y"), pares('x = """a\nb"""\ny = 1\n'))

    def test_f_string(self):
        self.assertEqual(codigos_de_erro('print(f"x={x}")'), ["prefixo_de_string"])

    def test_literais_numericos_malformados(self):
        casos = {"12abc": "malformado", "0x1F": "base", "1e5": "científica",
                 "1_000": "separador"}
        for lexema, trecho in casos.items():
            with self.subTest(lexema=lexema):
                r = analisar(f"x = {lexema}")
                self.assertEqual(r.erros[0].lexema, lexema)
                self.assertIn(trecho, r.erros[0].mensagem)

    def test_real_incompleto_e_zeros_a_esquerda(self):
        self.assertEqual(codigos_de_erro("x = 3."), ["literal_real_incompleto"])
        self.assertEqual(codigos_de_erro("x = 007"), ["zeros_a_esquerda"])

    def test_barra_invertida(self):
        self.assertEqual(codigos_de_erro("x = 1 + \\\n    2\n"), ["continuacao_com_barra"])
        self.assertEqual(codigos_de_erro("x = 1 \\ 2"), ["caractere_nao_reconhecido"])

    def test_caractere_unicode_descrito_pelo_nome(self):
        r = analisar("x = 5 × 2")
        self.assertIn("multiplication sign", r.erros[0].mensagem)

    def test_mensagens_nao_expoem_detalhes_internos(self):
        r = analisar("a $ b\n'x\n0x1\n\tc\n")
        for e in r.erros:
            self.assertNotIn("Traceback", e.mensagem)
            self.assertNotIn("scanner.py", e.mensagem)


class TestCasosDeBorda(unittest.TestCase):
    def test_codigo_vazio(self):
        r = analisar("")
        self.assertEqual([t.tipo for t in r.tokens], ["FIM_DE_ARQUIVO"])
        self.assertTrue(r.sucesso)

    def test_apenas_espacos_e_quebras(self):
        self.assertEqual(tipos("   \n\t\n  "), ["FIM_DE_ARQUIVO"])

    def test_apenas_comentarios(self):
        r = analisar("# a\n   # b\n")
        self.assertEqual([t.tipo for t in r.tokens], ["FIM_DE_ARQUIVO"])
        self.assertEqual(len(r.comentarios), 2)

    def test_token_no_fim_sem_quebra_de_linha(self):
        self.assertEqual(pares("x = abc"), [
            ("IDENTIFICADOR", "x"), ("OPERADOR_ATRIBUICAO", "="), ("IDENTIFICADOR", "abc")])

    def test_erro_sintatico_com_tokens_validos_e_tokenizado(self):
        r = analisar("if x > 5\n    print(x)\n")
        self.assertTrue(r.sucesso)
        self.assertIn("INDENT", [t.tipo for t in r.tokens])

    def test_contagem_por_categoria(self):
        c = analisar("x = 1\n").contagem()
        self.assertEqual(set(c), set(CATEGORIAS))
        self.assertEqual((c["IDENTIFICADOR"], c["LITERAL_INTEIRO"], c["NOVA_LINHA"]), (1, 1, 1))

    def test_cada_token_tem_um_passo(self):
        r = analisar("if a:\n    b = 'x'  # c\n")
        indices = [p["token"] for p in r.passos if p["tipo"] == "token"]
        self.assertEqual(indices, list(range(len(r.tokens))))
        self.assertTrue(all(p["descricao"] for p in r.passos))

    def test_limite_de_erros(self):
        r = analisar("$" * 300)
        self.assertEqual(len(r.erros), 100)


# ---------------------------------------------------------------------------
# Comparação com o tokenize da biblioteca padrão do Python (oráculo)
# ---------------------------------------------------------------------------

def tokens_do_python(codigo):
    """Tokens do módulo tokenize convertidos para (grupo, lexema, linha, coluna)."""
    resultado = []
    for t in tokenize.generate_tokens(io.StringIO(codigo).readline):
        nome = tokenize.tok_name[t.type]
        if nome in ("COMMENT", "NL", "ENCODING"):
            continue
        grupo = {"NAME": "NOME", "NUMBER": "NUMERO", "STRING": "STRING", "OP": "OP",
                 "NEWLINE": "NOVA_LINHA", "INDENT": "INDENT", "DEDENT": "DEDENT",
                 "ENDMARKER": "FIM_DE_ARQUIVO"}[nome]
        resultado.append((grupo, t.string, t.start[0], t.start[1] + 1))
    return resultado


GRUPOS = {
    "PALAVRA_RESERVADA": "NOME", "IDENTIFICADOR": "NOME", "LITERAL_INTEIRO": "NUMERO",
    "LITERAL_REAL": "NUMERO", "LITERAL_STRING": "STRING", "OPERADOR_ARITMETICO": "OP",
    "OPERADOR_RELACIONAL": "OP", "OPERADOR_ATRIBUICAO": "OP", "DELIMITADOR": "OP",
    "NOVA_LINHA": "NOVA_LINHA", "INDENT": "INDENT", "DEDENT": "DEDENT",
    "FIM_DE_ARQUIVO": "FIM_DE_ARQUIVO",
}


def tokens_do_scanner(codigo):
    r = analisar(codigo)
    assert r.sucesso, [e.mensagem for e in r.erros]
    return [(GRUPOS[t.tipo], t.lexema, t.linha, t.coluna) for t in r.tokens]


PROGRAMAS_DE_REFERENCIA = [
    # Exemplos da interface
    "# Área e média de duas medidas\nlargura = 8\naltura = 3.5\narea = largura * altura\n"
    "media = (largura + altura) / 2\nprint(area)\nprint(media)\n",
    'nota = 7.5\nif nota >= 7:\n    print("Aprovado")\nelif nota >= 5:\n'
    '    print("Recuperação")\nelse:\n    print("Reprovado")\n',
    'contador = 1\nsoma = 0\nwhile contador <= 5:\n    soma = soma + contador\n'
    '    if soma % 2 == 0:\n        print("Soma par:", soma)\n    contador = contador + 1\n'
    'print(soma)\n',
    'x = 10\nif x > 5\n    print("x é maior que 5")\n',
    # Casos de estrutura
    "x = 1",
    "if a:\n    b = 1",
    "if a:\n    if b:\n        c = 1\n    d = 2\ne = 3\n",
    "\n\n# comentário\n   \nx = 1  # fim\n\n",
    "x = (1 +\n     2 *\n  3)\nprint(x,\n      'a')\n",
    "while True:\n    if False:\n        x = 'it\\'s'\n\n    y = \"a\\\\\"\n",
    "if a != b:\n    x = -1\n# comentário recuado diferente\n        # outro\n    y = (a)\n",
    "t = (\n    1,\n    2,\n)\n",
    "a=1;" [:-1] + "\n",
]


def programa_aleatorio(rng):
    """Gera um programa válido do subconjunto, com blocos aninhados."""
    nomes = ["a", "b", "x", "total", "_tmp", "nota2", "y_1"]
    operadores = ["+", "-", "*", "/", "%"]
    relacionais = ["==", "!=", "<", "<=", ">", ">="]

    def termo():
        escolha = rng.random()
        if escolha < 0.35:
            return rng.choice(nomes)
        if escolha < 0.6:
            return str(rng.randint(0, 999))
        if escolha < 0.75:
            return f"{rng.randint(0, 99)}.{rng.randint(0, 99)}"
        if escolha < 0.85:
            return rng.choice(['"texto"', "'oi'", '"a\\"b"', "True", "False"])
        return f"({termo()} {rng.choice(operadores)} {termo()})"

    def expressao():
        e = termo()
        for _ in range(rng.randint(0, 3)):
            e += f"{rng.choice(['', ' ', '  '])}{rng.choice(operadores)} {termo()}"
        return e

    linhas = []

    def bloco(nivel, profundidade):
        for _ in range(rng.randint(1, 4)):
            recuo = "    " * nivel
            escolha = rng.random()
            if escolha < 0.15:
                linhas.append("")
            elif escolha < 0.25:
                linhas.append(recuo + "# comentário " + str(rng.randint(0, 9)))
            elif escolha < 0.55 or profundidade == 0:
                linhas.append(f"{recuo}{rng.choice(nomes)} = {expressao()}")
            elif escolha < 0.7:
                linhas.append(f"{recuo}print({expressao()}, {expressao()})")
            else:
                cabecalho = rng.choice(["if", "while"])
                linhas.append(f"{recuo}{cabecalho} {expressao()} "
                              f"{rng.choice(relacionais)} {expressao()}:")
                bloco(nivel + 1, profundidade - 1)
                if cabecalho == "if" and rng.random() < 0.5:
                    linhas.append(f"{recuo}else:")
                    bloco(nivel + 1, profundidade - 1)

    bloco(0, 3)
    final = "\n" if rng.random() < 0.7 else ""
    return "\n".join(linhas) + final


class TestComparacaoComTokenizeDoPython(unittest.TestCase):
    """O scanner deve produzir os mesmos tokens, lexemas e posições do Python
    para programas válidos do subconjunto."""

    def assertIgualAoPython(self, codigo):
        self.assertEqual(tokens_do_scanner(codigo), tokens_do_python(codigo), msg=repr(codigo))

    def test_programas_de_referencia(self):
        for codigo in PROGRAMAS_DE_REFERENCIA:
            with self.subTest(codigo=codigo[:40]):
                self.assertIgualAoPython(codigo)

    def test_300_programas_aleatorios(self):
        rng = random.Random(2026)
        for i in range(300):
            codigo = programa_aleatorio(rng)
            with self.subTest(programa=i):
                self.assertIgualAoPython(codigo)


if __name__ == "__main__":
    unittest.main()

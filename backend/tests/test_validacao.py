"""Testes unitários das regras de validação (sem servidor HTTP)."""

import unittest

from app.validacao import (
    LIMITE_CARACTERES,
    MENSAGENS,
    ErroValidacao,
    estatisticas,
    validar_corpo,
)


class TestValidarCorpo(unittest.TestCase):
    def assertErro(self, corpo, tipo, status):
        with self.assertRaises(ErroValidacao) as ctx:
            validar_corpo(corpo)
        self.assertEqual(ctx.exception.tipo, tipo)
        self.assertEqual(ctx.exception.status, status)
        self.assertEqual(ctx.exception.mensagem, MENSAGENS[tipo])

    # Casos aceitos ------------------------------------------------------
    def test_codigo_valido_e_devolvido_sem_alteracao(self):
        codigo = "x = 10\nprint(x)\n"
        self.assertEqual(validar_corpo({"codigo": codigo}), codigo)

    def test_codigo_com_erro_sintatico_e_aceito(self):
        # A validação desta etapa não analisa a sintaxe.
        codigo = 'if x > 5\n    print("x")'
        self.assertEqual(validar_corpo({"codigo": codigo}), codigo)

    def test_caracteres_especiais_e_unicode_sao_aceitos(self):
        codigo = 'msg = "ação ✓ <tag> & \\"aspas\\" \\t"\n# comentário: çãõ €'
        self.assertEqual(validar_corpo({"codigo": codigo}), codigo)

    def test_espacos_ao_redor_sao_preservados(self):
        codigo = "\n\n    x = 1   \n"
        self.assertEqual(validar_corpo({"codigo": codigo}), codigo)

    def test_campos_extras_sao_ignorados(self):
        self.assertEqual(validar_corpo({"codigo": "x = 1", "outro": 2}), "x = 1")

    def test_codigo_no_limite_exato_e_aceito(self):
        codigo = "x" * LIMITE_CARACTERES
        self.assertEqual(validar_corpo({"codigo": codigo}), codigo)

    # Problemas de entrada (400 e 413) ------------------------------------
    def test_texto_vazio(self):
        self.assertErro({"codigo": ""}, "entrada_vazia", 400)

    def test_apenas_espacos(self):
        self.assertErro({"codigo": "     "}, "entrada_em_branco", 400)

    def test_apenas_quebras_de_linha_e_tabulacoes(self):
        self.assertErro({"codigo": "\n\t \r\n  \n"}, "entrada_em_branco", 400)

    def test_acima_do_limite(self):
        self.assertErro(
            {"codigo": "x" * (LIMITE_CARACTERES + 1)}, "entrada_muito_grande", 413
        )

    # Requisições inválidas (422) -----------------------------------------
    def test_corpo_lista(self):
        self.assertErro(["x = 1"], "corpo_nao_objeto", 422)

    def test_corpo_texto(self):
        self.assertErro("x = 1", "corpo_nao_objeto", 422)

    def test_corpo_nulo(self):
        self.assertErro(None, "corpo_nao_objeto", 422)

    def test_campo_ausente(self):
        self.assertErro({"code": "x = 1"}, "campo_ausente", 422)

    def test_codigo_numero(self):
        self.assertErro({"codigo": 10}, "tipo_invalido", 422)

    def test_codigo_nulo(self):
        self.assertErro({"codigo": None}, "tipo_invalido", 422)

    def test_codigo_lista(self):
        self.assertErro({"codigo": ["x = 1"]}, "tipo_invalido", 422)


class TestEstatisticas(unittest.TestCase):
    def test_conta_linhas_e_caracteres(self):
        self.assertEqual(estatisticas("a = 1\nb = 2"), {"linhas": 2, "caracteres": 11})

    def test_linha_unica_sem_quebra(self):
        self.assertEqual(estatisticas("x"), {"linhas": 1, "caracteres": 1})

    def test_quebra_final_nao_cria_linha_extra(self):
        self.assertEqual(estatisticas("a\nb\n")["linhas"], 2)


if __name__ == "__main__":
    unittest.main()

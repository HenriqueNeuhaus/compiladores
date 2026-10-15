import { test } from "node:test";
import assert from "node:assert/strict";
import { LIMITE_CARACTERES, MENSAGENS, contarTexto, validarCodigo } from "../../js/validacao.js";

test("código válido é aceito", () => {
  assert.deepEqual(validarCodigo("x = 1\nprint(x)"), { valido: true });
});

test("código com erro sintático é aceito (a sintaxe não é verificada aqui)", () => {
  assert.equal(validarCodigo("if x > 5\n    print(x)").valido, true);
});

test("caracteres especiais e acentos são aceitos", () => {
  assert.equal(validarCodigo('s = "ação ✓ <b> & \\"x\\""').valido, true);
});

test("texto vazio é recusado com a mensagem de entrada vazia", () => {
  assert.deepEqual(validarCodigo(""), {
    valido: false,
    tipo: "entrada_vazia",
    mensagem: MENSAGENS.entrada_vazia,
  });
});

test("valor que não é texto é tratado como vazio", () => {
  assert.equal(validarCodigo(undefined).tipo, "entrada_vazia");
  assert.equal(validarCodigo(null).tipo, "entrada_vazia");
});

test("apenas espaços, tabulações e quebras de linha são recusados", () => {
  for (const texto of ["   ", "\n\n", "\t \r\n "]) {
    const r = validarCodigo(texto);
    assert.equal(r.valido, false);
    assert.equal(r.tipo, "entrada_em_branco");
    assert.equal(r.mensagem, MENSAGENS.entrada_em_branco);
  }
});

test("limite de tamanho: aceita no limite e recusa acima", () => {
  assert.equal(validarCodigo("x".repeat(LIMITE_CARACTERES)).valido, true);
  assert.equal(validarCodigo("x".repeat(LIMITE_CARACTERES + 1)).tipo, "entrada_muito_grande");
});

test("as mensagens do navegador são iguais às do backend", () => {
  // Mesmos textos de backend/app/validacao.py, para o estudante ver a mesma orientação.
  assert.equal(MENSAGENS.entrada_vazia, "Informe um código-fonte antes de solicitar a análise.");
  assert.match(MENSAGENS.entrada_muito_grande, /20000 caracteres/);
});

test("contarTexto conta linhas e caracteres", () => {
  assert.deepEqual(contarTexto(""), { linhas: 0, caracteres: 0 });
  assert.deepEqual(contarTexto("a = 1"), { linhas: 1, caracteres: 5 });
  assert.deepEqual(contarTexto("a\nb\n"), { linhas: 2, caracteres: 4 });
  assert.deepEqual(contarTexto("a\r\nb"), { linhas: 2, caracteres: 4 });
});

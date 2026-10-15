import { test } from "node:test";
import assert from "node:assert/strict";
import { EXEMPLOS, obterExemplo } from "../../js/exemplos.js";
import { validarCodigo } from "../../js/validacao.js";

test("há pelo menos três exemplos", () => {
  assert.ok(EXEMPLOS.length >= 3);
});

test("identificadores são únicos", () => {
  const ids = EXEMPLOS.map((e) => e.id);
  assert.equal(new Set(ids).size, ids.length);
});

for (const exemplo of EXEMPLOS) {
  test(`exemplo "${exemplo.id}" tem título, construções e código válido para envio`, () => {
    assert.ok(exemplo.titulo.length > 0);
    assert.ok(exemplo.construcoes.length > 0);
    assert.equal(validarCodigo(exemplo.codigo).valido, true);
  });

  test(`exemplo "${exemplo.id}" usa indentação com espaços, não tabulações`, () => {
    assert.ok(!exemplo.codigo.includes("\t"));
  });

  test(`obterExemplo("${exemplo.id}") devolve o próprio exemplo`, () => {
    assert.equal(obterExemplo(exemplo.id), exemplo);
  });
}

test("exemplos cobrem as construções planejadas do subconjunto", () => {
  const todos = EXEMPLOS.map((e) => e.codigo).join("\n");
  for (const construcao of ["=", "+", "*", "/", "if ", "elif ", "else:", "while ", "print("]) {
    assert.ok(todos.includes(construcao), `falta a construção ${construcao}`);
  }
});

test("obterExemplo devolve undefined para identificador inexistente", () => {
  assert.equal(obterExemplo("nao-existe"), undefined);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { MENSAGENS, URL_ANALISAR, enviarCodigo } from "../../js/api.js";

// fetch falso que registra a chamada e devolve uma resposta controlada.
function fetchFalso({ status = 200, corpo, jsonInvalido = false, erro } = {}) {
  const chamadas = [];
  const impl = async (url, init) => {
    chamadas.push({ url, init });
    if (erro) throw erro;
    return {
      status,
      ok: status >= 200 && status < 300,
      json: async () => {
        if (jsonInvalido) throw new SyntaxError("Unexpected token <");
        return corpo;
      },
    };
  };
  return { impl, chamadas };
}

test("envia POST em JSON com o campo codigo para /api/analisar", async () => {
  const { impl, chamadas } = fetchFalso({ corpo: { recebido: true, mensagem: "ok" } });
  await enviarCodigo('x = "ação"\n', { fetchImpl: impl });
  assert.equal(chamadas.length, 1);
  assert.equal(chamadas[0].url, URL_ANALISAR);
  assert.equal(chamadas[0].init.method, "POST");
  assert.equal(chamadas[0].init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(chamadas[0].init.body), { codigo: 'x = "ação"\n' });
});

test("resposta 200 com recebido=true é sucesso e traz os dados", async () => {
  const corpo = { recebido: true, mensagem: "Código recebido", estatisticas: { linhas: 1, caracteres: 5 } };
  const r = await enviarCodigo("x = 1", { fetchImpl: fetchFalso({ corpo }).impl });
  assert.deepEqual(r, { tipo: "sucesso", dados: corpo });
});

for (const status of [400, 413, 422]) {
  test(`resposta ${status} com erro é classificada como problema de entrada`, async () => {
    const corpo = { recebido: false, erro: { tipo: "x", mensagem: "Mensagem do servidor" } };
    const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ status, corpo }).impl });
    assert.deepEqual(r, { tipo: "entrada", mensagem: "Mensagem do servidor", erro: "x" });
  });
}

test("falha de rede é classificada como comunicação", async () => {
  const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ erro: new TypeError("Failed to fetch") }).impl });
  assert.deepEqual(r, { tipo: "comunicacao", mensagem: MENSAGENS.comunicacao });
});

for (const status of [502, 503, 504]) {
  test(`servidor indisponível (${status}) é classificado como comunicação`, async () => {
    const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ status, jsonInvalido: true }).impl });
    assert.equal(r.tipo, "comunicacao");
  });
}

test("tempo limite esgotado é classificado como comunicação", async () => {
  const lento = (url, init) =>
    new Promise((_, rejeitar) => {
      init.signal.addEventListener("abort", () => rejeitar(new DOMException("abortado", "AbortError")));
    });
  const r = await enviarCodigo("x", { fetchImpl: lento, timeoutMs: 20 });
  assert.equal(r.tipo, "comunicacao");
});

test("erro 500 gera mensagem genérica, sem repassar detalhes do servidor", async () => {
  const corpo = { recebido: false, erro: { tipo: "erro_interno", mensagem: "Traceback /srv/app" } };
  const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ status: 500, corpo }).impl });
  assert.deepEqual(r, { tipo: "inesperado", mensagem: MENSAGENS.inesperado });
});

test("resposta que não é JSON gera mensagem genérica", async () => {
  const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ status: 200, jsonInvalido: true }).impl });
  assert.equal(r.tipo, "inesperado");
});

test("resposta 200 fora do contrato gera mensagem genérica", async () => {
  const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ status: 200, corpo: { outro: 1 } }).impl });
  assert.equal(r.tipo, "inesperado");
});

test("erro de entrada sem mensagem no corpo gera mensagem genérica", async () => {
  const r = await enviarCodigo("x", { fetchImpl: fetchFalso({ status: 422, corpo: {} }).impl });
  assert.equal(r.tipo, "inesperado");
});

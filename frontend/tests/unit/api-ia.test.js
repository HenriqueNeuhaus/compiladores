import { test } from "node:test";
import assert from "node:assert/strict";
import { MENSAGENS_IA, URL_IA_EXPLICAR, explicarIA, statusIA } from "../../js/api.js";

function fetchFalso({ status = 200, corpo, jsonInvalido = false, erro, esperar } = {}) {
  const chamadas = [];
  const impl = async (url, init = {}) => {
    chamadas.push({ url, init });
    if (esperar) {
      await new Promise((resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(new DOMException("abortado", "AbortError")));
      });
    }
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

test("explicarIA envia o pedido ao backend, nunca ao Ollama", async () => {
  const { impl, chamadas } = fetchFalso({ corpo: { resposta: "Explicação", gerado_por_ia: true } });
  const r = await explicarIA({ tipo: "no", codigo: "x = 1", referencia: 3 }, { fetchImpl: impl });
  assert.equal(r.tipo, "sucesso");
  assert.equal(r.dados.resposta, "Explicação");
  assert.equal(chamadas[0].url, URL_IA_EXPLICAR);
  assert.ok(!chamadas[0].url.includes("11434"));
  assert.deepEqual(JSON.parse(chamadas[0].init.body), { tipo: "no", codigo: "x = 1", referencia: 3 });
});

test("explicarIA repassa as mensagens seguras de indisponibilidade e pedido inválido", async () => {
  for (const status of [422, 503, 504]) {
    const { impl } = fetchFalso({ status, corpo: { recebido: false, erro: { tipo: "ia_indisponivel", mensagem: "Assistente fora do ar." } } });
    const r = await explicarIA({ tipo: "pergunta", codigo: "" }, { fetchImpl: impl });
    assert.deepEqual(r, { tipo: "erro", mensagem: "Assistente fora do ar.", erro: "ia_indisponivel" });
  }
});

test("explicarIA usa mensagem genérica para 500, JSON inválido e falha de rede", async () => {
  const casos = [
    fetchFalso({ status: 500, corpo: { erro: { mensagem: "detalhe interno" } } }),
    fetchFalso({ jsonInvalido: true }),
  ];
  for (const { impl } of casos) {
    const r = await explicarIA({ tipo: "pergunta", codigo: "" }, { fetchImpl: impl });
    assert.equal(r.mensagem, MENSAGENS_IA.inesperado);
  }
  const { impl } = fetchFalso({ erro: new TypeError("Failed to fetch") });
  assert.equal((await explicarIA({ tipo: "pergunta" }, { fetchImpl: impl })).mensagem, MENSAGENS_IA.comunicacao);
});

test("explicarIA pode ser cancelada e respeita o tempo limite", async () => {
  const controle = new AbortController();
  const { impl } = fetchFalso({ esperar: true });
  const promessa = explicarIA({ tipo: "pergunta" }, { fetchImpl: impl, sinal: controle.signal });
  controle.abort();
  const r = await promessa;
  assert.equal(r.mensagem, MENSAGENS_IA.cancelado);
  assert.equal(r.cancelado, true);
  const lento = fetchFalso({ esperar: true });
  const r2 = await explicarIA({ tipo: "pergunta" }, { fetchImpl: lento.impl, timeoutMs: 20 });
  assert.equal(r2.mensagem, MENSAGENS_IA.comunicacao);
});

test("statusIA nunca lança exceção", async () => {
  const ok = fetchFalso({ corpo: { disponivel: true, modelo: "llama3.2" } });
  assert.equal((await statusIA({ fetchImpl: ok.impl })).disponivel, true);
  const fora = fetchFalso({ erro: new TypeError("rede") });
  assert.deepEqual(await statusIA({ fetchImpl: fora.impl }), { disponivel: false, mensagem: MENSAGENS_IA.comunicacao });
  const estranho = fetchFalso({ corpo: { nada: 1 } });
  assert.equal((await statusIA({ fetchImpl: estranho.impl })).disponivel, false);
});

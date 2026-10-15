// Comunicação com o backend.
// Contrato: POST /api/analisar com {"codigo": "<texto>"}.
// Toda resposta é convertida em um resultado com um destes tipos:
//   sucesso      -> o backend recebeu o código
//   entrada      -> o backend recusou o código ou a requisição (400, 413, 422)
//   comunicacao  -> o servidor não respondeu ou está indisponível
//   inesperado   -> qualquer outro problema (por exemplo, erro 500)

export const URL_ANALISAR = "/api/analisar";
export const TEMPO_LIMITE_MS = 10000;

export const MENSAGENS = {
  comunicacao: "Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente.",
  inesperado: "Ocorreu um erro inesperado ao processar a solicitação. Tente novamente.",
};

const STATUS_ENTRADA = new Set([400, 413, 422]);
const STATUS_INDISPONIVEL = new Set([502, 503, 504]);

/**
 * Envia o código ao backend e classifica a resposta.
 * @param {string} codigo
 * @param {{fetchImpl?: typeof fetch, timeoutMs?: number, url?: string}} [opcoes]
 */
export async function enviarCodigo(codigo, opcoes = {}) {
  const { fetchImpl = globalThis.fetch, timeoutMs = TEMPO_LIMITE_MS, url = URL_ANALISAR } = opcoes;
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), timeoutMs);

  let resposta;
  try {
    resposta = await fetchImpl(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codigo }),
      signal: controle.signal,
    });
  } catch {
    // Rede indisponível, servidor fora do ar ou tempo limite esgotado.
    return { tipo: "comunicacao", mensagem: MENSAGENS.comunicacao };
  } finally {
    clearTimeout(relogio);
  }

  if (STATUS_INDISPONIVEL.has(resposta.status)) {
    return { tipo: "comunicacao", mensagem: MENSAGENS.comunicacao };
  }

  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    return { tipo: "inesperado", mensagem: MENSAGENS.inesperado };
  }

  if (resposta.ok && dados && dados.recebido === true) {
    return { tipo: "sucesso", dados };
  }

  const erro = dados && dados.erro;
  if (STATUS_ENTRADA.has(resposta.status) && erro && typeof erro.mensagem === "string") {
    return { tipo: "entrada", mensagem: erro.mensagem, erro: erro.tipo };
  }

  // 500 ou qualquer resposta fora do contrato: mensagem genérica,
  // sem repassar detalhes técnicos ao estudante.
  return { tipo: "inesperado", mensagem: MENSAGENS.inesperado };
}

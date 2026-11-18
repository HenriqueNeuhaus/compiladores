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

// ---------------------------------------------------------------------------
// Assistente de IA (Etapa 4, diferencial). O navegador fala só com o backend;
// o backend é quem consulta o Ollama.
// ---------------------------------------------------------------------------

export const URL_IA_STATUS = "/api/ia/status";
export const URL_IA_EXPLICAR = "/api/ia/explicar";
export const TEMPO_LIMITE_IA_MS = 240000; // modelos no processador podem demorar

export const MENSAGENS_IA = {
  comunicacao: "Não foi possível falar com o servidor para obter a explicação. A análise continua disponível.",
  inesperado: "O assistente de IA não conseguiu responder agora. Tente novamente.",
  cancelado: "Pedido de explicação cancelado.",
};

/** Consulta se o assistente está disponível. Nunca lança exceção. */
export async function statusIA({ fetchImpl = globalThis.fetch, url = URL_IA_STATUS } = {}) {
  try {
    const resposta = await fetchImpl(url);
    const dados = await resposta.json();
    if (resposta.ok && dados && typeof dados.disponivel === "boolean") return dados;
  } catch {
    // servidor fora do ar: tratado abaixo
  }
  return { disponivel: false, mensagem: MENSAGENS_IA.comunicacao };
}

/**
 * Pede uma explicação ao backend.
 * corpo: {tipo: "token"|"no"|"erro"|"pergunta", codigo, referencia?, pergunta?}
 * Devolve {tipo: "sucesso", dados} ou {tipo: "erro", mensagem}.
 */
export async function explicarIA(corpo, opcoes = {}) {
  const { fetchImpl = globalThis.fetch, timeoutMs = TEMPO_LIMITE_IA_MS, url = URL_IA_EXPLICAR, sinal } = opcoes;
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort("tempo"), timeoutMs);
  const cancelar = () => controle.abort("cancelado");
  sinal?.addEventListener("abort", cancelar);
  let resposta;
  try {
    resposta = await fetchImpl(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
      signal: controle.signal,
    });
  } catch {
    const cancelado = sinal?.aborted;
    return { tipo: "erro", mensagem: cancelado ? MENSAGENS_IA.cancelado : MENSAGENS_IA.comunicacao, cancelado };
  } finally {
    clearTimeout(relogio);
    sinal?.removeEventListener("abort", cancelar);
  }
  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    return { tipo: "erro", mensagem: MENSAGENS_IA.inesperado };
  }
  if (resposta.ok && dados && typeof dados.resposta === "string") return { tipo: "sucesso", dados };
  // 422 e 503/504 trazem mensagens próprias e seguras do backend.
  if (dados && dados.erro && typeof dados.erro.mensagem === "string" && resposta.status !== 500) {
    return { tipo: "erro", mensagem: dados.erro.mensagem, erro: dados.erro.tipo };
  }
  return { tipo: "erro", mensagem: MENSAGENS_IA.inesperado };
}

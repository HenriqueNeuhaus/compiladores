// Painel "Assistente de IA": professor virtual e explicações contextuais
// (token, nó da AST e erro sintático) geradas pelo Llama 3.2 via backend.
// A IA só explica: tokens, AST e erros continuam vindo do scanner e do parser.

export const PERGUNTAS_SUGERIDAS = [
  "Qual a diferença entre scanner e parser?",
  "O que são símbolos terminais e não terminais?",
  "Qual a diferença entre a AST e a árvore de derivação?",
  "Como a precedência dos operadores aparece na árvore?",
  "Como funciona um parser descendente recursivo?",
  "Por que a gramática evita recursão à esquerda?",
];

export function iniciarAssistente(raiz, { explicar, consultarStatus }) {
  const doc = raiz.ownerDocument;
  const $ = (s) => raiz.querySelector(s);
  const el = {
    painel: $("#assistente-ia"),
    status: $("#ia-status"),
    sugestoes: $("#ia-sugestoes"),
    formulario: $("#ia-formulario"),
    pergunta: $("#ia-pergunta"),
    perguntar: $("#ia-perguntar"),
    cancelar: $("#ia-cancelar"),
    saida: $("#ia-saida"),
  };
  const criar = (tag, props = {}, ...filhos) => {
    const e = doc.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k in e) e[k] = v;
      else e.setAttribute(k, v);
    }
    e.append(...filhos.filter((f) => f !== null && f !== undefined));
    return e;
  };

  let codigoAnalisado = "";
  let controle = null;
  let relogio = null;

  for (const texto of PERGUNTAS_SUGERIDAS) {
    el.sugestoes.append(
      criar("li", {}, criar("button", {
        type: "button",
        className: "chip-pergunta",
        textContent: texto,
        onclick: () => pedir({ tipo: "pergunta", pergunta: texto }, "Pergunta"),
      })),
    );
  }

  el.formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const texto = el.pergunta.value.trim();
    if (!texto) {
      el.pergunta.focus();
      return;
    }
    pedir({ tipo: "pergunta", pergunta: texto }, "Pergunta");
  });
  el.cancelar.addEventListener("click", () => controle?.abort());

  function definirStatus(info) {
    el.status.dataset.disponivel = String(Boolean(info.disponivel));
    el.status.textContent = info.disponivel
      ? `Disponível (modelo ${info.modelo})`
      : `Indisponível. ${info.mensagem ?? ""}`.trim();
  }

  async function atualizarStatus() {
    el.status.dataset.disponivel = "verificando";
    el.status.textContent = "Verificando o assistente…";
    definirStatus(await consultarStatus());
  }

  function ocupado(sim) {
    el.perguntar.disabled = sim;
    el.cancelar.hidden = !sim;
    el.saida.setAttribute("aria-busy", String(sim));
    for (const b of raiz.querySelectorAll(".botao-ia, .chip-pergunta")) b.disabled = sim;
  }

  /**
   * Faz um pedido ao assistente.
   * pedido: {tipo, referencia?, pergunta?}; rotulo: o que está sendo explicado.
   */
  async function pedir(pedido, rotulo) {
    if (controle) return;
    const corpo = { codigo: codigoAnalisado, ...pedido };
    const pergunta = pedido.pergunta;
    controle = new AbortController();
    ocupado(true);
    const inicio = Date.now();
    const contador = criar("span", { className: "ia-tempo", textContent: "0 s" });
    el.saida.replaceChildren(
      criar("p", { className: "ia-alvo" }, criar("strong", { textContent: `${rotulo}: ` }), pergunta ?? "explicação didática"),
      criar("p", { className: "ia-carregando", role: "status" },
        criar("span", { className: "ia-girando", "aria-hidden": "true" }),
        " Gerando explicação com o Llama 3.2… No processador isso pode levar um ou dois minutos. ",
        contador),
    );
    relogio = setInterval(() => { contador.textContent = `${Math.round((Date.now() - inicio) / 1000)} s`; }, 1000);
    el.painel.scrollIntoView?.({ block: "nearest" });
    const r = await explicar(corpo, { sinal: controle.signal });
    clearInterval(relogio);
    controle = null;
    ocupado(false);
    const segundos = Math.round((Date.now() - inicio) / 1000);
    if (r.tipo !== "sucesso") {
      el.saida.replaceChildren(
        criar("p", { className: "ia-alvo" }, criar("strong", { textContent: `${rotulo}: ` }), pergunta ?? "explicação didática"),
        criar("p", { className: "ia-erro", role: "alert", textContent: r.mensagem }),
      );
      if (r.erro === "ia_indisponivel" || r.erro === "modelo_ausente") definirStatus({ disponivel: false, mensagem: r.mensagem });
      return r;
    }
    const d = r.dados;
    el.saida.replaceChildren(
      criar("p", { className: "ia-alvo" }, criar("strong", { textContent: `${rotulo}: ` }), pergunta ?? d.pergunta),
      criar("p", { className: "selo-ia", textContent: `Gerado por IA (${d.modelo}) em ${segundos} s` }),
      criar("div", { className: "ia-resposta", id: "ia-resposta" },
        ...d.resposta.split(/\n{2,}/).map((paragrafo) =>
          // O modelo às vezes usa **negrito** em Markdown: os asteriscos são removidos
          // e o texto é inserido como texto puro (nunca como HTML).
          criar("p", { textContent: paragrafo.replace(/\*\*(.+?)\*\*/g, "$1").trim() }))),
      criar("p", { className: "ia-aviso", textContent: d.aviso }),
      criar("details", { className: "ia-contexto" },
        criar("summary", { textContent: "Ver os dados do compilador enviados ao modelo" }),
        criar("pre", { textContent: JSON.stringify(d.contexto_enviado, null, 2) })),
    );
    return r;
  }

  return {
    definirCodigo(codigo) { codigoAnalisado = codigo; },
    explicarToken(indice, lexema) { return pedir({ tipo: "token", referencia: indice }, `Token ${lexema}`); },
    explicarNo(no) { return pedir({ tipo: "no", referencia: no.id }, `Nó ${no.tipo}`); },
    explicarErro(indice, erro) { return pedir({ tipo: "erro", referencia: indice }, `Erro na linha ${erro.linha}`); },
    atualizarStatus,
  };
}

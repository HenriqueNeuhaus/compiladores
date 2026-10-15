// Liga os elementos da página ao comportamento da aplicação.
// Recebe as dependências (envio ao backend e lista de exemplos) por
// parâmetro, o que facilita testar e trocar a implementação nas próximas etapas.

import { contarTexto, validarCodigo } from "./validacao.js";

const TITULOS = {
  sucesso: "Código recebido",
  entrada: "Revise o código-fonte",
  comunicacao: "Sem resposta do servidor",
  inesperado: "Algo deu errado",
};

export function iniciarInterface(raiz, { enviar, exemplos }) {
  const el = {
    codigo: raiz.querySelector("#codigo"),
    numeros: raiz.querySelector("#numeros-linha"),
    exemplo: raiz.querySelector("#exemplo"),
    descricao: raiz.querySelector("#descricao-exemplo"),
    analisar: raiz.querySelector("#analisar"),
    limpar: raiz.querySelector("#limpar"),
    contador: raiz.querySelector("#contador"),
    resultado: raiz.querySelector("#resultado"),
  };

  // Seletor de exemplos ---------------------------------------------------
  for (const exemplo of exemplos) {
    const opcao = raiz.ownerDocument.createElement("option");
    opcao.value = exemplo.id;
    opcao.textContent = exemplo.titulo;
    el.exemplo.append(opcao);
  }

  el.exemplo.addEventListener("change", () => {
    const escolhido = exemplos.find((e) => e.id === el.exemplo.value);
    if (!escolhido) {
      el.descricao.textContent = "";
      return;
    }
    el.codigo.value = escolhido.codigo;
    el.descricao.textContent = `Demonstra: ${escolhido.construcoes}.`;
    atualizarEditor();
    el.codigo.focus();
  });

  // Editor: numeração de linhas e contador ---------------------------------
  function atualizarEditor() {
    const { linhas, caracteres } = contarTexto(el.codigo.value);
    const total = Math.max(1, el.codigo.value.split("\n").length);
    el.numeros.textContent = Array.from({ length: total }, (_, i) => i + 1).join("\n");
    el.contador.textContent = `${linhas} ${linhas === 1 ? "linha" : "linhas"}, ${caracteres} ${
      caracteres === 1 ? "caractere" : "caracteres"
    }`;
    el.numeros.scrollTop = el.codigo.scrollTop;
  }
  el.codigo.addEventListener("input", atualizarEditor);
  el.codigo.addEventListener("scroll", () => {
    el.numeros.scrollTop = el.codigo.scrollTop;
  });

  // Tab insere quatro espaços (indentação de Python), em vez de sair do campo.
  // Esc seguido de Tab continua permitindo sair com o teclado.
  let escapou = false;
  el.codigo.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") {
      escapou = true;
      return;
    }
    if (evento.key === "Tab" && !evento.shiftKey && !escapou) {
      evento.preventDefault();
      const { selectionStart: ini, selectionEnd: fim, value } = el.codigo;
      el.codigo.value = value.slice(0, ini) + "    " + value.slice(fim);
      el.codigo.selectionStart = el.codigo.selectionEnd = ini + 4;
      atualizarEditor();
    }
    escapou = false;
  });

  el.limpar.addEventListener("click", () => {
    el.codigo.value = "";
    el.exemplo.value = "";
    el.descricao.textContent = "";
    atualizarEditor();
    mostrarVazio();
    el.codigo.focus();
  });

  // Área de resultados ------------------------------------------------------
  function mostrarVazio() {
    el.resultado.dataset.estado = "vazio";
    el.resultado.replaceChildren();
    const p = raiz.ownerDocument.createElement("p");
    p.className = "resultado-vazio";
    p.textContent =
      "Escreva um programa ou escolha um exemplo e clique em Analisar código. A resposta do servidor aparece aqui.";
    el.resultado.append(p);
  }

  function mostrar(tipo, mensagem, detalhes = []) {
    el.resultado.dataset.estado = tipo;
    el.resultado.replaceChildren();
    const doc = raiz.ownerDocument;
    const titulo = doc.createElement("h3");
    titulo.id = "resultado-titulo";
    titulo.textContent = TITULOS[tipo];
    const texto = doc.createElement("p");
    texto.id = "mensagem";
    texto.textContent = mensagem; // textContent: nunca interpreta HTML vindo da entrada
    el.resultado.append(titulo, texto);
    if (detalhes.length) {
      const lista = doc.createElement("dl");
      lista.className = "detalhes";
      for (const [termo, valor] of detalhes) {
        const dt = doc.createElement("dt");
        dt.textContent = termo;
        const dd = doc.createElement("dd");
        dd.textContent = valor;
        lista.append(dt, dd);
      }
      el.resultado.append(lista);
    }
    // Em telas estreitas o resultado fica abaixo do editor: traz para a vista.
    if (typeof el.resultado.scrollIntoView === "function") {
      el.resultado.scrollIntoView({ block: "nearest" });
    }
  }

  // Envio -----------------------------------------------------------------
  let enviando = false;
  el.analisar.addEventListener("click", async () => {
    if (enviando) return;
    const codigo = el.codigo.value;
    const validacao = validarCodigo(codigo);
    if (!validacao.valido) {
      mostrar("entrada", validacao.mensagem);
      el.codigo.focus();
      return;
    }

    enviando = true;
    el.analisar.disabled = true;
    el.analisar.textContent = "Enviando…";
    el.resultado.setAttribute("aria-busy", "true");
    try {
      const r = await enviar(codigo);
      if (r.tipo === "sucesso") {
        const est = r.dados.estatisticas || {};
        mostrar("sucesso", r.dados.mensagem, [
          ["Linhas recebidas", String(est.linhas ?? "-")],
          ["Caracteres recebidos", String(est.caracteres ?? "-")],
        ]);
      } else {
        mostrar(r.tipo, r.mensagem);
      }
    } catch {
      mostrar("inesperado", "Ocorreu um erro inesperado ao processar a solicitação. Tente novamente.");
    } finally {
      enviando = false;
      el.analisar.disabled = false;
      el.analisar.textContent = "Analisar código";
      el.resultado.removeAttribute("aria-busy");
    }
  });

  atualizarEditor();
  mostrarVazio();
  return el;
}

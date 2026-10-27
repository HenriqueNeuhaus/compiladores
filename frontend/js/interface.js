// Liga os elementos da página ao comportamento da aplicação.
// Recebe as dependências (envio ao backend e lista de exemplos) por
// parâmetro, o que facilita testar e trocar a implementação nas próximas etapas.

import { contarTexto, validarCodigo } from "./validacao.js";
import { CATEGORIAS, normalizarQuebras, resumoContagem, rotuloLexema, segmentarCodigo } from "./lexico.js";

const TITULOS = {
  lexico_ok: "Análise léxica concluída",
  lexico_erros: "Erros léxicos encontrados",
  entrada: "Revise o código-fonte",
  comunicacao: "Sem resposta do servidor",
  inesperado: "Algo deu errado",
};

const INTERVALO_REPRODUCAO_MS = 900;

export function iniciarInterface(raiz, { enviar, exemplos }) {
  const doc = raiz.ownerDocument;
  const $ = (seletor) => raiz.querySelector(seletor);
  const el = {
    codigo: $("#codigo"),
    numeros: $("#numeros-linha"),
    exemplo: $("#exemplo"),
    descricao: $("#descricao-exemplo"),
    analisar: $("#analisar"),
    limpar: $("#limpar"),
    contador: $("#contador"),
    resultado: $("#resultado"),
    analise: $("#analise-lexica"),
    desatualizado: $("#aviso-desatualizado"),
    destacado: $("#codigo-destacado"),
    tabela: $("#tabela-tokens tbody"),
    tabelaRolagem: $("#tabela-rolagem"),
    totalTokens: $("#total-tokens"),
    reprodutor: $("#reprodutor"),
    inicio: $("#passo-inicio"),
    anterior: $("#passo-anterior"),
    reproduzir: $("#passo-reproduzir"),
    proximo: $("#passo-proximo"),
    fim: $("#passo-fim"),
    barra: $("#passo-barra"),
    contadorPasso: $("#passo-contador"),
    descricaoPasso: $("#passo-descricao"),
    pilha: $("#pilha"),
  };

  const criar = (tag, propriedades = {}, ...filhos) => {
    const elemento = doc.createElement(tag);
    for (const [chave, valor] of Object.entries(propriedades)) {
      if (chave === "dataset") Object.assign(elemento.dataset, valor);
      else if (chave in elemento) elemento[chave] = valor;
      else elemento.setAttribute(chave, valor);
    }
    elemento.append(...filhos.filter((f) => f !== null && f !== undefined));
    return elemento;
  };

  // Nomes como OPERADOR_ATRIBUICAO podem quebrar depois de "_" em telas estreitas.
  const quebravel = (texto) =>
    texto.split("_").flatMap((parte, i, partes) => (i < partes.length - 1 ? [`${parte}_`, criar("wbr")] : [parte]));

  // Seletor de exemplos ---------------------------------------------------
  for (const exemplo of exemplos) {
    el.exemplo.append(criar("option", { value: exemplo.id, textContent: exemplo.titulo }));
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
    if (!el.analise.hidden) el.desatualizado.hidden = false;
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

  /** Seleciona no editor o trecho de linha:coluna a linha_final:coluna_final. */
  function selecionarNoEditor(item) {
    const linhas = el.codigo.value.split("\n");
    const deslocamento = (linha, coluna) => {
      let total = 0;
      for (let i = 0; i < linha - 1 && i < linhas.length; i++) total += linhas[i].length + 1;
      return total + Math.max(coluna - 1, 0);
    };
    const ini = deslocamento(item.linha, item.coluna);
    const fim = Math.max(ini + 1, deslocamento(item.linha_final ?? item.linha, (item.coluna_final ?? item.coluna) + 1));
    el.codigo.focus();
    el.codigo.setSelectionRange(ini, Math.min(fim, el.codigo.value.length));
  }

  el.limpar.addEventListener("click", () => {
    el.codigo.value = "";
    el.exemplo.value = "";
    el.descricao.textContent = "";
    ocultarAnalise();
    atualizarEditor();
    mostrarVazio();
    el.codigo.focus();
  });

  // Área de resultados ------------------------------------------------------
  function mostrarVazio() {
    el.resultado.dataset.estado = "vazio";
    el.resultado.replaceChildren(
      criar("p", { className: "resultado-vazio", textContent: "Como usar:" }),
      criar(
        "ol",
        { className: "como-usar" },
        criar("li", { textContent: "Escreva um programa em Python ou escolha um exemplo." }),
        criar("li", { textContent: "Clique em Analisar código." }),
        criar("li", { textContent: "Veja os tokens reconhecidos e os erros léxicos aqui." }),
        criar("li", { textContent: "Use o passo a passo, abaixo do editor, para acompanhar o scanner lendo o código." }),
      ),
    );
  }

  function mostrar(estado, mensagem, ...extras) {
    el.resultado.dataset.estado = estado;
    el.resultado.replaceChildren(
      criar("h3", { id: "resultado-titulo", textContent: TITULOS[estado] }),
      criar("p", { id: "mensagem", textContent: mensagem }), // textContent: nunca interpreta HTML
      ...extras.filter(Boolean),
    );
    // Em telas estreitas o resultado fica abaixo do editor: traz para a vista.
    if (typeof el.resultado.scrollIntoView === "function") el.resultado.scrollIntoView({ block: "nearest" });
  }

  function listaDeContagem(contagem) {
    const itens = resumoContagem(contagem);
    if (!itens.length) return null;
    return criar(
      "ul",
      { id: "contagem", className: "contagem", "aria-label": "Quantidade de tokens por categoria" },
      ...itens.map((c) =>
        criar(
          "li",
          { className: `chip ${c.classe}`, dataset: { tipo: c.tipo } },
          criar("span", { className: "chip-nome", textContent: c.nome }),
          criar("span", { className: "chip-qtd", textContent: String(c.quantidade) }),
        ),
      ),
    );
  }

  function listaDeOcorrencias(id, titulo, itens, classe, passoDe) {
    if (!itens.length) return null;
    return criar(
      "section",
      { id, className: `ocorrencias ${classe}` },
      criar("h4", { textContent: `${titulo} (${itens.length})` }),
      criar(
        "ul",
        {},
        ...itens.map((item, i) =>
          criar(
            "li",
            {},
            criar("p", { textContent: item.mensagem }),
            criar("button", {
              type: "button",
              className: "botao-texto",
              textContent: "Mostrar no código",
              "aria-label": `Mostrar no código: linha ${item.linha}, coluna ${item.coluna}`,
              onclick: () => {
                const passo = passoDe(i);
                if (passo !== undefined) irPara(passo);
                selecionarNoEditor(item);
              },
            }),
          ),
        ),
      ),
    );
  }

  // Análise léxica: visualização, tabela e passo a passo ---------------------
  let analise = null; // { passos, passoDoToken, passoDoErro, passoDoAviso }
  let atual = 0;
  let relogio = null;

  function ocultarAnalise() {
    pausar();
    analise = null;
    el.analise.hidden = true;
    el.desatualizado.hidden = true;
  }

  function mostrarAnalise(codigo, dados) {
    const passos = dados.passos ?? [];
    const passoDoToken = new Map();
    const passoDoErro = new Map();
    for (const p of passos) {
      if (p.token !== undefined && p.token !== null) passoDoToken.set(p.token, p.indice);
      if (p.erro !== undefined && p.erro !== null) passoDoErro.set(p.erro, p.indice);
    }
    analise = { passos, passoDoToken, passoDoErro, tokens: dados.tokens ?? [] };

    // Código colorido
    const { linhas, fim } = segmentarCodigo(codigo, dados);
    const segmento = (s) => {
      const atributos = { className: ["seg", s.classe, s.marcador ? `marcador marcador-${s.marcador}` : "",
        s.foraDoSubconjunto ? "fora-subconjunto" : "", s.erroSobreposto !== undefined ? "com-erro" : ""]
        .filter(Boolean).join(" ") };
      const dataset = {};
      if (s.passo !== undefined) dataset.passo = String(s.passo);
      if (s.token !== undefined) dataset.token = String(s.token);
      if (s.erro !== undefined) dataset.erro = String(s.erro);
      if (s.marcador === "nova-linha") atributos.title = "NOVA_LINHA";
      if (s.marcador === "dedent") atributos.title = "DEDENT";
      if (s.token !== undefined && !s.marcador) atributos.title = analise.tokens[s.token]?.tipo ?? "";
      if (s.erro !== undefined) atributos.title = "Erro léxico";
      const texto = s.marcador === "nova-linha" ? "↵" : s.marcador === "dedent" ? "⇤" : s.texto;
      return criar("span", { ...atributos, dataset }, texto);
    };
    const linhasHtml = linhas.map((linha) =>
      criar(
        "div",
        { className: "linha-codigo", dataset: { linha: String(linha.numero) } },
        criar("span", { className: "num", textContent: String(linha.numero), "aria-hidden": "true" }),
        criar("span", { className: "conteudo" }, ...linha.segmentos.map(segmento)),
      ),
    );
    if (fim) {
      linhasHtml.push(
        criar(
          "div",
          { className: "linha-codigo linha-fim" },
          criar("span", { className: "num", textContent: "", "aria-hidden": "true" }),
          criar("span", { className: "conteudo" }, segmento({ ...fim, texto: "FIM" })),
        ),
      );
    }
    el.destacado.replaceChildren(...linhasHtml);

    // Tabela de tokens
    el.totalTokens.textContent = String(analise.tokens.length);
    el.tabela.replaceChildren(
      ...analise.tokens.map((token, i) =>
        criar(
          "tr",
          { dataset: { token: String(i), passo: String(passoDoToken.get(i) ?? "") } },
          criar(
            "td",
            {},
            criar("button", {
              type: "button",
              className: "botao-token",
              textContent: String(i + 1),
              "aria-label": `Ir ao passo do token ${i + 1}: ${token.tipo} ${rotuloLexema(token)}`,
              onclick: () => irPara(passoDoToken.get(i)),
            }),
          ),
          criar("td", {}, criar("span", { className: `tipo ${CATEGORIAS[token.tipo]?.classe ?? ""}` }, ...quebravel(token.tipo))),
          criar("td", { className: "lexema" }, criar("code", { textContent: rotuloLexema(token) })),
          criar("td", { textContent: String(token.linha) }),
          criar("td", { textContent: String(token.coluna) }),
        ),
      ),
    );

    el.barra.max = String(Math.max(passos.length - 1, 0));
    el.analise.hidden = false;
    el.desatualizado.hidden = true;
    irPara(passos.length - 1, { rolar: false });
  }

  function rolarDentro(container, alvo) {
    if (!container || !alvo) return;
    const c = container.getBoundingClientRect();
    const a = alvo.getBoundingClientRect();
    if (a.top < c.top) container.scrollTop -= c.top - a.top + 8;
    else if (a.bottom > c.bottom) container.scrollTop += a.bottom - c.bottom + 8;
    if (a.left < c.left) container.scrollLeft -= c.left - a.left + 8;
    else if (a.right > c.right) container.scrollLeft += a.right - c.right + 8;
  }

  function irPara(indice, { rolar = true } = {}) {
    if (!analise || !analise.passos.length || indice === undefined || indice === null || indice === "") return;
    const total = analise.passos.length;
    atual = Math.min(Math.max(Number(indice), 0), total - 1);
    const passo = analise.passos[atual];

    el.barra.value = String(atual);
    el.contadorPasso.textContent = `Passo ${atual + 1} de ${total}`;
    el.descricaoPasso.textContent = passo.descricao;
    el.descricaoPasso.dataset.tipo = passo.tipo;
    el.pilha.replaceChildren(
      ...passo.pilha.map((nivel) => criar("li", { textContent: String(nivel), title: `${nivel} espaços` })),
    );

    let alvo = null;
    for (const span of el.destacado.querySelectorAll("[data-passo]")) {
      const p = Number(span.dataset.passo);
      span.classList.toggle("futuro", p > atual);
      span.classList.toggle("atual", p === atual);
      if (p === atual) alvo ??= span;
    }
    for (const linha of el.destacado.querySelectorAll(".linha-codigo")) {
      linha.classList.toggle("linha-atual", !alvo && Number(linha.dataset.linha) === passo.linha);
      if (!alvo && Number(linha.dataset.linha) === passo.linha) alvo = linha;
    }
    let linhaTabela = null;
    for (const tr of el.tabela.querySelectorAll("tr")) {
      const p = tr.dataset.passo === "" ? -1 : Number(tr.dataset.passo);
      tr.classList.toggle("futuro", p > atual);
      tr.classList.toggle("atual", p === atual);
      if (p === atual) linhaTabela = tr;
    }

    el.inicio.disabled = el.anterior.disabled = atual === 0;
    el.proximo.disabled = el.fim.disabled = atual === total - 1;
    if (rolar) {
      rolarDentro(el.destacado, alvo);
      rolarDentro(el.tabelaRolagem, linhaTabela);
    }
  }

  function pausar() {
    if (relogio) clearInterval(relogio);
    relogio = null;
    el.reproduzir.textContent = "Reproduzir";
    el.reproduzir.setAttribute("aria-pressed", "false");
  }

  function reproduzir() {
    if (!analise) return;
    if (atual >= analise.passos.length - 1) irPara(0);
    el.reproduzir.textContent = "Pausar";
    el.reproduzir.setAttribute("aria-pressed", "true");
    relogio = setInterval(() => {
      if (!analise || atual >= analise.passos.length - 1) {
        pausar();
        return;
      }
      irPara(atual + 1);
    }, INTERVALO_REPRODUCAO_MS);
  }

  el.inicio.addEventListener("click", () => { pausar(); irPara(0); });
  el.anterior.addEventListener("click", () => { pausar(); irPara(atual - 1); });
  el.proximo.addEventListener("click", () => { pausar(); irPara(atual + 1); });
  el.fim.addEventListener("click", () => { pausar(); irPara(analise ? analise.passos.length - 1 : 0); });
  el.reproduzir.addEventListener("click", () => (relogio ? pausar() : reproduzir()));
  el.barra.addEventListener("input", () => { pausar(); irPara(Number(el.barra.value)); });
  el.reprodutor.addEventListener("keydown", (evento) => {
    if (evento.target === el.barra) return; // o controle deslizante já trata as setas
    const acoes = { ArrowLeft: () => irPara(atual - 1), ArrowRight: () => irPara(atual + 1),
      Home: () => irPara(0), End: () => irPara(analise ? analise.passos.length - 1 : 0) };
    if (acoes[evento.key]) {
      evento.preventDefault();
      pausar();
      acoes[evento.key]();
    }
  });
  // Toque ou clique em um token do código leva ao passo em que ele foi lido.
  el.destacado.addEventListener("click", (evento) => {
    const span = evento.target.closest("[data-passo]");
    if (span) {
      pausar();
      irPara(Number(span.dataset.passo), { rolar: false });
    }
  });

  // Envio -----------------------------------------------------------------
  let enviando = false;
  el.analisar.addEventListener("click", async () => {
    if (enviando) return;
    const codigo = el.codigo.value;
    const validacao = validarCodigo(codigo);
    if (!validacao.valido) {
      ocultarAnalise();
      mostrar("entrada", validacao.mensagem);
      el.codigo.focus();
      return;
    }

    enviando = true;
    pausar();
    el.analisar.disabled = true;
    el.analisar.textContent = "Analisando…";
    el.resultado.setAttribute("aria-busy", "true");
    try {
      const r = await enviar(codigo);
      if (r.tipo === "sucesso" && Array.isArray(r.dados.tokens)) {
        const dados = r.dados;
        const ok = dados.sucesso === true;
        mostrar(
          ok ? "lexico_ok" : "lexico_erros",
          dados.mensagem,
          listaDeContagem(dados.contagem),
          listaDeOcorrencias("lista-erros", "Erros léxicos", dados.erros ?? [], "erros", (i) => analise?.passoDoErro.get(i)),
          listaDeOcorrencias("lista-avisos", "Avisos", dados.avisos ?? [], "avisos", (i) => {
            const aviso = dados.avisos[i];
            const indiceToken = (dados.tokens ?? []).findIndex((t) => t.linha === aviso.linha && t.coluna === aviso.coluna);
            return analise?.passoDoToken.get(indiceToken);
          }),
        );
        mostrarAnalise(normalizarQuebras(codigo), dados);
      } else if (r.tipo === "sucesso") {
        ocultarAnalise();
        mostrar("inesperado", "Ocorreu um erro inesperado ao processar a solicitação. Tente novamente.");
      } else {
        ocultarAnalise();
        mostrar(r.tipo, r.mensagem);
      }
    } catch {
      ocultarAnalise();
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

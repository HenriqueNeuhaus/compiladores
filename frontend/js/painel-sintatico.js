// Painel da análise sintática: árvore navegável (AST e árvore de derivação),
// código com o trecho do nó selecionado, detalhes do nó com a regra
// gramatical, filtro por tipo, exportação em JSON e o passo a passo da
// construção da árvore pelo parser descendente recursivo.

import { CATEGORIAS } from "./lexico.js";
import {
  achatar,
  ancestrais,
  arvoreEmTexto,
  categoriaDoNo,
  CATEGORIAS_NO,
  detalheDoNo,
  posicaoDoNo,
  rotuloDerivacao,
  tamanhoDerivacao,
  tiposPresentes,
  TIPOS_NO,
  tokensDoNo,
} from "./sintatico.js";

const INTERVALO_REPRODUCAO_MS = 700;
const EXPANDIR_TUDO_ATE = 400; // nós; acima disso a árvore abre só os primeiros níveis

export function iniciarPainelSintatico(raiz, { selecionarNoEditor, aoSelecionarNo, explicarNo } = {}) {
  const doc = raiz.ownerDocument;
  const $ = (s) => raiz.querySelector(s);
  const el = {
    painel: $("#analise-sintatica"),
    motivo: $("#sintatico-motivo"),
    conteudo: $("#sintatico-conteudo"),
    desatualizado: $("#aviso-desatualizado-sint"),
    verAst: $("#ver-ast"),
    verDerivacao: $("#ver-derivacao"),
    expandir: $("#expandir-tudo"),
    recolher: $("#recolher-tudo"),
    filtro: $("#filtro-tipo"),
    filtroInfo: $("#filtro-info"),
    exportar: $("#exportar-json"),
    arvore: $("#arvore"),
    arvoreAviso: $("#arvore-aviso"),
    textoArvore: $("#arvore-texto"),
    codigo: $("#sint-codigo"),
    detalhes: $("#no-detalhes"),
    reprodutor: $("#sint-reprodutor"),
    inicio: $("#sint-inicio"),
    anterior: $("#sint-anterior"),
    reproduzir: $("#sint-reproduzir"),
    proximo: $("#sint-proximo"),
    fim: $("#sint-fim"),
    barra: $("#sint-barra"),
    contador: $("#sint-contador"),
    descricao: $("#sint-descricao"),
    pilha: $("#sint-pilha"),
    tokens: $("#sint-tokens"),
    legenda: $("#legenda-nos"),
  };

  const criar = (tag, props = {}, ...filhos) => {
    const e = doc.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "dataset") Object.assign(e.dataset, v);
      else if (k in e) e[k] = v;
      else e.setAttribute(k, v);
    }
    e.append(...filhos.filter((f) => f !== null && f !== undefined && f !== false));
    return e;
  };

  // Legenda fixa das categorias de nó (forma + nome + cor).
  el.legenda.replaceChildren(
    ...Object.values(CATEGORIAS_NO).map((c) =>
      criar("li", {}, criar("span", { className: `no-simbolo ${c.classe}`, textContent: c.simbolo }), ` ${c.nome}`),
    ),
  );

  let estado = null; // { codigo, dados, linhasCodigo, visao, selecionado, filtro, passo }
  let relogio = null;

  // ------------------------------------------------------------------------
  // Código com destaque de trechos
  // ------------------------------------------------------------------------
  function desenharCodigo() {
    const { linhasCodigo } = estado;
    const marcas = []; // {linha, coluna, linhaF, colunaF, classe}
    const sint = estado.dados.sintatico;
    for (const erro of sint.erros || []) {
      marcas.push({ ...faixa(erro), classe: "trecho-erro" });
    }
    const passo = sint.passos[estado.passo];
    if (passo && estado.mostrandoPasso) {
      const token = estado.dados.tokens[passo.token];
      if (token && token.linha_final >= token.linha) marcas.push({ ...faixa(token), classe: "trecho-token" });
    }
    if (estado.selecionado) marcas.push({ ...estado.selecionado.faixa, classe: "trecho-selecionado" });

    el.codigo.replaceChildren(
      ...linhasCodigo.map((texto, i) => {
        const numero = i + 1;
        const conteudo = criar("span", { className: "conteudo" });
        // Cada caractere recebe as classes das marcas que o cobrem.
        const classes = Array.from({ length: Math.max(texto.length, 1) }, () => []);
        for (const m of marcas) {
          if (numero < m.linha || numero > m.linhaF) continue;
          const ini = numero === m.linha ? m.coluna : 1;
          const fim = numero === m.linhaF ? m.colunaF : texto.length;
          for (let c = ini; c <= Math.max(fim, ini); c++) if (classes[c - 1]) classes[c - 1].push(m.classe);
        }
        let atual = null;
        const pedacos = [];
        const caracteres = texto.length ? [...texto] : [""];
        caracteres.forEach((ch, c) => {
          const chave = classes[c].join(" ");
          if (atual && atual.chave === chave) atual.texto += ch;
          else pedacos.push((atual = { chave, texto: ch }));
        });
        for (const p of pedacos) {
          conteudo.append(p.chave ? criar("span", { className: p.chave, textContent: p.texto || " " }) : p.texto);
        }
        // Marca depois do último caractere (por exemplo, ':' que falta no fim da
        // linha): mostra um marcador visível no lugar do que era esperado.
        for (const m of marcas) {
          if (m.linha === numero && m.coluna > texto.length) {
            conteudo.append(criar("span", { className: `${m.classe} marca-fim`, textContent: "↵", title: "fim da linha" }));
          }
        }
        return criar(
          "div",
          { className: "linha-codigo", dataset: { linha: String(numero) } },
          criar("span", { className: "num", textContent: String(numero), "aria-hidden": "true" }),
          conteudo,
        );
      }),
    );
    const alvo = el.codigo.querySelector(".trecho-selecionado, .trecho-token");
    if (alvo) rolarDentro(el.codigo, alvo);
  }

  const faixa = (o) => ({
    linha: o.linha,
    coluna: o.coluna,
    linhaF: o.linha_final ?? o.linha,
    colunaF: Math.max(o.coluna_final ?? o.coluna, o.coluna),
  });

  function rolarDentro(container, alvo) {
    const c = container.getBoundingClientRect();
    const a = alvo.getBoundingClientRect();
    if (a.top < c.top) container.scrollTop -= c.top - a.top + 8;
    else if (a.bottom > c.bottom) container.scrollTop += a.bottom - c.bottom + 8;
  }

  // ------------------------------------------------------------------------
  // Árvore (AST ou derivação), com renderização preguiçosa dos filhos
  // ------------------------------------------------------------------------
  function arvoreAtual() {
    return estado.visao === "ast" ? estado.dados.sintatico.ast : estado.derivacao;
  }

  // A árvore de derivação recebe ids e faixas calculadas a partir das folhas.
  function prepararDerivacao(raizDerivacao) {
    if (!raizDerivacao) return null;
    let contador = 0;
    const visitar = (no) => {
      const novo = { ...no, id: contador++, filhos: [] };
      if (no.terminal) {
        novo.faixa = { linha: no.linha, coluna: no.coluna, linhaF: no.linha, colunaF: no.coluna + Math.max(no.lexema.length - 1, 0) };
      }
      for (const filho of no.filhos || []) novo.filhos.push(visitar(filho));
      const folhas = novo.filhos.map((f) => f.faixa).filter(Boolean);
      if (!novo.faixa && folhas.length) {
        const visiveis = folhas.filter((f) => f.colunaF >= f.coluna) ;
        const usar = visiveis.length ? visiveis : folhas;
        novo.faixa = { linha: usar[0].linha, coluna: usar[0].coluna, linhaF: usar.at(-1).linhaF, colunaF: usar.at(-1).colunaF };
      }
      return novo;
    };
    return visitar(raizDerivacao);
  }

  function faixaDoNo(no) {
    return estado.visao === "ast" ? faixa(no) : no.faixa;
  }

  function linhaDoNo(no, profundidade) {
    const ast = estado.visao === "ast";
    const temFilhos = no.filhos.length > 0;
    let corpo;
    if (ast) {
      const cat = categoriaDoNo(no.tipo);
      const detalhe = detalheDoNo(no);
      corpo = [
        criar("span", { className: `no-simbolo ${cat.classe}`, textContent: cat.simbolo, title: cat.nome, "aria-hidden": "true" }),
        criar("span", { className: `no-tipo ${cat.classe}`, textContent: no.tipo }),
        detalhe ? criar("code", { className: "no-detalhe", textContent: detalhe }) : null,
        no.papel ? criar("span", { className: "no-papel", textContent: no.papel }) : null,
      ];
    } else {
      const r = rotuloDerivacao(no);
      corpo = [
        criar("span", {
          className: r.terminal ? `deriv-terminal ${CATEGORIAS[no.terminal]?.classe ?? ""}` : "deriv-regra",
          textContent: r.texto,
        }),
      ];
    }
    const rotuloAcessivel = ast
      ? `${no.tipo}${detalheDoNo(no) ? " " + detalheDoNo(no) : ""}${no.papel ? ", " + no.papel : ""}, ${categoriaDoNo(no.tipo).nome}`
      : rotuloDerivacao(no).texto;
    const item = criar("li", {
      role: "treeitem",
      className: "no",
      tabIndex: -1,
      "aria-level": String(profundidade + 1),
      "aria-label": rotuloAcessivel,
      "aria-selected": "false",
      dataset: { id: String(no.id), tipo: no.tipo ?? (no.regra ? "regra" : "terminal") },
    });
    const linha = criar(
      "div",
      { className: "no-linha" },
      criar("span", {
        className: "no-alternar",
        textContent: temFilhos ? "▸" : "",
        "aria-hidden": "true",
      }),
      ...corpo,
    );
    item.append(linha);
    if (temFilhos) {
      item.setAttribute("aria-expanded", "false");
      item._no = no;
      item._profundidade = profundidade;
    }
    item._dados = no;
    return item;
  }

  function expandir(item, aberto) {
    if (!item.hasAttribute("aria-expanded")) return;
    item.setAttribute("aria-expanded", aberto ? "true" : "false");
    item.querySelector(":scope > .no-linha > .no-alternar").textContent = aberto ? "▾" : "▸";
    if (aberto && !item.querySelector(":scope > ul")) {
      const grupo = criar("ul", { role: "group" });
      for (const filho of item._no.filhos) grupo.append(linhaDoNo(filho, item._profundidade + 1));
      item.append(grupo);
      aplicarEstadoVisual(grupo);
    }
  }

  function desenharArvore() {
    const raizArvore = arvoreAtual();
    el.arvore.replaceChildren();
    el.textoArvore.textContent = "";
    el.arvore.hidden = !raizArvore;
    el.legenda.hidden = !raizArvore || estado.visao !== "ast";
    el.textoArvore.closest("details").hidden = !raizArvore || estado.visao !== "ast";
    if (!raizArvore) {
      el.arvoreAviso.hidden = false;
      el.arvoreAviso.textContent = estado.visao === "ast"
        ? "A AST não foi construída porque o código tem erro sintático. Veja os erros no resultado; o passo a passo mostra até onde o parser chegou."
        : "A árvore de derivação não foi construída porque o código tem erro sintático.";
      atualizarFiltro();
      return;
    }
    el.arvoreAviso.hidden = true;
    const total = estado.visao === "ast" ? achatar(raizArvore).length : tamanhoDerivacao(raizArvore);
    const raizItem = linhaDoNo(raizArvore, 0);
    el.arvore.append(raizItem);
    raizItem.tabIndex = 0;
    const limite = total <= EXPANDIR_TUDO_ATE ? Infinity : 3;
    abrirAte(raizItem, limite);
    if (estado.visao === "ast") el.textoArvore.textContent = arvoreEmTexto(raizArvore);
    atualizarFiltro();
    aplicarEstadoVisual(el.arvore);
  }

  function abrirAte(item, niveis) {
    if (niveis <= 0) return;
    expandir(item, true);
    const grupo = item.querySelector(":scope > ul");
    if (grupo) for (const filho of grupo.children) abrirAte(filho, niveis - 1);
  }

  function itensVisiveis() {
    return [...el.arvore.querySelectorAll('[role="treeitem"]')].filter(
      (i) => !i.parentElement.closest('[aria-expanded="false"]'),
    );
  }

  function itemPorId(id) {
    return el.arvore.querySelector(`[role="treeitem"][data-id="${id}"]`);
  }

  // Abre os ancestrais de um nó para que ele fique visível.
  function revelar(id) {
    const raizArvore = arvoreAtual();
    if (!raizArvore) return null;
    const caminho = estado.visao === "ast" ? ancestrais(raizArvore, id).reverse() : caminhoDerivacao(raizArvore, id);
    for (const idAncestral of caminho) {
      const item = itemPorId(idAncestral);
      if (item) expandir(item, true);
    }
    return itemPorId(id);
  }

  function caminhoDerivacao(raizArvore, id) {
    const caminho = [];
    const procurar = (no) => {
      if (no.id === id) return true;
      for (const f of no.filhos) if (procurar(f)) { caminho.unshift(no.id); return true; }
      return false;
    };
    procurar(raizArvore);
    return caminho;
  }

  function selecionar(item, { focar = true } = {}) {
    if (!item) return;
    for (const s of el.arvore.querySelectorAll('[aria-selected="true"]')) s.setAttribute("aria-selected", "false");
    for (const s of el.arvore.querySelectorAll('[role="treeitem"][tabindex="0"]')) s.tabIndex = -1;
    item.setAttribute("aria-selected", "true");
    item.tabIndex = 0;
    if (focar) item.focus({ preventScroll: true });
    rolarDentro(el.arvore, item.querySelector(".no-linha"));
    const no = item._dados;
    estado.selecionado = { id: no.id, faixa: faixaDoNo(no), no };
    desenharCodigo();
    mostrarDetalhes(no);
    if (aoSelecionarNo) aoSelecionarNo(estado.visao === "ast" ? no : null);
  }

  function mostrarDetalhes(no) {
    if (estado.visao !== "ast") {
      const r = rotuloDerivacao(no);
      const regra = no.regra ? estado.dados.sintatico.gramatica[no.regra] : null;
      el.detalhes.replaceChildren(
        criar("h4", { textContent: r.terminal ? `Terminal ${r.texto}` : `Regra ${no.regra}` }),
        regra ? criar("p", {}, "Produção: ", criar("code", { className: "producao", textContent: regra })) : null,
        criar("p", {
          textContent: r.terminal
            ? "Folha da árvore de derivação: um token consumido pelo parser."
            : `Nó interno: o parser aplicou esta regra e ela gerou ${no.filhos.length} filho(s).`,
        }),
      );
      return;
    }
    const info = TIPOS_NO[no.tipo];
    const cat = categoriaDoNo(no.tipo);
    const tokens = tokensDoNo(no, estado.dados.tokens);
    const atributos = Object.entries(no.atributos || {});
    el.detalhes.replaceChildren(
      criar("h4", {}, criar("span", { className: `no-simbolo ${cat.classe}`, textContent: cat.simbolo, "aria-hidden": "true" }), ` ${no.tipo}`),
      criar("p", { className: "no-descricao", textContent: `${info ? info.descricao : ""} (${cat.nome}).` }),
      criar(
        "dl",
        { className: "no-propriedades" },
        criar("dt", { textContent: "Regra" }),
        criar("dd", {}, criar("code", { className: "producao", textContent: estado.dados.sintatico.gramatica[no.regra] ?? no.regra })),
        no.papel ? criar("dt", { textContent: "Papel no nó pai" }) : null,
        no.papel ? criar("dd", { textContent: no.papel }) : null,
        criar("dt", { textContent: "Posição" }),
        criar("dd", { textContent: posicaoDoNo(no) }),
        atributos.length ? criar("dt", { textContent: "Atributos" }) : null,
        atributos.length ? criar("dd", { textContent: atributos.map(([k, v]) => `${k} = ${v}`).join("; ") }) : null,
        criar("dt", { textContent: "Filhos" }),
        criar("dd", { textContent: no.filhos.length ? no.filhos.map((f) => f.tipo).join(", ") : "nenhum (folha)" }),
      ),
      criar("p", { className: "tokens-titulo", textContent: `Tokens que formam este nó (${tokens.length}):` }),
      criar(
        "ul",
        { className: "tokens-do-no", "aria-label": "Tokens que formam este nó" },
        ...tokens.slice(0, 60).map(({ token }) =>
          criar("li", { className: `tipo ${CATEGORIAS[token.tipo]?.classe ?? ""}`, title: token.tipo, textContent: token.tipo === "NOVA_LINHA" ? "↵" : token.tipo === "INDENT" ? "INDENT" : token.lexema }),
        ),
        tokens.length > 60 ? criar("li", { textContent: `… e mais ${tokens.length - 60}` }) : null,
      ),
      criar("p", {
        className: "comparacao-tokens",
        textContent:
          tokens.length > 1
            ? `A sequência de ${tokens.length} tokens virou ${achatar(no).length} nó(s) na AST: parênteses, ':' e fins de linha não precisam de nó, porque a própria forma da árvore já guarda essa informação.`
            : "Este nó corresponde diretamente a um token.",
      }),
      criar(
        "div",
        { className: "acoes-no" },
        criar("button", {
          type: "button",
          className: "botao-texto",
          textContent: "Selecionar no editor",
          onclick: () => selecionarNoEditor && selecionarNoEditor(no),
        }),
        explicarNo
          ? criar("button", {
              type: "button",
              className: "botao-texto botao-ia",
              id: "explicar-no",
              textContent: "Explicar este nó com IA",
              onclick: () => explicarNo(no),
            })
          : null,
      ),
    );
  }

  // Teclado na árvore (padrão WAI-ARIA para tree view).
  el.arvore.addEventListener("keydown", (evento) => {
    const item = evento.target.closest('[role="treeitem"]');
    if (!item) return;
    const visiveis = itensVisiveis();
    const i = visiveis.indexOf(item);
    const acoes = {
      ArrowDown: () => selecionar(visiveis[Math.min(i + 1, visiveis.length - 1)]),
      ArrowUp: () => selecionar(visiveis[Math.max(i - 1, 0)]),
      Home: () => selecionar(visiveis[0]),
      End: () => selecionar(visiveis.at(-1)),
      ArrowRight: () => {
        if (item.getAttribute("aria-expanded") === "false") expandir(item, true);
        else if (item.getAttribute("aria-expanded") === "true") selecionar(item.querySelector(":scope > ul > li"));
      },
      ArrowLeft: () => {
        if (item.getAttribute("aria-expanded") === "true") expandir(item, false);
        else selecionar(item.parentElement.closest('[role="treeitem"]'));
      },
      Enter: () => selecionar(item),
      " ": () => selecionar(item),
    };
    if (acoes[evento.key]) {
      evento.preventDefault();
      acoes[evento.key]();
    }
  });

  el.arvore.addEventListener("click", (evento) => {
    const item = evento.target.closest('[role="treeitem"]');
    if (!item) return;
    if (evento.target.closest(".no-alternar") && item.hasAttribute("aria-expanded")) {
      expandir(item, item.getAttribute("aria-expanded") !== "true");
      return;
    }
    if (item.hasAttribute("aria-expanded") && item.getAttribute("aria-selected") === "true") {
      expandir(item, item.getAttribute("aria-expanded") !== "true");
    }
    selecionar(item);
  });

  el.expandir.addEventListener("click", () => {
    const raizItem = el.arvore.querySelector('[role="treeitem"]');
    if (raizItem) abrirAte(raizItem, Infinity);
  });
  el.recolher.addEventListener("click", () => {
    for (const item of el.arvore.querySelectorAll('[aria-expanded="true"]')) expandir(item, false);
    const raizItem = el.arvore.querySelector('[role="treeitem"]');
    if (raizItem) expandir(raizItem, true);
  });

  function trocarVisao(visao) {
    estado.visao = visao;
    el.verAst.setAttribute("aria-pressed", String(visao === "ast"));
    el.verDerivacao.setAttribute("aria-pressed", String(visao === "derivacao"));
    estado.selecionado = null;
    el.filtro.disabled = visao !== "ast";
    estado.filtro = "";
    el.detalhes.replaceChildren(
      criar("p", {
        className: "dica",
        textContent:
          visao === "ast"
            ? "Selecione um nó da árvore para ver a regra gramatical, os tokens que o formam e o trecho do código."
            : "A árvore de derivação mostra todas as regras aplicadas (nós internos) e todos os tokens consumidos (folhas). Compare o tamanho dela com o da AST.",
      }),
    );
    desenharArvore();
    desenharCodigo();
  }
  el.verAst.addEventListener("click", () => trocarVisao("ast"));
  el.verDerivacao.addEventListener("click", () => trocarVisao("derivacao"));

  // Filtro por tipo: destaca os nós do tipo escolhido e abre os caminhos até eles.
  function atualizarFiltro() {
    const ast = estado.dados.sintatico.ast;
    const tipos = ast ? tiposPresentes(ast) : [];
    el.filtro.replaceChildren(
      criar("option", { value: "", textContent: "Todos os tipos" }),
      ...tipos.map((t) => criar("option", { value: t.tipo, textContent: `${t.tipo} (${t.quantidade})` })),
    );
    el.filtro.value = estado.filtro || "";
    el.filtro.disabled = !ast || estado.visao !== "ast";
    el.filtroInfo.textContent = "";
  }
  el.filtro.addEventListener("change", () => {
    estado.filtro = el.filtro.value;
    const ast = estado.dados.sintatico.ast;
    if (estado.filtro && ast) {
      const ids = achatar(ast).filter(({ no }) => no.tipo === estado.filtro).map(({ no }) => no.id);
      for (const id of ids) revelar(id);
      el.filtroInfo.textContent = `${ids.length} nó(s) ${estado.filtro} destacado(s).`;
    } else {
      el.filtroInfo.textContent = "";
    }
    aplicarEstadoVisual(el.arvore);
  });

  // Exportação em JSON
  el.exportar.addEventListener("click", () => {
    const sint = estado.dados.sintatico;
    const conteudo = estado.visao === "ast"
      ? { codigo: estado.codigo, ast: sint.ast, erros: sint.erros }
      : { codigo: estado.codigo, arvore_derivacao: sint.derivacao, erros: sint.erros };
    const blob = new Blob([JSON.stringify(conteudo, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = criar("a", { href: url, download: estado.visao === "ast" ? "ast.json" : "arvore-derivacao.json" });
    doc.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  // ------------------------------------------------------------------------
  // Passo a passo da construção
  // ------------------------------------------------------------------------
  function aplicarEstadoVisual(container) {
    if (!estado) return;
    const passoAtual = estado.passo;
    const construindo = estado.mostrandoPasso && estado.visao === "ast";
    for (const item of container.querySelectorAll('[role="treeitem"]')) {
      const no = item._dados;
      const linha = item.querySelector(":scope > .no-linha");
      const futuro = construindo && no.passo > passoAtual;
      linha.classList.toggle("futuro", futuro);
      linha.classList.toggle("atual", construindo && no.passo === passoAtual);
      const filtrado = estado.filtro && estado.visao === "ast";
      linha.classList.toggle("filtrado", Boolean(filtrado && no.tipo === estado.filtro));
      linha.classList.toggle("fora-do-filtro", Boolean(filtrado && no.tipo !== estado.filtro));
    }
  }

  function irPara(indice) {
    const passos = estado.dados.sintatico.passos;
    if (!passos.length || indice === undefined || indice === null || Number.isNaN(indice)) return;
    estado.passo = Math.min(Math.max(Number(indice), 0), passos.length - 1);
    estado.mostrandoPasso = estado.passo < passos.length - 1;
    const passo = passos[estado.passo];
    el.barra.value = String(estado.passo);
    el.contador.textContent = `Passo ${estado.passo + 1} de ${passos.length}`;
    el.descricao.textContent = passo.descricao;
    el.descricao.dataset.tipo = passo.tipo;
    el.pilha.replaceChildren(...passo.pilha.map((regra) => criar("li", { textContent: regra, title: estado.dados.sintatico.gramatica[regra] })));
    // Fita de tokens: os já consumidos, o atual e os que faltam.
    for (const chip of el.tokens.children) {
      const i = Number(chip.dataset.indice);
      chip.classList.toggle("consumido", i < passo.token);
      chip.classList.toggle("atual", i === passo.token);
    }
    const atualChip = el.tokens.querySelector(".atual");
    if (atualChip) {
      const c = el.tokens.getBoundingClientRect();
      const a = atualChip.getBoundingClientRect();
      if (a.left < c.left || a.right > c.right) el.tokens.scrollLeft += a.left - c.left - c.width / 2;
    }
    if (passo.tipo === "construir" && estado.visao === "ast" && estado.dados.sintatico.ast) {
      const no = achatar(estado.dados.sintatico.ast).find(({ no: n }) => n.passo === estado.passo);
      if (no) revelar(no.no.id);
    }
    aplicarEstadoVisual(el.arvore);
    desenharCodigo();
    el.inicio.disabled = el.anterior.disabled = estado.passo === 0;
    el.proximo.disabled = el.fim.disabled = estado.passo === passos.length - 1;
  }

  function pausar() {
    if (relogio) clearInterval(relogio);
    relogio = null;
    el.reproduzir.textContent = "Reproduzir";
    el.reproduzir.setAttribute("aria-pressed", "false");
  }

  function reproduzir() {
    const total = estado.dados.sintatico.passos.length;
    if (estado.passo >= total - 1) irPara(0);
    el.reproduzir.textContent = "Pausar";
    el.reproduzir.setAttribute("aria-pressed", "true");
    relogio = setInterval(() => {
      if (!estado || estado.passo >= estado.dados.sintatico.passos.length - 1) return pausar();
      irPara(estado.passo + 1);
    }, INTERVALO_REPRODUCAO_MS);
  }

  el.inicio.addEventListener("click", () => { pausar(); irPara(0); });
  el.anterior.addEventListener("click", () => { pausar(); irPara(estado.passo - 1); });
  el.proximo.addEventListener("click", () => { pausar(); irPara(estado.passo + 1); });
  el.fim.addEventListener("click", () => { pausar(); irPara(estado.dados.sintatico.passos.length - 1); });
  el.reproduzir.addEventListener("click", () => (relogio ? pausar() : reproduzir()));
  el.barra.addEventListener("input", () => { pausar(); irPara(Number(el.barra.value)); });
  el.reprodutor.addEventListener("keydown", (evento) => {
    if (evento.target === el.barra) return;
    const total = estado.dados.sintatico.passos.length;
    const acoes = { ArrowLeft: estado.passo - 1, ArrowRight: estado.passo + 1, Home: 0, End: total - 1 };
    if (evento.key in acoes) {
      evento.preventDefault();
      pausar();
      irPara(acoes[evento.key]);
    }
  });

  // ------------------------------------------------------------------------
  // API do painel
  // ------------------------------------------------------------------------
  function mostrar(codigo, dados) {
    pausar();
    const sint = dados.sintatico;
    el.painel.hidden = false;
    el.desatualizado.hidden = true;
    if (!sint || !sint.executado) {
      el.motivo.hidden = false;
      el.motivo.textContent = sint ? sint.motivo : "A análise sintática não está disponível.";
      el.conteudo.hidden = true;
      estado = null;
      return;
    }
    el.motivo.hidden = true;
    el.conteudo.hidden = false;
    estado = {
      codigo,
      dados,
      linhasCodigo: codigo.split("\n"),
      visao: "ast",
      selecionado: null,
      filtro: "",
      passo: Math.max(sint.passos.length - 1, 0),
      mostrandoPasso: false,
      derivacao: prepararDerivacao(sint.derivacao),
    };
    el.tokens.replaceChildren(
      ...dados.tokens.map((t, i) =>
        criar("li", {
          className: `tipo ${CATEGORIAS[t.tipo]?.classe ?? ""}`,
          dataset: { indice: String(i) },
          title: `${t.tipo} (linha ${t.linha}, coluna ${t.coluna})`,
          textContent: t.tipo === "NOVA_LINHA" ? "↵" : ["INDENT", "DEDENT"].includes(t.tipo) ? t.tipo : t.tipo === "FIM_DE_ARQUIVO" ? "FIM" : t.lexema,
        }),
      ),
    );
    el.barra.max = String(Math.max(sint.passos.length - 1, 0));
    el.exportar.disabled = !sint.ast;
    trocarVisao("ast");
    irPara(estado.passo);
    if (sint.passos_truncados) {
      el.descricao.textContent += " (O programa é grande: o passo a passo foi limitado aos primeiros passos.)";
    }
  }

  function ocultar() {
    pausar();
    estado = null;
    el.painel.hidden = true;
  }

  function marcarDesatualizado() {
    if (!el.painel.hidden) el.desatualizado.hidden = false;
  }

  /** Seleciona o nó da AST com o id dado (usado por testes e pelos erros). */
  function selecionarNo(id) {
    if (!estado) return;
    if (estado.visao !== "ast") trocarVisao("ast");
    selecionar(revelar(id));
  }

  function irParaPasso(indice) {
    if (!estado) return;
    pausar();
    irPara(indice);
    el.reprodutor.scrollIntoView?.({ block: "nearest" });
  }

  return { mostrar, ocultar, marcarDesatualizado, selecionarNo, irParaPasso, noSelecionado: () => estado?.selecionado?.no ?? null };
}

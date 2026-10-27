// Funções de apresentação da análise léxica, sem acesso ao DOM.
// Transformam a resposta do backend em estruturas prontas para exibir:
// nomes amigáveis das categorias, lexemas legíveis, contagem e o código
// dividido em segmentos coloridos por categoria.

export const CATEGORIAS = {
  PALAVRA_RESERVADA: { nome: "Palavra reservada", classe: "cat-palavra", exemplo: "if, while, True" },
  IDENTIFICADOR: { nome: "Identificador", classe: "cat-identificador", exemplo: "nota, print, _x1" },
  LITERAL_INTEIRO: { nome: "Literal inteiro", classe: "cat-numero", exemplo: "0, 42" },
  LITERAL_REAL: { nome: "Literal real", classe: "cat-numero", exemplo: "3.14" },
  LITERAL_STRING: { nome: "Literal string", classe: "cat-string", exemplo: '"Aprovado"' },
  OPERADOR_ARITMETICO: { nome: "Operador aritmético", classe: "cat-operador", exemplo: "+ - * / %" },
  OPERADOR_RELACIONAL: { nome: "Operador relacional", classe: "cat-operador", exemplo: "== != < <= > >=" },
  OPERADOR_ATRIBUICAO: { nome: "Operador de atribuição", classe: "cat-operador", exemplo: "=" },
  DELIMITADOR: { nome: "Delimitador", classe: "cat-delimitador", exemplo: "( ) : ," },
  NOVA_LINHA: { nome: "Nova linha", classe: "cat-estrutura", exemplo: "fim de instrução" },
  INDENT: { nome: "Indentação (INDENT)", classe: "cat-indent", exemplo: "início de bloco" },
  DEDENT: { nome: "Fim de bloco (DEDENT)", classe: "cat-estrutura", exemplo: "fim de bloco" },
  FIM_DE_ARQUIVO: { nome: "Fim do arquivo", classe: "cat-estrutura", exemplo: "fim do código" },
};

const SEM_LARGURA = new Set(["NOVA_LINHA", "DEDENT", "FIM_DE_ARQUIVO"]);

/** Texto legível para o lexema de um token (os de estrutura não têm texto visível). */
export function rotuloLexema(token) {
  switch (token.tipo) {
    case "NOVA_LINHA":
      return token.lexema === "" ? "↵ (implícita)" : "↵";
    case "INDENT": {
      const n = token.lexema.length;
      return `${n} ${n === 1 ? "espaço" : "espaços"}`;
    }
    case "DEDENT":
      return "(sem texto)";
    case "FIM_DE_ARQUIVO":
      return "(fim)";
    default:
      return token.lexema;
  }
}

/** Categorias com pelo menos um token, na ordem de CATEGORIAS. */
export function resumoContagem(contagem) {
  return Object.keys(CATEGORIAS)
    .filter((tipo) => (contagem?.[tipo] ?? 0) > 0)
    .map((tipo) => ({ tipo, nome: CATEGORIAS[tipo].nome, classe: CATEGORIAS[tipo].classe, quantidade: contagem[tipo] }));
}

/** Mesma normalização de quebras de linha feita pelo backend. */
export function normalizarQuebras(codigo) {
  return codigo.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

/**
 * Divide o código em linhas de segmentos para a visualização colorida.
 * Cada segmento traz o texto, a classe CSS e as referências ao token,
 * erro ou comentário de origem, além do índice do passo que o produziu.
 * NOVA_LINHA e DEDENT viram marcadores sem texto do código.
 */
export function segmentarCodigo(codigo, resultado) {
  const linhas = normalizarQuebras(codigo).split("\n");
  const { tokens = [], erros = [], comentarios = [], passos = [] } = resultado;

  const passoDoToken = new Map();
  const passoDoErro = new Map();
  const passosIgnorados = [];
  for (const passo of passos) {
    if (passo.token !== undefined && passo.token !== null) passoDoToken.set(passo.token, passo.indice);
    if (passo.erro !== undefined && passo.erro !== null) passoDoErro.set(passo.erro, passo.indice);
    if (passo.tipo === "ignorado") passosIgnorados.push(passo);
  }

  // Dono de cada caractere: [linha][coluna-1] -> descritor do segmento
  const donos = linhas.map((texto) => new Array(texto.length).fill(null));
  const marcadores = linhas.map(() => new Map()); // coluna (0-based) -> lista de marcadores
  let fim = null;

  const marcar = (linha, ini, fimCol, dono) => {
    const linhaDonos = donos[linha - 1];
    if (!linhaDonos) return;
    for (let c = ini; c <= fimCol && c - 1 < linhaDonos.length; c++) {
      if (c >= 1 && linhaDonos[c - 1] === null) linhaDonos[c - 1] = dono;
    }
  };

  tokens.forEach((token, i) => {
    const passo = passoDoToken.get(i);
    if (token.tipo === "FIM_DE_ARQUIVO") {
      fim = { marcador: "fim", token: i, passo, classe: CATEGORIAS.FIM_DE_ARQUIVO.classe };
      return;
    }
    if (SEM_LARGURA.has(token.tipo)) {
      const mapa = marcadores[token.linha - 1];
      if (!mapa) return;
      const chave = token.coluna - 1;
      if (!mapa.has(chave)) mapa.set(chave, []);
      mapa.get(chave).push({
        marcador: token.tipo === "NOVA_LINHA" ? "nova-linha" : "dedent",
        token: i,
        passo,
        classe: CATEGORIAS[token.tipo].classe,
      });
      return;
    }
    marcar(token.linha, token.coluna, token.coluna_final, {
      token: i,
      passo,
      classe: CATEGORIAS[token.tipo]?.classe ?? "",
      foraDoSubconjunto: Boolean(token.fora_do_subconjunto),
    });
  });

  comentarios.forEach((comentario, i) => {
    const passo = passosIgnorados.find((p) => p.linha === comentario.linha && p.coluna === comentario.coluna)?.indice;
    marcar(comentario.linha, comentario.coluna, comentario.coluna_final, { comentario: i, passo, classe: "cat-comentario" });
  });

  // Erros ocupam os caracteres livres. Se todos os caracteres do erro já
  // pertencem a tokens (por exemplo, parêntese não fechado), os tokens
  // recebem a referência ao erro.
  erros.forEach((erro, j) => {
    const passo = passoDoErro.get(j);
    for (let linha = erro.linha; linha <= erro.linha_final; linha++) {
      const texto = linhas[linha - 1];
      if (texto === undefined) continue;
      const ini = linha === erro.linha ? erro.coluna : 1;
      const fimCol = linha === erro.linha_final ? erro.coluna_final : texto.length;
      let livre = false;
      for (let c = ini; c <= fimCol && c <= texto.length; c++) if (donos[linha - 1][c - 1] === null) livre = true;
      if (livre) {
        marcar(linha, ini, fimCol, { erro: j, passo, classe: "cat-erro" });
      } else {
        for (let c = ini; c <= fimCol && c <= texto.length; c++) {
          const dono = donos[linha - 1][c - 1];
          if (dono && dono.erro === undefined) dono.erroSobreposto = j;
        }
      }
    }
  });

  const resultadoLinhas = linhas.map((texto, l) => {
    const segmentos = [];
    let atual = null;
    const fechar = () => {
      if (atual) segmentos.push(atual);
      atual = null;
    };
    for (let c = 0; c <= texto.length; c++) {
      const lista = marcadores[l].get(c);
      if (lista) {
        fechar();
        for (const m of lista) segmentos.push({ texto: "", ...m });
      }
      if (c === texto.length) break;
      const dono = donos[l][c];
      if (atual && atual.dono === dono) {
        atual.texto += texto[c];
      } else {
        fechar();
        atual = { texto: texto[c], dono };
      }
    }
    fechar();
    // Marcadores além do fim da linha (não deveriam existir, mas não se perdem)
    for (const [c, lista] of marcadores[l]) {
      if (c > texto.length) for (const m of lista) segmentos.push({ texto: "", ...m });
    }
    return {
      numero: l + 1,
      segmentos: segmentos.map(({ dono, ...resto }) => (dono ? { ...resto, ...dono } : resto)),
    };
  });

  return { linhas: resultadoLinhas, fim };
}

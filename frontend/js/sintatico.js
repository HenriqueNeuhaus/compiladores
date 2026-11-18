// Funções de apresentação da análise sintática, sem acesso ao DOM.
// Transformam a AST, a árvore de derivação e os erros devolvidos pelo backend
// em rótulos, categorias e listas prontas para a interface.

// Cada tipo de nó tem uma categoria. A categoria define a cor e também um
// símbolo e um nome escritos, para que a informação não dependa só da cor.
export const CATEGORIAS_NO = {
  estrutura: { nome: "estrutura", simbolo: "▣", classe: "no-estrutura" },
  instrucao: { nome: "instrução", simbolo: "◆", classe: "no-instrucao" },
  controle: { nome: "controle de fluxo", simbolo: "⑂", classe: "no-controle" },
  operacao: { nome: "operação", simbolo: "●", classe: "no-operacao" },
  valor: { nome: "valor", simbolo: "■", classe: "no-valor" },
  nome: { nome: "nome", simbolo: "▲", classe: "no-nome" },
};

export const TIPOS_NO = {
  PROGRAMA: { categoria: "estrutura", descricao: "o programa inteiro" },
  BLOCO: { categoria: "estrutura", descricao: "sequência de instruções de um bloco indentado" },
  ATRIBUICAO: { categoria: "instrucao", descricao: "guarda o valor de uma expressão em uma variável" },
  CHAMADA_FUNCAO: { categoria: "instrucao", descricao: "chamada de função com seus argumentos" },
  CONDICIONAL: { categoria: "controle", descricao: "if com elif e else opcionais" },
  SENAO_SE: { categoria: "controle", descricao: "ramo elif: outra condição e seu bloco" },
  REPETICAO: { categoria: "controle", descricao: "laço while: condição e corpo" },
  COMPARACAO: { categoria: "operacao", descricao: "comparação entre dois valores" },
  ADICAO: { categoria: "operacao", descricao: "soma dos dois filhos" },
  SUBTRACAO: { categoria: "operacao", descricao: "filho da esquerda menos o da direita" },
  MULTIPLICACAO: { categoria: "operacao", descricao: "produto dos dois filhos" },
  DIVISAO: { categoria: "operacao", descricao: "filho da esquerda dividido pelo da direita" },
  RESTO: { categoria: "operacao", descricao: "resto da divisão" },
  OPERACAO_UNARIA: { categoria: "operacao", descricao: "sinal + ou - aplicado a um valor" },
  IDENTIFICADOR: { categoria: "nome", descricao: "nome de variável ou função" },
  LITERAL_INTEIRO: { categoria: "valor", descricao: "número inteiro escrito no código" },
  LITERAL_REAL: { categoria: "valor", descricao: "número real escrito no código" },
  LITERAL_STRING: { categoria: "valor", descricao: "texto entre aspas" },
  LITERAL_LOGICO: { categoria: "valor", descricao: "valor lógico True ou False" },
};

/** Categoria (cor, símbolo e nome) de um tipo de nó. */
export function categoriaDoNo(tipo) {
  const info = TIPOS_NO[tipo];
  return CATEGORIAS_NO[info ? info.categoria : "estrutura"];
}

/** Detalhe curto que acompanha o tipo do nó na árvore. */
export function detalheDoNo(no) {
  const a = no.atributos || {};
  switch (no.tipo) {
    case "IDENTIFICADOR":
    case "ATRIBUICAO":
      return a.nome;
    case "CHAMADA_FUNCAO":
      return `${a.nome}(${a.argumentos === 1 ? "1 argumento" : `${a.argumentos} argumentos`})`;
    case "LITERAL_INTEIRO":
    case "LITERAL_REAL":
    case "LITERAL_STRING":
    case "LITERAL_LOGICO":
      return a.valor;
    case "COMPARACAO":
    case "ADICAO":
    case "SUBTRACAO":
    case "MULTIPLICACAO":
    case "DIVISAO":
    case "RESTO":
    case "OPERACAO_UNARIA":
      return a.operador;
    case "BLOCO":
    case "PROGRAMA":
      return a.instrucoes === 1 ? "1 instrução" : `${a.instrucoes} instruções`;
    default:
      return "";
  }
}

/** Posição legível: "linha 2, colunas 4–12" ou "linhas 2–5". */
export function posicaoDoNo(no) {
  if (no.linha === no.linha_final) {
    return no.coluna === no.coluna_final || no.coluna_final < no.coluna
      ? `linha ${no.linha}, coluna ${no.coluna}`
      : `linha ${no.linha}, colunas ${no.coluna}–${no.coluna_final}`;
  }
  return `linhas ${no.linha}–${no.linha_final}`;
}

/** Lista em pré-ordem: [{no, profundidade, pai}], na ordem dos ids. */
export function achatar(raiz) {
  const lista = [];
  const visitar = (no, profundidade, pai) => {
    lista.push({ no, profundidade, pai });
    for (const filho of no.filhos) visitar(filho, profundidade + 1, no);
  };
  if (raiz) visitar(raiz, 0, null);
  return lista;
}

/** Ids dos ancestrais de um nó (do pai até a raiz). */
export function ancestrais(raiz, id) {
  const caminho = [];
  const procurar = (no) => {
    if (no.id === id) return true;
    for (const filho of no.filhos) {
      if (procurar(filho)) {
        caminho.push(no.id);
        return true;
      }
    }
    return false;
  };
  if (raiz) procurar(raiz);
  return caminho;
}

/** Tipos de nó presentes na árvore, com a quantidade, em ordem de aparição. */
export function tiposPresentes(raiz) {
  const contagem = new Map();
  for (const { no } of achatar(raiz)) contagem.set(no.tipo, (contagem.get(no.tipo) || 0) + 1);
  return [...contagem].map(([tipo, quantidade]) => ({ tipo, quantidade }));
}

const antes = (l1, c1, l2, c2) => l1 < l2 || (l1 === l2 && c1 <= c2);

/** Tokens contidos no trecho do nó (exceto os de estrutura sem texto). */
export function tokensDoNo(no, tokens) {
  return tokens
    .map((token, indice) => ({ token, indice }))
    .filter(({ token }) =>
      !["DEDENT", "FIM_DE_ARQUIVO"].includes(token.tipo) &&
      antes(no.linha, no.coluna, token.linha, token.coluna) &&
      antes(token.linha_final, token.coluna_final, no.linha_final, no.coluna_final) &&
      !(token.tipo === "NOVA_LINHA" && token.lexema === ""));
}

/** Ids dos nós já construídos até o passo indicado (inclusive). */
export function nosConstruidosAte(raiz, passo) {
  const ids = new Set();
  for (const { no } of achatar(raiz)) if (no.passo >= 0 && no.passo <= passo) ids.add(no.id);
  return ids;
}

/** Texto da árvore indentada, útil para leitores de tela e para copiar. */
export function arvoreEmTexto(raiz) {
  const linhas = [];
  const visitar = (no, prefixo, ultimo, raizDaArvore) => {
    const detalhe = detalheDoNo(no);
    const papel = no.papel ? ` (${no.papel})` : "";
    const rotulo = `${no.tipo}${detalhe ? ": " + detalhe : ""}${papel}`;
    linhas.push(raizDaArvore ? rotulo : `${prefixo}${ultimo ? "└── " : "├── "}${rotulo}`);
    const proximo = raizDaArvore ? "" : prefixo + (ultimo ? "    " : "│   ");
    no.filhos.forEach((f, i) => visitar(f, proximo, i === no.filhos.length - 1, false));
  };
  if (raiz) visitar(raiz, "", true, true);
  return linhas.join("\n");
}

/** Rótulo de um nó da árvore de derivação (regra ou token terminal). */
export function rotuloDerivacao(no) {
  if (no.regra) return { texto: no.regra, terminal: false };
  const visivel = { NOVA_LINHA: "↵", INDENT: "INDENT", DEDENT: "DEDENT", FIM_DE_ARQUIVO: "FIM" };
  const lexema = visivel[no.terminal] ?? no.lexema;
  return { texto: `${no.terminal} ${lexema === no.terminal ? "" : lexema}`.trim(), terminal: true };
}

/** Quantidade de nós de uma árvore de derivação e da AST, para comparar. */
export function tamanhoDerivacao(no) {
  if (!no) return 0;
  return 1 + (no.filhos || []).reduce((s, f) => s + tamanhoDerivacao(f), 0);
}

/** "esperado" do erro em texto: ':' , 'expressão', 'recuo (INDENT)'... */
export function textoEsperado(esperado) {
  const nomes = {
    expressao: "uma expressão",
    NOVA_LINHA: "fim da linha",
    INDENT: "um recuo (INDENT)",
    IDENTIFICADOR: "um nome",
    LITERAL_INTEIRO: "um número inteiro",
    LITERAL_REAL: "um número real",
    LITERAL_STRING: "uma string",
  };
  return esperado.map((e) => nomes[e] ?? `'${e}'`).join(", ");
}

export function textoEncontrado(erro) {
  const nomes = {
    NOVA_LINHA: "fim da linha",
    FIM_DE_ARQUIVO: "fim do código",
    INDENT: "recuo (INDENT)",
    DEDENT: "fim de bloco (DEDENT)",
  };
  return nomes[erro.encontrado] ?? `'${erro.encontrado}'`;
}

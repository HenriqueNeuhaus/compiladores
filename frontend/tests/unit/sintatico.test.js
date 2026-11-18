import { test } from "node:test";
import assert from "node:assert/strict";
import {
  achatar,
  ancestrais,
  arvoreEmTexto,
  categoriaDoNo,
  CATEGORIAS_NO,
  detalheDoNo,
  nosConstruidosAte,
  posicaoDoNo,
  rotuloDerivacao,
  tamanhoDerivacao,
  textoEncontrado,
  textoEsperado,
  tiposPresentes,
  TIPOS_NO,
  tokensDoNo,
} from "../../js/sintatico.js";

const no = (id, tipo, atributos, filhos = [], pos = {}, extra = {}) => ({
  id, tipo, atributos, filhos, papel: null, regra: "x", passo: id + 10,
  linha: 1, coluna: 1, linha_final: 1, coluna_final: 1, ...pos, ...extra,
});

// AST de "r = 10 + 5 * 2", no formato devolvido pelo backend.
function astExemplo() {
  const dez = no(3, "LITERAL_INTEIRO", { valor: "10" }, [], { coluna: 5, coluna_final: 6 }, { papel: "esquerda", passo: 9 });
  const cinco = no(5, "LITERAL_INTEIRO", { valor: "5" }, [], { coluna: 10, coluna_final: 10 }, { papel: "esquerda", passo: 14 });
  const dois = no(6, "LITERAL_INTEIRO", { valor: "2" }, [], { coluna: 14, coluna_final: 14 }, { papel: "direita", passo: 19 });
  const mult = no(4, "MULTIPLICACAO", { operador: "*" }, [cinco, dois], { coluna: 10, coluna_final: 14 }, { papel: "direita", passo: 20 });
  const soma = no(2, "ADICAO", { operador: "+" }, [dez, mult], { coluna: 5, coluna_final: 14 }, { papel: "valor", passo: 22 });
  const alvo = no(1, "IDENTIFICADOR", { nome: "r" }, [], { coluna: 1, coluna_final: 1 }, { papel: "alvo", passo: 3 });
  const atrib = no(7, "ATRIBUICAO", { nome: "r" }, [alvo, soma], { coluna: 1, coluna_final: 14 }, { passo: 25 });
  atrib.id = 1; alvo.id = 2; soma.id = 3; dez.id = 4; mult.id = 5; cinco.id = 6; dois.id = 7;
  return no(0, "PROGRAMA", { instrucoes: 1 }, [atrib], { coluna: 1, linha_final: 2, coluna_final: 0 }, { passo: 30 });
}

const tok = (tipo, lexema, coluna, coluna_final = coluna + lexema.length - 1, linha = 1) => ({
  tipo, lexema, linha, coluna, linha_final: linha, coluna_final,
});

test("todo tipo de nó do backend tem categoria com símbolo e nome", () => {
  const tiposDoBackend = ["PROGRAMA", "BLOCO", "ATRIBUICAO", "CHAMADA_FUNCAO", "CONDICIONAL", "SENAO_SE",
    "REPETICAO", "COMPARACAO", "ADICAO", "SUBTRACAO", "MULTIPLICACAO", "DIVISAO", "RESTO",
    "OPERACAO_UNARIA", "IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING", "LITERAL_LOGICO"];
  assert.deepEqual(Object.keys(TIPOS_NO).sort(), [...tiposDoBackend].sort());
  for (const tipo of tiposDoBackend) {
    const cat = categoriaDoNo(tipo);
    assert.ok(cat.simbolo && cat.nome && cat.classe, tipo);
  }
  // A forma (símbolo) é diferente em cada categoria: a cor não é a única pista.
  const simbolos = Object.values(CATEGORIAS_NO).map((c) => c.simbolo);
  assert.equal(new Set(simbolos).size, simbolos.length);
});

test("detalheDoNo mostra nome, valor ou operador conforme o tipo", () => {
  const ast = astExemplo();
  assert.equal(detalheDoNo(ast), "1 instrução");
  assert.equal(detalheDoNo(ast.filhos[0]), "r");
  assert.equal(detalheDoNo(ast.filhos[0].filhos[1]), "+");
  assert.equal(detalheDoNo(ast.filhos[0].filhos[1].filhos[0]), "10");
  assert.equal(detalheDoNo(no(9, "CHAMADA_FUNCAO", { nome: "print", argumentos: 2 })), "print(2 argumentos)");
  assert.equal(detalheDoNo(no(9, "CHAMADA_FUNCAO", { nome: "f", argumentos: 1 })), "f(1 argumento)");
  assert.equal(detalheDoNo(no(9, "CONDICIONAL", { elif: 0, else: false })), "");
});

test("posicaoDoNo descreve uma coluna, um intervalo ou várias linhas", () => {
  assert.equal(posicaoDoNo({ linha: 1, coluna: 5, linha_final: 1, coluna_final: 5 }), "linha 1, coluna 5");
  assert.equal(posicaoDoNo({ linha: 2, coluna: 4, linha_final: 2, coluna_final: 12 }), "linha 2, colunas 4–12");
  assert.equal(posicaoDoNo({ linha: 2, coluna: 1, linha_final: 5, coluna_final: 3 }), "linhas 2–5");
});

test("achatar percorre em pré-ordem e ancestrais devolve o caminho até a raiz", () => {
  const ast = astExemplo();
  const lista = achatar(ast);
  assert.deepEqual(lista.map((i) => i.no.id), [0, 1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(lista.map((i) => i.profundidade), [0, 1, 2, 2, 3, 3, 4, 4]);
  assert.deepEqual(ancestrais(ast, 6), [5, 3, 1, 0]);
  assert.deepEqual(ancestrais(ast, 0), []);
  assert.deepEqual(achatar(null), []);
});

test("tiposPresentes conta os nós por tipo", () => {
  assert.deepEqual(tiposPresentes(astExemplo()), [
    { tipo: "PROGRAMA", quantidade: 1 }, { tipo: "ATRIBUICAO", quantidade: 1 },
    { tipo: "IDENTIFICADOR", quantidade: 1 }, { tipo: "ADICAO", quantidade: 1 },
    { tipo: "LITERAL_INTEIRO", quantidade: 3 }, { tipo: "MULTIPLICACAO", quantidade: 1 },
  ]);
});

test("tokensDoNo devolve os tokens dentro do trecho do nó", () => {
  const tokens = [tok("IDENTIFICADOR", "r", 1), tok("OPERADOR_ATRIBUICAO", "=", 3), tok("LITERAL_INTEIRO", "10", 5),
    tok("OPERADOR_ARITMETICO", "+", 8), tok("LITERAL_INTEIRO", "5", 10), tok("OPERADOR_ARITMETICO", "*", 12),
    tok("LITERAL_INTEIRO", "2", 14), tok("NOVA_LINHA", "", 15, 14), tok("FIM_DE_ARQUIVO", "", 1, 0, 2)];
  const mult = astExemplo().filhos[0].filhos[1].filhos[1];
  assert.deepEqual(tokensDoNo(mult, tokens).map((t) => t.token.lexema), ["5", "*", "2"]);
  const atrib = astExemplo().filhos[0];
  assert.deepEqual(tokensDoNo(atrib, tokens).map((t) => t.indice), [0, 1, 2, 3, 4, 5, 6]);
});

test("nosConstruidosAte acompanha a construção de baixo para cima", () => {
  const ast = astExemplo();
  assert.deepEqual([...nosConstruidosAte(ast, 9)].sort(), [2, 4]);
  // A multiplicação (passo 20) só existe depois de 5 e 2; a soma (22), depois dela.
  assert.ok(nosConstruidosAte(ast, 20).has(5));
  assert.ok(!nosConstruidosAte(ast, 20).has(3));
  assert.equal(nosConstruidosAte(ast, 99).size, 8);
});

test("arvoreEmTexto desenha a AST indentada, com papel e detalhe", () => {
  assert.equal(arvoreEmTexto(astExemplo()), [
    "PROGRAMA: 1 instrução",
    "└── ATRIBUICAO: r",
    "    ├── IDENTIFICADOR: r (alvo)",
    "    └── ADICAO: + (valor)",
    "        ├── LITERAL_INTEIRO: 10 (esquerda)",
    "        └── MULTIPLICACAO: * (direita)",
    "            ├── LITERAL_INTEIRO: 5 (esquerda)",
    "            └── LITERAL_INTEIRO: 2 (direita)",
  ].join("\n"));
  assert.equal(arvoreEmTexto(null), "");
});

test("rotuloDerivacao distingue regras de terminais", () => {
  assert.deepEqual(rotuloDerivacao({ regra: "soma", filhos: [] }), { texto: "soma", terminal: false });
  assert.deepEqual(rotuloDerivacao({ terminal: "LITERAL_INTEIRO", lexema: "10" }), { texto: "LITERAL_INTEIRO 10", terminal: true });
  assert.deepEqual(rotuloDerivacao({ terminal: "NOVA_LINHA", lexema: "\n" }), { texto: "NOVA_LINHA ↵", terminal: true });
  assert.deepEqual(rotuloDerivacao({ terminal: "INDENT", lexema: "    " }), { texto: "INDENT", terminal: true });
  assert.equal(tamanhoDerivacao({ regra: "a", filhos: [{ regra: "b", filhos: [{ terminal: "X", lexema: "x" }] }] }), 3);
  assert.equal(tamanhoDerivacao(null), 0);
});

test("textos de esperado e encontrado são legíveis", () => {
  assert.equal(textoEsperado([":"]), "':'");
  assert.equal(textoEsperado(["expressao"]), "uma expressão");
  assert.equal(textoEsperado([")", ","]), "')', ','");
  assert.equal(textoEsperado(["INDENT"]), "um recuo (INDENT)");
  assert.equal(textoEncontrado({ encontrado: "NOVA_LINHA" }), "fim da linha");
  assert.equal(textoEncontrado({ encontrado: "FIM_DE_ARQUIVO" }), "fim do código");
  assert.equal(textoEncontrado({ encontrado: "*" }), "'*'");
});

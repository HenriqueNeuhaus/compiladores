import { test } from "node:test";
import assert from "node:assert/strict";
import { CATEGORIAS, resumoContagem, rotuloLexema, segmentarCodigo } from "../../js/lexico.js";

const token = (tipo, lexema, linha, coluna, coluna_final = coluna + lexema.length - 1, extra = {}) => ({
  tipo, lexema, linha, coluna, linha_final: linha, coluna_final, fora_do_subconjunto: false, ...extra,
});

// Resposta equivalente à do backend para "if a:\n    b = 1\n"
function respostaBloco() {
  const tokens = [
    token("PALAVRA_RESERVADA", "if", 1, 1),
    token("IDENTIFICADOR", "a", 1, 4),
    token("DELIMITADOR", ":", 1, 5),
    token("NOVA_LINHA", "\n", 1, 6),
    token("INDENT", "    ", 2, 1),
    token("IDENTIFICADOR", "b", 2, 5),
    token("OPERADOR_ATRIBUICAO", "=", 2, 7),
    token("LITERAL_INTEIRO", "1", 2, 9),
    token("NOVA_LINHA", "\n", 2, 10),
    token("DEDENT", "", 3, 1, 0),
    token("FIM_DE_ARQUIVO", "", 3, 1, 0),
  ];
  const passos = tokens.map((_, i) => ({ indice: i, tipo: "token", token: i, linha: 1, coluna: 1 }));
  return { tokens, passos, erros: [], comentarios: [] };
}

test("todas as categorias do backend têm nome e classe", () => {
  const backend = ["PALAVRA_RESERVADA", "IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING",
    "OPERADOR_ARITMETICO", "OPERADOR_RELACIONAL", "OPERADOR_ATRIBUICAO", "DELIMITADOR", "NOVA_LINHA",
    "INDENT", "DEDENT", "FIM_DE_ARQUIVO"];
  assert.deepEqual(Object.keys(CATEGORIAS).sort(), [...backend].sort());
  for (const tipo of backend) assert.ok(CATEGORIAS[tipo].nome && CATEGORIAS[tipo].classe);
});

test("rotuloLexema torna visíveis os tokens de estrutura", () => {
  assert.equal(rotuloLexema(token("NOVA_LINHA", "\n", 1, 1)), "↵");
  assert.equal(rotuloLexema(token("NOVA_LINHA", "", 1, 1)), "↵ (implícita)");
  assert.equal(rotuloLexema(token("INDENT", "    ", 1, 1)), "4 espaços");
  assert.equal(rotuloLexema(token("INDENT", " ", 1, 1)), "1 espaço");
  assert.equal(rotuloLexema(token("DEDENT", "", 1, 1)), "(sem texto)");
  assert.equal(rotuloLexema(token("FIM_DE_ARQUIVO", "", 1, 1)), "(fim)");
  assert.equal(rotuloLexema(token("LITERAL_STRING", '"oi"', 1, 1)), '"oi"');
});

test("resumoContagem mantém só categorias presentes, na ordem padrão", () => {
  const r = resumoContagem({ IDENTIFICADOR: 2, PALAVRA_RESERVADA: 1, LITERAL_REAL: 0 });
  assert.deepEqual(r.map((c) => [c.tipo, c.quantidade]), [["PALAVRA_RESERVADA", 1], ["IDENTIFICADOR", 2]]);
});

test("segmentarCodigo reconstrói exatamente o texto de cada linha", () => {
  const codigo = "if a:\n    b = 1\n";
  const { linhas } = segmentarCodigo(codigo, respostaBloco());
  assert.deepEqual(linhas.map((l) => l.segmentos.map((s) => s.texto).join("")), ["if a:", "    b = 1", ""]);
});

test("cada token vira um segmento com sua classe e o passo correspondente", () => {
  const { linhas } = segmentarCodigo("if a:\n    b = 1\n", respostaBloco());
  const linha1 = linhas[0].segmentos.filter((s) => s.texto.trim());
  assert.deepEqual(linha1.map((s) => [s.texto, s.classe, s.token, s.passo]), [
    ["if", "cat-palavra", 0, 0],
    ["a", "cat-identificador", 1, 1],
    [":", "cat-delimitador", 2, 2],
  ]);
  const indent = linhas[1].segmentos[0];
  assert.deepEqual([indent.texto, indent.classe, indent.token], ["    ", "cat-indent", 4]);
});

test("NOVA_LINHA e DEDENT viram marcadores, e FIM_DE_ARQUIVO fica separado", () => {
  const { linhas, fim } = segmentarCodigo("if a:\n    b = 1\n", respostaBloco());
  const ultimo = linhas[0].segmentos.at(-1);
  assert.deepEqual([ultimo.marcador, ultimo.token], ["nova-linha", 3]);
  assert.deepEqual(linhas[2].segmentos.map((s) => s.marcador), ["dedent"]);
  assert.deepEqual([fim.marcador, fim.token], ["fim", 10]);
});

test("comentários e espaços aparecem sem virar token", () => {
  const resposta = {
    tokens: [token("IDENTIFICADOR", "x", 1, 1), token("NOVA_LINHA", "\n", 1, 8), token("FIM_DE_ARQUIVO", "", 2, 1, 0)],
    comentarios: [{ lexema: "# c", linha: 1, coluna: 5, coluna_final: 7 }],
    passos: [
      { indice: 0, tipo: "token", token: 0, linha: 1, coluna: 1 },
      { indice: 1, tipo: "ignorado", linha: 1, coluna: 5 },
      { indice: 2, tipo: "token", token: 1, linha: 1, coluna: 8 },
    ],
    erros: [],
  };
  const { linhas } = segmentarCodigo("x   # c\n", resposta);
  const segs = linhas[0].segmentos;
  assert.deepEqual(segs.map((s) => s.texto), ["x", "   ", "# c", ""]);
  assert.equal(segs[1].classe, undefined);
  assert.deepEqual([segs[2].classe, segs[2].comentario, segs[2].passo], ["cat-comentario", 0, 1]);
});

test("erro léxico ocupa o trecho inválido", () => {
  const resposta = {
    tokens: [token("IDENTIFICADOR", "a", 1, 1), token("IDENTIFICADOR", "b", 1, 5), token("FIM_DE_ARQUIVO", "", 2, 1, 0)],
    erros: [{ tipo: "ERRO_LEXICO", lexema: "$", linha: 1, coluna: 3, linha_final: 1, coluna_final: 3, mensagem: "x" }],
    passos: [{ indice: 0, tipo: "erro", erro: 0, linha: 1, coluna: 3 }],
    comentarios: [],
  };
  const segs = segmentarCodigo("a $ b", resposta).linhas[0].segmentos;
  const erro = segs.find((s) => s.texto === "$");
  assert.deepEqual([erro.classe, erro.erro, erro.passo], ["cat-erro", 0, 0]);
});

test("erro que cobre um token já existente é associado ao token", () => {
  const resposta = {
    tokens: [token("IDENTIFICADOR", "print", 1, 1), token("DELIMITADOR", "(", 1, 6), token("FIM_DE_ARQUIVO", "", 2, 1, 0)],
    erros: [{ lexema: "(", linha: 1, coluna: 6, linha_final: 1, coluna_final: 6, mensagem: "não fechado" }],
    passos: [],
    comentarios: [],
  };
  const segs = segmentarCodigo("print(", resposta).linhas[0].segmentos;
  assert.equal(segs.find((s) => s.texto === "(").erroSobreposto, 0);
});

test("erro de várias linhas é marcado em todas elas", () => {
  const resposta = {
    tokens: [token("FIM_DE_ARQUIVO", "", 3, 1, 0)],
    erros: [{ lexema: '"""a\nb"""', linha: 1, coluna: 1, linha_final: 2, coluna_final: 4, mensagem: "x" }],
    passos: [],
    comentarios: [],
  };
  const { linhas } = segmentarCodigo('"""a\nb"""', resposta);
  assert.equal(linhas[0].segmentos[0].classe, "cat-erro");
  assert.equal(linhas[1].segmentos[0].classe, "cat-erro");
});

test("quebras de linha do Windows são normalizadas como no backend", () => {
  const { linhas } = segmentarCodigo("x\r\ny", { tokens: [], passos: [], erros: [], comentarios: [] });
  assert.deepEqual(linhas.map((l) => l.segmentos.map((s) => s.texto).join("")), ["x", "y"]);
});

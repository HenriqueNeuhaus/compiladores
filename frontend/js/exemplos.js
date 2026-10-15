// Programas de exemplo do subconjunto de Python tratado pelo projeto.
// Cada exemplo indica as construções que pretende demonstrar nas próximas
// etapas (análise léxica e sintática).

export const EXEMPLOS = [
  {
    id: "atribuicao",
    titulo: "Atribuição e expressões aritméticas",
    construcoes: "Atribuição, números inteiros e decimais, operadores + - * /, parênteses e print",
    codigo: [
      "# Área e média de duas medidas",
      "largura = 8",
      "altura = 3.5",
      "area = largura * altura",
      "media = (largura + altura) / 2",
      "print(area)",
      "print(media)",
      "",
    ].join("\n"),
  },
  {
    id: "condicional",
    titulo: "Estrutura condicional",
    construcoes: "if, elif e else, operadores relacionais, strings e blocos indentados (INDENT/DEDENT)",
    codigo: [
      "nota = 7.5",
      "if nota >= 7:",
      '    print("Aprovado")',
      "elif nota >= 5:",
      '    print("Recuperação")',
      "else:",
      '    print("Reprovado")',
      "",
    ].join("\n"),
  },
  {
    id: "repeticao",
    titulo: "Repetição com blocos aninhados",
    construcoes: "while, if dentro de while, operador %, comparação == e vários níveis de indentação",
    codigo: [
      "contador = 1",
      "soma = 0",
      "while contador <= 5:",
      "    soma = soma + contador",
      "    if soma % 2 == 0:",
      '        print("Soma par:", soma)',
      "    contador = contador + 1",
      "print(soma)",
      "",
    ].join("\n"),
  },
  {
    id: "erro-sintatico",
    titulo: "Programa com erro intencional",
    construcoes: "if sem os dois-pontos no fim da linha: será usado para demonstrar a detecção de erros sintáticos",
    codigo: [
      "x = 10",
      "if x > 5",
      '    print("x é maior que 5")',
      "",
    ].join("\n"),
  },
];

/** Devolve o exemplo pelo identificador, ou undefined se não existir. */
export function obterExemplo(id) {
  return EXEMPLOS.find((exemplo) => exemplo.id === id);
}

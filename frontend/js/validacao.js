// Validação do código-fonte feita no navegador, antes do envio.
// O backend repete essas verificações: esta camada só evita requisições
// desnecessárias e dá uma resposta imediata ao estudante.

export const LIMITE_CARACTERES = 20000;

export const MENSAGENS = {
  entrada_vazia: "Informe um código-fonte antes de solicitar a análise.",
  entrada_em_branco:
    "O código informado contém apenas espaços ou quebras de linha. Escreva um programa ou escolha um exemplo.",
  entrada_muito_grande: `O código informado ultrapassa o limite de ${LIMITE_CARACTERES} caracteres.`,
};

/**
 * Verifica se o texto pode ser enviado para análise.
 * Não verifica a sintaxe: programas com erros são aceitos de propósito.
 * @param {unknown} texto
 * @returns {{valido: true} | {valido: false, tipo: string, mensagem: string}}
 */
export function validarCodigo(texto) {
  const invalido = (tipo) => ({ valido: false, tipo, mensagem: MENSAGENS[tipo] });
  if (typeof texto !== "string" || texto.length === 0) return invalido("entrada_vazia");
  if (texto.trim().length === 0) return invalido("entrada_em_branco");
  if (texto.length > LIMITE_CARACTERES) return invalido("entrada_muito_grande");
  return { valido: true };
}

/** Quantidade de linhas e caracteres, para o contador abaixo do editor. */
export function contarTexto(texto) {
  const linhas = texto.length === 0 ? 0 : texto.replace(/\r?\n$/, "").split(/\r?\n/).length;
  return { linhas, caracteres: texto.length };
}

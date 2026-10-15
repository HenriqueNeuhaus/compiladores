"""Validação da requisição de análise.

Este módulo não depende do framework web: recebe o corpo já decodificado
(ou o erro de decodificação) e decide se o código-fonte pode ser processado.
Assim as regras podem ser testadas isoladamente e reaproveitadas quando os
analisadores léxico e sintático forem adicionados.
"""

from dataclasses import dataclass

# Limite de tamanho do código-fonte aceito, em caracteres.
# Programas didáticos do subconjunto de Python são pequenos; o limite evita
# que entradas muito grandes travem a visualização passo a passo.
LIMITE_CARACTERES = 20_000

MENSAGENS = {
    "json_invalido": "A requisição não contém um JSON válido.",
    "corpo_nao_objeto": 'O corpo da requisição deve ser um objeto JSON com o campo "codigo".',
    "campo_ausente": 'O campo obrigatório "codigo" não foi informado.',
    "tipo_invalido": 'O campo "codigo" deve ser um texto.',
    "entrada_vazia": "Informe um código-fonte antes de solicitar a análise.",
    "entrada_em_branco": (
        "O código informado contém apenas espaços ou quebras de linha. "
        "Escreva um programa ou escolha um exemplo."
    ),
    "entrada_muito_grande": (
        f"O código informado ultrapassa o limite de {LIMITE_CARACTERES} caracteres."
    ),
}


@dataclass(frozen=True)
class ErroValidacao(Exception):
    """Erro de entrada com o tipo, a mensagem e o código HTTP correspondentes."""

    tipo: str
    status: int

    @property
    def mensagem(self) -> str:
        return MENSAGENS[self.tipo]


def validar_corpo(corpo: object) -> str:
    """Valida o corpo JSON decodificado e devolve o código-fonte.

    Regras:
    - o corpo deve ser um objeto com o campo "codigo" (422 se não for);
    - "codigo" deve ser texto (422);
    - texto vazio (400) ou só com espaços e quebras de linha (400) é recusado;
    - texto acima de LIMITE_CARACTERES é recusado (413).

    O conteúdo do código não é verificado: programas com erros léxicos ou
    sintáticos são aceitos, pois serão usados para demonstrar a detecção de
    erros nas próximas etapas.
    """
    if not isinstance(corpo, dict):
        raise ErroValidacao("corpo_nao_objeto", 422)
    if "codigo" not in corpo:
        raise ErroValidacao("campo_ausente", 422)

    codigo = corpo["codigo"]
    if not isinstance(codigo, str):
        raise ErroValidacao("tipo_invalido", 422)
    if codigo == "":
        raise ErroValidacao("entrada_vazia", 400)
    if codigo.strip() == "":
        raise ErroValidacao("entrada_em_branco", 400)
    if len(codigo) > LIMITE_CARACTERES:
        raise ErroValidacao("entrada_muito_grande", 413)
    return codigo


def estatisticas(codigo: str) -> dict:
    """Informações simples sobre o texto recebido, devolvidas ao usuário."""
    return {
        "linhas": len(codigo.splitlines()) or 1,
        "caracteres": len(codigo),
    }

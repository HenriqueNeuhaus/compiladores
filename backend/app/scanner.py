"""Analisador léxico (scanner) do subconjunto de Python.

O scanner percorre o código caractere a caractere e produz:
- tokens: unidades com significado (palavras reservadas, identificadores,
  literais, operadores, delimitadores e os tokens de estrutura NOVA_LINHA,
  INDENT, DEDENT e FIM_DE_ARQUIVO);
- erros léxicos: trechos que não formam nenhum token do subconjunto;
- avisos: trechos válidos em Python, mas fora do subconjunto, que não
  impedem a análise léxica (por exemplo, a palavra reservada "for");
- comentários: registrados para a visualização, mas sem gerar tokens;
- passos: a sequência de decisões do scanner, usada pela interface para
  mostrar a tokenização passo a passo.

Assim como no Python, a indentação é tratada pelo analisador léxico: uma
pilha guarda os níveis de indentação abertos. Uma linha mais recuada que o
topo empilha um nível e gera INDENT; uma linha menos recuada desempilha
níveis e gera um DEDENT para cada um. Dentro de parênteses, quebras de
linha e indentação são ignoradas (junção implícita de linhas).

Linhas e colunas começam em 1. "coluna_final" é a coluna do último
caractere do lexema (inclusiva); tokens sem largura (DEDENT, FIM_DE_ARQUIVO
e a NOVA_LINHA implícita do fim do arquivo) têm coluna_final = coluna - 1.
"""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass

# ---------------------------------------------------------------------------
# Escopo léxico
# ---------------------------------------------------------------------------

PALAVRAS_RESERVADAS = ("if", "elif", "else", "while", "True", "False")

# Palavras reservadas de Python que existem na linguagem, mas não no
# subconjunto. São reconhecidas como PALAVRA_RESERVADA com um aviso, para
# que o estudante saiba por que elas não serão aceitas pela análise sintática.
PALAVRAS_RESERVADAS_FORA = (
    "None", "and", "as", "assert", "async", "await", "break", "class",
    "continue", "def", "del", "except", "finally", "for", "from", "global",
    "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise",
    "return", "try", "with", "yield",
)

OPERADORES_DO_SUBCONJUNTO = {
    "+": "OPERADOR_ARITMETICO",
    "-": "OPERADOR_ARITMETICO",
    "*": "OPERADOR_ARITMETICO",
    "/": "OPERADOR_ARITMETICO",
    "%": "OPERADOR_ARITMETICO",
    "==": "OPERADOR_RELACIONAL",
    "!=": "OPERADOR_RELACIONAL",
    "<": "OPERADOR_RELACIONAL",
    "<=": "OPERADOR_RELACIONAL",
    ">": "OPERADOR_RELACIONAL",
    ">=": "OPERADOR_RELACIONAL",
    "=": "OPERADOR_ATRIBUICAO",
    "(": "DELIMITADOR",
    ")": "DELIMITADOR",
    ":": "DELIMITADOR",
    ",": "DELIMITADOR",
}

# Operadores e delimitadores de Python fora do subconjunto, com uma breve
# explicação. O scanner os reconhece pelo casamento mais longo para dar uma
# mensagem precisa (por exemplo, "//" é um operador, não duas barras).
OPERADORES_FORA = {
    "**=": "atribuição com potência", "//=": "atribuição com divisão inteira",
    ">>=": "atribuição com deslocamento", "<<=": "atribuição com deslocamento",
    "...": "reticências",
    "**": "potência", "//": "divisão inteira", "+=": "atribuição composta",
    "-=": "atribuição composta", "*=": "atribuição composta",
    "/=": "atribuição composta", "%=": "atribuição composta",
    "&=": "atribuição composta", "|=": "atribuição composta",
    "^=": "atribuição composta", "@=": "atribuição composta",
    "->": "anotação de retorno", "<<": "deslocamento de bits",
    ">>": "deslocamento de bits", ":=": "expressão de atribuição (morsa)",
    "&": "operação bit a bit", "|": "operação bit a bit",
    "^": "operação bit a bit", "~": "operação bit a bit",
    "@": "decoradores e multiplicação de matrizes",
    ".": "acesso a atributo", ";": "separador de instruções",
    "[": "listas e índices", "]": "listas e índices",
    "{": "dicionários e conjuntos", "}": "dicionários e conjuntos",
}

PREFIXOS_DE_STRING = {"f", "r", "b", "u", "rb", "br", "fr", "rf"}

CATEGORIAS = (
    "PALAVRA_RESERVADA", "IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL",
    "LITERAL_STRING", "OPERADOR_ARITMETICO", "OPERADOR_RELACIONAL",
    "OPERADOR_ATRIBUICAO", "DELIMITADOR", "NOVA_LINHA", "INDENT", "DEDENT",
    "FIM_DE_ARQUIVO",
)

LARGURA_TABULACAO = 8   # como no Python: a tabulação avança até o próximo múltiplo de 8
LIMITE_ERROS = 100


# ---------------------------------------------------------------------------
# Estruturas de saída
# ---------------------------------------------------------------------------

@dataclass
class Token:
    tipo: str
    lexema: str
    linha: int
    coluna: int
    linha_final: int
    coluna_final: int
    fora_do_subconjunto: bool = False


@dataclass
class Ocorrencia:
    """Erro léxico ou aviso."""

    tipo: str            # "ERRO_LEXICO" ou "AVISO"
    codigo: str
    lexema: str
    linha: int
    coluna: int
    linha_final: int
    coluna_final: int
    mensagem: str


@dataclass
class Comentario:
    lexema: str
    linha: int
    coluna: int
    coluna_final: int


@dataclass
class ResultadoLexico:
    tokens: list[Token]
    erros: list[Ocorrencia]
    avisos: list[Ocorrencia]
    comentarios: list[Comentario]
    passos: list[dict]

    @property
    def sucesso(self) -> bool:
        return not self.erros

    def contagem(self) -> dict[str, int]:
        contagem = {categoria: 0 for categoria in CATEGORIAS}
        for token in self.tokens:
            contagem[token.tipo] += 1
        return contagem

    def como_dict(self) -> dict:
        return {
            "sucesso": self.sucesso,
            "tokens": [asdict(t) for t in self.tokens],
            "erros": [asdict(e) for e in self.erros],
            "avisos": [asdict(a) for a in self.avisos],
            "comentarios": [asdict(c) for c in self.comentarios],
            "contagem": self.contagem(),
            "passos": self.passos,
        }


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _eh_inicio_de_identificador(c: str) -> bool:
    return c.isascii() and (c.isalpha() or c == "_")


def _eh_parte_de_identificador(c: str) -> bool:
    return c.isascii() and (c.isalnum() or c == "_")


def _mostrar(lexema: str) -> str:
    """Representação legível de um lexema dentro de uma mensagem."""
    return repr(lexema) if lexema.strip() else f"'{lexema}'"


def _descrever_caractere(c: str) -> str:
    if c == "\t":
        return "tabulação"
    if c.isascii() and c.isprintable():
        return f"'{c}'"
    nome = unicodedata.name(c, "")
    return f"'{c}' ({nome.lower()})" if nome else f"U+{ord(c):04X}"


class Scanner:
    def __init__(self, codigo: str):
        # Quebras de linha do Windows (\r\n) e antigas (\r) viram \n.
        self.fonte = codigo.replace("\r\n", "\n").replace("\r", "\n")
        self.pos = 0
        self.linha = 1
        self.coluna = 1
        self.pilha = [0]
        self.parenteses: list[tuple[int, int]] = []   # posições dos "(" abertos
        self.linha_logica_aberta = False
        self.tokens: list[Token] = []
        self.erros: list[Ocorrencia] = []
        self.avisos: list[Ocorrencia] = []
        self.comentarios: list[Comentario] = []
        self.passos: list[dict] = []
        self.erros_descartados = 0

    # -- navegação -------------------------------------------------------
    def _atual(self, deslocamento: int = 0) -> str:
        i = self.pos + deslocamento
        return self.fonte[i] if i < len(self.fonte) else ""

    def _avancar(self) -> str:
        c = self.fonte[self.pos]
        self.pos += 1
        if c == "\n":
            self.linha += 1
            self.coluna = 1
        else:
            self.coluna += 1
        return c

    # -- registro --------------------------------------------------------
    def _passo(self, tipo: str, descricao: str, linha: int, coluna: int,
               linha_final: int, coluna_final: int, **extra) -> None:
        self.passos.append({
            "indice": len(self.passos),
            "tipo": tipo,
            "descricao": descricao,
            "linha": linha,
            "coluna": coluna,
            "linha_final": linha_final,
            "coluna_final": coluna_final,
            "pilha": list(self.pilha),
            **extra,
        })

    def _emitir(self, tipo: str, lexema: str, linha: int, coluna: int,
                descricao: str, fora: bool = False,
                linha_final: int | None = None, coluna_final: int | None = None) -> None:
        if linha_final is None:
            linha_final = linha
        if coluna_final is None:
            coluna_final = coluna + len(lexema) - 1
        token = Token(tipo, lexema, linha, coluna, linha_final, coluna_final, fora)
        self.tokens.append(token)
        if tipo not in ("NOVA_LINHA", "INDENT", "DEDENT", "FIM_DE_ARQUIVO"):
            self.linha_logica_aberta = True
        self._passo("token", descricao, linha, coluna, linha_final, coluna_final,
                    token=len(self.tokens) - 1)

    def _erro(self, codigo: str, lexema: str, linha: int, coluna: int,
              explicacao: str, linha_final: int | None = None,
              coluna_final: int | None = None) -> None:
        if linha_final is None:
            linha_final = linha
        if coluna_final is None:
            coluna_final = coluna + max(len(lexema), 1) - 1
        mensagem = f"Erro léxico na linha {linha}, coluna {coluna}: {explicacao}"
        if len(self.erros) >= LIMITE_ERROS:
            self.erros_descartados += 1
            return
        erro = Ocorrencia("ERRO_LEXICO", codigo, lexema, linha, coluna,
                          linha_final, coluna_final, mensagem)
        self.erros.append(erro)
        self._passo("erro", mensagem, linha, coluna, linha_final, coluna_final,
                    erro=len(self.erros) - 1)

    def _aviso(self, codigo: str, lexema: str, linha: int, coluna: int,
               explicacao: str) -> None:
        mensagem = f"Aviso na linha {linha}, coluna {coluna}: {explicacao}"
        self.avisos.append(Ocorrencia("AVISO", codigo, lexema, linha, coluna,
                                      linha, coluna + len(lexema) - 1, mensagem))

    # -- execução --------------------------------------------------------
    def executar(self) -> ResultadoLexico:
        inicio_de_linha = True
        while True:
            if inicio_de_linha and not self.parenteses:
                inicio_de_linha = False
                if not self._processar_inicio_de_linha():
                    inicio_de_linha = True
                    if self.pos >= len(self.fonte):
                        break
                    continue

            c = self._atual()
            if c == "":
                break
            if c == "\n":
                if self.parenteses:
                    linha, coluna = self.linha, self.coluna
                    self._avancar()
                    self._passo(
                        "ignorado",
                        f"Quebra de linha dentro de parênteses (aberto na linha "
                        f"{self.parenteses[-1][0]}): ignorada. A linha lógica continua "
                        f"na próxima linha física (junção implícita de linhas).",
                        linha, coluna, linha, coluna)
                    continue
                self._fim_de_linha_logica()
                inicio_de_linha = True
                continue
            if c in " \t\f":
                self._avancar()
                continue
            if c == "#":
                self._ler_comentario()
                continue
            if c == "\\":
                self._ler_barra_invertida()
                continue
            if _eh_inicio_de_identificador(c) or c.isalpha():
                self._ler_palavra()
            elif c.isdigit() and c.isascii():
                self._ler_numero()
            elif c in "\"'":
                self._ler_string_como_token()
            else:
                self._ler_operador_ou_desconhecido()

        self._finalizar()
        return ResultadoLexico(self.tokens, self.erros, self.avisos,
                               self.comentarios, self.passos)

    # -- estrutura de linhas e indentação ----------------------------------
    def _processar_inicio_de_linha(self) -> bool:
        """Mede a indentação no início de uma linha física.

        Devolve False se a linha estiver em branco ou só tiver comentário
        (ela é ignorada e não altera a pilha); True se a linha tem código.
        """
        linha = self.linha
        largura = 0
        tabulacao_em = None
        while self._atual() in (" ", "\t", "\f") and self._atual() != "":
            c = self._avancar()
            if c == " ":
                largura += 1
            elif c == "\t":
                if tabulacao_em is None:
                    tabulacao_em = self.coluna - 1
                largura = (largura // LARGURA_TABULACAO + 1) * LARGURA_TABULACAO
            else:  # \f reinicia a contagem, como no Python
                largura = 0
        recuo = self.fonte[self.pos - (self.coluna - 1):self.pos]

        c = self._atual()
        if c in ("", "\n", "#"):
            if c == "#":
                self._ler_comentario()
            if self._atual() == "\n":
                col = self.coluna
                self._avancar()
                self._passo("ignorado",
                            f"Linha {linha} sem código (em branco ou só com comentário): "
                            f"ignorada. Ela não gera NOVA_LINHA e não altera a indentação.",
                            linha, 1, linha, col)
            return False

        if tabulacao_em is not None:
            self._erro("indentacao_com_tabulacao", "\t", linha, tabulacao_em,
                       "a indentação usa tabulação. Neste subconjunto, indente apenas com "
                       "espaços (recomenda-se 4 espaços por nível).")

        topo = self.pilha[-1]
        if largura > topo:
            self.pilha.append(largura)
            self._emitir(
                "INDENT", recuo, linha, 1,
                f"A linha {linha} começa com {largura} espaço(s), mais que o nível atual "
                f"({topo}). O scanner empilha {largura} e gera INDENT: começa um novo bloco.",
                coluna_final=len(recuo))
        elif largura < topo:
            while self.pilha[-1] > largura:
                saiu = self.pilha.pop()
                self._emitir(
                    "DEDENT", "", linha, self.coluna,
                    f"A linha {linha} começa com {largura} espaço(s), menos que o nível "
                    f"{saiu}. O scanner desempilha {saiu} e gera DEDENT: um bloco termina.",
                    coluna_final=self.coluna - 1)
            if self.pilha[-1] != largura:
                niveis = ", ".join(str(n) for n in self.pilha)
                self._erro(
                    "indentacao_inconsistente", recuo, linha, 1,
                    f"indentação inconsistente: o recuo de {largura} espaço(s) não "
                    f"corresponde a nenhum nível aberto (níveis: {niveis}). Alinhe a linha "
                    f"com um dos blocos anteriores.",
                    coluna_final=max(len(recuo), 1))
                self.pilha.append(largura)
        return True

    def _fim_de_linha_logica(self) -> None:
        linha, coluna = self.linha, self.coluna
        self._avancar()
        if self.linha_logica_aberta:
            self.linha_logica_aberta = False
            self._emitir("NOVA_LINHA", "\n", linha, coluna,
                         f"Fim da linha lógica {linha}: o scanner gera NOVA_LINHA, que "
                         f"marca o fim de uma instrução.")

    def _finalizar(self) -> None:
        for linha, coluna in self.parenteses:
            self._erro("parentese_nao_fechado", "(", linha, coluna,
                       "o parêntese '(' aberto aqui não foi fechado até o fim do código.")
        self.parenteses.clear()

        if self.linha_logica_aberta:
            self.linha_logica_aberta = False
            self._emitir("NOVA_LINHA", "", self.linha, self.coluna,
                         "O código termina sem quebra de linha: o scanner gera uma "
                         "NOVA_LINHA implícita para fechar a última instrução.",
                         coluna_final=self.coluna - 1)

        linha_final = self.linha if self.coluna == 1 else self.linha + 1
        while len(self.pilha) > 1:
            saiu = self.pilha.pop()
            self._emitir("DEDENT", "", linha_final, 1,
                         f"Fim do código com o bloco de nível {saiu} aberto: o scanner "
                         f"desempilha {saiu} e gera DEDENT.",
                         coluna_final=0)
        self._emitir("FIM_DE_ARQUIVO", "", linha_final, 1,
                     "Fim do código: o scanner gera FIM_DE_ARQUIVO. A análise léxica "
                     "terminou.", coluna_final=0)

    # -- categorias de lexemas ---------------------------------------------
    def _ler_comentario(self) -> None:
        linha, coluna, inicio = self.linha, self.coluna, self.pos
        while self._atual() not in ("", "\n"):
            self._avancar()
        texto = self.fonte[inicio:self.pos]
        self.comentarios.append(Comentario(texto, linha, coluna, coluna + len(texto) - 1))
        self._passo("ignorado",
                    "Comentário: começa com '#' e vai até o fim da linha. É ignorado "
                    "e não gera token.",
                    linha, coluna, linha, coluna + len(texto) - 1)

    def _ler_barra_invertida(self) -> None:
        linha, coluna = self.linha, self.coluna
        self._avancar()
        if self._atual() == "\n":
            self._avancar()   # continua a linha lógica, para não gerar erros em cascata
            self._erro("continuacao_com_barra", "\\", linha, coluna,
                       "a continuação de linha com '\\' existe em Python, mas não faz "
                       "parte do subconjunto. Use parênteses para quebrar uma expressão "
                       "em várias linhas.")
        else:
            self._erro("caractere_nao_reconhecido", "\\", linha, coluna,
                       "caractere não reconhecido '\\'. Fora de uma string, a barra "
                       "invertida só aparece em continuação de linha, que não faz parte "
                       "do subconjunto.")

    def _ler_palavra(self) -> None:
        linha, coluna, inicio = self.linha, self.coluna, self.pos
        while _eh_parte_de_identificador(self._atual()) and self._atual() != "":
            self._avancar()
        if self._atual().isalnum() and not self._atual().isascii() or (
                self.pos == inicio and self._atual().isalpha()):
            while self._atual() != "" and (self._atual().isalnum() or self._atual() == "_"):
                self._avancar()
            palavra = self.fonte[inicio:self.pos]
            fora = next(c for c in palavra if not c.isascii())
            self._erro("identificador_com_caractere_nao_ascii", palavra, linha, coluna,
                       f"o identificador '{palavra}' contém {_descrever_caractere(fora)}. "
                       f"Neste subconjunto, identificadores usam apenas letras sem acento, "
                       f"dígitos e '_'.")
            return

        palavra = self.fonte[inicio:self.pos]
        if palavra.lower() in PREFIXOS_DE_STRING and self._atual() in "\"'" and self._atual():
            lexema = self._consumir_string(linha, coluna, inicio)
            if lexema is not None:
                self._erro("prefixo_de_string", lexema, linha, coluna,
                           f"strings com o prefixo '{palavra}' (como f-strings) existem em "
                           f"Python, mas não fazem parte do subconjunto. Use uma string "
                           f"simples entre aspas.")
            return

        if palavra in PALAVRAS_RESERVADAS:
            self._emitir("PALAVRA_RESERVADA", palavra, linha, coluna,
                         f"Leu '{palavra}': tem a forma de um identificador, mas está na "
                         f"lista de palavras reservadas → PALAVRA_RESERVADA.")
        elif palavra in PALAVRAS_RESERVADAS_FORA:
            self._emitir("PALAVRA_RESERVADA", palavra, linha, coluna,
                         f"Leu '{palavra}': é uma palavra reservada de Python → "
                         f"PALAVRA_RESERVADA. Ela não faz parte do subconjunto, então "
                         f"gera um aviso.", fora=True)
            self._aviso("palavra_reservada_fora_do_subconjunto", palavra, linha, coluna,
                        f"'{palavra}' é uma palavra reservada de Python, mas não faz parte "
                        f"do subconjunto. O scanner a reconhece, porém a análise sintática "
                        f"não vai aceitá-la.")
        else:
            self._emitir("IDENTIFICADOR", palavra, linha, coluna,
                         f"Leu '{palavra}': começa com letra ou '_' e continua com letras, "
                         f"dígitos ou '_' → IDENTIFICADOR.")

    def _ler_numero(self) -> None:
        linha, coluna, inicio = self.linha, self.coluna, self.pos
        while self._atual().isdigit() and self._atual().isascii() and self._atual():
            self._avancar()
        tipo = "LITERAL_INTEIRO"

        if self._atual() == ".":
            if self._atual(1).isdigit() and self._atual(1).isascii():
                self._avancar()
                while self._atual().isdigit() and self._atual().isascii() and self._atual():
                    self._avancar()
                tipo = "LITERAL_REAL"
            else:
                self._avancar()
                lexema = self.fonte[inicio:self.pos]
                self._erro("literal_real_incompleto", lexema, linha, coluna,
                           f"número real incompleto {_mostrar(lexema)}: depois do ponto "
                           f"deve vir pelo menos um dígito (por exemplo, "
                           f"'{lexema}0').")
                return

        if _eh_parte_de_identificador(self._atual()) and self._atual():
            while _eh_parte_de_identificador(self._atual()) and self._atual():
                anterior = self._avancar()
                if anterior in "eE" and self._atual() in "+-" and self._atual():
                    self._avancar()
            lexema = self.fonte[inicio:self.pos]
            minusculo = lexema.lower()
            if minusculo[:2] in ("0x", "0o", "0b"):
                explicacao = (f"o literal {_mostrar(lexema)} está em outra base numérica "
                              f"(hexadecimal, octal ou binária), que não faz parte do "
                              f"subconjunto. Use números decimais.")
            elif "e" in minusculo and minusculo.split("e")[0].replace(".", "").isdigit():
                explicacao = (f"o literal {_mostrar(lexema)} usa notação científica, que "
                              f"não faz parte do subconjunto. Escreva o número por extenso.")
            elif "_" in lexema and lexema.replace("_", "").isdigit():
                explicacao = (f"o separador '_' em números ({_mostrar(lexema)}) não faz "
                              f"parte do subconjunto. Escreva os dígitos sem separador.")
            else:
                explicacao = (f"literal numérico malformado {_mostrar(lexema)}: um número "
                              f"não pode ser seguido de letras. Lembre-se de que "
                              f"identificadores não podem começar com dígito.")
            self._erro("literal_numerico_malformado", lexema, linha, coluna, explicacao)
            return

        lexema = self.fonte[inicio:self.pos]
        if tipo == "LITERAL_INTEIRO" and len(lexema) > 1 and lexema[0] == "0" \
                and lexema.strip("0") != "":
            self._erro("zeros_a_esquerda", lexema, linha, coluna,
                       f"o inteiro {_mostrar(lexema)} tem zeros à esquerda, o que Python "
                       f"não permite. Escreva {int(lexema)}.")
            return

        if tipo == "LITERAL_INTEIRO":
            descricao = f"Leu '{lexema}': sequência de dígitos → LITERAL_INTEIRO."
        else:
            descricao = (f"Leu '{lexema}': dígitos, ponto e mais dígitos → LITERAL_REAL. "
                         f"Ao ver o ponto, o scanner olhou o próximo caractere para "
                         f"confirmar que era um dígito.")
        self._emitir(tipo, lexema, linha, coluna, descricao)

    def _consumir_string(self, linha: int, coluna: int, inicio: int) -> str | None:
        """Consome uma string a partir da aspa atual.

        Devolve o lexema (desde `inicio`) ou None se já registrou um erro.
        """
        aspa = self._atual()
        if self.fonte[self.pos:self.pos + 3] == aspa * 3:
            for _ in range(3):
                self._avancar()
            fim = self.fonte.find(aspa * 3, self.pos)
            ate = len(self.fonte) if fim == -1 else fim + 3
            while self.pos < ate:
                self._avancar()
            lexema = self.fonte[inicio:self.pos]
            situacao = "e não foi fechada" if fim == -1 else ""
            self._erro("string_com_tres_aspas", lexema, linha, coluna,
                       f"strings com três aspas existem em Python, mas não fazem parte do "
                       f"subconjunto{(' ' + situacao) if situacao else ''}. Use aspas "
                       f"simples ou duplas em uma única linha.",
                       linha_final=self.linha, coluna_final=max(self.coluna - 1, 1))
            return None

        self._avancar()   # aspa de abertura
        while True:
            c = self._atual()
            if c in ("", "\n"):
                lexema = self.fonte[inicio:self.pos]
                self._erro("string_nao_fechada", lexema, linha, coluna,
                           f"a string que começa aqui não foi fechada antes do fim da "
                           f"linha. Feche-a com {aspa} na mesma linha.")
                return None
            if c == "\\":
                self._avancar()
                if self._atual() not in ("", "\n"):
                    self._avancar()
                continue
            self._avancar()
            if c == aspa:
                return self.fonte[inicio:self.pos]

    def _ler_string_como_token(self) -> None:
        linha, coluna, inicio = self.linha, self.coluna, self.pos
        lexema = self._consumir_string(linha, coluna, inicio)
        if lexema is not None:
            self._emitir("LITERAL_STRING", lexema, linha, coluna,
                         f"Leu {lexema}: começa e termina com a mesma aspa, na mesma "
                         f"linha → LITERAL_STRING.")

    def _ler_operador_ou_desconhecido(self) -> None:
        linha, coluna = self.linha, self.coluna
        for tamanho in (3, 2, 1):
            candidato = self.fonte[self.pos:self.pos + tamanho]
            if len(candidato) < tamanho:
                continue
            if candidato in OPERADORES_DO_SUBCONJUNTO:
                for _ in range(tamanho):
                    self._avancar()
                tipo = OPERADORES_DO_SUBCONJUNTO[candidato]
                if candidato == "(":
                    self.parenteses.append((linha, coluna))
                elif candidato == ")" and self.parenteses:
                    self.parenteses.pop()
                descricao = f"Leu '{candidato}' → {tipo}."
                if tamanho == 1 and candidato in "<>=":
                    descricao = (f"Leu '{candidato}'. O scanner olhou o próximo caractere "
                                 f"e ele não forma um operador maior → {tipo}.")
                elif tamanho == 2:
                    descricao = (f"Leu '{candidato}': o scanner olhou um caractere à frente "
                                 f"e escolheu o operador mais longo ('{candidato}' em vez "
                                 f"de '{candidato[0]}') → {tipo}.")
                self._emitir(tipo, candidato, linha, coluna, descricao)
                return
            if candidato in OPERADORES_FORA:
                for _ in range(tamanho):
                    self._avancar()
                self._erro("operador_fora_do_subconjunto", candidato, linha, coluna,
                           f"'{candidato}' existe em Python ({OPERADORES_FORA[candidato]}), "
                           f"mas não faz parte do subconjunto.")
                return

        c = self._avancar()
        self._erro("caractere_nao_reconhecido", c, linha, coluna,
                   f"caractere não reconhecido {_descrever_caractere(c)}. Verifique se ele "
                   f"faz parte do subconjunto suportado.")


def analisar(codigo: str) -> ResultadoLexico:
    """Executa a análise léxica do código e devolve o resultado completo."""
    return Scanner(codigo).executar()

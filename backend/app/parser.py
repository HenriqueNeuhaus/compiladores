"""Analisador sintático (parser) do subconjunto de Python.

Estratégia: descendente recursivo, escrito à mão. Cada não terminal da
gramática (veja GRAMATICA, abaixo, e docs/gramatica.md) é um método da classe
Parser. O parser recebe a lista de tokens produzida pelo scanner da Etapa 3,
olha o próximo token (às vezes os dois próximos) para decidir qual regra
aplicar e constrói a árvore sintática abstrata (AST).

Além da AST, o parser registra:
- erros sintáticos, com o que foi encontrado, o que era esperado e a regra
  gramatical envolvida;
- a árvore de derivação (árvore concreta), com todas as regras aplicadas e
  todos os terminais consumidos;
- passos: a sequência de decisões (entrar em uma regra, consumir um token,
  construir um nó, registrar um erro), usada pela interface para mostrar a
  análise passo a passo.

Recuperação de erros (modo pânico): ao encontrar um erro em uma instrução, o
parser registra o erro, descarta os tokens até o fim da linha (NOVA_LINHA) e
continua na instrução seguinte. Dois-pontos e parêntese de fechamento que
faltam no fim da linha são "inseridos" virtualmente, para que o bloco seguinte
continue sendo analisado sem erros em cascata.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import scanner

# ---------------------------------------------------------------------------
# Gramática (EBNF). Os mesmos textos aparecem em docs/gramatica.md; um teste
# verifica que a documentação e o código não divergem.
# ---------------------------------------------------------------------------

GRAMATICA = {
    "programa": 'programa = { instrucao } FIM_DE_ARQUIVO ;',
    "instrucao": 'instrucao = atribuicao | chamada_simples | condicional | repeticao ;',
    "atribuicao": 'atribuicao = IDENTIFICADOR "=" expressao NOVA_LINHA ;',
    "chamada_simples": 'chamada_simples = chamada NOVA_LINHA ;',
    "condicional": ('condicional = "if" expressao ":" bloco { "elif" expressao ":" bloco } '
                    '[ "else" ":" bloco ] ;'),
    "repeticao": 'repeticao = "while" expressao ":" bloco ;',
    "bloco": 'bloco = NOVA_LINHA INDENT instrucao { instrucao } DEDENT ;',
    "expressao": 'expressao = comparacao ;',
    "comparacao": 'comparacao = soma [ OPERADOR_RELACIONAL soma ] ;',
    "soma": 'soma = termo { ( "+" | "-" ) termo } ;',
    "termo": 'termo = fator { ( "*" | "/" | "%" ) fator } ;',
    "fator": 'fator = ( "+" | "-" ) fator | primario ;',
    "primario": ('primario = LITERAL_INTEIRO | LITERAL_REAL | LITERAL_STRING | "True" | "False" '
                 '| chamada | IDENTIFICADOR | "(" expressao ")" ;'),
    "chamada": 'chamada = IDENTIFICADOR "(" [ argumentos ] ")" ;',
    "argumentos": 'argumentos = expressao { "," expressao } ;',
}

# Descrição curta de cada regra, usada nas mensagens e na interface.
DESCRICAO_REGRA = {
    "programa": "o programa inteiro: uma sequência de instruções",
    "instrucao": "uma instrução: atribuição, chamada de função, if ou while",
    "atribuicao": "atribuição: nome, '=', valor e fim da linha",
    "chamada_simples": "chamada de função usada como instrução",
    "condicional": "estrutura condicional if/elif/else",
    "repeticao": "laço while",
    "bloco": "bloco indentado com pelo menos uma instrução",
    "expressao": "expressão",
    "comparacao": "comparação com no máximo um operador relacional",
    "soma": "soma e subtração (associativas à esquerda)",
    "termo": "multiplicação, divisão e resto (associativas à esquerda)",
    "fator": "sinal unário (+ ou -) aplicado a um fator",
    "primario": "valor básico: número, string, True/False, nome, chamada ou expressão entre parênteses",
    "chamada": "chamada de função: nome, '(', argumentos e ')'",
    "argumentos": "lista de argumentos separados por vírgula",
}

TIPOS_DE_NO = {
    "PROGRAMA": "programa",
    "BLOCO": "bloco",
    "ATRIBUICAO": "atribuicao",
    "CHAMADA_FUNCAO": "chamada",
    "CONDICIONAL": "condicional",
    "SENAO_SE": "condicional",
    "REPETICAO": "repeticao",
    "COMPARACAO": "comparacao",
    "ADICAO": "soma",
    "SUBTRACAO": "soma",
    "MULTIPLICACAO": "termo",
    "DIVISAO": "termo",
    "RESTO": "termo",
    "OPERACAO_UNARIA": "fator",
    "IDENTIFICADOR": "primario",
    "LITERAL_INTEIRO": "primario",
    "LITERAL_REAL": "primario",
    "LITERAL_STRING": "primario",
    "LITERAL_LOGICO": "primario",
}

OPERACOES_BINARIAS = {
    "+": "ADICAO", "-": "SUBTRACAO", "*": "MULTIPLICACAO", "/": "DIVISAO", "%": "RESTO",
}

LIMITE_ERROS = 50
LIMITE_PASSOS = 20_000
LIMITE_PROFUNDIDADE = 200

PALAVRAS_DE_INSTRUCAO = {"if", "elif", "else", "while"}
OPERADORES_LOGICOS = {"and": "e lógico", "or": "ou lógico", "not": "negação lógica",
                      "in": "teste de pertinência", "is": "teste de identidade"}


# ---------------------------------------------------------------------------
# Estruturas de resultado
# ---------------------------------------------------------------------------

@dataclass
class No:
    """Nó da AST. 'regra' é a regra gramatical que construiu o nó e 'papel'
    diz o que ele representa para o nó pai (condição, valor, esquerda...)."""

    tipo: str
    regra: str
    linha: int
    coluna: int
    linha_final: int
    coluna_final: int
    atributos: dict = field(default_factory=dict)
    filhos: list["No"] = field(default_factory=list)
    papel: str | None = None
    id: int = -1
    passo: int = -1
    # Extensão incluindo parênteses ao redor (não aparece no JSON): usada para
    # que o nó pai cubra também os parênteses no código.
    extensao: tuple[int, int, int, int] | None = None

    def como_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "regra": self.regra,
            "papel": self.papel,
            "linha": self.linha,
            "coluna": self.coluna,
            "linha_final": self.linha_final,
            "coluna_final": self.coluna_final,
            "atributos": self.atributos,
            "passo": self.passo,
            "filhos": [f.como_dict() for f in self.filhos],
        }


@dataclass
class ErroSintatico:
    codigo: str
    linha: int
    coluna: int
    linha_final: int
    coluna_final: int
    encontrado: str
    encontrado_tipo: str
    esperado: list[str]
    regra: str
    mensagem: str
    tipo: str = "ERRO_SINTATICO"

    def como_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "codigo": self.codigo,
            "linha": self.linha,
            "coluna": self.coluna,
            "linha_final": self.linha_final,
            "coluna_final": self.coluna_final,
            "encontrado": self.encontrado,
            "encontrado_tipo": self.encontrado_tipo,
            "esperado": self.esperado,
            "regra": self.regra,
            "producao": GRAMATICA.get(self.regra, ""),
            "mensagem": self.mensagem,
        }


@dataclass
class ResultadoSintatico:
    ast: No | None
    derivacao: dict | None
    erros: list[ErroSintatico]
    passos: list[dict]
    passos_truncados: bool = False

    @property
    def sucesso(self) -> bool:
        return not self.erros

    def contagem_nos(self) -> dict[str, int]:
        contagem: dict[str, int] = {}

        def visitar(no: No) -> None:
            contagem[no.tipo] = contagem.get(no.tipo, 0) + 1
            for filho in no.filhos:
                visitar(filho)

        if self.ast is not None:
            visitar(self.ast)
        return contagem

    def como_dict(self) -> dict:
        return {
            "executado": True,
            "sucesso": self.sucesso,
            "ast": self.ast.como_dict() if self.sucesso and self.ast else None,
            "derivacao": self.derivacao if self.sucesso else None,
            "erros": [e.como_dict() for e in self.erros],
            "contagem_nos": self.contagem_nos() if self.sucesso else {},
            "passos": self.passos,
            "passos_truncados": self.passos_truncados,
            "gramatica": GRAMATICA,
        }


class _Abortar(Exception):
    """Erro sintático já registrado; interrompe a instrução atual (modo pânico)."""


class _LimiteDeErros(Exception):
    """Muitos erros: a análise para."""


def _descrever(token: scanner.Token) -> str:
    """Como o token aparece nas mensagens."""
    if token.tipo == "NOVA_LINHA":
        return "o fim da linha"
    if token.tipo == "FIM_DE_ARQUIVO":
        return "o fim do código"
    if token.tipo == "INDENT":
        return "um recuo (INDENT) no início da linha"
    if token.tipo == "DEDENT":
        return "o fim do bloco (DEDENT)"
    return f"'{token.lexema}'"


def _encontrado(token: scanner.Token) -> str:
    """Valor do campo 'encontrado' do erro."""
    if token.tipo in ("NOVA_LINHA", "FIM_DE_ARQUIVO", "INDENT", "DEDENT"):
        return token.tipo
    return token.lexema


OPERADORES = {"OPERADOR_ARITMETICO", "OPERADOR_RELACIONAL", "OPERADOR_ATRIBUICAO"}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: list[scanner.Token]):
        if not tokens or tokens[-1].tipo != "FIM_DE_ARQUIVO":
            raise ValueError("a lista de tokens deve terminar em FIM_DE_ARQUIVO")
        self.tokens = tokens
        self.pos = 0
        self.erros: list[ErroSintatico] = []
        self.passos: list[dict] = []
        self.passos_truncados = False
        self.pilha: list[str] = []
        # Árvore de derivação: cada regra aberta é um nó; terminais são folhas.
        self.derivacao_pilha: list[dict] = []
        self.derivacao_raiz: dict | None = None

    # -- utilitários ---------------------------------------------------------

    def _atual(self, deslocamento: int = 0) -> scanner.Token:
        indice = min(self.pos + deslocamento, len(self.tokens) - 1)
        return self.tokens[indice]

    def _eh(self, tipo: str, lexema: str | None = None, deslocamento: int = 0) -> bool:
        token = self._atual(deslocamento)
        return token.tipo == tipo and (lexema is None or token.lexema == lexema)

    def _passo(self, tipo: str, descricao: str, **extra) -> int:
        if len(self.passos) >= LIMITE_PASSOS:
            self.passos_truncados = True
            return -1
        token = self._atual()
        passo = {
            "indice": len(self.passos),
            "tipo": tipo,
            "descricao": descricao,
            "pilha": list(self.pilha),
            "token": min(self.pos, len(self.tokens) - 1),
            "linha": token.linha,
            "coluna": token.coluna,
        }
        passo.update(extra)
        self.passos.append(passo)
        return passo["indice"]

    def _entrar(self, regra: str) -> None:
        if len(self.pilha) >= LIMITE_PROFUNDIDADE:
            self._falhar("aninhamento_excessivo",
                         f"o código tem estruturas aninhadas demais (mais de "
                         f"{LIMITE_PROFUNDIDADE} regras abertas ao mesmo tempo). Simplifique "
                         "a expressão ou divida o bloco.", [], self._atual())
        self.pilha.append(regra)
        token = self._atual()
        self._passo("entrar",
                    f"Aplica a regra {regra} ({DESCRICAO_REGRA[regra]}). "
                    f"Próximo token: {_descrever(token)}.",
                    regra=regra)
        no = {"regra": regra, "filhos": []}
        if self.derivacao_pilha:
            self.derivacao_pilha[-1]["filhos"].append(no)
        else:
            self.derivacao_raiz = no
        self.derivacao_pilha.append(no)

    def _sair(self) -> None:
        self.pilha.pop()
        no = self.derivacao_pilha.pop()
        if not no["filhos"] and self.derivacao_pilha:
            # Regra opcional que não consumiu nada: some da árvore de derivação.
            self.derivacao_pilha[-1]["filhos"].remove(no)

    def _consumir(self) -> scanner.Token:
        token = self._atual()
        regra = self.pilha[-1] if self.pilha else "programa"
        self._passo("consumir",
                    f"Consome {_descrever(token)} ({token.tipo}), esperado pela regra {regra}.",
                    regra=regra)
        if self.derivacao_pilha:
            self.derivacao_pilha[-1]["filhos"].append(
                {"terminal": token.tipo, "lexema": token.lexema,
                 "linha": token.linha, "coluna": token.coluna})
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def _no(self, tipo: str, inicio: scanner.Token, fim: scanner.Token,
            atributos: dict | None = None, filhos: list[No] | None = None,
            descricao: str | None = None) -> No:
        no = No(tipo=tipo, regra=TIPOS_DE_NO[tipo], linha=inicio.linha, coluna=inicio.coluna,
                linha_final=fim.linha_final, coluna_final=fim.coluna_final,
                atributos=atributos or {}, filhos=filhos or [])
        texto = descricao or f"Constrói o nó {tipo}."
        no.passo = self._passo("construir", texto, no_tipo=tipo,
                               no_linha=no.linha, no_coluna=no.coluna)
        return no

    @staticmethod
    def _inicio(no: No) -> scanner.Token:
        linha, coluna = (no.extensao[0], no.extensao[1]) if no.extensao else (no.linha, no.coluna)
        return scanner.Token("", "", linha, coluna, linha, coluna)

    @staticmethod
    def _fim(no: No) -> scanner.Token:
        linha, coluna = ((no.extensao[2], no.extensao[3]) if no.extensao
                         else (no.linha_final, no.coluna_final))
        return scanner.Token("", "", linha, coluna, linha, coluna)

    def _erro(self, codigo: str, mensagem: str, esperado: list[str],
              token: scanner.Token | None = None, regra: str | None = None) -> None:
        token = token or self._atual()
        regra = regra or (self.pilha[-1] if self.pilha else "programa")
        texto = f"Erro sintático na linha {token.linha}, coluna {token.coluna}: {mensagem}"
        erro = ErroSintatico(
            codigo=codigo, linha=token.linha, coluna=token.coluna,
            linha_final=token.linha_final,
            coluna_final=max(token.coluna_final, token.coluna),
            encontrado=_encontrado(token), encontrado_tipo=token.tipo,
            esperado=esperado, regra=regra, mensagem=texto)
        self.erros.append(erro)
        self._passo("erro", texto, erro=len(self.erros) - 1, regra=regra)
        if len(self.erros) >= LIMITE_ERROS:
            raise _LimiteDeErros

    def _falhar(self, codigo: str, mensagem: str, esperado: list[str],
                token: scanner.Token | None = None, regra: str | None = None) -> None:
        self._erro(codigo, mensagem, esperado, token, regra)
        raise _Abortar

    # -- regra inicial --------------------------------------------------------

    def analisar(self) -> ResultadoSintatico:
        ast = None
        try:
            ast = self._programa()
        except _LimiteDeErros:
            pass
        self._numerar(ast)
        return ResultadoSintatico(ast=ast, derivacao=self.derivacao_raiz, erros=self.erros,
                                  passos=self.passos, passos_truncados=self.passos_truncados)

    @staticmethod
    def _numerar(ast: No | None) -> None:
        contador = 0

        def visitar(no: No) -> None:
            nonlocal contador
            no.id = contador
            contador += 1
            for filho in no.filhos:
                visitar(filho)

        if ast is not None:
            visitar(ast)

    def _programa(self) -> No:
        self._entrar("programa")
        instrucoes: list[No] = []
        while not self._eh("FIM_DE_ARQUIVO"):
            no = self._instrucao_com_recuperacao()
            if no is not None:
                instrucoes.append(no)
        fim = self._consumir()
        inicio = scanner.Token("", "", 1, 1, 1, 1)
        programa = self._no("PROGRAMA", inicio, fim, {"instrucoes": len(instrucoes)}, instrucoes,
                            f"Constrói o nó PROGRAMA com {len(instrucoes)} instrução(ões) "
                            "no nível principal.")
        programa.coluna_final = max(programa.coluna_final, 0)
        self._sair()
        return programa

    def _instrucao_com_recuperacao(self) -> No | None:
        """Analisa uma instrução; em caso de erro, sincroniza no fim da linha."""
        profundidade = len(self.pilha)
        profundidade_derivacao = len(self.derivacao_pilha)
        inicio = self.pos
        if self._eh("INDENT"):
            self._bloco_orfao()
            return None
        try:
            return self._instrucao()
        except _Abortar:
            # Fecha as regras que estavam abertas quando o erro aconteceu.
            del self.pilha[profundidade:]
            del self.derivacao_pilha[profundidade_derivacao:]
            self._sincronizar()
            if self.pos == inicio and not self._eh("FIM_DE_ARQUIVO"):
                self.pos += 1  # garante progresso, mesmo diante de um token inesperado
            return None

    def _bloco_orfao(self) -> None:
        """Linha recuada sem estrutura que abra bloco: registra o erro e analisa
        as instruções recuadas mesmo assim (descartando-as), sem erros em cascata."""
        self._erro("indentacao_inesperada",
                   "esta linha está recuada, mas não há um if, elif, else ou while "
                   "terminado em ':' na linha anterior. Em Python, o recuo só é usado "
                   "para o bloco de uma estrutura. Remova o recuo ou complete a estrutura.",
                   ["IDENTIFICADOR", "if", "while"], self._atual(), "instrucao")
        self.pos += 1
        while not self._eh("DEDENT") and not self._eh("FIM_DE_ARQUIVO"):
            self._instrucao_com_recuperacao()
        if self._eh("DEDENT"):
            self.pos += 1

    def _sincronizar(self) -> None:
        """Modo pânico: descarta tokens até o fim da linha. Se a linha abria um
        bloco (NOVA_LINHA seguida de INDENT), o bloco é analisado mesmo assim,
        para que os erros dentro dele também apareçam, mas é descartado."""
        descartados = []
        while not self._eh("NOVA_LINHA") and not self._eh("FIM_DE_ARQUIVO") \
                and not self._eh("DEDENT"):
            descartados.append(self.tokens[self.pos].lexema)
            self.pos += 1
        if self._eh("NOVA_LINHA"):
            self.pos += 1
        texto = " ".join(d for d in descartados if d) or "nenhum token"
        self._passo("recuperar",
                    f"Recuperação de erro (modo pânico): descarta até o fim da linha "
                    f"({texto}) e recomeça na próxima instrução.")
        if self._eh("INDENT"):
            # O bloco pertence à linha com erro: é analisado, mas descartado.
            self.pos += 1
            while not self._eh("DEDENT") and not self._eh("FIM_DE_ARQUIVO"):
                self._instrucao_com_recuperacao()
            if self._eh("DEDENT"):
                self.pos += 1

    # -- instruções -----------------------------------------------------------

    def _instrucao(self) -> No:
        """Escolhe a alternativa olhando o próximo token (e, para distinguir
        atribuição de chamada, também o seguinte: LL(2) nesse ponto)."""
        self._entrar("instrucao")
        token = self._atual()
        if token.tipo == "PALAVRA_RESERVADA" and token.lexema == "if":
            no = self._condicional()
        elif token.tipo == "PALAVRA_RESERVADA" and token.lexema == "while":
            no = self._repeticao()
        elif token.tipo == "IDENTIFICADOR" and self._eh("OPERADOR_ATRIBUICAO", deslocamento=1):
            no = self._atribuicao()
        elif token.tipo == "IDENTIFICADOR" and self._eh("DELIMITADOR", "(", deslocamento=1):
            no = self._chamada_simples()
        else:
            self._instrucao_invalida(token)
            raise AssertionError("inalcançável")
        self._sair()
        return no

    def _instrucao_invalida(self, token: scanner.Token) -> None:
        """Explica por que o token não pode começar uma instrução."""
        esperado = ["IDENTIFICADOR", "if", "while"]
        if token.tipo == "PALAVRA_RESERVADA" and token.lexema in ("elif", "else"):
            self._falhar(f"{token.lexema}_sem_if",
                         f"'{token.lexema}' só pode aparecer logo depois do bloco de um if "
                         f"(ou de um elif), no mesmo nível de indentação. Verifique se existe "
                         f"um if antes dele e se o recuo do '{token.lexema}' é igual ao do if.",
                         esperado)
        if token.tipo == "PALAVRA_RESERVADA" and self._eh("OPERADOR_ATRIBUICAO", deslocamento=1):
            self._falhar("palavra_reservada_como_identificador",
                         f"'{token.lexema}' é uma palavra reservada e não pode ser usada como "
                         "nome de variável. Escolha outro nome.",
                         ["IDENTIFICADOR"])
        if token.tipo == "PALAVRA_RESERVADA" and token.lexema not in scanner.PALAVRAS_RESERVADAS:
            self._falhar("palavra_fora_do_subconjunto",
                         f"'{token.lexema}' é uma palavra reservada de Python, mas a construção "
                         "que ela inicia não faz parte do subconjunto. As instruções aceitas são "
                         "atribuição, chamada de função, if/elif/else e while.",
                         esperado)
        if token.tipo == "NOVA_LINHA":
            self._falhar("token_inesperado", "esperava-se o início de uma instrução.", esperado)
        if token.tipo == "DELIMITADOR" and token.lexema == ")":
            self._falhar("parentese_sem_abertura",
                         "')' fecha um parêntese que não foi aberto.", esperado)
        # Uma expressão usada sozinha como instrução: analisa a expressão
        # para dar uma mensagem precisa.
        inicio = self.pos
        try:
            expressao = self._expressao()
        except _Abortar:
            raise
        fim = self._atual()
        if expressao.tipo == "COMPARACAO" and expressao.atributos.get("operador") == "==" \
                and fim.tipo == "NOVA_LINHA":
            self._falhar("expressao_sem_efeito",
                         "a comparação '==' sozinha não faz nada. Para guardar um valor em "
                         "uma variável use '=' (atribuição); '==' só compara dois valores, "
                         "por exemplo na condição de um if.",
                         ["="], self.tokens[inicio], "instrucao")
        if fim.tipo == "OPERADOR_ATRIBUICAO":
            self._falhar("atribuicao_invalida",
                         "o lado esquerdo de '=' deve ser apenas o nome de uma variável; "
                         "não é possível atribuir um valor a uma expressão ou a um literal.",
                         ["IDENTIFICADOR"], self.tokens[inicio], "atribuicao")
        if fim.tipo == "NOVA_LINHA":
            self._falhar("expressao_sem_efeito",
                         "esta linha contém só uma expressão, que é calculada e descartada. "
                         "Uma instrução deve ser uma atribuição (nome = valor), uma chamada de "
                         "função como print(...), um if ou um while.",
                         esperado, self.tokens[inicio], "instrucao")
        self._fim_de_instrucao(fim, "instrucao")

    def _operador_logico(self, token: scanner.Token) -> None:
        """'and', 'or', 'not', 'in' e 'is' são operadores em Python, mas não no subconjunto."""
        if token.tipo == "PALAVRA_RESERVADA" and token.lexema in OPERADORES_LOGICOS:
            self._falhar("operador_logico_fora_do_subconjunto",
                         f"'{token.lexema}' ({OPERADORES_LOGICOS[token.lexema]}) é um operador de "
                         "Python, mas não faz parte do subconjunto. Use um if dentro de outro "
                         "if para combinar condições.", ["NOVA_LINHA", ":"], token)

    def _fim_de_instrucao(self, token: scanner.Token, regra: str) -> None:
        self._operador_logico(token)
        anterior = self.tokens[self.pos - 1] if self.pos > 0 else token
        if token.tipo == "DELIMITADOR" and token.lexema == ")":
            self._falhar("parentese_sem_abertura",
                         "')' fecha um parêntese que não foi aberto nesta expressão.",
                         ["NOVA_LINHA"], token, regra)
        if token.tipo == "OPERADOR_RELACIONAL" and regra == "comparacao":
            self._falhar("comparacao_encadeada",
                         f"comparações encadeadas como 'a < b {token.lexema} c' não fazem parte "
                         "do subconjunto: cada comparação aceita um único operador relacional.",
                         ["NOVA_LINHA"], token, "comparacao")
        dica = ""
        if token.tipo in ("IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING") \
                or (token.tipo == "DELIMITADOR" and token.lexema == "("):
            dica = (f" Falta um operador entre '{anterior.lexema}' e '{token.lexema}'?"
                    if anterior.lexema else "")
        self._falhar("fim_de_instrucao_esperado",
                     f"era esperado o fim da instrução, mas foi encontrado {_descrever(token)}."
                     f"{dica} Em Python cada instrução ocupa uma linha.",
                     ["NOVA_LINHA"], token, regra)

    def _esperar_fim_de_linha(self, regra: str) -> scanner.Token:
        if self._eh("NOVA_LINHA"):
            return self._consumir()
        self._fim_de_instrucao(self._atual(), regra)
        raise AssertionError("inalcançável")

    def _atribuicao(self) -> No:
        self._entrar("atribuicao")
        nome = self._consumir()
        alvo = self._no("IDENTIFICADOR", nome, nome, {"nome": nome.lexema},
                        descricao=f"Constrói o nó IDENTIFICADOR '{nome.lexema}' (alvo da atribuição).")
        alvo.papel = "alvo"
        igual = self._consumir()
        if self._eh("NOVA_LINHA") or self._eh("FIM_DE_ARQUIVO"):
            self._falhar("expressao_ausente",
                         f"depois de '=' era esperado o valor a ser guardado em '{nome.lexema}', "
                         f"mas foi encontrado {_descrever(self._atual())}.",
                         ["expressao"], regra="atribuicao")
        self._exigir_operando(igual)
        valor = self._expressao()
        valor.papel = "valor"
        self._esperar_fim_de_linha("atribuicao")
        no = self._no("ATRIBUICAO", nome, self._fim(valor), {"nome": nome.lexema}, [alvo, valor],
                      f"Constrói o nó ATRIBUICAO: o valor da expressão será guardado em "
                      f"'{nome.lexema}'.")
        self._sair()
        return no

    def _chamada_simples(self) -> No:
        self._entrar("chamada_simples")
        chamada = self._chamada()
        self._esperar_fim_de_linha("chamada_simples")
        self._sair()
        return chamada

    def _dois_pontos(self, construcao: str, regra: str) -> None:
        """Espera ':'. Se a linha acabou, registra o erro e continua como se o
        ':' estivesse lá (recuperação por inserção), para analisar o bloco."""
        if self._eh("DELIMITADOR", ":"):
            self._consumir()
            return
        token = self._atual()
        self._operador_logico(token)
        mensagem = (f"era esperado ':' no fim da linha do {construcao}, mas foi encontrado "
                    f"{_descrever(token)}. Em Python, toda linha que abre um bloco "
                    "(if, elif, else, while) termina com dois-pontos.")
        if token.tipo == "NOVA_LINHA":
            self._erro("dois_pontos_ausente", mensagem, [":"], token, regra)
            self._passo("recuperar", "Recuperação por inserção: continua como se o ':' "
                                     "estivesse no fim da linha, para analisar o bloco.")
            return
        if token.tipo == "OPERADOR_ATRIBUICAO":
            mensagem = ("'=' guarda um valor e não pode ser usado em uma condição. "
                        "Para comparar dois valores use '=='.")
            self._falhar("atribuicao_na_condicao", mensagem, ["==", ":"], token, regra)
        self._falhar("dois_pontos_ausente", mensagem, [":"], token, regra)

    def _bloco(self, construcao: str, linha_abertura: int) -> No:
        self._entrar("bloco")
        if self._eh("NOVA_LINHA"):
            inicio_linha = self._consumir()
        else:
            token = self._atual()
            self._falhar("bloco_na_mesma_linha",
                         f"o bloco do {construcao} deve começar na linha seguinte, recuado. "
                         "Instruções na mesma linha depois de ':' não fazem parte do "
                         "subconjunto.", ["NOVA_LINHA"], token, "bloco")
        if not self._eh("INDENT"):
            token = self._atual()
            if token.tipo == "FIM_DE_ARQUIVO":
                self._falhar("fim_inesperado",
                             f"o código terminou antes do bloco do {construcao} aberto na linha "
                             f"{linha_abertura}. Escreva pelo menos uma instrução recuada "
                             "depois dos dois-pontos.", ["INDENT"], token, "bloco")
            self._falhar("bloco_ausente",
                         f"o {construcao} da linha {linha_abertura} precisa de um bloco: "
                         "a linha seguinte deve estar recuada (por exemplo, 4 espaços) em "
                         "relação a ele. Foi encontrado "
                         f"{_descrever(token)} sem recuo.", ["INDENT"], token, "bloco")
        self._consumir()  # INDENT
        instrucoes: list[No] = []
        while not self._eh("DEDENT") and not self._eh("FIM_DE_ARQUIVO"):
            no = self._instrucao_com_recuperacao()
            if no is not None:
                instrucoes.append(no)
        fim = self._consumir() if self._eh("DEDENT") else self._atual()
        primeiro = instrucoes[0] if instrucoes else None
        ultimo = instrucoes[-1] if instrucoes else None
        bloco = self._no("BLOCO", self._inicio(primeiro) if primeiro else inicio_linha,
                         self._fim(ultimo) if ultimo else fim,
                         {"instrucoes": len(instrucoes)}, instrucoes,
                         f"Constrói o nó BLOCO do {construcao} com {len(instrucoes)} "
                         "instrução(ões). O DEDENT marcou o fim do bloco.")
        self._sair()
        return bloco

    def _condicional(self) -> No:
        self._entrar("condicional")
        inicio = self._consumir()  # if
        condicao = self._condicao("if")
        self._dois_pontos("if", "condicional")
        entao = self._bloco("if", inicio.linha)
        entao.papel = "então"
        filhos = [condicao, entao]
        while self._eh("PALAVRA_RESERVADA", "elif"):
            token_elif = self._consumir()
            cond_elif = self._condicao("elif")
            self._dois_pontos("elif", "condicional")
            bloco_elif = self._bloco("elif", token_elif.linha)
            bloco_elif.papel = "então"
            ramo = self._no("SENAO_SE", token_elif, self._fim(bloco_elif), {},
                            [cond_elif, bloco_elif],
                            "Constrói o nó SENAO_SE (elif): outra condição, testada só se as "
                            "anteriores forem falsas.")
            ramo.papel = "senão se"
            filhos.append(ramo)
        if self._eh("PALAVRA_RESERVADA", "else"):
            token_else = self._consumir()
            self._dois_pontos("else", "condicional")
            senao = self._bloco("else", token_else.linha)
            senao.papel = "senão"
            filhos.append(senao)
        no = self._no("CONDICIONAL", inicio, self._fim(filhos[-1]),
                      {"elif": sum(1 for f in filhos if f.tipo == "SENAO_SE"),
                       "else": filhos[-1].papel == "senão"}, filhos,
                      "Constrói o nó CONDICIONAL com a condição e os blocos.")
        self._sair()
        return no

    def _condicao(self, construcao: str) -> No:
        token = self._atual()
        if token.tipo in ("NOVA_LINHA", "FIM_DE_ARQUIVO") or (
                token.tipo == "DELIMITADOR" and token.lexema == ":"):
            self._falhar("condicao_ausente",
                         f"depois de '{construcao}' era esperada uma condição (por exemplo, "
                         f"x > 0), mas foi encontrado {_descrever(token)}.",
                         ["expressao"], token, "condicional" if construcao != "while" else "repeticao")
        condicao = self._expressao()
        condicao.papel = "condição"
        return condicao

    def _repeticao(self) -> No:
        self._entrar("repeticao")
        inicio = self._consumir()  # while
        condicao = self._condicao("while")
        self._dois_pontos("while", "repeticao")
        corpo = self._bloco("while", inicio.linha)
        corpo.papel = "corpo"
        no = self._no("REPETICAO", inicio, self._fim(corpo), {}, [condicao, corpo],
                      "Constrói o nó REPETICAO: o corpo se repete enquanto a condição "
                      "for verdadeira.")
        self._sair()
        return no

    # -- expressões -----------------------------------------------------------

    def _expressao(self) -> No:
        self._entrar("expressao")
        no = self._comparacao()
        self._sair()
        return no

    def _comparacao(self) -> No:
        self._entrar("comparacao")
        esquerda = self._soma()
        if self._eh("OPERADOR_RELACIONAL"):
            operador = self._consumir()
            self._exigir_operando(operador)
            direita = self._soma()
            esquerda.papel, direita.papel = "esquerda", "direita"
            esquerda = self._no("COMPARACAO", self._inicio(esquerda), self._fim(direita),
                                {"operador": operador.lexema}, [esquerda, direita],
                                f"Constrói o nó COMPARACAO '{operador.lexema}' com os dois "
                                "lados já analisados.")
            if self._eh("OPERADOR_RELACIONAL"):
                self._fim_de_instrucao(self._atual(), "comparacao")
        self._sair()
        return esquerda

    def _binaria(self, regra: str, operadores: set[str], proxima) -> No:
        self._entrar(regra)
        esquerda = proxima()
        while self._eh("OPERADOR_ARITMETICO") and self._atual().lexema in operadores:
            operador = self._consumir()
            self._exigir_operando(operador)
            direita = proxima()
            tipo = OPERACOES_BINARIAS[operador.lexema]
            esquerda.papel, direita.papel = "esquerda", "direita"
            esquerda = self._no(tipo, self._inicio(esquerda), self._fim(direita),
                                {"operador": operador.lexema}, [esquerda, direita],
                                f"Constrói o nó {tipo} ('{operador.lexema}'). O que já foi "
                                "lido fica à esquerda: por isso a operação é associativa à "
                                "esquerda.")
        self._sair()
        return esquerda

    def _soma(self) -> No:
        return self._binaria("soma", {"+", "-"}, self._termo)

    def _termo(self) -> No:
        return self._binaria("termo", {"*", "/", "%"}, self._fator)

    def _exigir_operando(self, operador: scanner.Token) -> None:
        """Diagnósticos de operando ausente logo depois de um operador."""
        token = self._atual()
        if token.tipo in ("NOVA_LINHA", "FIM_DE_ARQUIVO") or (
                token.tipo == "DELIMITADOR" and token.lexema in (")", ":", ",")):
            self._falhar("operando_ausente",
                         f"o operador '{operador.lexema}' precisa de um valor à direita, mas "
                         f"foi encontrado {_descrever(token)}.",
                         ["expressao"], token, self.pilha[-1] if self.pilha else "expressao")
        if token.tipo in OPERADORES and not (
                token.tipo == "OPERADOR_ARITMETICO" and token.lexema in ("+", "-")):
            self._falhar("operadores_consecutivos",
                         f"dois operadores seguidos: '{operador.lexema}' e '{token.lexema}'. "
                         f"Depois de '{operador.lexema}' era esperado um valor (número, nome "
                         "ou expressão entre parênteses).",
                         ["expressao"], token, self.pilha[-1] if self.pilha else "expressao")

    def _fator(self) -> No:
        self._entrar("fator")
        if self._eh("OPERADOR_ARITMETICO") and self._atual().lexema in ("+", "-"):
            operador = self._consumir()
            self._exigir_operando(operador)
            operando = self._fator()
            operando.papel = "operando"
            no = self._no("OPERACAO_UNARIA", operador, self._fim(operando),
                          {"operador": operador.lexema}, [operando],
                          f"Constrói o nó OPERACAO_UNARIA: sinal '{operador.lexema}' "
                          "aplicado ao fator seguinte.")
        else:
            no = self._primario()
        self._sair()
        return no

    def _primario(self) -> No:
        self._entrar("primario")
        token = self._atual()
        literais = {"LITERAL_INTEIRO": "LITERAL_INTEIRO", "LITERAL_REAL": "LITERAL_REAL",
                    "LITERAL_STRING": "LITERAL_STRING"}
        if token.tipo in literais:
            self._consumir()
            no = self._no(literais[token.tipo], token, token, {"valor": token.lexema},
                          descricao=f"Constrói a folha {token.tipo} com o valor {token.lexema}.")
        elif token.tipo == "PALAVRA_RESERVADA" and token.lexema in ("True", "False"):
            self._consumir()
            no = self._no("LITERAL_LOGICO", token, token, {"valor": token.lexema},
                          descricao=f"Constrói a folha LITERAL_LOGICO com o valor {token.lexema}.")
        elif token.tipo == "IDENTIFICADOR" and self._eh("DELIMITADOR", "(", deslocamento=1):
            no = self._chamada()
        elif token.tipo == "IDENTIFICADOR":
            self._consumir()
            no = self._no("IDENTIFICADOR", token, token, {"nome": token.lexema},
                          descricao=f"Constrói a folha IDENTIFICADOR '{token.lexema}'.")
        elif token.tipo == "DELIMITADOR" and token.lexema == "(":
            abre = self._consumir()
            if self._eh("DELIMITADOR", ")"):
                self._falhar("expressao_ausente",
                             "os parênteses estão vazios: era esperada uma expressão entre "
                             "'(' e ')'.", ["expressao"], self._atual(), "primario")
            no = self._expressao()
            if not self._eh("DELIMITADOR", ")"):
                fim = self._atual()
                self._falhar("parentese_nao_fechado",
                             f"era esperado ')' para fechar o parêntese aberto na linha "
                             f"{abre.linha}, coluna {abre.coluna}, mas foi encontrado "
                             f"{_descrever(fim)}.", [")"], fim, "primario")
            fecha = self._consumir()
            no.extensao = (abre.linha, abre.coluna, fecha.linha, fecha.coluna)
            self._passo("construir",
                        "Os parênteses só agrupam: a AST não guarda um nó para eles. A "
                        "expressão de dentro vira um único filho, o que muda a precedência.",
                        no_tipo=no.tipo, no_linha=no.linha, no_coluna=no.coluna)
        else:
            self._primario_invalido(token)
        self._sair()
        return no

    def _primario_invalido(self, token: scanner.Token) -> None:
        esperado = ["IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING",
                    "True", "False", "("]
        self._operador_logico(token)
        if token.tipo == "FIM_DE_ARQUIVO":
            self._falhar("fim_inesperado",
                         "o código terminou no meio de uma expressão.", esperado, token)
        if token.tipo == "NOVA_LINHA":
            self._falhar("expressao_incompleta",
                         "a linha terminou antes de a expressão ser concluída.", esperado, token)
        if token.tipo == "PALAVRA_RESERVADA":
            self._falhar("palavra_reservada_inesperada",
                         f"'{token.lexema}' é uma palavra reservada e não pode aparecer no "
                         "meio de uma expressão; era esperado um valor (número, string, "
                         "True/False, nome ou expressão entre parênteses).", esperado, token)
        if token.tipo in OPERADORES:
            self._falhar("operando_ausente",
                         f"era esperado um valor antes do operador '{token.lexema}'.",
                         esperado, token)
        self._falhar("token_inesperado",
                     f"era esperado um valor (número, string, True/False, nome ou expressão "
                     f"entre parênteses), mas foi encontrado {_descrever(token)}.",
                     esperado, token)

    def _chamada(self) -> No:
        self._entrar("chamada")
        nome = self._consumir()
        abre = self._consumir()  # (
        argumentos: list[No] = []
        if not self._eh("DELIMITADOR", ")"):
            self._entrar("argumentos")
            while True:
                if self._eh("DELIMITADOR", ",") or self._eh("DELIMITADOR", ")"):
                    self._falhar("argumento_ausente",
                                 f"era esperado um argumento na chamada de '{nome.lexema}', mas "
                                 f"foi encontrado {_descrever(self._atual())}.",
                                 ["expressao"], self._atual(), "argumentos")
                argumento = self._expressao()
                argumento.papel = f"argumento {len(argumentos) + 1}"
                argumentos.append(argumento)
                if not self._eh("DELIMITADOR", ","):
                    break
                self._consumir()
            self._sair()
        if not self._eh("DELIMITADOR", ")"):
            fim = self._atual()
            dica = (" Faltou uma vírgula entre os argumentos?"
                    if fim.tipo in ("IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL",
                                    "LITERAL_STRING") else "")
            self._falhar("parentese_nao_fechado",
                         f"era esperado ')' para fechar a chamada de '{nome.lexema}' aberta na "
                         f"coluna {abre.coluna}, mas foi encontrado {_descrever(fim)}.{dica}",
                         [")", ","], fim, "chamada")
        fecha = self._consumir()
        no = self._no("CHAMADA_FUNCAO", nome, fecha,
                      {"nome": nome.lexema, "argumentos": len(argumentos)}, argumentos,
                      f"Constrói o nó CHAMADA_FUNCAO '{nome.lexema}' com "
                      f"{len(argumentos)} argumento(s).")
        self._sair()
        return no


def analisar_tokens(tokens: list[scanner.Token]) -> ResultadoSintatico:
    """Executa o parser sobre uma lista de tokens já produzida pelo scanner."""
    return Parser(tokens).analisar()


def analisar(codigo: str) -> tuple[scanner.ResultadoLexico, dict]:
    """Fluxo completo: scanner e, se não houver erro léxico, parser.

    Decisão de projeto: com erro léxico o parser não é executado, porque a
    sequência de tokens está incompleta e geraria erros sintáticos sem sentido.
    """
    lexico = scanner.analisar(codigo)
    if not lexico.sucesso:
        return lexico, nao_executado(len(lexico.erros))
    return lexico, analisar_tokens(lexico.tokens).como_dict()


def nao_executado(erros_lexicos: int) -> dict:
    plural = "erro léxico" if erros_lexicos == 1 else "erros léxicos"
    return {
        "executado": False,
        "sucesso": False,
        "ast": None,
        "derivacao": None,
        "erros": [],
        "contagem_nos": {},
        "passos": [],
        "passos_truncados": False,
        "gramatica": GRAMATICA,
        "motivo": (f"A análise sintática não foi executada porque o código tem "
                   f"{erros_lexicos} {plural}. Corrija-os primeiro: com tokens faltando, "
                   "o parser apontaria erros que não existem."),
    }

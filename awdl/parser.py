"""
parser.py

Stage 2 of the AWDL compiler: Syntax Analysis (Parsing).

A hand-written recursive-descent parser. Each grammar rule below has a
matching method. The parser consumes the Token stream produced by the
Lexer and builds an AST (see ast_nodes.py).

Grammar (informal EBNF):

    program     := agent*
    agent       := 'agent' IDENT '{' input_decl step_decl* chain_decl* on_error_decl? '}'
    input_decl  := 'input' ':' IDENT ':' IDENT
    step_decl   := 'step' IDENT '(' [IDENT (',' IDENT)*] ')' '->' IDENT ':' IDENT
    chain_decl  := IDENT ('->' IDENT)+
    on_error    := 'on_error' ':' 'retry' '(' NUMBER ')'

On a syntax error, the parser records it and performs panic-mode recovery:
it skips tokens until it reaches a token that could plausibly start the
next declaration (STEP, ON_ERROR, IDENT, or RBRACE), so that one mistake
doesn't prevent the rest of the file from being checked.
"""

from .lexer import Token, TokenType
from .ast_nodes import Program, AgentDecl, InputDecl, StepDecl, ChainDecl, OnErrorDecl


class ParseError(Exception):
    def __init__(self, message, token: Token):
        super().__init__(f"Syntax error at line {token.line}, col {token.col}: {message}")
        self.token = token


# tokens that can plausibly start a new declaration inside an agent body —
# used as recovery points after a syntax error
RECOVERY_STARTS = {TokenType.STEP, TokenType.ON_ERROR, TokenType.IDENT, TokenType.RBRACE}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: list[ParseError] = []

    # ---- token stream helpers -------------------------------------------------

    def _peek(self, offset: int = 0) -> Token:
        i = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[i]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _check(self, ttype: TokenType) -> bool:
        return self._peek().type == ttype

    def _expect(self, ttype: TokenType, msg: str) -> Token:
        if self._check(ttype):
            return self._advance()
        raise ParseError(f"expected {msg}, found {self._peek().lexeme!r}", self._peek())

    def _synchronize(self):
        """Panic-mode recovery: skip tokens until a safe restart point.

        A bare IDENT only counts as a safe restart if it's actually the
        start of a chain declaration (IDENT followed by ARROW) — otherwise
        we'd stop on leftover identifiers from the broken statement itself.
        """
        while not self._check(TokenType.EOF):
            if self._peek().type in (TokenType.STEP, TokenType.ON_ERROR, TokenType.RBRACE):
                return
            if self._peek().type == TokenType.IDENT and self._peek(1).type == TokenType.ARROW:
                return
            self._advance()

    # ---- grammar rules -------------------------------------------------------

    def parse_program(self) -> Program:
        program = Program()
        while not self._check(TokenType.EOF):
            try:
                program.agents.append(self._parse_agent())
            except ParseError as e:
                self.errors.append(e)
                self._synchronize()
        return program

    def _parse_agent(self) -> AgentDecl:
        self._expect(TokenType.AGENT, "'agent'")
        name_tok = self._expect(TokenType.IDENT, "agent name")
        self._expect(TokenType.LBRACE, "'{'")

        agent = AgentDecl(name=name_tok.lexeme)

        # input declaration (required, appears once)
        self._expect(TokenType.INPUT, "'input' declaration")
        self._expect(TokenType.COLON, "':'")
        in_name = self._expect(TokenType.IDENT, "input name")
        self._expect(TokenType.COLON, "':'")
        in_type = self._expect(TokenType.IDENT, "input type")
        agent.inputs.append(InputDecl(in_name.lexeme, in_type.lexeme))

        # steps, chains, on_error — order-flexible, loop until '}'
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            try:
                if self._check(TokenType.STEP):
                    agent.steps.append(self._parse_step())
                elif self._check(TokenType.ON_ERROR):
                    agent.on_error = self._parse_on_error()
                elif self._check(TokenType.IDENT):
                    agent.chains.append(self._parse_chain())
                else:
                    raise ParseError(
                        f"unexpected token {self._peek().lexeme!r} in agent body",
                        self._peek(),
                    )
            except ParseError as e:
                self.errors.append(e)
                self._synchronize()

        self._expect(TokenType.RBRACE, "'}'")
        return agent

    def _parse_step(self) -> StepDecl:
        step_tok = self._expect(TokenType.STEP, "'step'")
        name_tok = self._expect(TokenType.IDENT, "step name")
        self._expect(TokenType.LPAREN, "'('")

        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENT, "parameter name").lexeme)
            while self._check(TokenType.COMMA):
                self._advance()
                params.append(self._expect(TokenType.IDENT, "parameter name").lexeme)

        self._expect(TokenType.RPAREN, "')'")
        self._expect(TokenType.ARROW, "'->'")
        out_name = self._expect(TokenType.IDENT, "output name")
        self._expect(TokenType.COLON, "':'")
        out_type = self._expect(TokenType.IDENT, "output type")

        return StepDecl(
            name=name_tok.lexeme,
            params=params,
            output_name=out_name.lexeme,
            output_type=out_type.lexeme,
            line=step_tok.line,
        )

    def _parse_chain(self) -> ChainDecl:
        names = [self._expect(TokenType.IDENT, "step name").lexeme]
        while self._check(TokenType.ARROW):
            self._advance()
            names.append(self._expect(TokenType.IDENT, "step name").lexeme)
        return ChainDecl(step_names=names)

    def _parse_on_error(self) -> OnErrorDecl:
        self._expect(TokenType.ON_ERROR, "'on_error'")
        self._expect(TokenType.COLON, "':'")
        self._expect(TokenType.RETRY, "'retry'")
        self._expect(TokenType.LPAREN, "'('")
        num_tok = self._expect(TokenType.NUMBER, "retry count")
        self._expect(TokenType.RPAREN, "')'")
        return OnErrorDecl(strategy="retry", arg=int(num_tok.lexeme))


def parse(tokens: list[Token]) -> tuple[Program, list[ParseError]]:
    parser = Parser(tokens)
    program = parser.parse_program()
    return program, parser.errors

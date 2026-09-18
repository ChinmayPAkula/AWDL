"""
lexer.py

Stage 1 of the AWDL compiler: Lexical Analysis.

Takes raw AWDL source text and converts it into a flat stream of Tokens.
Each Token knows its type, its raw text, and its line/column position
(so later stages can report errors that point at exact source locations).
"""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Keywords
    AGENT = auto()
    INPUT = auto()
    STEP = auto()
    ON_ERROR = auto()
    RETRY = auto()

    # Literals / names
    IDENT = auto()      # e.g. Researcher, search, query, string, list
    NUMBER = auto()      # e.g. 3

    # Symbols
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    COLON = auto()       # :
    ARROW = auto()        # ->
    COMMA = auto()        # ,

    EOF = auto()


KEYWORDS = {
    "agent": TokenType.AGENT,
    "input": TokenType.INPUT,
    "step": TokenType.STEP,
    "on_error": TokenType.ON_ERROR,
    "retry": TokenType.RETRY,
}


@dataclass
class Token:
    type: TokenType
    lexeme: str      # the raw text that produced this token
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.lexeme!r}, line={self.line}, col={self.col})"


class LexerError(Exception):
    """Raised when the lexer encounters a character it cannot tokenize."""
    def __init__(self, message, line, col):
        super().__init__(f"Lexical error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    # ---- low-level helpers -------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else "\0"

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    # ---- main entry point ---------------------------------------------------

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                break
            start_line, start_col = self.line, self.col
            ch = self._peek()

            if ch.isalpha() or ch == "_":
                self._read_identifier_or_keyword(start_line, start_col)
            elif ch.isdigit():
                self._read_number(start_line, start_col)
            elif ch == "{":
                self._advance(); self._add(TokenType.LBRACE, "{", start_line, start_col)
            elif ch == "}":
                self._advance(); self._add(TokenType.RBRACE, "}", start_line, start_col)
            elif ch == "(":
                self._advance(); self._add(TokenType.LPAREN, "(", start_line, start_col)
            elif ch == ")":
                self._advance(); self._add(TokenType.RPAREN, ")", start_line, start_col)
            elif ch == ":":
                self._advance(); self._add(TokenType.COLON, ":", start_line, start_col)
            elif ch == ",":
                self._advance(); self._add(TokenType.COMMA, ",", start_line, start_col)
            elif ch == "-" and self._peek(1) == ">":
                self._advance(); self._advance()
                self._add(TokenType.ARROW, "->", start_line, start_col)
            else:
                raise LexerError(f"unexpected character {ch!r}", start_line, start_col)

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return self.tokens

    # ---- token producers ------------------------------------------------------

    def _skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "#":  # comment to end of line
                while self._peek() not in ("\n", "\0"):
                    self._advance()
            else:
                break

    def _read_identifier_or_keyword(self, line, col):
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.source[start:self.pos]
        ttype = KEYWORDS.get(text, TokenType.IDENT)
        self._add(ttype, text, line, col)

    def _read_number(self, line, col):
        start = self.pos
        while self._peek().isdigit():
            self._advance()
        text = self.source[start:self.pos]
        self._add(TokenType.NUMBER, text, line, col)

    def _add(self, ttype: TokenType, lexeme: str, line: int, col: int):
        self.tokens.append(Token(ttype, lexeme, line, col))


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()

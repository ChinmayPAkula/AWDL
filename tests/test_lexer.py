"""Baseline tests for awdl/lexer.py (Phase 1), recorded before Phase 3 changes."""

import pytest

from awdl.lexer import tokenize, LexerError, TokenType


def test_tokenizes_keywords():
    tokens = tokenize("agent input step on_error retry")
    types = [t.type for t in tokens[:-1]]  # drop EOF
    assert types == [
        TokenType.AGENT,
        TokenType.INPUT,
        TokenType.STEP,
        TokenType.ON_ERROR,
        TokenType.RETRY,
    ]


def test_tokenizes_symbols():
    tokens = tokenize("{ } ( ) : -> ,")
    types = [t.type for t in tokens[:-1]]
    assert types == [
        TokenType.LBRACE,
        TokenType.RBRACE,
        TokenType.LPAREN,
        TokenType.RPAREN,
        TokenType.COLON,
        TokenType.ARROW,
        TokenType.COMMA,
    ]


def test_tokenizes_identifiers_and_numbers():
    tokens = tokenize("query results_2 42")
    assert tokens[0].type == TokenType.IDENT
    assert tokens[0].lexeme == "query"
    assert tokens[1].type == TokenType.IDENT
    assert tokens[1].lexeme == "results_2"
    assert tokens[2].type == TokenType.NUMBER
    assert tokens[2].lexeme == "42"


def test_skips_comments_and_whitespace():
    tokens = tokenize("agent # a comment\n  step")
    types = [t.type for t in tokens[:-1]]
    assert types == [TokenType.AGENT, TokenType.STEP]


def test_tracks_line_and_column():
    tokens = tokenize("agent\nstep")
    assert tokens[0].line == 1 and tokens[0].col == 1
    assert tokens[1].line == 2 and tokens[1].col == 1


def test_ends_with_eof():
    tokens = tokenize("agent")
    assert tokens[-1].type == TokenType.EOF


def test_invalid_character_raises_lexer_error_with_position():
    with pytest.raises(LexerError) as exc_info:
        tokenize("agent X { input: q @ string }")
    assert exc_info.value.line == 1
    assert exc_info.value.col == 20


def test_empty_source_produces_only_eof():
    tokens = tokenize("")
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.EOF

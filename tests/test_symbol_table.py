"""Baseline tests for awdl/symbol_table.py (Phase 2)."""

import pytest

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.symbol_table import SymbolTable, DuplicateStepError

RESEARCHER = """
agent Researcher {
  input: query : string
  step search(query) -> results : list
  step summarize(results) -> summary : string
}
"""


def _build_symtab(source):
    program, _ = parse(tokenize(source))
    agent = program.agents[0]
    symtab = SymbolTable()
    for inp in agent.inputs:
        symtab.define_input(inp)
    for step in agent.steps:
        symtab.define_step(step)
    return symtab, agent


def test_resolve_input():
    symtab, _ = _build_symtab(RESEARCHER)
    resolved = symtab.resolve("query")
    assert resolved.name == "query"
    assert resolved.type_name == "string"


def test_resolve_step_output():
    symtab, _ = _build_symtab(RESEARCHER)
    resolved = symtab.resolve("results")
    assert resolved.name == "search"


def test_resolve_unknown_returns_none():
    symtab, _ = _build_symtab(RESEARCHER)
    assert symtab.resolve("nonexistent") is None


def test_all_step_names():
    symtab, _ = _build_symtab(RESEARCHER)
    assert symtab.all_step_names() == {"search", "summarize"}


def test_duplicate_step_raises():
    symtab, agent = _build_symtab(RESEARCHER)
    with pytest.raises(DuplicateStepError):
        symtab.define_step(agent.steps[0])

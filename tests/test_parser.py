"""Baseline tests for awdl/parser.py (Phase 1), recorded before Phase 3 changes."""

from awdl.lexer import tokenize
from awdl.parser import parse

RESEARCHER = """
agent Researcher {
  input: query : string

  step search(query) -> results : list
  step summarize(results) -> summary : string
  step validate(summary) -> final : string

  search -> summarize -> validate

  on_error: retry(3)
}
"""

BROKEN = """
agent Researcher {
  input: query : string

  step search(query) -> results : list
  step summarize(results -> summary : string

  step validate(summary) -> final : string

  search -> summarize -> validate

  on_error: retry(3)
}
"""


def test_valid_program_has_no_errors():
    program, errors = parse(tokenize(RESEARCHER))
    assert errors == []
    assert len(program.agents) == 1


def test_valid_program_structure():
    program, _ = parse(tokenize(RESEARCHER))
    agent = program.agents[0]
    assert agent.name == "Researcher"
    assert [s.name for s in agent.steps] == ["search", "summarize", "validate"]
    assert agent.chains[0].step_names == ["search", "summarize", "validate"]
    assert agent.on_error.strategy == "retry"
    assert agent.on_error.arg == 3


def test_panic_mode_recovery_still_parses_remaining_steps():
    program, errors = parse(tokenize(BROKEN))
    assert len(errors) == 1
    assert "expected ')'" in str(errors[0])
    agent = program.agents[0]
    # summarize's broken declaration is skipped, but validate still parses
    assert [s.name for s in agent.steps] == ["search", "validate"]


def test_empty_program_has_no_agents():
    program, errors = parse(tokenize(""))
    assert program.agents == []
    assert errors == []


def test_missing_input_declaration_is_a_syntax_error():
    # Recovery cascades (there's no 'input' to anchor on), but it must
    # terminate and report at least the root cause - see parser.py's
    # parse_program() forced-progress fix.
    source = "agent X { step a() -> b : string }"
    program, errors = parse(tokenize(source))
    assert len(errors) >= 1
    assert "expected 'input' declaration" in str(errors[0])


def test_multiple_agents_in_one_file():
    source = """
    agent A { input: x : string }
    agent B { input: y : number }
    """
    program, errors = parse(tokenize(source))
    assert errors == []
    assert [a.name for a in program.agents] == ["A", "B"]

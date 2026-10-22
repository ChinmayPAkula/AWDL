"""Baseline tests for awdl/ir.py (Phase 2)."""

import pytest

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.semantic import analyze
from awdl.ir import build_ir, topo_order, CycleError


def _build(source):
    program, _ = parse(tokenize(source))
    symtabs, errors, _ = analyze(program)
    agent = program.agents[0]
    assert errors == []
    return build_ir(agent, symtabs[agent.name])


RESEARCHER = """
agent Researcher {
  input: query : string
  step search(query) -> results : list
  step summarize(results) -> summary : string
  step validate(summary) -> final : string
  search -> summarize -> validate
}
"""


def test_depends_on_derived_from_params():
    agent_ir = _build(RESEARCHER)
    assert agent_ir.nodes["search"].depends_on == set()
    assert agent_ir.nodes["summarize"].depends_on == {"search"}
    assert agent_ir.nodes["validate"].depends_on == {"summarize"}


def test_topo_order_respects_dependencies():
    agent_ir = _build(RESEARCHER)
    order = topo_order(agent_ir)
    assert order.index("search") < order.index("summarize") < order.index("validate")


def test_entry_input_captured():
    agent_ir = _build(RESEARCHER)
    assert agent_ir.entry_input == "query"


def test_topo_order_one_step():
    source = """
    agent A {
      input: x : string
      step only(x) -> y : string
    }
    """
    agent_ir = _build(source)
    assert topo_order(agent_ir) == ["only"]


def test_topo_order_diamond():
    source = """
    agent A {
      input: x : string
      step a(x) -> a_out : string
      step b(a_out) -> b_out : string
      step c(a_out) -> c_out : string
      step d(b_out, c_out) -> d_out : string
    }
    """
    agent_ir = _build(source)
    order = topo_order(agent_ir)
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("d")
    assert order.index("c") < order.index("d")

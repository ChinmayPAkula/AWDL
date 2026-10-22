"""Tests for awdl/codegen.py (Phase 3)."""

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.semantic import analyze
from awdl.ir import build_ir
from awdl.optimizer import optimize
from awdl.codegen import generate_plan, plan_to_json

WIDE = """
agent Reporter {
  input: query : string
  step fetch_news(query) -> news : string
  step fetch_weather(query) -> weather : string
  step combine(news, weather) -> report : string
  fetch_news -> combine
  fetch_weather -> combine
}
"""


def _plan(source):
    program, _ = parse(tokenize(source))
    symtabs, errors, _ = analyze(program)
    agent = program.agents[0]
    assert errors == []
    chain_endpoints = {c.step_names[-1] for c in agent.chains}
    agent_ir = build_ir(agent, symtabs[agent.name])
    optimized_ir, report = optimize(agent_ir, chain_endpoints)
    return generate_plan(optimized_ir, report, chain_endpoints)


def test_levels_reflect_optimizer_grouping():
    plan = _plan(WIDE)
    assert [s["step"] for s in plan["levels"][0]] == ["fetch_news", "fetch_weather"]
    assert [s["step"] for s in plan["levels"][1]] == ["combine"]


def test_input_and_on_error_captured():
    plan = _plan(WIDE)
    assert plan["input"] == {"name": "query", "type": "string"}
    assert plan["on_error"] is None


def test_final_outputs_from_chain_endpoints():
    plan = _plan(WIDE)
    assert plan["final_outputs"] == ["report"]


def test_final_outputs_without_chains_falls_back_to_unconsumed():
    # With no chains, dead-step elimination has already removed any step
    # whose output is unconsumed (that's the definition of dead without a
    # chain to protect it) - so after optimization the only thing left
    # "unconsumed" is whatever the optimizer judged meaningful to keep.
    # Here 'b' is dead (nothing consumes b_out, no chain names it), so only
    # 'a' survives and a_out is correctly reported as the final output.
    source = """
    agent A {
      input: x : string
      step a(x) -> a_out : string
      step b(a_out) -> b_out : string
    }
    """
    plan = _plan(source)
    assert plan["final_outputs"] == ["a_out"]
    all_steps = [s["step"] for level in plan["levels"] for s in level]
    assert all_steps == ["a"]


def test_dead_steps_are_absent_from_the_plan():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      step unused(query) -> scratch : string
      step summarize(results) -> summary : string
      search -> summarize
    }
    """
    plan = _plan(source)
    all_steps = [s["step"] for level in plan["levels"] for s in level]
    assert "unused" not in all_steps


def test_plan_to_json_is_deterministic():
    plan1 = _plan(WIDE)
    plan2 = _plan(WIDE)
    assert plan_to_json(plan1) == plan_to_json(plan2)


def test_plan_is_valid_json():
    import json
    plan = _plan(WIDE)
    json.loads(plan_to_json(plan))  # must not raise

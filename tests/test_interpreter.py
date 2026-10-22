"""Tests for awdl/interpreter.py (Phase 3)."""

import pytest

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.semantic import analyze
from awdl.ir import build_ir
from awdl.optimizer import optimize
from awdl.codegen import generate_plan
from awdl.interpreter import execute, AWDLRuntimeError, InputTypeError
from awdl.steps import StepRegistry


def _plan(source):
    program, _ = parse(tokenize(source))
    symtabs, errors, _ = analyze(program)
    agent = program.agents[0]
    assert errors == []
    chain_endpoints = {c.step_names[-1] for c in agent.chains}
    agent_ir = build_ir(agent, symtabs[agent.name])
    optimized_ir, report = optimize(agent_ir, chain_endpoints)
    return generate_plan(optimized_ir, report, chain_endpoints)


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


def test_runs_end_to_end_with_mocks_only():
    plan = _plan(RESEARCHER)
    result = execute(plan, "some query")
    assert result.ok
    assert "final" in result.final_outputs


def test_sequential_and_parallel_produce_same_final_outputs():
    plan = _plan(WIDE)
    seq = execute(plan, "x", sequential=True)
    par = execute(plan, "x", sequential=False)
    assert seq.final_outputs == par.final_outputs


def test_retry_recovers_from_transient_failure():
    plan = _plan(RESEARCHER)  # retry(3) -> 4 total attempts
    registry = StepRegistry()
    registry.inject_failure("search", times=2)
    result = execute(plan, "q", registry=registry)
    search_record = next(r for r in result.records if r.step == "search")
    assert search_record.status == "ok"
    assert search_record.attempts == 3


def test_retry_exhausted_raises_and_skips_downstream():
    plan = _plan(RESEARCHER)  # retry(3) -> 4 total attempts
    registry = StepRegistry()
    registry.inject_failure("search", times=10)  # more than it'll ever get

    with pytest.raises(AWDLRuntimeError) as exc_info:
        execute(plan, "q", registry=registry)

    err = exc_info.value
    assert err.step == "search"
    assert err.attempts == 4
    result = err.result
    search_record = next(r for r in result.records if r.step == "search")
    assert search_record.status == "failed"
    downstream = [r for r in result.records if r.step in ("summarize", "validate")]
    assert all(r.status == "skipped" for r in downstream)


def test_no_error_policy_fails_on_first_attempt():
    source = """
    agent A {
      input: x : string
      step a(x) -> y : string
      a
    }
    """
    plan = _plan(source)
    registry = StepRegistry()
    registry.inject_failure("a", times=1)
    with pytest.raises(AWDLRuntimeError) as exc_info:
        execute(plan, "x", registry=registry)
    assert exc_info.value.attempts == 1


def test_wrong_typed_return_value_is_a_runtime_error():
    source = """
    agent A {
      input: x : string
      step a(x) -> y : number
      a
    }
    """
    plan = _plan(source)
    registry = StepRegistry()
    registry.register("a", lambda x: "not a number")
    with pytest.raises(AWDLRuntimeError):
        execute(plan, "x", registry=registry)


def test_bad_input_type_rejected_before_running_anything():
    plan = _plan(RESEARCHER)
    with pytest.raises(InputTypeError):
        execute(plan, 12345)  # input is declared string


def test_independent_steps_both_run_when_one_in_same_level_fails():
    plan = _plan(WIDE)
    registry = StepRegistry()
    registry.inject_failure("fetch_news", times=10)
    with pytest.raises(AWDLRuntimeError) as exc_info:
        execute(plan, "x", registry=registry)
    result = exc_info.value.result
    weather_record = next(r for r in result.records if r.step == "fetch_weather")
    assert weather_record.status == "ok"
    combine_record = next(r for r in result.records if r.step == "combine")
    assert combine_record.status == "skipped"

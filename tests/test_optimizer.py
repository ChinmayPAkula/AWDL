"""Baseline tests for awdl/optimizer.py (Phase 2)."""

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.semantic import analyze
from awdl.ir import build_ir
from awdl.optimizer import optimize, parallel_levels


def _build(source):
    program, _ = parse(tokenize(source))
    symtabs, errors, _ = analyze(program)
    agent = program.agents[0]
    assert errors == []
    chain_endpoints = {c.step_names[-1] for c in agent.chains}
    agent_ir = build_ir(agent, symtabs[agent.name])
    return agent_ir, chain_endpoints


def test_dead_step_removed():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      step unused(query) -> scratch : string
      step summarize(results) -> summary : string
      search -> summarize
    }
    """
    agent_ir, chain_endpoints = _build(source)
    optimized_ir, report = optimize(agent_ir, chain_endpoints)
    assert report.removed_dead_steps == ["unused"]
    assert "unused" not in optimized_ir.nodes


def test_chain_endpoint_is_never_dead():
    source = """
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      search -> search
    }
    """
    # single-step chain keeps 'search' alive even though nothing consumes it
    agent_ir, chain_endpoints = _build("""
    agent Researcher {
      input: query : string
      step search(query) -> results : list
      search
    }
    """)
    optimized_ir, report = optimize(agent_ir, chain_endpoints)
    assert report.removed_dead_steps == []
    assert "search" in optimized_ir.nodes


def test_parallel_levels_groups_independent_steps():
    source = """
    agent Reporter {
      input: query : string
      step fetch_news(query) -> news : string
      step fetch_weather(query) -> weather : string
      step combine(news, weather) -> report : string
    }
    """
    agent_ir, _ = _build(source)
    levels = parallel_levels(agent_ir)
    assert levels[0] == ["fetch_news", "fetch_weather"]
    assert levels[1] == ["combine"]


def test_wide_fan_in_fan_out():
    source = """
    agent Wide {
      input: x : string
      step a(x) -> a_out : string
      step b(x) -> b_out : string
      step c(x) -> c_out : string
      step combine(a_out, b_out, c_out) -> result : string
    }
    """
    agent_ir, _ = _build(source)
    levels = parallel_levels(agent_ir)
    assert set(levels[0]) == {"a", "b", "c"}
    assert levels[1] == ["combine"]

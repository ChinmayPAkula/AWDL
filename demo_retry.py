"""
demo_retry.py

Phase 3 demonstration: on_error: retry(n) actually recovering from, and
eventually giving up on, a failing step.

main.py's generic CLI always uses deterministic stub step functions, which
never fail, so retry never has anything to recover from there. This script
compiles examples/retry_demo.awdl the same way main.py does, then runs the
resulting plan twice with real, controlled step functions:

  1. A step that fails on its first two calls and succeeds on the third -
     demonstrates retry(3) recovering a transient failure.
  2. A step that always fails - demonstrates retry(3) correctly exhausting
     its attempts and raising StepExecutionError.

Usage:
    python demo_retry.py
"""

from awdl.lexer import tokenize
from awdl.parser import parse
from awdl.semantic import analyze
from awdl.ir import build_ir
from awdl.optimizer import optimize
from awdl.codegen import generate_plan
from awdl.interpreter import Interpreter, StepExecutionError


def compile_plan(path: str) -> dict:
    source = open(path).read()
    program, parse_errors = parse(tokenize(source))
    assert not parse_errors, parse_errors
    symtabs, sem_errors, _ = analyze(program)
    assert not sem_errors, sem_errors

    agent = program.agents[0]
    agent_ir = build_ir(agent, symtabs[agent.name])
    chain_endpoints = {c.step_names[-1] for c in agent.chains}
    optimized_ir, _ = optimize(agent_ir, chain_endpoints)
    return generate_plan(optimized_ir)


def make_flaky_fetch(fail_times: int):
    """Returns a step function that raises for its first `fail_times` calls,
    then succeeds. A fresh closure per scenario keeps call counts isolated."""
    calls = {"count": 0}

    def fetch(query):
        calls["count"] += 1
        if calls["count"] <= fail_times:
            raise RuntimeError(f"simulated transient failure #{calls['count']}")
        return f"fetched result for {query!r} on attempt {calls['count']}"

    return fetch


def main():
    plan = compile_plan("examples/retry_demo.awdl")

    print("=== Scenario 1: fails twice, then succeeds (retry(3) recovers) ===")
    interpreter = Interpreter({"fetch": make_flaky_fetch(fail_times=2)})
    env = interpreter.run(plan, "weather in Chennai")
    for line in interpreter.trace:
        print(" ", line)
    print("  final variables:", env)

    print()
    print("=== Scenario 2: always fails (retry(3) exhausts and raises) ===")
    interpreter = Interpreter({"fetch": make_flaky_fetch(fail_times=999)})
    try:
        interpreter.run(plan, "weather in Chennai")
    except StepExecutionError as e:
        for line in interpreter.trace:
            print(" ", line)
        print(f"  FAILED as expected: {e}")


if __name__ == "__main__":
    main()

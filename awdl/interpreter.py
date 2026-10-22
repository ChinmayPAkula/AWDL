"""
interpreter.py

Phase 3 - Interpretation and Execution.

A runtime engine that executes a JSON execution plan (produced by codegen.py)
in the dependency order the plan already lists, invoking one step function per
step, and retrying a failed step according to the plan's on_error policy.

Per the project's declared scope (Phase 1 proposal, Section 6: "steps may be
mocked or stubbed functions" - live LLM integration is explicitly out of
scope), a step with no real implementation registered falls back to a
deterministic stub so a pipeline still runs end-to-end for demonstration.
Callers that want real behavior (or a controlled failure, to demonstrate
retry) pass their own step_functions mapping.
"""

from typing import Any, Callable


class StepExecutionError(Exception):
    def __init__(self, step_name: str, attempts: int, last_error: Exception):
        super().__init__(f"step '{step_name}' failed after {attempts} attempt(s): {last_error}")
        self.step_name = step_name
        self.attempts = attempts
        self.last_error = last_error


_PLACEHOLDER_BY_TYPE: dict[str, Callable[[], Any]] = {
    "string": lambda: "<stub output>",
    "number": lambda: 0,
    "boolean": lambda: True,
    "list": lambda: [],
    "object": lambda: {},
}


def default_step_function(output_type: str) -> Callable[..., Any]:
    """A stub step: ignores its arguments and fabricates a value of the
    declared output type, so an unimplemented step doesn't block the rest
    of the pipeline from being demonstrated end-to-end."""
    make_value = _PLACEHOLDER_BY_TYPE.get(output_type, lambda: None)
    return lambda *args, **kwargs: make_value()


class Interpreter:
    def __init__(self, step_functions: dict[str, Callable[..., Any]] | None = None):
        self.step_functions = step_functions or {}
        self.trace: list[str] = []

    def run(self, plan: dict, entry_value: Any) -> dict[str, Any]:
        """Executes every step in the plan's listed order (already a valid
        topological order from codegen.generate_plan). Returns a dict mapping
        every variable name - the agent's input plus each step's output - to
        the value it produced."""
        env: dict[str, Any] = {plan["entry_input"]: entry_value}

        on_error = plan.get("on_error")
        max_attempts = 1
        if on_error and on_error.get("strategy") == "retry":
            max_attempts = 1 + int(on_error.get("arg", 0))

        for step in plan["steps"]:
            args = [env[name] for name in step["inputs"]]
            fn = self.step_functions.get(step["name"]) or default_step_function(step["output_type"])

            result, last_error = None, None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = fn(*args)
                    self.trace.append(f"{step['name']}: ok (attempt {attempt}/{max_attempts})")
                    break
                except Exception as e:
                    last_error = e
                    self.trace.append(f"{step['name']}: failed attempt {attempt}/{max_attempts} ({e})")
            else:
                raise StepExecutionError(step["name"], max_attempts, last_error)

            env[step["output"]] = result

        return env


def run_plan(
    plan: dict,
    entry_value: Any,
    step_functions: dict[str, Callable[..., Any]] | None = None,
) -> dict[str, Any]:
    return Interpreter(step_functions).run(plan, entry_value)

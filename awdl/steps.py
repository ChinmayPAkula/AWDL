"""
steps.py

Phase 3 - Step Registry.

AWDL describes a pipeline's shape; something still has to supply each step's
actual behavior. StepRegistry maps a step name to a Python callable that
takes the step's input values (in declared order) and returns its output
value.

Any step with nothing registered for it falls back to a deterministic mock
(default_mock(output_type)) so an .awdl file runs end to end with zero
setup - this is the project's declared scope (steps are mocked/stubbed;
AWDL orchestrates, it does not ship an LLM client).

Two features exist purely to make the runtime's behavior demonstrable
without writing real flaky code or a real slow one:
  - inject_failure(step, times): the step raises StepFailure on its first
    `times` calls, then calls through to the real/mock function - this is
    how on_error: retry(n) actually gets shown recovering something.
  - set_delay(step, ms) / set_default_delay(ms): sleeps before returning,
    so parallel vs. sequential execution timing is visible on a wide level.
"""

import time
from typing import Any, Callable

_PLACEHOLDER_BY_TYPE: dict[str, Callable[[], Any]] = {
    "string": lambda: "mock",
    "number": lambda: 1,
    "boolean": lambda: True,
    "list": lambda: ["mock"],
    "object": lambda: {"mock": True},
}


class StepFailure(Exception):
    """Raised by an injected failure (see StepRegistry.inject_failure)."""


def default_mock(output_type: str, step_name: str, inputs: list[Any]) -> Any:
    """Deterministically fabricates a value of the declared output type.
    The value always matches output_type so the interpreter's own runtime
    type check (Interpreter._validate_output) never rejects a pure mock."""
    make_value = _PLACEHOLDER_BY_TYPE.get(output_type)
    if make_value is None:
        return None
    if output_type == "string":
        joined = ", ".join(str(v) for v in inputs)
        return f"{step_name}({joined})"[:200]
    return make_value()


class StepRegistry:
    def __init__(self):
        self._functions: dict[str, Callable[..., Any]] = {}
        self._fail_remaining: dict[str, int] = {}
        self._delay_ms: dict[str, float] = {}
        self._default_delay_ms: float = 0.0

    def register(self, step_name: str, fn: Callable[..., Any]) -> None:
        self._functions[step_name] = fn

    def load_file(self, path: str) -> None:
        """Loads a Python file exposing a module-level STEPS = {name: fn}
        dict and registers every entry from it. User-supplied steps override
        mocks for the names they provide."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("awdl_user_steps", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        steps = getattr(module, "STEPS", {})
        for name, fn in steps.items():
            self.register(name, fn)

    def inject_failure(self, step_name: str, times: int) -> None:
        self._fail_remaining[step_name] = self._fail_remaining.get(step_name, 0) + times

    def set_delay(self, step_name: str, ms: float) -> None:
        self._delay_ms[step_name] = ms

    def set_default_delay(self, ms: float) -> None:
        self._default_delay_ms = ms

    def call(self, step_name: str, output_type: str, inputs: list[Any]) -> Any:
        delay = self._delay_ms.get(step_name, self._default_delay_ms)
        if delay:
            time.sleep(delay / 1000.0)

        remaining = self._fail_remaining.get(step_name, 0)
        if remaining > 0:
            self._fail_remaining[step_name] = remaining - 1
            raise StepFailure(f"injected failure for '{step_name}' ({remaining} remaining)")

        fn = self._functions.get(step_name)
        if fn is not None:
            return fn(*inputs)
        return default_mock(output_type, step_name, inputs)

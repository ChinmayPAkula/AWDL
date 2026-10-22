"""
interpreter.py

Phase 3 - Interpretation and Execution.

Executes a JSON execution plan (from codegen.py) level by level. Steps
within one level have no dependency on each other (that's what makes them
one level - see optimizer.parallel_levels()), so by default they run
concurrently via a thread pool; --sequential (main.py) forces one at a time,
which exists specifically so the two can be timed against each other.

Retry counting: on_error: retry(n) means a step gets at most n + 1 attempts
total (the first attempt, plus up to n retries). This is stated here, and
nowhere else, because it is easy to get the off-by-one wrong.

If a step exhausts its attempts, steps in later levels that depend on its
output are marked "skipped" rather than run (there is nothing meaningful to
give them), but other steps already running in the same level are allowed
to finish. AWDLRuntimeError is still raised so the CLI can report a clean
runtime failure and the right exit code, but it carries the full
ExecutionResult (every step's status) as .result, so the caller can print
a complete report even though the run ultimately failed.

Thread-safety: the shared environment dict is only written by the main
thread, after a whole level's futures have completed and been collected.
Each step function only ever sees a snapshot dict handed to it before the
level starts; nothing mutates shared state from a worker thread.
"""

import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any

from .steps import StepRegistry, default_mock

RUNTIME_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    # bool is a subclass of int in Python, so it must be excluded explicitly
    # or every boolean would also satisfy the "number" check.
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


class InputTypeError(Exception):
    """The value given for the agent's declared input doesn't match its type."""


@dataclass
class StepRecord:
    step: str
    status: str                  # "ok" | "failed" | "skipped"
    attempts: int
    duration_ms: float
    error: str | None = None


@dataclass
class ExecutionResult:
    agent: str
    final_outputs: dict[str, Any]
    environment: dict[str, Any]
    records: list[StepRecord] = field(default_factory=list)
    levels_executed: list[list[str]] = field(default_factory=list)
    total_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return all(r.status == "ok" for r in self.records)


class AWDLRuntimeError(Exception):
    def __init__(self, agent: str, step: str, attempts: int, last_error: str, result: ExecutionResult):
        super().__init__(f"agent '{agent}', step '{step}' failed after {attempts} attempt(s): {last_error}")
        self.agent = agent
        self.step = step
        self.attempts = attempts
        self.last_error = last_error
        self.result = result


def default_input_value(type_name: str) -> Any:
    """A sample value matching the agent's declared input type, used when
    the caller doesn't supply one explicitly."""
    return default_mock(type_name, "input", [])


def _validate_input(plan: dict, value: Any) -> None:
    type_name = plan["input"]["type"]
    check = RUNTIME_TYPE_CHECKS.get(type_name)
    if check is not None and not check(value):
        raise InputTypeError(
            f"agent '{plan['agent']}' expects input '{plan['input']['name']}' as {type_name}, "
            f"got {type(value).__name__}"
        )


def _max_attempts(plan: dict) -> int:
    on_error = plan.get("on_error")
    if on_error and on_error.get("strategy") == "retry":
        return 1 + int(on_error.get("attempts", 0))
    return 1


def _run_one_step(step_entry: dict, env_snapshot: dict, registry: StepRegistry, max_attempts: int):
    """Runs a single step with retry, returning (StepRecord, value_or_None).
    Never raises - a step that exhausts its attempts is reported as a
    'failed' record rather than propagating an exception, so a thread pool
    future can always be collected cleanly."""
    name = step_entry["step"]
    inputs = [env_snapshot[n] for n in step_entry["inputs"]]
    output_type = step_entry["output_type"]

    start = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            value = registry.call(name, output_type, inputs)
            check = RUNTIME_TYPE_CHECKS.get(output_type)
            if check is not None and not check(value):
                raise TypeError(f"returned {type(value).__name__}, expected {output_type}")
            duration_ms = (time.perf_counter() - start) * 1000
            return StepRecord(name, "ok", attempt, duration_ms), value
        except Exception as e:
            last_error = e

    duration_ms = (time.perf_counter() - start) * 1000
    return StepRecord(name, "failed", max_attempts, duration_ms, str(last_error)), None


def execute(
    plan: dict,
    entry_value: Any = None,
    registry: StepRegistry | None = None,
    sequential: bool = False,
) -> ExecutionResult:
    registry = registry or StepRegistry()
    if entry_value is None:
        entry_value = default_input_value(plan["input"]["type"])
    _validate_input(plan, entry_value)

    env: dict[str, Any] = {plan["input"]["name"]: entry_value}
    max_attempts = _max_attempts(plan)
    records: list[StepRecord] = []
    levels_executed: list[list[str]] = []
    skipped_steps: set[str] = set()
    had_failure = False

    start_total = time.perf_counter()

    for level in plan["levels"]:
        levels_executed.append([s["step"] for s in level])

        runnable = [s for s in level if all(i in env for i in s["inputs"])]
        for s in level:
            if s not in runnable:
                records.append(StepRecord(s["step"], "skipped", 0, 0.0, "upstream dependency failed"))
                skipped_steps.add(s["step"])

        if not runnable:
            continue

        if sequential:
            results = [(s, _run_one_step(s, env, registry, max_attempts)) for s in runnable]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(runnable)) as pool:
                env_snapshot = dict(env)  # workers only ever read this snapshot
                future_to_step = {
                    pool.submit(_run_one_step, s, env_snapshot, registry, max_attempts): s
                    for s in runnable
                }
                results = [(future_to_step[f], f.result()) for f in concurrent.futures.as_completed(future_to_step)]
            results.sort(key=lambda pair: pair[0]["step"])  # deterministic report order

        for step_entry, (record, value) in results:
            records.append(record)
            if record.status == "ok":
                env[step_entry["output"]] = value
            else:
                had_failure = True
                skipped_steps.add(step_entry["step"])

    total_ms = (time.perf_counter() - start_total) * 1000
    final_outputs = {name: env[name] for name in plan["final_outputs"] if name in env}
    result = ExecutionResult(
        agent=plan["agent"],
        final_outputs=final_outputs,
        environment=env,
        records=records,
        levels_executed=levels_executed,
        total_ms=total_ms,
    )

    if had_failure:
        failed_record = next(r for r in records if r.status == "failed")
        raise AWDLRuntimeError(plan["agent"], failed_record.step, failed_record.attempts, failed_record.error, result)

    return result

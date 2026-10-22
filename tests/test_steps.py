"""Tests for awdl/steps.py (Phase 3)."""

import os
import tempfile

import pytest

from awdl.steps import StepRegistry, StepFailure, default_mock


def test_default_mock_matches_declared_type():
    assert isinstance(default_mock("string", "s", []), str)
    assert isinstance(default_mock("number", "s", []), int)
    assert isinstance(default_mock("boolean", "s", []), bool)
    assert isinstance(default_mock("list", "s", []), list)
    assert isinstance(default_mock("object", "s", []), dict)


def test_registry_calls_mock_when_nothing_registered():
    registry = StepRegistry()
    result = registry.call("search", "list", ["hello"])
    assert isinstance(result, list)


def test_registry_calls_registered_function():
    registry = StepRegistry()
    registry.register("double", lambda x: x * 2)
    assert registry.call("double", "number", [21]) == 42


def test_inject_failure_raises_then_succeeds():
    registry = StepRegistry()
    registry.register("flaky", lambda: "ok")
    registry.inject_failure("flaky", times=2)

    with pytest.raises(StepFailure):
        registry.call("flaky", "string", [])
    with pytest.raises(StepFailure):
        registry.call("flaky", "string", [])
    assert registry.call("flaky", "string", []) == "ok"


def test_delay_sleeps_for_configured_duration():
    import time
    registry = StepRegistry()
    registry.register("slow", lambda: "done")
    registry.set_delay("slow", 50)
    start = time.perf_counter()
    registry.call("slow", "string", [])
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms >= 40  # generous threshold, avoids flakiness


def test_load_file_registers_steps():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "my_steps.py")
        with open(path, "w") as f:
            f.write("STEPS = {'greet': lambda name: f'hello {name}'}\n")

        registry = StepRegistry()
        registry.load_file(path)
        assert registry.call("greet", "string", ["world"]) == "hello world"

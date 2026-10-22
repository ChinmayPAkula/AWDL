# Phase 3 Implementation Progress

## Note on source material

No Phase 3-specific PRD was provided for this phase (unlike Phase 2, which had
`AWDL_Phase2_PRD.pdf`). This implementation is instead built directly from two
things that *are* specified:

1. The general lab manual's Phase 3 section ("Final Implementation and
   Testing" - complete remaining functionality, integrate all modules, test
   broadly, evaluate and document).
2. The original Phase 1 proposal's own stated Phase 3 scope (Section 5/9):
   *"a target-code generator that lowers the optimized DAG into an
   executable specification"* and *"a runtime interpreter that executes the
   pipeline with built-in retry-based error recovery,"* with steps explicitly
   scoped as *"mocked or stubbed functions"* (Section 6 - live LLM
   integration is out of scope). Phase 2's own progress report already named
   these two items, in this wording, as what's deferred to Phase 3.

## Done

- **Target code generator** (`awdl/codegen.py`) - `generate_plan(agent_ir)`
  lowers an optimized `AgentIR` into a JSON-serializable execution plan: steps
  listed in a valid topological order (reusing `ir.topo_order()`), each with
  its inputs, output, output type, and dependencies, plus the agent's
  `on_error` policy. `to_json()` serializes it for inspection/handoff.
- **Runtime interpreter** (`awdl/interpreter.py`) - `Interpreter.run(plan,
  entry_value)` executes a plan's steps in the order the plan already lists,
  threading each step's output into an environment dict that later steps read
  their inputs from. Implements retry-based error recovery: if the plan
  declares `on_error: retry(n)`, a step that raises is retried up to `n`
  extra times before the whole run fails with `StepExecutionError` (which
  reports the step name, attempt count, and the last underlying error).
- Step functions are **mocked/stubbed** per the explicit Phase 1 scope: when
  no real implementation is registered for a step, `default_step_function()`
  fabricates a deterministic placeholder value of the step's declared type,
  so any compiled pipeline can be run end-to-end for demonstration even
  without real agent/LLM logic behind it. Callers (e.g. `demo_retry.py`) can
  register real functions per step name to override this.
- **`main.py`** extended with Stage 6 (prints the generated JSON plan) and
  Stage 7 (runs it through the interpreter and prints the execution trace and
  final variables), for every agent that made it past semantic analysis -
  consistent with the existing per-agent skip logic from Phase 2.
- **`demo_retry.py`** - a standalone script demonstrating retry actually
  doing something, since `main.py`'s generic stub functions never fail on
  their own. Compiles `examples/retry_demo.awdl` through the full pipeline,
  then runs the resulting plan twice with a real step function: once that
  fails twice and succeeds on the third attempt (retry recovers it), and once
  that always fails (retry correctly exhausts and raises
  `StepExecutionError`). Both scenarios were run and verified to produce the
  expected trace and outcome.
- All 7 existing Phase 1/2 example files plus the new `retry_demo.awdl` were
  re-run end-to-end through the extended `main.py` and confirmed to still
  produce their Phase 2-documented behavior unchanged, with Stages 6-7 now
  running (and producing a plan + execution trace) for every agent that has
  no semantic errors.

## Design decisions

- **Retry is agent-level, not per-step**, because that's what the Phase 1
  grammar actually defines (`on_error` is declared once per `agent` block,
  not attached to individual `step` declarations). The interpreter applies
  the same retry budget uniformly to every step in the plan rather than
  inventing per-step retry syntax that was never part of the approved
  grammar.
- **Execution stops at the first step that exhausts its retries**, rather
  than skipping it and continuing. A later step's input may depend on the
  failed step's output, so there's no meaningful way to continue without it;
  this mirrors how the Phase 2 semantic analyzer treats an invalid agent
  (skip cleanly, don't produce a nonsensical partial result).
- **Stub step functions are keyed by declared output type, not step name**,
  so an unimplemented pipeline is still fully runnable and inspectable
  end-to-end without the demo author having to hand-write a fake function for
  every single step.

## Deferred / explicitly out of scope

- Real LLM/agent calls behind step functions - out of scope per the Phase 1
  proposal itself (steps are mocked/stubbed by design, not an oversight).
- Concurrent execution of the parallel levels the Phase 2 optimizer computes
  - the interpreter still executes the plan's steps sequentially in
    topological order; `report.levels_after` is informational, not acted on
    by the runtime. True concurrent execution (e.g. via threads/async) was
    not in Phase 1's stated Phase 3 scope and would be a natural Phase 4/
    stretch item if the course allowed one.
- A graphical DAG visualization - named a stretch goal, not a requirement, in
  the original Phase 1 proposal's Scope section.

# Development Log

Dated entries, one per build step from the Phase 3 PRD's implementation order (section 9). Kept factual and short.

## 2026-10-22 - Step 1: Test scaffolding

Added `tests/` with a pytest baseline suite covering all Phase 1 and Phase 2 modules
(`test_lexer.py`, `test_parser.py`, `test_symbol_table.py`, `test_semantic.py`,
`test_ir.py`, `test_optimizer.py`) before making any Phase 3 changes, as the PRD
requires.

Running this baseline exposed a real bug: `Parser.parse_program()`'s top-level
error recovery could loop forever. When an agent body is missing its required
`input:` declaration and the very next token already looks like a safe restart
point to `_synchronize()` (for example `step`), `_synchronize()` returns
immediately without consuming anything, `parse_program()` retries the same
failing position, and the cycle repeats without end. Reproduced with
`agent X { step a() -> b : string }`.

Fixed in `awdl/parser.py`: `parse_program()` now records the token position
before each `_parse_agent()` attempt, and if a `ParseError` handler's call to
`_synchronize()` didn't move the position at all, it force-advances one token
before retrying. This guarantees forward progress without changing recovery
behavior for every other (non-degenerate) case, which the rest of the baseline
suite (parser, semantic, IR, optimizer) confirms still passes unchanged.

Result: 39/39 baseline tests pass; all 7 existing example files still produce
their previously-documented output with no regressions.

## 2026-10-22 - Step 2: Typed parameters

Closed the gap flagged in the Phase 2 report (producer/consumer type
compatibility was never checked, only that types were individually known).

Grammar change, backward compatible: `param := IDENT [':' IDENT]`, so both
`step s(x)` and `step s(x : string)` still parse. Added `Param(name,
type_name)` to `ast_nodes.py`; `StepDecl.params` is now `list[Param]` instead
of `list[str]`. Updated every consumer: `parser.py` (`_parse_param()`),
`semantic.py` (reads `param.name`, plus the new mismatch check),
`ir.py` (`IRNode.inputs = [p.name for p in step.params]`), and `main.py`'s
Stage 2 printout.

New semantic check in `semantic.py`: when a parameter has a declared type
and resolves to a real producer (the agent's input or another step's
output), the types must match exactly; mismatch is a `SemanticError`
naming the step, parameter, expected type, and actual type, e.g.
`step 'summarize' expects 'results' as list but 'search' produces string`.
An untyped parameter still gets the undefined-reference check but skips the
mismatch check. An unknown type name on a parameter is flagged the same way
as an unknown output type.

New fixtures: `examples/type_mismatch.awdl` (produces exactly the error
above) and `examples/researcher_typed.awdl` (a fully-typed, passing variant
of the main example). Added 8 new tests across `test_parser.py` and
`test_semantic.py` covering typed/untyped/mismatched/unknown-type parameters
against both step and input producers.

Result: 47/47 tests pass; all 7 Phase 1/2 example files plus the 2 new
typed-parameter fixtures behave as expected; `demo_retry.py` unaffected.

## 2026-10-22 - Step 3: Code generation (JSON execution plan)

Rewrote `awdl/codegen.py` to the plan schema specified by the Phase 3 PRD
(section 4.2), replacing the flat, pre-PRD guess that was in the repo before
this PRD existed. `generate_plan(agent_ir, report, chain_endpoints)` now
emits `levels` (the optimizer's `parallel_levels()` grouping, after dead-step
removal, steps sorted by name within a level for determinism), an `input`
object with name and type, an `on_error` object, and `final_outputs`: the
outputs of chain-ending steps if the agent has any chains, else the outputs
of whatever nothing else consumes.

This needed one small, additive IR change: `AgentIR` gained an
`entry_input_type` field (the agent's declared input type wasn't previously
carried on the IR, only its name), populated in `ir.build_ir()` and
propagated through `optimizer.optimize()`'s reconstruction of the optimized
`AgentIR`.

Found and documented a real edge case while testing `final_outputs`: an
agent with *no* declared chains, where a step's output is never consumed,
has that step removed by dead-step elimination (that's the exact definition
of "dead" without a chain to protect it) - so the "steps nobody consumes"
fallback branch of `final_outputs` only ever sees genuinely-kept output,
never a false positive. Not a bug; documented as expected optimizer
behavior.

`main.py`'s old pre-PRD Stage 6/7 wiring (built as a guess before this PRD
existed) was removed, since the PRD requires bare `python main.py file.awdl`
to keep producing exactly the Stage 1-5 output it always has, with Stages
6-7 moved behind CLI flags added in a later step. The old `demo_retry.py`
script and `examples/retry_demo.awdl` (built against the same pre-PRD
interpreter) were removed; the PRD's own `--fail`-flag-driven
`retry_recovers.awdl`/`retry_exhausted.awdl` fixtures supersede them.

Result: 54/54 tests pass (7 new in `test_codegen.py`); all 9 example files
(7 original + 2 typed-parameter ones from step 2) still compile through
Stages 1-5 with no regressions.

## 2026-10-22 - Step 4: Step registry

Added `awdl/steps.py`: `StepRegistry` maps a step name to a Python callable
taking the step's inputs in declared order and returning its output. Any
step with nothing registered falls back to `default_mock(output_type, ...)`,
which fabricates a value matching the declared type (so the interpreter's
own runtime type check, coming in step 5, never rejects a pure mock).

Three features exist specifically to make runtime behavior demonstrable
without hand-writing real flaky/slow code: `register()` for a single
override, `load_file()` for a user's `--steps file.py` exposing a module-
level `STEPS = {name: fn}` dict, `inject_failure(step, times)` (raises
`StepFailure` for the first N calls, then calls through - this is how
`on_error: retry(n)` gets demonstrated), and `set_delay()`/
`set_default_delay()` (sleeps before returning, so a parallel level's timing
is visibly different from running the same steps sequentially).

Result: 60/60 tests pass (6 new in `test_steps.py`).

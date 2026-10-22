# Phase 3 Implementation Progress

## Note on source material

The college only issued a general lab manual (Phase 3 = "Final Implementation
and Testing": complete remaining functionality, integrate all modules, test
broadly, evaluate, document) plus the Phase 1 proposal's own stated Phase 3
scope: a target-code generator lowering the optimized DAG into an executable
specification, and a runtime interpreter with retry-based error recovery,
steps mocked/stubbed by design. That proposal scope is what this phase
delivers - deliberately kept to what was actually proposed, rather than
speculatively expanding it.

## Done

- **Typed parameters** (`awdl/ast_nodes.py`, `awdl/parser.py`) - an optional
  type annotation on a step parameter (`step s(x : string)`), backward
  compatible with the untyped form. Closes the type-checking gap named in the
  Phase 2 report: a new semantic check (`awdl/semantic.py`) flags a mismatch
  between a parameter's declared type and what its producer (the agent's
  input, or another step) actually produces.
- **Target code generator** (`awdl/codegen.py`) - `generate_plan()` lowers an
  optimized `AgentIR` plus its `OptimizationReport` into a JSON-serializable
  execution plan: steps grouped into the same parallel levels the optimizer
  computed (not just a flat topological order), each with its inputs,
  output, type, and the agent's `on_error` policy. Deterministic - the same
  program always produces byte-identical JSON.
- **Step registry** (`awdl/steps.py`) - maps a step name to a real Python
  function. Any step with nothing registered falls back to a deterministic
  mock matching its declared output type, so every `.awdl` file runs end to
  end with zero setup. Also supports injecting a controlled failure
  (`inject_failure`), which is how retry recovery is demonstrated without
  writing real flaky code.
- **Runtime interpreter** (`awdl/interpreter.py`) - `execute(plan, ...)`
  runs the plan level by level. Steps within one level run concurrently via
  a thread pool by default (`--sequential` forces one at a time, so the two
  can be compared); the shared environment is only written by the main
  thread after a level's results are all collected, so worker threads never
  touch shared mutable state. A step that raises, or returns a value that
  doesn't match its declared output type, is retried per the agent's
  `on_error: retry(n)` policy (n retries after the first attempt, n + 1
  attempts total). If a step still fails after retries, steps that depend on
  its output are marked "skipped" rather than run, while the rest of that
  step's level is still allowed to finish; the interpreter raises
  `AWDLRuntimeError` but attaches the full per-step report to it, so the
  caller can still show what happened to everything else.
- **`main.py`** now runs all seven stages for any agent that compiles clean,
  with a single `--sequential` flag to force non-concurrent execution for
  comparison.
- **68 tests** across `tests/`, covering every module (lexer, parser, symbol
  table, semantic, IR, optimizer, codegen, step registry, interpreter),
  including typed-parameter type checking, retry recovery, retry exhaustion
  with downstream skip propagation, wrong-typed return values, and bad input
  rejection.

## Design decisions

- **Retry is agent-level, not per-step**, because that's what the Phase 1
  grammar defines (`on_error` is declared once per `agent`, not per `step`).
- **A failed step stops downstream execution but not its own level** -
  independent steps already running alongside a failing one are allowed to
  finish, since they have no dependency on it; only steps that actually
  needed the failed step's output are skipped.
- **Concurrency is a real thread pool, not just a computed grouping** - the
  Phase 2 optimizer could already tell you which steps *could* run in
  parallel; Phase 3 actually runs them that way, which is what "runtime
  interpreter" means per the original proposal.

## Deliberately out of scope

The Phase 1 proposal is explicit that these are not required, so they were
not built:

- Real LLM/agent calls behind step functions (steps are mocked/stubbed by
  design, Section 6 of the Phase 1 proposal).
- A general-purpose type system, generics, or structural typing - AWDL
  checks exact matches against five named types only.
- A graphical IDE or DAG visualization - named a stretch goal, not a
  requirement, in the Phase 1 proposal's Scope section.
- Distributed/multi-machine execution.

Also out of scope, for the more practical reason of staying proportionate to
a lab project: a full `argparse` CLI surface with a dozen flags, Graphviz DOT
export, generated 1000-step benchmark suites, and a set of eight separate
documentation files. A later, much more elaborate internal draft of this
phase pursued all of that; it was deliberately scaled back down to what the
actual Phase 1 proposal promised once that draft's scope became clear.

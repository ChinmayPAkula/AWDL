# Phase 2 Implementation Progress

## Done

- **Symbol table** (`awdl/symbol_table.py`) — one scoped table per agent, tracking the
  declared input and every step's params/output/type; `resolve(name)` maps a variable
  name back to whichever declaration produces it; duplicate step names raise
  `DuplicateStepError`.
- **Semantic analyzer** (`awdl/semantic.py`) — validates, per agent:
  - undefined-reference detection (every step parameter must resolve to the input or
    another step's output)
  - known-type checking (input/output types must be one of `string`, `number`,
    `boolean`, `list`, `object`)
  - dependency-cycle detection (DFS with a white/gray/black coloring over the
    parameter-derived dependency graph)
  - chain consistency (every step name in a chain must be an actually-declared step)

  Like the parser, it does not stop at the first error — it collects everything so one
  mistake doesn't hide the rest of the report.
- **Intermediate representation** (`awdl/ir.py`) — lowers a semantically-valid
  `AgentDecl` into an `AgentIR` (a DAG of `IRNode`s with `depends_on` edges derived
  from the symbol table). `topo_order()` (Kahn's algorithm) gives a valid execution
  order and doubles as an IR-level cycle-detection safety net.
- **Optimizer** (`awdl/optimizer.py`) —
  - dead-step elimination: drops steps whose output is never consumed by another step
    and that aren't the endpoint of a declared chain
  - `parallel_levels()`: groups steps with no unmet dependencies into levels that
    could run concurrently, and reports a before/after comparison
    (`OptimizationReport`)
- **`main.py`** extended with Stage 3 (semantic analysis), Stage 4 (IR), and Stage 5
  (optimization); an agent with semantic errors has its IR/optimization stages skipped,
  but other agents in the same file still get processed.
- **Test fixtures**: `examples/undefined_ref.awdl`, `examples/cycle.awdl`,
  `examples/dead_step.awdl`, `examples/parallel.awdl`, `examples/duplicate_step.awdl`,
  documented in `examples/README.md`. All seven example files (two from Phase 1, five
  new) were run through `main.py` and produce the expected result at the expected
  stage.

## Design decision: type checking

AWDL's grammar doesn't attach an expected type to each step parameter (params are
just names), so Phase 2 implements the minimum viable type check described in the
PRD: every input/output type must be one of AWDL's known types
(`string`/`number`/`boolean`/`list`/`object`); unknown or misspelled types are
flagged. Catching a real mismatch (e.g. a step expecting `string` but receiving a
`list`) would require extending `StepDecl.params` to carry `(name, expected_type)`
pairs in the grammar and parser — deferred, since it changes the Phase 1 grammar
rather than building on top of it.

## Partial / deferred to Phase 3

- Target code generation (lowering the optimized DAG into an executable JSON plan)
- Runtime interpreter with retry-based error recovery (`on_error: retry(n)` is parsed
  and carried through the IR, but not yet acted on)
- Real concurrent execution of parallel levels (Phase 2 only computes and reports the
  grouping)

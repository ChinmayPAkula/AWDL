# AWDL — Agent Workflow Definition Language

A domain-specific language and compiler for declarative AI agent pipeline orchestration, built as a Compiler Design Lab project (Course Code: BCSE307P).

## Why

Agent orchestration frameworks in current use (LangChain-style tools) wire agent steps together with general-purpose imperative code. That has three consequences:

1. **No static validation** — broken data dependencies or type mismatches only surface at runtime.
2. **No automatic optimization** — independent steps run sequentially by default, even when they could be parallelized.
3. **Scattered error handling** — retries/fallbacks are ad hoc rather than declared centrally.

AWDL addresses this with a small language in which a pipeline's structure, data flow, and error-handling policy are declared explicitly, so a compiler can catch errors before execution and optimize the execution plan automatically.

## Example

```awdl
agent Researcher {
  input: query : string

  step search(query) -> results : list
  step summarize(results) -> summary : string
  step validate(summary) -> final : string

  search -> summarize -> validate

  on_error: retry(3)
}
```

## Compiler pipeline

```
AWDL Source (.awdl)
      |
      v
  [ Lexer ] --tokens--> [ Parser ] --AST--> [ Semantic Analyzer ]
                                                    |
                                          (uses / builds) v
                                                [ Symbol Table ]
                                                    |
                                                    v
                                    [ IR Generator ] --> DAG (steps + data edges)
                                                    |
                                                    v
                                              [ Optimizer ]
                                    (dead-step elimination, reordering)
                                                    |
                                                    v
                                        [ Target Code Generator ]
                                                    |
                                                    v
                                        Executable Plan (JSON)
                                                    |
                                                    v
                              [ Runtime Interpreter / Execution Engine ]
                                    (executes steps, handles retries)
                                                    |
                                                    v
                                          Final Output / Results
```

## Current status

**Implemented (Phase 1):**
- `awdl/lexer.py` — full tokenizer for keywords (`agent`, `input`, `step`, `on_error`, `retry`), identifiers, numbers, symbols (`{ } ( ) : -> ,`), `#` comments, with line/column tracking and `LexerError` reporting.
- `awdl/parser.py` — recursive-descent parser producing a full AST (`awdl/ast_nodes.py`): agent blocks, input declarations, step declarations, data-flow chains (`a -> b -> c`), and `on_error: retry(n)` directives, with panic-mode error recovery so a single mistake doesn't stop the rest of the file from being checked.

**Implemented (Phase 2):**
- `awdl/symbol_table.py` — a scoped symbol table per agent, tracking the declared input and every step's params/output/type, with `resolve(name)` mapping a variable name back to whichever declaration produces it.
- `awdl/semantic.py` — semantic analyzer validating undefined references, known types, dependency cycles (DFS), and chain consistency; collects every error instead of stopping at the first one.
- `awdl/ir.py` — lowers a semantically-valid agent into a DAG (`AgentIR` of `IRNode`s with `depends_on` edges); `topo_order()` gives a valid execution order.
- `awdl/optimizer.py` — dead-step elimination and `parallel_levels()` grouping, with an `OptimizationReport` showing the before/after effect.
- `main.py` — CLI entry point running a `.awdl` file through all five stages: lexing, parsing, semantic analysis, IR generation, and optimization.

See [`PHASE2_PROGRESS.md`](PHASE2_PROGRESS.md) for implementation notes and design decisions.

**Planned (Phase 3):**
- Target-code generator (executable JSON plan)
- Runtime interpreter with retry-based error recovery
- Real concurrent execution of parallel levels

## Usage

```bash
python main.py examples/researcher.awdl       # valid pipeline
python main.py examples/broken.awdl           # syntax-error recovery
python main.py examples/undefined_ref.awdl    # semantic error: undefined reference
python main.py examples/cycle.awdl            # semantic error: dependency cycle
python main.py examples/duplicate_step.awdl   # semantic error: duplicate step
python main.py examples/dead_step.awdl        # optimizer: dead-step elimination
python main.py examples/parallel.awdl         # optimizer: parallel-level grouping
```

See [`examples/README.md`](examples/README.md) for what each file demonstrates.

## Project structure

```
awdl/
  awdl/
    lexer.py          # Stage 1: lexical analysis
    parser.py          # Stage 2: syntax analysis -> AST
    ast_nodes.py        # AST node definitions
    symbol_table.py      # Stage 3: scoped symbol table
    semantic.py           # Stage 3: semantic analysis
    ir.py                  # Stage 4: DAG intermediate representation
    optimizer.py             # Stage 5: dead-step elimination, parallel grouping
  examples/
    researcher.awdl        # valid example pipeline
    broken.awdl              # syntax error + recovery
    undefined_ref.awdl         # semantic error: undefined reference
    cycle.awdl                   # semantic error: dependency cycle
    duplicate_step.awdl            # semantic error: duplicate step
    dead_step.awdl                   # optimizer: dead-step elimination
    parallel.awdl                     # optimizer: parallel-level grouping
  main.py            # CLI entry point
```

## Author

Chinmayy — Reg. No. 24BCE0500

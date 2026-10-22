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

Parameters can optionally carry a type (`step summarize(results : list) -> summary : string`); the semantic analyzer then checks it matches what actually produces that value.

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
                                    (dead-step elimination, parallel-level grouping)
                                                    |
                                                    v
                                        [ Target Code Generator ]
                                                    |
                                                    v
                                        Executable Plan (JSON, grouped into levels)
                                                    |
                                                    v
                              [ Runtime Interpreter / Execution Engine ]
                                (executes each level, parallel steps concurrently,
                                            handles retries)
                                                    |
                                                    v
                                          Final Output / Results
```

## Status: all three phases complete

- **Phase 1** — `awdl/lexer.py` + `awdl/parser.py`: full tokenizer and recursive-descent parser building a complete AST, with panic-mode syntax-error recovery.
- **Phase 2** — `awdl/symbol_table.py` + `awdl/semantic.py` + `awdl/ir.py` + `awdl/optimizer.py`: scoped symbol table, semantic analysis (undefined references, known types, dependency cycles, chain consistency), a DAG intermediate representation, and an optimizer doing dead-step elimination and parallel-level grouping.
- **Phase 3** — `awdl/codegen.py` + `awdl/steps.py` + `awdl/interpreter.py`:
  - **Typed parameters** (`step s(x : string)`, backward compatible with untyped ones) and producer/consumer type-mismatch detection, completing the semantic analysis gap from Phase 2.
  - **Target code generation**: the optimized DAG is lowered into a JSON execution plan, grouped into the same parallel levels the optimizer computed.
  - **Step registry**: maps a step name to a real Python function; any step with nothing registered falls back to a deterministic mock, so every `.awdl` file runs end to end with zero setup (steps are mocked/stubbed by design — AWDL orchestrates, it doesn't ship an LLM client).
  - **Runtime interpreter**: executes the plan level by level, running each level's independent steps concurrently (a thread pool) unless `--sequential` is passed; retries a failing step per its `on_error: retry(n)` policy (n retries after the first attempt, so n + 1 attempts total); if a step still fails, steps that depend on it are marked skipped rather than run, while the rest of that step's level is still allowed to finish.

See [`docs/DEVELOPMENT_LOG.md`](docs/DEVELOPMENT_LOG.md) for the build history and design decisions made along the way, including a real parser bug found and fixed by the test suite.

## Usage

```bash
python main.py examples/researcher.awdl            # valid pipeline, all 7 stages run
python main.py examples/researcher_typed.awdl      # typed-parameter variant, also passes
python main.py examples/type_mismatch.awdl         # semantic error: type mismatch
python main.py examples/broken.awdl                # syntax-error recovery
python main.py examples/undefined_ref.awdl         # semantic error: undefined reference
python main.py examples/cycle.awdl                 # semantic error: dependency cycle
python main.py examples/duplicate_step.awdl        # semantic error: duplicate step
python main.py examples/dead_step.awdl             # optimizer: dead-step elimination
python main.py examples/parallel.awdl              # optimizer + runtime: parallel levels
python main.py examples/parallel.awdl --sequential # same file, forced one-step-at-a-time
```

See [`examples/README.md`](examples/README.md) for what each file demonstrates.

### Running the test suite

```bash
python -m pip install pytest pytest-cov
python -m pytest tests/ -q
```

## Project structure

```
awdl/
  awdl/
    lexer.py          # Stage 1: lexical analysis
    parser.py          # Stage 2: syntax analysis -> AST
    ast_nodes.py        # AST node definitions (including typed Param)
    symbol_table.py      # Stage 3: scoped symbol table
    semantic.py           # Stage 3: semantic analysis (incl. type mismatch)
    ir.py                  # Stage 4: DAG intermediate representation
    optimizer.py             # Stage 5: dead-step elimination, parallel grouping
    codegen.py                 # Stage 6: JSON execution plan (levels)
    steps.py                    # step registry: mocks, real functions, failure injection
    interpreter.py                # Stage 7: concurrent execution, retry recovery
  examples/              # sample .awdl programs, one per behavior (see examples/README.md)
  tests/                 # pytest suite covering every module
  main.py                # CLI entry point
```

## Author

Chinmayy — Reg. No. 24BCE0500

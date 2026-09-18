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
- `main.py` — CLI entry point that runs a `.awdl` file through lexing and parsing and prints the resulting tokens/AST.

**Planned (Phase 2/3):**
- Semantic analyzer with a scoped symbol table (type checking, undefined-reference detection, dependency-cycle detection)
- DAG-based intermediate representation
- Optimization pass (dead-step elimination, independent-step reordering for parallel execution)
- Target-code generator (executable JSON plan)
- Runtime interpreter with retry-based error recovery

See [`PPT_BRIEF.md`](PPT_BRIEF.md) for the full project write-up (problem statement, objectives, scope, background study, methodology, architecture).

## Usage

```bash
python main.py examples/researcher.awdl   # valid pipeline
python main.py examples/broken.awdl       # demonstrates syntax-error recovery
```

## Project structure

```
awdl/
  awdl/
    lexer.py       # Stage 1: lexical analysis
    parser.py       # Stage 2: syntax analysis -> AST
    ast_nodes.py     # AST node definitions
  examples/
    researcher.awdl  # valid example pipeline
    broken.awdl       # example with a syntax error
  main.py            # CLI entry point
```

## Author

Chinmayy — Reg. No. 24BCE0500

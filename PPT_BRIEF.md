# Instructions for Claude: Build a PPTX for this project

Create a PowerPoint presentation (.pptx) for a Compiler Design Lab "Review 1" submission.

## Theme requirements (important)
- Color palette: light blue and white ONLY. Suggested tones: background `#FFFFFF` or `#F5FAFF`, accent bars/headers `#BFDDF2` / `#8EC5E8`, title text `#1B3A57` (dark blue-grey, not pure black), body text `#2E2E2E`.
- Do NOT use a generic "AI-generated" look: no glowing gradients, no robot/circuit-board clip art, no purple-to-blue gradients, no neon, no stock "AI brain" icons.
- Instead use: clean flat design, plenty of white space, a thin horizontal accent rule under titles, simple geometric shapes (rounded rectangles, thin-line boxes) for diagrams, and a consistent sans-serif font (e.g. Calibri, Segoe UI, or Lato).
- Diagrams (pipeline/architecture) should be built from simple boxes and arrows in the light-blue palette — not decorative icons.
- Keep each slide sparse: a short headline + 3-6 bullet points max, or a diagram. Avoid walls of text.

## Deck content

### Slide 1 — Title
- AWDL — Agent Workflow Definition Language
- Subtitle: A Domain-Specific Language and Compiler for Declarative AI Agent Pipeline Orchestration
- Compiler Design Lab — Review 1 (Phase 1 Deliverables)
- Course Code: BCSE307P
- Name: Chinmayy | Reg No: 24BCE0500

### Slide 2 — Problem Statement
- Agent orchestration today (LangChain-style tools) uses imperative glue code
- No static validation before execution — broken data deps/type mismatches only surface at runtime
- No automatic optimization — independent steps run sequentially by default
- Error-handling (retries/fallbacks) scattered ad hoc through code

### Slide 3 — Motivation
- Agentic AI is a fast-growing, current area — original + practically relevant project
- Declarative + statically checked pipelines improve reliability (cf. SQL vs. hand-written query logic)
- Builds direct experience in both compiler construction and agentic-AI system design

### Slide 4 — Objectives
- Formal grammar for AWDL (agents, typed steps, data-flow chaining, error handling)
- Lexer with line/column error reporting
- Recursive-descent parser building an AST with panic-mode error recovery
- Semantic analyzer: scoped symbol table, type checking, dependency-cycle detection
- IR: step-dependency DAG + optimization (dead-step elimination, parallel reordering)
- Target-code generator (executable JSON plan) + runtime interpreter with retry recovery

### Slide 5 — Scope
**In scope:** full front end (lexer, parser, AST) + back end (semantic analysis, IR, optimization, codegen, interpretation) for single-file AWDL programs; primitive/collection types (string, number, boolean, list, object); sequential + simple data-parallel execution; retry-based error recovery.

**Out of scope:** distributed execution, live LLM API integration (steps are mocked/stubbed), full general-purpose type system, graphical IDE (DAG visualization is a stretch goal).

### Slide 6 — Background Study
- LangChain / CrewAI / LangGraph: Python APIs for chaining steps, but no static validation or plan optimization — pipelines only checked by running them
- LangGraph's graph-based pipeline representation supports AWDL's choice of a DAG as IR
- Compiler-theory foundations: recursive-descent parsing (Aho/Lam/Sethi/Ullman), scoped symbol tables, dead-code elimination (adapted to dead-step elimination), topological sort (cycle detection + parallel ordering)

### Slide 7 — Compiler Design Concepts Involved (table)
| Concept | Application in AWDL |
|---|---|
| Lexical Analysis | Tokenizing keywords (`agent`, `step`, `input`, `on_error`), identifiers, types, symbols (`->`, `:`, `{}`) |
| Syntax Analysis | Recursive-descent parser; builds the AST |
| Semantic Analysis | Type checking between chained steps; undefined-reference & cycle detection |
| Symbol Table | Per-agent scoped table: step name, input/output types, position |
| IR Generation | AST lowered into a DAG (nodes = steps, edges = data deps) |
| Optimization | Dead-step elimination; independent-step reordering for parallelism |
| Target Code Gen | DAG lowered into executable JSON plan |
| Interpretation | Runtime engine executes plan in dependency order |
| Error Handling | Lexical/syntax/semantic errors with panic-mode recovery; runtime retry via `on_error` |

### Slide 8 — Proposed Methodology (6 stages)
1. Grammar design (EBNF)
2. Front end: lexer + recursive-descent parser → AST
3. Semantic layer: symbol table, type checks, cycle detection
4. IR + optimization: AST → DAG, dead-step elimination, reordering
5. Code generation + runtime interpreter with retry recovery
6. Testing: valid / invalid / edge-case AWDL programs

### Slide 9 — System Architecture (diagram slide)
Render as a clean vertical flow diagram using boxes + arrows (light blue boxes, white background, dark blue text), not the ASCII art verbatim:

AWDL Source (.awdl) → Lexer → Parser → AST → Semantic Analyzer (+ Symbol Table) → IR Generator (DAG) → Optimizer (dead-step elimination, reordering) → Target Code Generator → Executable Plan (JSON) → Runtime Interpreter → Final Output

### Slide 10 — Technology Stack (table)
| Component | Tool |
|---|---|
| Language | Python 3 |
| Parsing | Hand-written recursive-descent parser (no parser generator) |
| Data Structures | Custom AST node classes; DAG via adjacency lists |
| Visualization (stretch) | Graphviz |
| Testing | pytest / unittest |
| Version Control | Git + GitHub, incremental commits per stage |
| IDE | Visual Studio Code |

### Slide 11 — Current Prototype Status
This is implemented and working today (ahead of the original Phase-1 plan, which only promised a partial parser):
- **Lexer** — complete: tokenizes all keywords (`agent`, `input`, `step`, `on_error`, `retry`), identifiers, numbers, symbols (`{ } ( ) : -> ,`), comments (`#`), with line/column tracking and `LexerError` reporting
- **Parser** — complete recursive-descent parser producing a full AST: agent blocks, input declarations, step declarations (params, output name/type), chain declarations (`a -> b -> c`), `on_error: retry(n)` directives, with panic-mode error recovery so one bad line doesn't stop the whole file from being checked
- Example input (`examples/researcher.awdl`) parses cleanly into a 3-step agent (`search -> summarize -> validate`) with a retry(3) error policy; `examples/broken.awdl` demonstrates syntax-error recovery
- **Next (Phase 2):** semantic analyzer + symbol table, DAG-based IR, optimizer, code generator, runtime interpreter

Include this code snippet (as a monospace text box, light blue-tinted background box):
```
agent Researcher {
  input: query : string
  step search(query) -> results : list
  step summarize(results) -> summary : string
  step validate(summary) -> final : string
  search -> summarize -> validate
  on_error: retry(3)
}
```

### Slide 12 — Expected Outcomes
- Working AWDL compiler: lexing → parsing → semantic analysis → IR → optimization → codegen → execution
- Test suite of valid/invalid/edge-case AWDL programs with correct error detection at each stage
- Before/after comparison showing optimizer effect (dead steps removed, independent steps reordered/parallelized)
- Reusable, documented codebase as a portfolio project

### Slide 13 — Thank You / Questions
- Simple closing slide, light blue accent bar, "Thank You" + "Questions?"

## Output
Produce the deck as a downloadable .pptx file.

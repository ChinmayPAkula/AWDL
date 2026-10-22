# Example AWDL programs

| File | Purpose | Expected outcome |
|---|---|---|
| `researcher.awdl` | A valid 3-step pipeline | No errors at any stage |
| `broken.awdl` | Missing `)` in a step declaration | Syntax error, with panic-mode recovery still parsing the rest of the file (which then surfaces two knock-on semantic errors) |
| `undefined_ref.awdl` | A step consumes a parameter no one produces | Semantic error: undefined reference |
| `cycle.awdl` | Two steps depend on each other | Semantic error: dependency cycle |
| `dead_step.awdl` | A step's output is never consumed and it isn't a chain endpoint | No semantic errors; optimizer removes the step as dead |
| `parallel.awdl` | Two steps depend only on the agent's input, not on each other | No semantic errors; optimizer groups them into the same parallel level |
| `duplicate_step.awdl` | Two `step` declarations share a name in one agent | Semantic error: duplicate step |
| `researcher_typed.awdl` | Typed variant of `researcher.awdl`, every parameter annotated and matching its producer | No errors at any stage |
| `type_mismatch.awdl` | A typed parameter whose declared type doesn't match what its producer actually produces | Semantic error: producer/consumer type mismatch |

Run any of them with:

```bash
python main.py examples/<file>.awdl
```

This runs all 7 stages: lexing, parsing, semantic analysis, IR generation,
optimization, target code generation, and execution. For a file with
semantic errors, Stages 4-7 are skipped for that agent and the errors are
reported at Stage 3 instead.

Add `--sequential` to force Stage 7 to run one step at a time instead of
running each parallel level concurrently - try it on `parallel.awdl` to see
both modes produce the same result:

```bash
python main.py examples/parallel.awdl --sequential
```

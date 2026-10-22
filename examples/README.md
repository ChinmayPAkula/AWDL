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
| `retry_demo.awdl` | A single step with `on_error: retry(3)` | Compiles and runs fine through `main.py` (stub never fails); run via `demo_retry.py` instead to see retry actually recover from, and then exhaust against, a real failing step |

Run any of them with:

```bash
python main.py examples/<file>.awdl
```

For files that compile without semantic errors, `main.py` also runs Stage 6
(target code generation - prints the JSON execution plan) and Stage 7
(interpretation - runs the plan with stubbed step functions and prints the
execution trace and final variables).

`retry_demo.awdl` is best demonstrated with its dedicated script instead,
since `main.py`'s stub functions never fail on their own:

```bash
python demo_retry.py
```

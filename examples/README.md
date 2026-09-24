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

Run any of them with:

```bash
python main.py examples/<file>.awdl
```

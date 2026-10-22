"""
main.py
-------
Entry point for the AWDL prototype (Phase 1 + Phase 2 + Phase 3).

Usage:
    python main.py examples/researcher.awdl

Runs the source file through Stages 1-5 (lexing, parsing, semantic analysis,
IR generation, optimization) and prints the results. Stages 6-7 (target code
generation and interpretation/execution) are available behind CLI flags
added in a later Phase 3 build step; see --help once those land.
"""

import sys
from awdl.lexer import tokenize, LexerError
from awdl.parser import parse
from awdl.semantic import analyze
from awdl.ir import build_ir, topo_order, CycleError
from awdl.optimizer import optimize


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <file.awdl>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r") as f:
        source = f.read()

    print(f"=== Compiling {path} ===\n")

    print("Stage 1: Lexical Analysis")
    try:
        tokens = tokenize(source)
    except LexerError as e:
        print(f"FAILED: {e}")
        sys.exit(1)
    print(f"Produced {len(tokens)} tokens.\n")

    # --- Stage 2: Syntax Analysis ---
    print("Stage 2: Syntax Analysis")
    program, errors = parse(tokens)

    if errors:
        print(f"{len(errors)} syntax error(s) found:")
        for e in errors:
            print(f"  - {e}")
        print()
    else:
        print("No syntax errors.\n")

    print(f"Parsed {len(program.agents)} agent(s):\n")
    for agent in program.agents:
        print(f"Agent '{agent.name}'")
        for inp in agent.inputs:
            print(f"  input  {inp.name}: {inp.type_name}")
        for step in agent.steps:
            params_str = ', '.join(
                f"{p.name}: {p.type_name}" if p.type_name else p.name
                for p in step.params
            )
            print(f"  step   {step.name}({params_str}) -> {step.output_name}: {step.output_type}")
        for chain in agent.chains:
            print(f"  chain  {' -> '.join(chain.step_names)}")
        if agent.on_error:
            print(f"  on_error: {agent.on_error.strategy}({agent.on_error.arg})")
        print()

    # --- Stage 3: Semantic Analysis ---
    print("Stage 3: Semantic Analysis")
    symtabs, sem_errors, errors_by_agent = analyze(program)

    if sem_errors:
        print(f"{len(sem_errors)} semantic error(s) found:")
        for e in sem_errors:
            print(f"  - {e}")
        print()
    else:
        print("No semantic errors.\n")

    # --- Stages 4-5: IR + Optimization (per agent, skip agents with semantic errors) ---
    for agent in program.agents:
        if errors_by_agent.get(agent.name):
            print(f"Skipping IR/optimization for agent '{agent.name}' due to semantic errors.\n")
            continue

        symtab = symtabs[agent.name]

        print(f"Stage 4: Intermediate Representation - agent '{agent.name}'")
        agent_ir = build_ir(agent, symtab)
        try:
            order = topo_order(agent_ir)
        except CycleError as e:
            print(f"  FAILED: {e}\n")
            continue
        for name in order:
            node = agent_ir.nodes[name]
            deps = ", ".join(sorted(node.depends_on)) or "(none)"
            print(f"  node   {node.name}: inputs={node.inputs} -> {node.output}:{node.output_type}  depends_on=[{deps}]")
        print()

        print(f"Stage 5: Optimization - agent '{agent.name}'")
        chain_endpoints = {chain.step_names[-1] for chain in agent.chains}
        optimized_ir, report = optimize(agent_ir, chain_endpoints)
        print(f"  dead steps removed: {report.removed_dead_steps or '(none)'}")
        print(f"  levels before (sequential): {report.levels_before}")
        print(f"  levels after  (parallel-grouped): {report.levels_after}")
        print()

        # Stages 6 (target code generation) and 7 (interpretation/execution)
        # are added behind CLI flags in a later Phase 3 step, per the Phase 3
        # PRD's requirement that bare `python main.py file.awdl` keep
        # producing exactly the Stage 1-5 output it always has.


if __name__ == "__main__":
    main()

"""
main.py
-------
Entry point for the AWDL prototype (Phase 1).

Usage:
    python main.py examples/researcher.awdl
    python main.py examples/broken.awdl

Runs the source file through:
    1. Lexical Analysis (tokenize)
    2. Syntax Analysis   (parse -> AST)

and prints the results. Semantic analysis, IR generation, optimization,
code generation, and execution are Phase 2 / Phase 3 work.
"""

import sys
from awdl.lexer import tokenize, LexerError
from awdl.parser import parse


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
            print(f"  step   {step.name}({', '.join(step.params)}) -> {step.output_name}: {step.output_type}")
        for chain in agent.chains:
            print(f"  chain  {' -> '.join(chain.step_names)}")
        if agent.on_error:
            print(f"  on_error: {agent.on_error.strategy}({agent.on_error.arg})")
        print()


if __name__ == "__main__":
    main()

"""
codegen.py

Phase 3 - Target Code Generation.

Lowers an optimized AgentIR into an executable specification: a JSON-serializable
execution plan listing steps in a valid topological order, each with its inputs,
output, output type, and dependencies, plus the agent's error-handling policy.
This plan is what the runtime interpreter (interpreter.py) consumes to actually
execute the pipeline - it is the boundary between "what to run" (compiler) and
"how to run it" (runtime), same separation a traditional compiler keeps between
emitted code and the process that executes it.
"""

import json

from .ir import AgentIR, topo_order


def generate_plan(agent_ir: AgentIR) -> dict:
    order = topo_order(agent_ir)

    steps = []
    for name in order:
        node = agent_ir.nodes[name]
        steps.append({
            "name": node.name,
            "inputs": list(node.inputs),
            "output": node.output,
            "output_type": node.output_type,
            "depends_on": sorted(node.depends_on),
        })

    on_error = None
    if agent_ir.on_error is not None:
        on_error = {"strategy": agent_ir.on_error.strategy, "arg": agent_ir.on_error.arg}

    return {
        "agent": agent_ir.agent_name,
        "entry_input": agent_ir.entry_input,
        "steps": steps,
        "on_error": on_error,
    }


def to_json(plan: dict) -> str:
    return json.dumps(plan, indent=2)

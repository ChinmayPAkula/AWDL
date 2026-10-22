"""
codegen.py

Phase 3 - Target Code Generation.

Lowers an optimized AgentIR plus its OptimizationReport into a plain dict,
serializable to JSON: a self-contained execution plan that the interpreter
can run from alone, without the AST or IR. Steps are grouped into levels
(the optimizer's parallel_levels(), after dead-step removal) so the plan
directly reflects the optimized program, not just a flat topological order.
"""

import json

from .ir import AgentIR
from .optimizer import OptimizationReport


def generate_plan(agent_ir: AgentIR, report: OptimizationReport, chain_endpoints: set[str] | None = None) -> dict:
    levels = []
    for level in report.levels_after:
        level_entries = []
        for name in sorted(level):  # deterministic: sort within a level by step name
            node = agent_ir.nodes[name]
            level_entries.append({
                "step": node.name,
                "inputs": list(node.inputs),
                "output": node.output,
                "output_type": node.output_type,
            })
        levels.append(level_entries)

    input_decl = {"name": agent_ir.entry_input, "type": agent_ir.entry_input_type}

    on_error = None
    if agent_ir.on_error is not None:
        on_error = {"strategy": agent_ir.on_error.strategy, "attempts": agent_ir.on_error.arg}

    final_outputs = _final_outputs(agent_ir, chain_endpoints or set())

    return {
        "agent": agent_ir.agent_name,
        "input": input_decl,
        "on_error": on_error,
        "levels": levels,
        "final_outputs": final_outputs,
    }


def _final_outputs(agent_ir: AgentIR, chain_endpoints: set[str]) -> list[str]:
    """The outputs of steps that end a declared chain, if the agent has any
    chains; otherwise the outputs of steps nobody else consumes (the natural
    notion of "the pipeline's result(s)" when there's no chain to say so
    explicitly)."""
    present_endpoints = chain_endpoints & agent_ir.nodes.keys()
    if present_endpoints:
        return sorted(agent_ir.nodes[name].output for name in present_endpoints)

    consumed = set()
    for node in agent_ir.nodes.values():
        consumed.update(node.depends_on)
    return sorted(node.output for name, node in agent_ir.nodes.items() if name not in consumed)


def plan_to_json(plan: dict) -> str:
    return json.dumps(plan, indent=2, sort_keys=False)

"""
optimizer.py

Phase 2 — Code Optimization.

Operates on an AgentIR and returns a new, optimized AgentIR plus an
OptimizationReport describing what changed, so the effect is visible in a
demo:

  a) dead-step elimination      — drop steps whose output is never consumed
                                   and that aren't a declared chain endpoint
  b) independent-step reordering — group steps with no unmet dependencies
                                   into "levels" that could run in parallel
"""

from dataclasses import dataclass

from .ir import AgentIR, IRNode


@dataclass
class OptimizationReport:
    removed_dead_steps: list[str]
    levels_before: list[list[str]]   # each step its own level, in original order
    levels_after: list[list[str]]    # after grouping independents


def optimize(agent_ir: AgentIR, chain_endpoints: set[str] | None = None) -> tuple[AgentIR, OptimizationReport]:
    chain_endpoints = chain_endpoints or set()

    consumed = set()
    for node in agent_ir.nodes.values():
        consumed.update(node.depends_on)

    dead = [
        name for name in agent_ir.nodes
        if name not in consumed and name not in chain_endpoints
    ]

    live_nodes: dict[str, IRNode] = {
        name: node for name, node in agent_ir.nodes.items() if name not in dead
    }
    # also drop dangling depends_on pointing at removed nodes
    for node in live_nodes.values():
        node.depends_on = {d for d in node.depends_on if d in live_nodes}

    optimized_ir = AgentIR(
        agent_name=agent_ir.agent_name,
        nodes=live_nodes,
        entry_input=agent_ir.entry_input,
        on_error=agent_ir.on_error,
    )

    levels_before = [[name] for name in agent_ir.nodes]
    levels_after = parallel_levels(optimized_ir)

    report = OptimizationReport(
        removed_dead_steps=dead,
        levels_before=levels_before,
        levels_after=levels_after,
    )
    return optimized_ir, report


def parallel_levels(agent_ir: AgentIR) -> list[list[str]]:
    """Returns levels of step names; steps within a level have no
    dependency on each other and can conceptually run concurrently."""
    remaining = dict(agent_ir.nodes)
    done: set[str] = set()
    levels: list[list[str]] = []

    while remaining:
        ready = sorted(
            name for name, node in remaining.items()
            if node.depends_on <= done
        )
        if not ready:
            # shouldn't happen for an already-validated DAG; avoid infinite loop
            break
        levels.append(ready)
        for name in ready:
            done.add(name)
            del remaining[name]

    return levels

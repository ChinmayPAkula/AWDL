"""
ir.py

Phase 2 — Intermediate Representation.

Lowers a semantically-valid AgentDecl into a DAG: one IRNode per step, with
depends_on edges derived from the symbol table (a step depends on whichever
other step produces each of its parameters; the agent's raw input is not a
dependency edge, since it's always available).

topo_order() gives a valid execution order and doubles as an IR-level
cycle-detection safety net (it raises if the graph isn't a DAG).
"""

from dataclasses import dataclass, field

from .ast_nodes import AgentDecl, OnErrorDecl
from .symbol_table import SymbolTable


@dataclass
class IRNode:
    name: str                              # step name
    inputs: list[str]                      # variable names consumed
    output: str                            # variable name produced
    output_type: str
    depends_on: set[str] = field(default_factory=set)  # step names this node needs first


@dataclass
class AgentIR:
    agent_name: str
    nodes: dict[str, IRNode]               # step name -> IRNode
    entry_input: str                       # the agent's declared input name
    on_error: OnErrorDecl | None


class CycleError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def build_ir(agent: AgentDecl, symtab: SymbolTable) -> AgentIR:
    nodes: dict[str, IRNode] = {}

    for step in agent.steps:
        depends_on = set()
        for param in step.params:
            producer = symtab.resolve(param)
            if producer is not None and hasattr(producer, "params"):  # a StepDecl
                depends_on.add(producer.name)

        nodes[step.name] = IRNode(
            name=step.name,
            inputs=list(step.params),
            output=step.output_name,
            output_type=step.output_type,
            depends_on=depends_on,
        )

    entry_input = symtab.input_decl.name if symtab.input_decl is not None else ""

    return AgentIR(
        agent_name=agent.name,
        nodes=nodes,
        entry_input=entry_input,
        on_error=agent.on_error,
    )


def topo_order(agent_ir: AgentIR) -> list[str]:
    """Kahn's algorithm. Raises CycleError if the graph isn't a DAG."""
    in_degree = {name: 0 for name in agent_ir.nodes}
    for node in agent_ir.nodes.values():
        for dep in node.depends_on:
            in_degree[node.name] += 1

    # dependents[x] = nodes that depend on x
    dependents: dict[str, list[str]] = {name: [] for name in agent_ir.nodes}
    for node in agent_ir.nodes.values():
        for dep in node.depends_on:
            dependents[dep].append(node.name)

    queue = sorted(name for name, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        queue.sort()
        current = queue.pop(0)
        order.append(current)
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(agent_ir.nodes):
        raise CycleError(f"cycle detected in agent '{agent_ir.agent_name}' IR — cannot compute a topological order")

    return order

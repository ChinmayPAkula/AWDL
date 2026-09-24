"""
semantic.py

Phase 2 — Semantic Analysis.

Walks the AST (one agent at a time) and checks that a syntactically valid
program is also meaningful:

  a) undefined-reference detection  — every step parameter must resolve to
     the agent's input or another step's output
  b) type compatibility             — every value flowing between steps
     must have one of AWDL's known types
  c) cycle detection                — the chain-derived dependency graph
     must be acyclic (DFS with a "visiting" set)
  d) chain consistency              — every name in a chain must be an
     actually-declared step

Like the parser, the analyzer does not stop at the first error: it collects
every error it finds so one mistake doesn't hide the rest of the report.
"""

from .ast_nodes import Program, AgentDecl
from .symbol_table import SymbolTable, DuplicateStepError

KNOWN_TYPES = {"string", "number", "boolean", "list", "object"}


class SemanticError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"Semantic error (line {line}): {message}" if line else f"Semantic error: {message}")
        self.message = message
        self.line = line


class SemanticAnalyzer:
    def __init__(self):
        self.errors: list[SemanticError] = []
        self.errors_by_agent: dict[str, list[SemanticError]] = {}

    def analyze(self, program: Program) -> dict[str, SymbolTable]:
        symtabs: dict[str, SymbolTable] = {}
        for agent in program.agents:
            before = len(self.errors)
            symtabs[agent.name] = self._analyze_agent(agent)
            self.errors_by_agent[agent.name] = self.errors[before:]
        return symtabs

    # ---- per-agent analysis --------------------------------------------------

    def _analyze_agent(self, agent: AgentDecl) -> SymbolTable:
        symtab = SymbolTable()

        for inp in agent.inputs:
            symtab.define_input(inp)

        for step in agent.steps:
            try:
                symtab.define_step(step)
            except DuplicateStepError as e:
                self.errors.append(SemanticError(f"duplicate step '{e.name}' in agent '{agent.name}'", e.line))

        self._check_types_and_refs(agent, symtab)
        self._check_chain_consistency(agent, symtab)
        self._check_cycles(agent, symtab)

        return symtab

    def _check_types_and_refs(self, agent: AgentDecl, symtab: SymbolTable) -> None:
        if symtab.input_decl is not None and symtab.input_decl.type_name not in KNOWN_TYPES:
            self.errors.append(SemanticError(
                f"agent '{agent.name}' input '{symtab.input_decl.name}' has unknown type "
                f"'{symtab.input_decl.type_name}'"
            ))

        for step in agent.steps:
            if step.output_type not in KNOWN_TYPES:
                self.errors.append(SemanticError(
                    f"step '{step.name}' output '{step.output_name}' has unknown type '{step.output_type}'",
                    step.line,
                ))
            for param in step.params:
                producer = symtab.resolve(param)
                if producer is None:
                    self.errors.append(SemanticError(
                        f"step '{step.name}' references undefined parameter '{param}'",
                        step.line,
                    ))

    def _check_chain_consistency(self, agent: AgentDecl, symtab: SymbolTable) -> None:
        for chain in agent.chains:
            for name in chain.step_names:
                if symtab.resolve_step(name) is None:
                    self.errors.append(SemanticError(
                        f"chain references undeclared step '{name}' in agent '{agent.name}'"
                    ))

    def _check_cycles(self, agent: AgentDecl, symtab: SymbolTable) -> None:
        deps = self._build_dependency_graph(agent, symtab)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in deps}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for dep in deps.get(node, ()):
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    return True
                if color[dep] == WHITE and dfs(dep):
                    return True
            color[node] = BLACK
            return False

        for node in list(deps.keys()):
            if color[node] == WHITE:
                if dfs(node):
                    self.errors.append(SemanticError(
                        f"dependency cycle detected in agent '{agent.name}' (involving step '{node}')"
                    ))
                    return

    def _build_dependency_graph(self, agent: AgentDecl, symtab: SymbolTable) -> dict[str, set[str]]:
        """step name -> set of step names it depends on (producers of its params)."""
        deps: dict[str, set[str]] = {step.name: set() for step in agent.steps}
        for step in agent.steps:
            for param in step.params:
                producer = symtab.resolve(param)
                if producer is not None and hasattr(producer, "params"):  # a StepDecl, not the InputDecl
                    deps[step.name].add(producer.name)
        return deps


def analyze(program: Program) -> tuple[dict[str, SymbolTable], list[SemanticError], dict[str, list[SemanticError]]]:
    analyzer = SemanticAnalyzer()
    symtabs = analyzer.analyze(program)
    return symtabs, analyzer.errors, analyzer.errors_by_agent

"""
symbol_table.py

Phase 2 — Symbol Table Management.

A scoped symbol table, one instance per agent. Tracks the agent's declared
input and every step's name, parameters, and output (name + type), and
resolves a variable name back to whichever declaration produces it.
"""

from .ast_nodes import InputDecl, StepDecl


class DuplicateStepError(Exception):
    def __init__(self, name: str, line: int = 0):
        super().__init__(f"duplicate step '{name}' (line {line})")
        self.name = name
        self.line = line


class SymbolTable:
    def __init__(self):
        self._input: InputDecl | None = None
        self._steps: dict[str, StepDecl] = {}

    def define_input(self, input_decl: InputDecl) -> None:
        self._input = input_decl

    def define_step(self, step_decl: StepDecl) -> None:
        if step_decl.name in self._steps:
            raise DuplicateStepError(step_decl.name, step_decl.line)
        self._steps[step_decl.name] = step_decl

    def resolve(self, name: str) -> InputDecl | StepDecl | None:
        if self._input is not None and self._input.name == name:
            return self._input
        for step in self._steps.values():
            if step.output_name == name:
                return step
        return None

    def resolve_step(self, name: str) -> StepDecl | None:
        return self._steps.get(name)

    def all_step_names(self) -> set[str]:
        return set(self._steps.keys())

    @property
    def input_decl(self) -> InputDecl | None:
        return self._input

"""
ast_nodes.py
------------
The Abstract Syntax Tree (AST) node types for AWDL.

The parser (Stage 2) builds a tree of these objects from the token stream.
Later stages (semantic analysis, IR generation) walk this tree.
"""

from dataclasses import dataclass, field


@dataclass
class InputDecl:
    name: str
    type_name: str


@dataclass
class StepDecl:
    name: str
    params: list[str]         # names of inputs this step consumes, e.g. ["query"]
    output_name: str          # e.g. "results"
    output_type: str          # e.g. "list"
    line: int = 0


@dataclass
class ChainDecl:
    """A data-flow chain like: search -> summarize -> validate"""
    step_names: list[str]


@dataclass
class OnErrorDecl:
    strategy: str              # e.g. "retry"
    arg: int                   # e.g. 3


@dataclass
class AgentDecl:
    name: str
    inputs: list[InputDecl] = field(default_factory=list)
    steps: list[StepDecl] = field(default_factory=list)
    chains: list[ChainDecl] = field(default_factory=list)
    on_error: OnErrorDecl | None = None


@dataclass
class Program:
    agents: list[AgentDecl] = field(default_factory=list)

"""
MiniLang AST Node Definitions
──────────────────────────────
Every node carries a `line` field for error reporting in later phases.
"""

from dataclasses import dataclass, field
from typing import Any


# ── Base ─────────────────────────────────────────────────────────────

@dataclass
class ASTNode:
    line: int = 0


# ── Top‑level ────────────────────────────────────────────────────────

@dataclass
class Program(ASTNode):
    name: str = ""
    declarations: list[Any] = field(default_factory=list)
    body: Any = None                       # Compound


# ── Declarations ─────────────────────────────────────────────────────

@dataclass
class VarDecl(ASTNode):
    names: list[str] = field(default_factory=list)
    var_type: Any = None                   # str "integer" or ArrayType

@dataclass
class ArrayType(ASTNode):
    size: int = 0
    elem_type: str = "integer"


# ── Statements ───────────────────────────────────────────────────────

@dataclass
class Compound(ASTNode):
    statements: list[Any] = field(default_factory=list)

@dataclass
class Assign(ASTNode):
    target: Any = None                     # Identifier or ArrayAccess
    value: Any = None                      # expression

@dataclass
class IfStmt(ASTNode):
    condition: Any = None
    then_branch: Any = None
    else_branch: Any = None                # may be None

@dataclass
class WhileStmt(ASTNode):
    condition: Any = None
    body: Any = None

@dataclass
class ReadStmt(ASTNode):
    variables: list[Any] = field(default_factory=list)  # list of Identifier

@dataclass
class WriteStmt(ASTNode):
    items: list[Any] = field(default_factory=list)      # list of exprs/strings

@dataclass
class ProcCall(ASTNode):
    name: str = ""
    args: list[Any] = field(default_factory=list)


# ── Expressions ──────────────────────────────────────────────────────

@dataclass
class BinOp(ASTNode):
    op: str = ""
    left: Any = None
    right: Any = None

@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    operand: Any = None

@dataclass
class Num(ASTNode):
    value: int = 0

@dataclass
class Str(ASTNode):
    value: str = ""

@dataclass
class Identifier(ASTNode):
    name: str = ""

@dataclass
class ArrayAccess(ASTNode):
    name: str = ""
    index: Any = None                      # expression

@dataclass
class FuncCall(ASTNode):
    name: str = ""
    args: list[Any] = field(default_factory=list)


# ── Pretty Printer ───────────────────────────────────────────────────

def print_ast(node: Any, indent: int = 0) -> None:
    """Recursively print an AST tree in readable indented form."""
    pad = "  " * indent

    if node is None:
        print(f"{pad}(none)")
        return

    if isinstance(node, Program):
        print(f"{pad}Program '{node.name}'")
        for d in node.declarations:
            print_ast(d, indent + 1)
        print_ast(node.body, indent + 1)

    elif isinstance(node, VarDecl):
        print(f"{pad}VarDecl {node.names} : {_type_str(node.var_type)}")

    elif isinstance(node, Compound):
        print(f"{pad}Compound")
        for s in node.statements:
            print_ast(s, indent + 1)

    elif isinstance(node, Assign):
        print(f"{pad}Assign")
        print_ast(node.target, indent + 1)
        print_ast(node.value, indent + 1)

    elif isinstance(node, IfStmt):
        print(f"{pad}If")
        print_ast(node.condition, indent + 1)
        print(f"{pad}Then")
        print_ast(node.then_branch, indent + 1)
        if node.else_branch is not None:
            print(f"{pad}Else")
            print_ast(node.else_branch, indent + 1)

    elif isinstance(node, WhileStmt):
        print(f"{pad}While")
        print_ast(node.condition, indent + 1)
        print(f"{pad}Do")
        print_ast(node.body, indent + 1)

    elif isinstance(node, ReadStmt):
        print(f"{pad}Read")
        for v in node.variables:
            print_ast(v, indent + 1)

    elif isinstance(node, WriteStmt):
        print(f"{pad}Write")
        for item in node.items:
            print_ast(item, indent + 1)

    elif isinstance(node, ProcCall):
        print(f"{pad}ProcCall '{node.name}'")
        for a in node.args:
            print_ast(a, indent + 1)

    elif isinstance(node, BinOp):
        print(f"{pad}BinOp '{node.op}'")
        print_ast(node.left, indent + 1)
        print_ast(node.right, indent + 1)

    elif isinstance(node, UnaryOp):
        print(f"{pad}UnaryOp '{node.op}'")
        print_ast(node.operand, indent + 1)

    elif isinstance(node, Num):
        print(f"{pad}Num {node.value}")

    elif isinstance(node, Str):
        print(f"{pad}Str {node.value!r}")

    elif isinstance(node, Identifier):
        print(f"{pad}Id '{node.name}'")

    elif isinstance(node, ArrayAccess):
        print(f"{pad}ArrayAccess '{node.name}'")
        print_ast(node.index, indent + 1)

    elif isinstance(node, FuncCall):
        print(f"{pad}FuncCall '{node.name}'")
        for a in node.args:
            print_ast(a, indent + 1)

    else:
        print(f"{pad}??? {node}")


def _type_str(t: Any) -> str:
    if isinstance(t, ArrayType):
        return f"array[{t.size}] of {t.elem_type}"
    return str(t)

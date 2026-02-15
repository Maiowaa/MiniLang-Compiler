"""
MiniLang Semantic Analyzer
──────────────────────────
Walks the AST and performs:
  1. Symbol‑table construction (variables & arrays)
  2. Undeclared‑identifier detection
  3. Type checking (integer only for now)

Errors are collected with line numbers; analysis always continues.
"""

from minilang.ast_nodes import (
    ASTNode, Program, VarDecl, ArrayType, Compound,
    Assign, IfStmt, WhileStmt, ReadStmt, WriteStmt, ProcCall,
    BinOp, UnaryOp, Num, Str, Identifier, ArrayAccess, FuncCall,
)


# ── Symbol Table Entry ───────────────────────────────────────────────

class Symbol:
    """One entry in the symbol table."""
    def __init__(self, name: str, kind: str, data_type: str,
                 size: int = 0, line: int = 0):
        self.name      = name        # variable name
        self.kind      = kind        # "var" | "array"
        self.data_type = data_type   # "integer"
        self.size      = size        # array size (0 for plain vars)
        self.line      = line        # declaration line

    def __repr__(self) -> str:
        if self.kind == "array":
            return f"Symbol({self.name}, array[{self.size}] of {self.data_type})"
        return f"Symbol({self.name}, {self.data_type})"


# ── Analyzer ─────────────────────────────────────────────────────────

class SemanticAnalyzer:
    """Visit every AST node, build symbol table, report semantic errors."""

    def __init__(self) -> None:
        self.symbols: dict[str, Symbol] = {}
        self.errors: list[str] = []

    def _error(self, line: int, msg: str) -> None:
        self.errors.append(f"[line {line}] {msg}")

    # ── public entry ─────────────────────────────────────────────

    def analyze(self, node: ASTNode) -> None:
        self.visit(node)

    # ── visitor dispatch ─────────────────────────────────────────

    def visit(self, node) -> str:
        """Visit a node and return its inferred type (or 'error')."""
        if node is None:
            return "error"

        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, None)
        if visitor:
            return visitor(node)

        self._error(getattr(node, "line", 0),
                    f"Unknown AST node: {type(node).__name__}")
        return "error"

    # ── top level ────────────────────────────────────────────────

    def visit_Program(self, node: Program) -> str:
        for decl in node.declarations:
            self.visit(decl)
        self.visit(node.body)
        return "void"

    # ── declarations ─────────────────────────────────────────────

    def visit_VarDecl(self, node: VarDecl) -> str:
        if isinstance(node.var_type, ArrayType):
            kind      = "array"
            data_type = node.var_type.elem_type
            size      = node.var_type.size
        else:
            kind      = "var"
            data_type = str(node.var_type)
            size      = 0

        for name in node.names:
            if name in self.symbols:
                self._error(node.line,
                            f"Variable '{name}' already declared "
                            f"(first at line {self.symbols[name].line})")
            else:
                self.symbols[name] = Symbol(name, kind, data_type,
                                            size, node.line)
        return "void"

    # ── statements ───────────────────────────────────────────────

    def visit_Compound(self, node: Compound) -> str:
        for stmt in node.statements:
            self.visit(stmt)
        return "void"

    def visit_Assign(self, node: Assign) -> str:
        target_type = self.visit(node.target)
        value_type  = self.visit(node.value)
        if target_type != "error" and value_type != "error":
            if target_type != value_type:
                self._error(node.line,
                            f"Type mismatch in assignment: "
                            f"'{target_type}' := '{value_type}'")
        return "void"

    def visit_IfStmt(self, node: IfStmt) -> str:
        self.visit(node.condition)
        self.visit(node.then_branch)
        if node.else_branch is not None:
            self.visit(node.else_branch)
        return "void"

    def visit_WhileStmt(self, node: WhileStmt) -> str:
        self.visit(node.condition)
        self.visit(node.body)
        return "void"

    def visit_ReadStmt(self, node: ReadStmt) -> str:
        for var in node.variables:
            self.visit(var)
        return "void"

    def visit_WriteStmt(self, node: WriteStmt) -> str:
        for item in node.items:
            self.visit(item)
        return "void"

    def visit_ProcCall(self, node: ProcCall) -> str:
        for arg in node.args:
            self.visit(arg)
        return "void"

    # ── expressions ──────────────────────────────────────────────

    def visit_BinOp(self, node: BinOp) -> str:
        lt = self.visit(node.left)
        rt = self.visit(node.right)
        if lt == "error" or rt == "error":
            return "error"
        if lt != rt:
            self._error(node.line,
                        f"Type mismatch in '{node.op}': "
                        f"'{lt}' vs '{rt}'")
            return "error"
        return lt                          # both same → propagate

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        return self.visit(node.operand)

    def visit_Num(self, _node: Num) -> str:
        return "integer"

    def visit_Str(self, _node: Str) -> str:
        return "string"

    def visit_Identifier(self, node: Identifier) -> str:
        sym = self.symbols.get(node.name)
        if sym is None:
            self._error(node.line, f"Undeclared identifier '{node.name}'")
            return "error"
        if sym.kind == "array":
            self._error(node.line,
                        f"Array '{node.name}' used without index")
            return "error"
        return sym.data_type

    def visit_ArrayAccess(self, node: ArrayAccess) -> str:
        sym = self.symbols.get(node.name)
        if sym is None:
            self._error(node.line, f"Undeclared identifier '{node.name}'")
            return "error"
        if sym.kind != "array":
            self._error(node.line,
                        f"'{node.name}' is not an array")
            return "error"
        idx_type = self.visit(node.index)
        if idx_type != "error" and idx_type != "integer":
            self._error(node.line, "Array index must be integer")
        return sym.data_type

    def visit_FuncCall(self, node: FuncCall) -> str:
        for arg in node.args:
            self.visit(arg)
        return "integer"                   # assume integer return


# ── Helper: print symbol table ───────────────────────────────────────

def print_symbols(symbols: dict[str, Symbol]) -> None:
    print(f"{'Name':<16} {'Kind':<8} {'Type':<10} {'Size':<6} {'Line'}")
    print("-" * 50)
    for sym in symbols.values():
        print(f"{sym.name:<16} {sym.kind:<8} {sym.data_type:<10} "
              f"{sym.size:<6} {sym.line}")

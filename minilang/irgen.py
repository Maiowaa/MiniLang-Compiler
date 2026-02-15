"""
MiniLang Intermediate Code Generator
─────────────────────────────────────
Walks the AST and emits three‑address code (TAC).

Instruction format:  (op, arg1, arg2, result)

Temporaries  : t1, t2, …
Labels       : L1, L2, …
"""

from minilang.ast_nodes import (
    ASTNode, Program, VarDecl, ArrayType, Compound,
    Assign, IfStmt, WhileStmt, ReadStmt, WriteStmt, ProcCall,
    BinOp, UnaryOp, Num, Str, Identifier, ArrayAccess, FuncCall,
)


class IRInstruction:
    """Single three‑address code instruction."""
    __slots__ = ("op", "arg1", "arg2", "result")

    def __init__(self, op: str, arg1="", arg2="", result=""):
        self.op     = op
        self.arg1   = arg1
        self.arg2   = arg2
        self.result = result

    def __repr__(self) -> str:
        parts = [self.op]
        if self.arg1 != "":
            parts.append(str(self.arg1))
        if self.arg2 != "":
            parts.append(str(self.arg2))
        if self.result != "":
            parts.append(str(self.result))
        return "\t".join(parts)


class IRGenerator:
    """Emit three‑address code from a MiniLang AST."""

    def __init__(self) -> None:
        self.code: list[IRInstruction] = []
        self._temp_count  = 0
        self._label_count = 0

    # ── helpers ──────────────────────────────────────────────────

    def _new_temp(self) -> str:
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _new_label(self) -> str:
        self._label_count += 1
        return f"L{self._label_count}"

    def _emit(self, op: str, arg1="", arg2="", result="") -> None:
        self.code.append(IRInstruction(op, arg1, arg2, result))

    # ── public entry ─────────────────────────────────────────────

    def generate(self, node: ASTNode) -> list[IRInstruction]:
        self.visit(node)
        return self.code

    # ── visitor dispatch ─────────────────────────────────────────

    def visit(self, node) -> str:
        """Visit a node; return the place (temp/var/literal) holding the value."""
        if node is None:
            return ""
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, None)
        if visitor:
            return visitor(node)
        return ""

    # ── top level ────────────────────────────────────────────────

    def visit_Program(self, node: Program) -> str:
        self._emit("PROGRAM", node.name)
        self.visit(node.body)
        self._emit("HALT")
        return ""

    # ── declarations (no code emitted) ───────────────────────────

    def visit_VarDecl(self, _node: VarDecl) -> str:
        return ""

    # ── statements ───────────────────────────────────────────────

    def visit_Compound(self, node: Compound) -> str:
        for stmt in node.statements:
            self.visit(stmt)
        return ""

    def visit_Assign(self, node: Assign) -> str:
        src = self.visit(node.value)
        if isinstance(node.target, ArrayAccess):
            idx = self.visit(node.target.index)
            self._emit("[]=", src, idx, node.target.name)
        else:
            self._emit(":=", src, "", node.target.name)
        return ""

    def visit_IfStmt(self, node: IfStmt) -> str:
        cond = self.visit(node.condition)
        else_label = self._new_label()
        end_label  = self._new_label()

        if node.else_branch is not None:
            self._emit("IFZ", cond, "", else_label)
            self.visit(node.then_branch)
            self._emit("GOTO", "", "", end_label)
            self._emit("LABEL", "", "", else_label)
            self.visit(node.else_branch)
            self._emit("LABEL", "", "", end_label)
        else:
            self._emit("IFZ", cond, "", else_label)
            self.visit(node.then_branch)
            self._emit("LABEL", "", "", else_label)
        return ""

    def visit_WhileStmt(self, node: WhileStmt) -> str:
        top_label = self._new_label()
        end_label = self._new_label()
        self._emit("LABEL", "", "", top_label)
        cond = self.visit(node.condition)
        self._emit("IFZ", cond, "", end_label)
        self.visit(node.body)
        self._emit("GOTO", "", "", top_label)
        self._emit("LABEL", "", "", end_label)
        return ""

    def visit_ReadStmt(self, node: ReadStmt) -> str:
        for var in node.variables:
            self._emit("READ", "", "", var.name)
        return ""

    def visit_WriteStmt(self, node: WriteStmt) -> str:
        for item in node.items:
            val = self.visit(item)
            self._emit("WRITE", val)
        return ""

    def visit_ProcCall(self, node: ProcCall) -> str:
        for arg in node.args:
            val = self.visit(arg)
            self._emit("PARAM", val)
        self._emit("CALL", node.name, str(len(node.args)), "")
        return ""

    # ── expressions ──────────────────────────────────────────────

    def visit_BinOp(self, node: BinOp) -> str:
        left  = self.visit(node.left)
        right = self.visit(node.right)
        tmp   = self._new_temp()
        self._emit(node.op, left, right, tmp)
        return tmp

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        operand = self.visit(node.operand)
        tmp     = self._new_temp()
        self._emit(node.op, operand, "", tmp)
        return tmp

    def visit_Num(self, node: Num) -> str:
        return str(node.value)

    def visit_Str(self, node: Str) -> str:
        return repr(node.value)

    def visit_Identifier(self, node: Identifier) -> str:
        return node.name

    def visit_ArrayAccess(self, node: ArrayAccess) -> str:
        idx = self.visit(node.index)
        tmp = self._new_temp()
        self._emit("=[]", node.name, idx, tmp)
        return tmp

    def visit_FuncCall(self, node: FuncCall) -> str:
        for arg in node.args:
            val = self.visit(arg)
            self._emit("PARAM", val)
        tmp = self._new_temp()
        self._emit("CALL", node.name, str(len(node.args)), tmp)
        return tmp


# ── Pretty printer ───────────────────────────────────────────────────

def print_ir(code: list[IRInstruction]) -> None:
    """Print the three‑address code in a readable table."""
    print(f"{'#':<4} {'Op':<8} {'Arg1':<14} {'Arg2':<14} {'Result'}")
    print("-" * 56)
    for i, instr in enumerate(code):
        print(f"{i:<4} {instr.op:<8} {str(instr.arg1):<14} "
              f"{str(instr.arg2):<14} {instr.result}")

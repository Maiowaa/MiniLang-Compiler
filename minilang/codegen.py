"""
MiniLang Code Generator
───────────────────────
Converts three‑address code (TAC) into stack‑machine pseudo‑assembly.

Target machine model
────────────────────
• Operand stack  — PUSH / POP
• Named memory   — STORE name / LOAD name
• Arithmetic     — ADD, SUB, MUL, DIV  (pop 2 → push 1)
• Comparison     — CMP_LT, CMP_GT, CMP_LE, CMP_GE, CMP_EQ, CMP_NE
• Control flow   — LABEL, JUMP, JUMP_IF_ZERO
• I/O            — READ_INT, WRITE_INT, WRITE_STR
• Array          — ALOAD name (pop index → push value)
•                  ASTORE name (pop value, pop index)
• Program        — HALT
"""

from minilang.irgen import IRInstruction


# ── operator → stack instruction mapping ─────────────────────────────

_ARITH = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "/": "DIV",
}

_CMP = {
    "<":  "CMP_LT",
    ">":  "CMP_GT",
    "<=": "CMP_LE",
    ">=": "CMP_GE",
    "=":  "CMP_EQ",
    "<>": "CMP_NE",
}


class CodeGenerator:
    """Translate a list[IRInstruction] into stack‑machine assembly lines."""

    def __init__(self) -> None:
        self.output: list[str] = []

    def _emit(self, line: str) -> None:
        self.output.append(line)

    # ── public entry ─────────────────────────────────────────────

    def generate(self, ir: list[IRInstruction]) -> list[str]:
        for instr in ir:
            self._translate(instr)
        return self.output

    # ── per‑instruction translation ──────────────────────────────

    def _translate(self, i: IRInstruction) -> None:
        op = i.op

        # ── program / halt ──
        if op == "PROGRAM":
            self._emit(f"; ── program {i.arg1} ──")
            return
        if op == "HALT":
            self._emit("HALT")
            return

        # ── labels & jumps ──
        if op == "LABEL":
            self._emit(f"{i.result}:")
            return
        if op == "GOTO":
            self._emit(f"  JUMP {i.result}")
            return
        if op == "IFZ":
            self._push_operand(i.arg1)
            self._emit(f"  JUMP_IF_ZERO {i.result}")
            return

        # ── assignment  :=  src → dest ──
        if op == ":=":
            self._push_operand(i.arg1)
            self._emit(f"  STORE {i.result}")
            return

        # ── array store  []=  src idx name ──
        if op == "[]=":
            self._push_operand(i.arg2)     # index
            self._push_operand(i.arg1)     # value
            self._emit(f"  ASTORE {i.result}")
            return

        # ── array load  =[]  name idx tmp ──
        if op == "=[]":
            self._push_operand(i.arg2)     # index
            self._emit(f"  ALOAD {i.arg1}")
            self._emit(f"  STORE {i.result}")
            return

        # ── arithmetic / comparison  op arg1 arg2 → result ──
        if op in _ARITH:
            self._push_operand(i.arg1)
            self._push_operand(i.arg2)
            self._emit(f"  {_ARITH[op]}")
            self._emit(f"  STORE {i.result}")
            return
        if op in _CMP:
            self._push_operand(i.arg1)
            self._push_operand(i.arg2)
            self._emit(f"  {_CMP[op]}")
            self._emit(f"  STORE {i.result}")
            return

        # ── logical ──
        if op == "not":
            self._push_operand(i.arg1)
            self._emit("  NOT")
            self._emit(f"  STORE {i.result}")
            return
        if op == "and":
            self._push_operand(i.arg1)
            self._push_operand(i.arg2)
            self._emit("  AND")
            self._emit(f"  STORE {i.result}")
            return
        if op == "or":
            self._push_operand(i.arg1)
            self._push_operand(i.arg2)
            self._emit("  OR")
            self._emit(f"  STORE {i.result}")
            return

        # ── I/O ──
        if op == "READ":
            self._emit(f"  READ_INT")
            self._emit(f"  STORE {i.result}")
            return
        if op == "WRITE":
            val = str(i.arg1)
            if val.startswith("'") or val.startswith('"'):
                self._emit(f"  PUSH_STR {val}")
                self._emit("  WRITE_STR")
            else:
                self._push_operand(val)
                self._emit("  WRITE_INT")
            return

        # ── function call ──
        if op == "PARAM":
            self._push_operand(i.arg1)
            return
        if op == "CALL":
            self._emit(f"  CALL {i.arg1} {i.arg2}")
            self._emit(f"  STORE {i.result}")
            return

        # ── fallback ──
        self._emit(f"  ; unknown IR op: {op}")

    # ── push helper ──────────────────────────────────────────────

    def _push_operand(self, operand: str) -> None:
        """Emit PUSH for a literal, LOAD for a variable/temp (pushes to stack)."""
        s = str(operand)
        if s == "":
            return
        # integer literal → push immediate
        if s.lstrip("-").isdigit():
            self._emit(f"  PUSH {s}")
        else:
            # variable or temporary → load onto stack
            self._emit(f"  LOAD {s}")


# ── Pretty print ─────────────────────────────────────────────────────

def print_asm(lines: list[str]) -> None:
    for line in lines:
        print(line)

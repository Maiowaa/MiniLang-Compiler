"""
MiniLang AI Suggestion Engine
──────────────────────────────
Three-layer architecture for intelligent error fixing and code quality analysis.

  Layer 1 — MATCHER : Fuzzy name matching, keyword confusion, structural patterns
  Layer 2 — DOCTOR  : AST-aware concrete code-rewrite generation
  Layer 3 — ADVISOR : Proactive code-quality analysis on valid programs
"""

import re
import difflib
from typing import Any

from minilang.ast_nodes import (
    ASTNode, Program, VarDecl, ArrayType, Compound,
    Assign, IfStmt, WhileStmt, ReadStmt, WriteStmt, ProcCall,
    BinOp, UnaryOp, Num, Str, Identifier, ArrayAccess, FuncCall,
)
from minilang.tokens import RESERVED_WORDS


# ═══════════════════════════════════════════════════════════════════════
#  Layer 1: MATCHER — fuzzy matching & structural pattern detection
# ═══════════════════════════════════════════════════════════════════════

def fuzzy_match(name: str, candidates: list[str],
                cutoff: float = 0.5, n: int = 3) -> list[str]:
    """Return close matches for `name` from `candidates` using SequenceMatcher."""
    return difflib.get_close_matches(name, candidates, n=n, cutoff=cutoff)


def is_reserved_word(name: str) -> bool:
    """Check if `name` collides with a MiniLang reserved word."""
    return name.lower() in RESERVED_WORDS


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[len(b)]


# ═══════════════════════════════════════════════════════════════════════
#  Layer 2: DOCTOR — concrete code-rewrite generation
# ═══════════════════════════════════════════════════════════════════════

def generate_declaration(name: str, var_type: str = "integer") -> str:
    """Generate a variable declaration statement."""
    return f"var {name} : {var_type};"


def generate_indexed_access(name: str, rhs: str | None = None) -> str:
    """Generate array access syntax."""
    if rhs is not None:
        return f"{name}[<index>] := {rhs}"
    return f"{name}[<index>]"


def fix_unterminated_string(source_line: str) -> str:
    """Append a closing single-quote to an unterminated string."""
    stripped = source_line.rstrip()
    return stripped + "'"


def fix_missing_semicolon(source_line: str) -> str:
    """Append a semicolon to the line."""
    stripped = source_line.rstrip()
    if not stripped.endswith(";"):
        return stripped + ";"
    return stripped


def remove_illegal_char(source_line: str, char: str) -> str:
    """Remove an illegal character from the line."""
    return source_line.replace(char, "", 1)


# ═══════════════════════════════════════════════════════════════════════
#  Main Suggestion Engine
# ═══════════════════════════════════════════════════════════════════════

class SuggestionEngine:
    """
    Generates actionable suggestions for compiler errors and code quality.

    Usage:
        engine = SuggestionEngine(symbols, source_lines, ast)
        hints  = engine.suggest_for_error(error_msg, line_num)
        advice = engine.analyze_code_quality(ast, symbols, ir_code)
    """

    def __init__(self, symbols: dict | None = None,
                 source_lines: list[str] | None = None,
                 ast: ASTNode | None = None) -> None:
        self.symbols = symbols or {}
        self.source_lines = source_lines or []
        self.ast = ast

    # ── Layer 1 + 2: Error → Suggestions ─────────────────────────

    def suggest_for_error(self, error_msg: str, line: int = 0) -> list[str]:
        """
        Analyze an error message and return a list of actionable suggestions.
        Combines Layer 1 (matching) and Layer 2 (code rewrites).
        """
        hints: list[str] = []

        # ── Undeclared identifier ──
        m = re.search(r"Undeclared identifier '(\w+)'", error_msg)
        if m:
            name = m.group(1)
            hints.extend(self._suggest_undeclared(name, line))
            return hints

        # ── Duplicate declaration ──
        m = re.search(r"Variable '(\w+)' already declared \(first at line (\d+)\)", error_msg)
        if m:
            name, first_line = m.group(1), m.group(2)
            hints.append(f"Remove the duplicate declaration of '{name}' on line {line} "
                         f"(already declared at line {first_line})")
            return hints

        # ── Type mismatch in assignment ──
        m = re.search(r"Type mismatch in assignment: '(\w+)' := '(\w+)'", error_msg)
        if m:
            target_type, value_type = m.group(1), m.group(2)
            hints.extend(self._suggest_type_mismatch(target_type, value_type, line))
            return hints

        # ── Type mismatch in operator ──
        m = re.search(r"Type mismatch in '(.+?)': '(\w+)' vs '(\w+)'", error_msg)
        if m:
            op, lt, rt = m.group(1), m.group(2), m.group(3)
            hints.append(f"Both operands of '{op}' must be the same type. "
                         f"Left is '{lt}', right is '{rt}'")
            if lt == "integer" and rt == "string":
                hints.append("Replace the string operand with an integer expression")
            elif lt == "string" and rt == "integer":
                hints.append("Replace the string operand with an integer expression")
            return hints

        # ── Array used without index ──
        m = re.search(r"Array '(\w+)' used without index", error_msg)
        if m:
            name = m.group(1)
            src = self._get_source_line(line)
            # try to extract what's on the RHS if it's an assignment
            rhs_match = re.search(rf"{name}\s*:=\s*(.+)", src) if src else None
            if rhs_match:
                rhs = rhs_match.group(1).rstrip(";").strip()
                hints.append(f"Add index → {name}[<index>] := {rhs}")
            else:
                hints.append(f"Add index → use {name}[<index>] instead of {name}")
            sym = self.symbols.get(name)
            if sym and hasattr(sym, "size") and sym.size > 0:
                hints.append(f"Valid indices for '{name}': 0 to {sym.size - 1}")
            return hints

        # ── Non-array used with index ──
        m = re.search(r"'(\w+)' is not an array", error_msg)
        if m:
            name = m.group(1)
            hints.append(f"Remove the index [...] — '{name}' is a plain variable, not an array")
            src = self._get_source_line(line)
            if src:
                fixed = re.sub(rf"{name}\s*\[.*?\]", name, src)
                hints.append(f"Corrected line → {fixed.strip()}")
            return hints

        # ── Array index must be integer ──
        if "Array index must be integer" in error_msg:
            hints.append("Array indices must be integer expressions")
            hints.append("Replace the index with an integer variable or literal")
            return hints

        # ── Parse errors: Expected X, got Y ──
        m = re.search(r"Expected (\w+), got (\w+)", error_msg)
        if m:
            expected, got = m.group(1), m.group(2)
            hints.extend(self._suggest_parse_fix(expected, got, line))
            return hints

        # ── Unexpected token in expression ──
        m = re.search(r"Unexpected token in expression: (\w+) \((.+?)\)", error_msg)
        if m:
            tok_type, tok_val = m.group(1), m.group(2)
            hints.append(f"Expected a value (number, variable, or '(' expression ')') "
                         f"but found {tok_type}")
            if tok_type == "SEMICOLON":
                hints.append("There may be a missing expression before the ';'")
            elif tok_type == "END":
                hints.append("There may be an incomplete statement before 'end'")
            return hints

        # ── Lexer: unterminated string ──
        if "Unterminated string" in error_msg:
            hints.append("Add a closing ' (single quote) to terminate the string")
            src = self._get_source_line(line)
            if src:
                hints.append(f"Fixed line → {fix_unterminated_string(src)}")
            return hints

        # ── Lexer: unexpected character ──
        m = re.search(r"Unexpected character: '?(.)'?", error_msg)
        if m:
            char = m.group(1)
            hints.append(f"Remove the illegal character '{char}'")
            src = self._get_source_line(line)
            if src:
                hints.append(f"Fixed line → {remove_illegal_char(src, char).strip()}")
            # common confusions
            if char == "@":
                hints.append("MiniLang uses ':=' for assignment, not '@'")
            elif char == "#":
                hints.append("MiniLang uses '!' for comments, not '#'")
            elif char == "&":
                hints.append("MiniLang uses 'and' for logical AND, not '&'")
            elif char == "|":
                hints.append("MiniLang uses 'or' for logical OR, not '|'")
            elif char == "!":
                hints.append("'!' starts a comment in MiniLang — "
                             "use 'not' for logical negation")
            return hints

        # ── Fallback: generic advice ──
        if error_msg:
            hints.append("Review the MiniLang language specification for correct syntax")

        return hints

    # ── Layer 1 helpers ──────────────────────────────────────────

    def _suggest_undeclared(self, name: str, line: int) -> list[str]:
        """Generate suggestions for an undeclared identifier."""
        hints: list[str] = []
        sym_names = list(self.symbols.keys())

        # fuzzy match against symbol table
        matches = fuzzy_match(name, sym_names, cutoff=0.5)
        if matches:
            distances = [(m, _levenshtein(name, m)) for m in matches]
            distances.sort(key=lambda x: x[1])
            best, dist = distances[0]
            hints.append(f"Did you mean '{best}'? (edit distance: {dist})")
            if len(distances) > 1:
                others = ", ".join(f"'{d[0]}'" for d in distances[1:])
                hints.append(f"Other similar names: {others}")

        # keyword confusion check
        if is_reserved_word(name):
            hints.append(f"'{name}' is a reserved keyword and cannot be used "
                         f"as a variable name")

        # suggest adding a declaration
        inferred_type = self._infer_type_from_usage(name, line)
        decl = generate_declaration(name, inferred_type)
        hints.append(f"Add declaration → {decl}")

        return hints

    def _infer_type_from_usage(self, name: str, line: int) -> str:
        """Try to infer what type a variable should be from how it's used."""
        src = self._get_source_line(line)
        if src:
            # check if it's used with an index → probably wants array
            if re.search(rf"{name}\s*\[", src):
                return "array[10] of integer"
            # check if assigned a string
            if re.search(rf"{name}\s*:=\s*'", src):
                return "integer"  # MiniLang only supports integer vars
        return "integer"

    def _suggest_type_mismatch(self, target_type: str, value_type: str,
                               line: int) -> list[str]:
        """Suggest fixes for type mismatch in assignments."""
        hints: list[str] = []
        if target_type == "integer" and value_type == "string":
            hints.append("Replace the string value with an integer expression")
            src = self._get_source_line(line)
            if src:
                # try to show what the string literal is
                m = re.search(r":=\s*'([^']*)'", src)
                if m:
                    hints.append(f"Remove the string literal '{m.group(1)}' "
                                 f"and use an integer instead")
        elif target_type == "string" and value_type == "integer":
            hints.append("The target expects a string but received an integer")
        else:
            hints.append(f"Ensure both sides of ':=' have matching types "
                         f"(have: '{target_type}' := '{value_type}')")
        return hints

    def _suggest_parse_fix(self, expected: str, got: str,
                           line: int) -> list[str]:
        """Generate contextual parse-error suggestions."""
        hints: list[str] = []

        _fix_map = {
            ("SEMICOLON", "BEGIN"):
                "Add a ';' after the declaration before 'begin'",
            ("SEMICOLON", "IDENTIFIER"):
                "Add a ';' at the end of the previous statement",
            ("SEMICOLON", "END"):
                "Add a ';' before 'end' or check for a missing statement",
            ("ASSIGN", "SEMICOLON"):
                "Add ':= <expression>' to complete the assignment",
            ("ASSIGN", "EQ"):
                "Use ':=' for assignment, not '=' (which is comparison in MiniLang)",
            ("RPAREN", "EOF"):
                "Add a closing ')' — there is an unmatched '('",
            ("RBRACKET", "EOF"):
                "Add a closing ']' — there is an unmatched '['",
            ("END", "EOF"):
                "Add 'end' — there is an unmatched 'begin'",
            ("DOT", "EOF"):
                "Add '.' at the end of the program",
            ("IDENTIFIER", "INTLIT"):
                "Expected a variable name but found a number",
            ("IDENTIFIER", "BEGIN"):
                "Expected a variable name — did you forget any declarations?",
            ("INTEGER", "IDENTIFIER"):
                "Expected type 'integer' but found an identifier",
        }

        key = (expected, got)
        if key in _fix_map:
            hints.append(_fix_map[key])
        else:
            hints.append(f"Expected {_readable_token(expected)} but found "
                         f"{_readable_token(got)}")

        # show fixed line if it's a missing semicolon
        if expected == "SEMICOLON":
            src = self._get_source_line(line)
            if src:
                hints.append(f"Fixed line → {fix_missing_semicolon(src)}")

        return hints

    # ── Utility ──────────────────────────────────────────────────

    def _get_source_line(self, line: int) -> str | None:
        """Get source line (1-indexed) safely."""
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return None


# ═══════════════════════════════════════════════════════════════════════
#  Layer 3: ADVISOR — proactive code quality analysis
# ═══════════════════════════════════════════════════════════════════════

class CodeAdvisor:
    """
    Analyze valid MiniLang programs for potential improvements.

    Runs after successful compilation to provide proactive advice.
    """

    def __init__(self, ast: ASTNode, symbols: dict,
                 source_lines: list[str],
                 ir_code: list | None = None) -> None:
        self.ast = ast
        self.symbols = symbols
        self.source_lines = source_lines
        self.ir_code = ir_code or []

    def analyze(self) -> list[str]:
        """Run all Layer 3 analyses and return a list of advisory messages."""
        advice: list[str] = []
        advice.extend(self._find_unused_variables())
        advice.extend(self._find_write_only_variables())
        advice.extend(self._detect_potential_infinite_loops())
        advice.extend(self._detect_redundant_assignments())
        advice.extend(self._detect_constant_folding())
        advice.extend(self._check_array_bounds())
        advice.extend(self._suggest_naming())
        return advice

    # ── unused variables ─────────────────────────────────────────

    def _find_unused_variables(self) -> list[str]:
        """Find variables declared but never referenced."""
        used = set()
        self._collect_used_names(self.ast, used)
        advice = []
        for name, sym in self.symbols.items():
            if name not in used:
                advice.append(
                    f"⚠ WARNING  [line {sym.line}] Variable '{name}' is declared "
                    f"but never used. Consider removing it."
                )
        return advice

    def _collect_used_names(self, node: Any, used: set) -> None:
        """Walk AST and collect all identifier names that are read or written."""
        if node is None:
            return
        if isinstance(node, Identifier):
            used.add(node.name)
        elif isinstance(node, ArrayAccess):
            used.add(node.name)
            self._collect_used_names(node.index, used)
        elif isinstance(node, Program):
            # don't count declarations as "usage"
            self._collect_used_names(node.body, used)
        elif isinstance(node, Compound):
            for s in node.statements:
                self._collect_used_names(s, used)
        elif isinstance(node, Assign):
            self._collect_used_names(node.target, used)
            self._collect_used_names(node.value, used)
        elif isinstance(node, IfStmt):
            self._collect_used_names(node.condition, used)
            self._collect_used_names(node.then_branch, used)
            self._collect_used_names(node.else_branch, used)
        elif isinstance(node, WhileStmt):
            self._collect_used_names(node.condition, used)
            self._collect_used_names(node.body, used)
        elif isinstance(node, ReadStmt):
            for v in node.variables:
                self._collect_used_names(v, used)
        elif isinstance(node, WriteStmt):
            for item in node.items:
                self._collect_used_names(item, used)
        elif isinstance(node, ProcCall):
            for a in node.args:
                self._collect_used_names(a, used)
        elif isinstance(node, FuncCall):
            for a in node.args:
                self._collect_used_names(a, used)
        elif isinstance(node, BinOp):
            self._collect_used_names(node.left, used)
            self._collect_used_names(node.right, used)
        elif isinstance(node, UnaryOp):
            self._collect_used_names(node.operand, used)

    # ── write-only variables ─────────────────────────────────────

    def _find_write_only_variables(self) -> list[str]:
        """Find variables that are assigned to but never read."""
        written: set[str] = set()
        read: set[str] = set()
        self._collect_read_write(self.ast, written, read)
        advice = []
        for name in written - read:
            if name in self.symbols:
                sym = self.symbols[name]
                advice.append(
                    f"⚠ WARNING  Variable '{name}' (line {sym.line}) is assigned "
                    f"but its value is never read."
                )
        return advice

    def _collect_read_write(self, node: Any,
                            written: set, read: set) -> None:
        """Separate write targets from read references."""
        if node is None:
            return
        if isinstance(node, Assign):
            # target is written to
            if isinstance(node.target, Identifier):
                written.add(node.target.name)
            elif isinstance(node.target, ArrayAccess):
                written.add(node.target.name)
                self._collect_reads(node.target.index, read)
            # value is read
            self._collect_reads(node.value, read)
        elif isinstance(node, ReadStmt):
            for v in node.variables:
                if isinstance(v, Identifier):
                    written.add(v.name)
        elif isinstance(node, WriteStmt):
            for item in node.items:
                self._collect_reads(item, read)
        elif isinstance(node, Compound):
            for s in node.statements:
                self._collect_read_write(s, written, read)
        elif isinstance(node, IfStmt):
            self._collect_reads(node.condition, read)
            self._collect_read_write(node.then_branch, written, read)
            self._collect_read_write(node.else_branch, written, read)
        elif isinstance(node, WhileStmt):
            self._collect_reads(node.condition, read)
            self._collect_read_write(node.body, written, read)
        elif isinstance(node, Program):
            self._collect_read_write(node.body, written, read)
        elif isinstance(node, ProcCall):
            for a in node.args:
                self._collect_reads(a, read)
        elif isinstance(node, FuncCall):
            for a in node.args:
                self._collect_reads(a, read)

    def _collect_reads(self, node: Any, read: set) -> None:
        """Collect all identifiers that are read (not assigned to)."""
        if node is None:
            return
        if isinstance(node, Identifier):
            read.add(node.name)
        elif isinstance(node, ArrayAccess):
            read.add(node.name)
            self._collect_reads(node.index, read)
        elif isinstance(node, BinOp):
            self._collect_reads(node.left, read)
            self._collect_reads(node.right, read)
        elif isinstance(node, UnaryOp):
            self._collect_reads(node.operand, read)
        elif isinstance(node, FuncCall):
            for a in node.args:
                self._collect_reads(a, read)

    # ── potential infinite loops ──────────────────────────────────

    def _detect_potential_infinite_loops(self) -> list[str]:
        """Detect while loops where the condition variable is never modified."""
        advice = []
        self._check_while_loops(self.ast, advice)
        return advice

    def _check_while_loops(self, node: Any, advice: list) -> None:
        if node is None:
            return
        if isinstance(node, WhileStmt):
            cond_vars = set()
            self._collect_reads(node.condition, cond_vars)
            body_written: set[str] = set()
            body_read: set[str] = set()
            self._collect_read_write(node.body, body_written, body_read)
            unmodified = cond_vars - body_written
            if unmodified and cond_vars:
                vars_str = ", ".join(f"'{v}'" for v in sorted(unmodified))
                advice.append(
                    f"⚠ WARNING  [line {node.line}] Potential infinite loop — "
                    f"condition variable(s) {vars_str} not modified in loop body."
                )
            # recurse into body
            self._check_while_loops(node.body, advice)
        elif isinstance(node, Compound):
            for s in node.statements:
                self._check_while_loops(s, advice)
        elif isinstance(node, IfStmt):
            self._check_while_loops(node.then_branch, advice)
            self._check_while_loops(node.else_branch, advice)
        elif isinstance(node, Program):
            self._check_while_loops(node.body, advice)

    # ── redundant assignments ────────────────────────────────────

    def _detect_redundant_assignments(self) -> list[str]:
        """Detect x := a; x := b where the first assignment is wasted."""
        advice = []
        self._check_redundant_in(self.ast, advice)
        return advice

    def _check_redundant_in(self, node: Any, advice: list) -> None:
        if node is None:
            return
        if isinstance(node, Compound):
            stmts = node.statements
            for i in range(len(stmts) - 1):
                cur = stmts[i]
                nxt = stmts[i + 1]
                if (isinstance(cur, Assign) and isinstance(nxt, Assign)):
                    cur_name = self._assign_target_name(cur)
                    nxt_name = self._assign_target_name(nxt)
                    if (cur_name and nxt_name and cur_name == nxt_name
                            and not self._reads_var(nxt.value, cur_name)):
                        advice.append(
                            f"⚠ WARNING  [line {cur.line}] Redundant assignment — "
                            f"'{cur_name}' is immediately overwritten on line {nxt.line}."
                        )
            for s in stmts:
                self._check_redundant_in(s, advice)
        elif isinstance(node, IfStmt):
            self._check_redundant_in(node.then_branch, advice)
            self._check_redundant_in(node.else_branch, advice)
        elif isinstance(node, WhileStmt):
            self._check_redundant_in(node.body, advice)
        elif isinstance(node, Program):
            self._check_redundant_in(node.body, advice)

    @staticmethod
    def _assign_target_name(node: Assign) -> str | None:
        if isinstance(node.target, Identifier):
            return node.target.name
        return None

    def _reads_var(self, node: Any, var_name: str) -> bool:
        """Check if an expression reads a specific variable."""
        if node is None:
            return False
        if isinstance(node, Identifier):
            return node.name == var_name
        if isinstance(node, ArrayAccess):
            return node.name == var_name or self._reads_var(node.index, var_name)
        if isinstance(node, BinOp):
            return self._reads_var(node.left, var_name) or self._reads_var(node.right, var_name)
        if isinstance(node, UnaryOp):
            return self._reads_var(node.operand, var_name)
        if isinstance(node, FuncCall):
            return any(self._reads_var(a, var_name) for a in node.args)
        return False

    # ── constant folding opportunities ───────────────────────────

    def _detect_constant_folding(self) -> list[str]:
        """Detect BinOp nodes where both operands are Num literals."""
        advice = []
        self._check_const_fold(self.ast, advice)
        return advice

    def _check_const_fold(self, node: Any, advice: list) -> None:
        if node is None:
            return
        if isinstance(node, BinOp):
            if isinstance(node.left, Num) and isinstance(node.right, Num):
                try:
                    result = self._eval_const(node.op, node.left.value, node.right.value)
                    if result is not None:
                        advice.append(
                            f"ℹ OPTIMIZE [line {node.line}] Constant expression "
                            f"{node.left.value} {node.op} {node.right.value} "
                            f"can be simplified to {result}."
                        )
                except Exception:
                    pass
            self._check_const_fold(node.left, advice)
            self._check_const_fold(node.right, advice)
        elif isinstance(node, Assign):
            self._check_const_fold(node.value, advice)
        elif isinstance(node, Compound):
            for s in node.statements:
                self._check_const_fold(s, advice)
        elif isinstance(node, IfStmt):
            self._check_const_fold(node.condition, advice)
            self._check_const_fold(node.then_branch, advice)
            self._check_const_fold(node.else_branch, advice)
        elif isinstance(node, WhileStmt):
            self._check_const_fold(node.condition, advice)
            self._check_const_fold(node.body, advice)
        elif isinstance(node, WriteStmt):
            for item in node.items:
                self._check_const_fold(item, advice)
        elif isinstance(node, Program):
            self._check_const_fold(node.body, advice)

    @staticmethod
    def _eval_const(op: str, a: int, b: int) -> int | None:
        ops = {"+": a + b, "-": a - b, "*": a * b}
        if op == "/" and b != 0:
            ops["/"] = a // b
        return ops.get(op)

    # ── array bounds checking ────────────────────────────────────

    def _check_array_bounds(self) -> list[str]:
        """Check for array accesses with constant indices that are out of bounds."""
        advice = []
        self._walk_array_bounds(self.ast, advice)
        return advice

    def _walk_array_bounds(self, node: Any, advice: list) -> None:
        if node is None:
            return
        if isinstance(node, ArrayAccess):
            sym = self.symbols.get(node.name)
            if sym and hasattr(sym, "size") and sym.size > 0:
                if isinstance(node.index, Num):
                    idx = node.index.value
                    if idx < 0 or idx >= sym.size:
                        advice.append(
                            f"⚠ WARNING  [line {node.line}] Array index {idx} "
                            f"is out of bounds for '{node.name}' "
                            f"(valid range: 0 to {sym.size - 1})."
                        )
            self._walk_array_bounds(node.index, advice)
        elif isinstance(node, Assign):
            self._walk_array_bounds(node.target, advice)
            self._walk_array_bounds(node.value, advice)
        elif isinstance(node, Compound):
            for s in node.statements:
                self._walk_array_bounds(s, advice)
        elif isinstance(node, IfStmt):
            self._walk_array_bounds(node.condition, advice)
            self._walk_array_bounds(node.then_branch, advice)
            self._walk_array_bounds(node.else_branch, advice)
        elif isinstance(node, WhileStmt):
            self._walk_array_bounds(node.condition, advice)
            self._walk_array_bounds(node.body, advice)
        elif isinstance(node, WriteStmt):
            for item in node.items:
                self._walk_array_bounds(item, advice)
        elif isinstance(node, BinOp):
            self._walk_array_bounds(node.left, advice)
            self._walk_array_bounds(node.right, advice)
        elif isinstance(node, Program):
            self._walk_array_bounds(node.body, advice)

    # ── naming quality ───────────────────────────────────────────

    def _suggest_naming(self) -> list[str]:
        """Suggest better names for single-character variables."""
        short_names = [name for name in self.symbols if len(name) == 1]
        if not short_names:
            return []

        _suggestions = {
            "a": "accumulator, result, first_value",
            "b": "buffer, second_value, base",
            "c": "counter, count, char_val",
            "d": "delta, difference, divisor",
            "i": "index, iterator, counter",
            "j": "inner_index, col_index",
            "k": "key, constant",
            "n": "count, total, size",
            "p": "pointer, position, product",
            "r": "result, remainder, row",
            "s": "sum, size, start",
            "t": "temp, total, time_val",
            "x": "x_coord, input_val, value",
            "y": "y_coord, output_val, result",
            "z": "z_coord, depth, extra",
        }

        names_str = ", ".join(f"'{n}'" for n in sorted(short_names))
        suggestions_detail = []
        for n in sorted(short_names):
            alt = _suggestions.get(n, "a_more_descriptive_name")
            suggestions_detail.append(f"'{n}' → {alt}")

        advice = [
            f"ℹ STYLE    Single-character variable names ({names_str}) "
            f"reduce readability. Consider more descriptive names:",
        ]
        for detail in suggestions_detail:
            advice.append(f"           {detail}")

        return advice


# ═══════════════════════════════════════════════════════════════════════
#  Utility
# ═══════════════════════════════════════════════════════════════════════

def _readable_token(tok_name: str) -> str:
    """Convert TokenType name to human-readable form."""
    _map = {
        "SEMICOLON": "';'",
        "COLON": "':'",
        "COMMA": "','",
        "DOT": "'.'",
        "LPAREN": "'('",
        "RPAREN": "')'",
        "LBRACKET": "'['",
        "RBRACKET": "']'",
        "ASSIGN": "':='",
        "EQ": "'='",
        "PLUS": "'+'",
        "MINUS": "'-'",
        "STAR": "'*'",
        "SLASH": "'/'",
        "BEGIN": "'begin'",
        "END": "'end'",
        "IF": "'if'",
        "THEN": "'then'",
        "ELSE": "'else'",
        "WHILE": "'while'",
        "DO": "'do'",
        "PROGRAM": "'program'",
        "VAR": "'var'",
        "INTEGER": "'integer'",
        "IDENTIFIER": "an identifier",
        "INTLIT": "a number",
        "STRLIT": "a string",
        "EOF": "end of file",
    }
    return _map.get(tok_name, tok_name)

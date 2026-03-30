"""
MiniLang Listing Generator
──────────────────────────
Produces a compiler listing that shows:
  1. Source code with line numbers
  2. Errors printed directly below the line they belong to
  3. AI suggestions (💡 FIX) below each error
  4. Target code only if the source is error‑free
  5. AI Code Advisor section for clean compiles
"""

from minilang.lexer import Lexer
from minilang.parser import Parser
from minilang.semantic import SemanticAnalyzer
from minilang.irgen import IRGenerator
from minilang.codegen import CodeGenerator
from minilang.suggestions import CodeAdvisor


def _group_errors(errors: list[str]) -> dict[int, list[str]]:
    """Parse '[line N] …' messages and group them by line number."""
    grouped: dict[int, list[str]] = {}
    for msg in errors:
        line = 0
        if msg.startswith("[line "):
            try:
                line = int(msg.split("]")[0].replace("[line ", ""))
            except ValueError:
                pass
        grouped.setdefault(line, []).append(msg)
    return grouped


def _merge_suggestions(*dicts: dict[int, list[str]]) -> dict[int, list[str]]:
    """Merge multiple suggestion dicts into one, keyed by line number."""
    merged: dict[int, list[str]] = {}
    for d in dicts:
        for line, hints in d.items():
            merged.setdefault(line, []).extend(hints)
    return merged


def compile_listing(source: str, show_suggestions: bool = True,
                    advisor_only: bool = False) -> str:
    """
    Run the full compiler pipeline and return a listing string.

    The listing contains:
      • Numbered source lines
      • Errors shown under the line they belong to
      • AI suggestions (💡 FIX) under each error
      • A summary section
      • Target code (only if zero errors)
      • AI Code Advisor section (on clean compiles)
    """
    lines = source.splitlines()
    all_errors: list[str] = []
    out: list[str] = []

    # ── Phase 1: Lexing ──────────────────────────────────────────
    lexer  = Lexer(source)
    tokens = lexer.tokenize()
    all_errors.extend(lexer.errors)

    # ── Phase 2: Parsing ─────────────────────────────────────────
    parser = Parser(tokens)
    ast    = parser.parse()
    all_errors.extend(parser.errors)

    # ── Phase 3: Semantic ────────────────────────────────────────
    analyzer = SemanticAnalyzer()
    if not lexer.errors and not parser.errors:
        analyzer.analyze(ast, source)
        all_errors.extend(analyzer.errors)

    # ── Collect all suggestions ──────────────────────────────────
    all_suggestions = _merge_suggestions(
        lexer.suggestions,
        parser.suggestions,
        analyzer.suggestions,
    )

    # ── Build the listing ────────────────────────────────────────
    grouped = _group_errors(all_errors)

    if not advisor_only:
        out.append("═══ Source Listing ═══")
        out.append("")
        for i, line in enumerate(lines, start=1):
            out.append(f"  {i:4d} | {line}")
            if i in grouped:
                for err in grouped[i]:
                    out.append(f"       *** {err}")
                # show suggestions for this line
                if show_suggestions and i in all_suggestions:
                    seen = set()
                    for hint in all_suggestions[i]:
                        if hint not in seen:
                            out.append(f"       💡 FIX: {hint}")
                            seen.add(hint)

        # errors not tied to a line
        if 0 in grouped:
            out.append("")
            for err in grouped[0]:
                out.append(f"  *** {err}")

        # ── Summary ──────────────────────────────────────────────
        out.append("")
        total = len(all_errors)
        if total:
            out.append(f"── {total} error(s) found. Target code NOT generated. ──")
        else:
            out.append("── 0 errors. Compilation successful. ──")

            # ── Phase 4 + 5: IR → Assembly ───────────────────────
            gen  = IRGenerator()
            ir   = gen.generate(ast)
            cg   = CodeGenerator()
            asm  = cg.generate(ir)

            out.append("")
            out.append("═══ Generated Code ═══")
            out.append("")
            for asm_line in asm:
                out.append(asm_line)

    # ── Layer 3: AI Code Advisor (only on clean compiles) ────────
    if show_suggestions and not all_errors:
        gen  = IRGenerator()
        ir   = gen.generate(ast)

        advisor = CodeAdvisor(
            ast=ast,
            symbols=analyzer.symbols,
            source_lines=lines,
            ir_code=ir,
        )
        advice = advisor.analyze()
        if advice:
            out.append("")
            out.append("═══ AI Code Advisor ═══")
            out.append("")
            for a in advice:
                out.append(f"  {a}")

    return "\n".join(out)

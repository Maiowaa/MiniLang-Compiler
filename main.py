#!/usr/bin/env python3
"""
MiniLang Compiler — CLI Entry Point
────────────────────────────────────
Usage:  python3 main.py <source_file> [--phase lexer|parser|semantic|ir|codegen|compile]
                                      [--no-suggestions]
                                      [--advisor-only]

Default phase is 'compile' (full listing output).
AI suggestions are enabled by default. Use --no-suggestions to suppress.
"""

import sys
from minilang.lexer import Lexer
from minilang.parser import Parser
from minilang.ast_nodes import print_ast
from minilang.semantic import SemanticAnalyzer, print_symbols
from minilang.irgen import IRGenerator, print_ir
from minilang.codegen import CodeGenerator, print_asm
from minilang.listing import compile_listing


def _print_suggestions(suggestions: dict[int, list[str]]) -> None:
    """Print AI suggestions grouped by line number."""
    if not suggestions:
        return
    for line in sorted(suggestions):
        for hint in suggestions[line]:
            print(f"  💡 FIX [line {line}]: {hint}")


def run_lexer(source: str, show_suggestions: bool = True) -> None:
    """Tokenize and print the token table."""
    lexer  = Lexer(source)
    tokens = lexer.tokenize()

    print(f"{'Line':<6} {'Token Type':<14} {'Value'}")
    print("-" * 50)
    for tok in tokens:
        print(f"{tok.line:<6} {tok.token_type.name:<14} {tok.value!r}")

    if lexer.errors:
        print(f"\n── {len(lexer.errors)} lexical error(s) ──")
        for err in lexer.errors:
            print(f"  {err}")
        if show_suggestions and lexer.suggestions:
            print(f"\n═══ AI Suggestions ═══")
            _print_suggestions(lexer.suggestions)
    else:
        print("\nNo lexical errors.")


def run_parser(source: str, show_suggestions: bool = True):
    """Tokenize → Parse → print AST. Returns (ast, has_errors)."""
    # ── lexing ──
    lexer  = Lexer(source)
    tokens = lexer.tokenize()

    if lexer.errors:
        print(f"── {len(lexer.errors)} lexical error(s) ──")
        for err in lexer.errors:
            print(f"  {err}")
        if show_suggestions and lexer.suggestions:
            print(f"\n═══ AI Suggestions ═══")
            _print_suggestions(lexer.suggestions)
        print()

    # ── parsing ──
    parser = Parser(tokens)
    ast    = parser.parse()

    print("═══ AST ═══")
    print_ast(ast)

    if parser.errors:
        print(f"\n── {len(parser.errors)} parse error(s) ──")
        for err in parser.errors:
            print(f"  {err}")
        if show_suggestions and parser.suggestions:
            print(f"\n═══ AI Suggestions ═══")
            _print_suggestions(parser.suggestions)

    has_errors = bool(lexer.errors or parser.errors)
    return ast, has_errors


def run_semantic(source: str, show_suggestions: bool = True):
    """Tokenize → Parse → Semantic analysis. Returns (ast, has_errors)."""
    ast, has_errors = run_parser(source, show_suggestions)

    if has_errors:
        print("\nSkipping semantic analysis due to earlier errors.")
        return ast, True

    # ── semantic ──
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast, source)

    print("\n═══ Symbol Table ═══")
    print_symbols(analyzer.symbols)

    if analyzer.errors:
        print(f"\n── {len(analyzer.errors)} semantic error(s) ──")
        for err in analyzer.errors:
            print(f"  {err}")
        if show_suggestions and analyzer.suggestions:
            print(f"\n═══ AI Suggestions ═══")
            _print_suggestions(analyzer.suggestions)
        return ast, True
    else:
        print("\nNo semantic errors.")

    return ast, False


def run_ir(source: str, show_suggestions: bool = True):
    """Tokenize → Parse → Semantic → IR generation. Returns (ir_code, has_errors)."""
    ast, has_errors = run_semantic(source, show_suggestions)

    if has_errors:
        print("\nSkipping IR generation due to earlier errors.")
        return [], True

    # ── IR generation ──
    gen  = IRGenerator()
    code = gen.generate(ast)

    print("\n═══ Three-Address Code ═══")
    print_ir(code)
    return code, False


def run_codegen(source: str, show_suggestions: bool = True) -> None:
    """Full pipeline: Lexer → Parser → Semantic → IR → Code generation."""
    ir_code, has_errors = run_ir(source, show_suggestions)

    if has_errors:
        print("\nSkipping code generation due to earlier errors.")
        return

    # ── code generation ──
    cg  = CodeGenerator()
    asm = cg.generate(ir_code)

    print("\n═══ Stack-Machine Assembly ═══")
    print_asm(asm)


def run_compile(source: str, show_suggestions: bool = True,
                advisor_only: bool = False) -> None:
    """Full pipeline: produce a compiler listing with inline errors + code."""
    print(compile_listing(source,
                          show_suggestions=show_suggestions,
                          advisor_only=advisor_only))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <source_file> "
              "[--phase lexer|parser|semantic|ir|codegen|compile] "
              "[--no-suggestions] [--advisor-only]")
        sys.exit(1)

    filepath = sys.argv[1]
    phase    = "compile"                   # default

    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        if idx + 1 < len(sys.argv):
            phase = sys.argv[idx + 1]

    show_suggestions = "--no-suggestions" not in sys.argv
    advisor_only     = "--advisor-only" in sys.argv

    try:
        with open(filepath, "r") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file '{filepath}' not found.")
        sys.exit(1)

    if phase == "lexer":
        run_lexer(source, show_suggestions)
    elif phase == "parser":
        run_parser(source, show_suggestions)
    elif phase == "semantic":
        run_semantic(source, show_suggestions)
    elif phase == "ir":
        run_ir(source, show_suggestions)
    elif phase == "codegen":
        run_codegen(source, show_suggestions)
    else:
        run_compile(source, show_suggestions, advisor_only)


if __name__ == "__main__":
    main()

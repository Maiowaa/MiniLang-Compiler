#!/usr/bin/env python3
"""
MiniLang Compiler — CLI Entry Point
────────────────────────────────────
Usage:  python3 main.py <source_file> [--phase lexer|parser|semantic|ir|codegen|compile]

Default phase is 'compile' (full listing output).
"""

import sys
from minilang.lexer import Lexer
from minilang.parser import Parser
from minilang.ast_nodes import print_ast
from minilang.semantic import SemanticAnalyzer, print_symbols
from minilang.irgen import IRGenerator, print_ir
from minilang.codegen import CodeGenerator, print_asm
from minilang.listing import compile_listing


def run_lexer(source: str) -> None:
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
    else:
        print("\nNo lexical errors.")


def run_parser(source: str):
    """Tokenize → Parse → print AST. Returns (ast, has_errors)."""
    # ── lexing ──
    lexer  = Lexer(source)
    tokens = lexer.tokenize()

    if lexer.errors:
        print(f"── {len(lexer.errors)} lexical error(s) ──")
        for err in lexer.errors:
            print(f"  {err}")
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

    has_errors = bool(lexer.errors or parser.errors)
    return ast, has_errors


def run_semantic(source: str):
    """Tokenize → Parse → Semantic analysis. Returns (ast, has_errors)."""
    ast, has_errors = run_parser(source)

    if has_errors:
        print("\nSkipping semantic analysis due to earlier errors.")
        return ast, True

    # ── semantic ──
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)

    print("\n═══ Symbol Table ═══")
    print_symbols(analyzer.symbols)

    if analyzer.errors:
        print(f"\n── {len(analyzer.errors)} semantic error(s) ──")
        for err in analyzer.errors:
            print(f"  {err}")
        return ast, True
    else:
        print("\nNo semantic errors.")

    return ast, False


def run_ir(source: str):
    """Tokenize → Parse → Semantic → IR generation. Returns (ir_code, has_errors)."""
    ast, has_errors = run_semantic(source)

    if has_errors:
        print("\nSkipping IR generation due to earlier errors.")
        return [], True

    # ── IR generation ──
    gen  = IRGenerator()
    code = gen.generate(ast)

    print("\n═══ Three-Address Code ═══")
    print_ir(code)
    return code, False


def run_codegen(source: str) -> None:
    """Full pipeline: Lexer → Parser → Semantic → IR → Code generation."""
    ir_code, has_errors = run_ir(source)

    if has_errors:
        print("\nSkipping code generation due to earlier errors.")
        return

    # ── code generation ──
    cg  = CodeGenerator()
    asm = cg.generate(ir_code)

    print("\n═══ Stack-Machine Assembly ═══")
    print_asm(asm)


def run_compile(source: str) -> None:
    """Full pipeline: produce a compiler listing with inline errors + code."""
    print(compile_listing(source))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <source_file> [--phase lexer|parser|semantic|ir|codegen|compile]")
        sys.exit(1)

    filepath = sys.argv[1]
    phase    = "compile"                   # default

    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        if idx + 1 < len(sys.argv):
            phase = sys.argv[idx + 1]

    try:
        with open(filepath, "r") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file '{filepath}' not found.")
        sys.exit(1)

    if phase == "lexer":
        run_lexer(source)
    elif phase == "parser":
        run_parser(source)
    elif phase == "semantic":
        run_semantic(source)
    elif phase == "ir":
        run_ir(source)
    elif phase == "codegen":
        run_codegen(source)
    else:
        run_compile(source)


if __name__ == "__main__":
    main()

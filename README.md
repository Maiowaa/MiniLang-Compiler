# MiniLang Compiler

A complete compiler pipeline for **MiniLang**, a small imperative programming language, built in Python.

## Features

- **6-phase pipeline:** Lexer → Parser → Semantic Analyzer → IR Generator → Code Generator → Listing
- **Robust error handling** — reports all errors with line numbers, doesn't stop at first error
- **Phase-by-phase testing** via `--phase` CLI flag
- **Stack-machine assembly** output
- **Listing file** with numbered source lines and inline errors

## Quick Start

```bash
# Full compile (listing + assembly if no errors)
python3 main.py examples/fib.ml

# Run individual phases
python3 main.py examples/fib.ml --phase lexer
python3 main.py examples/fib.ml --phase parser
python3 main.py examples/fib.ml --phase semantic
python3 main.py examples/fib.ml --phase ir
python3 main.py examples/fib.ml --phase codegen
```

## Language Syntax

```
program fib;
var a, b, temp, i : integer;
begin
  a := 0;
  b := 1;
  i := 10;
  while i > 0 do
  begin
    temp := a + b;
    a := b;
    b := temp;
    i := i - 1
  end;
  write('Result: ', b)
end.
```

## Project Structure

```
minilang/
├── tokens.py      # Token definitions
├── lexer.py       # Lexical analyzer
├── ast_nodes.py   # AST node classes
├── parser.py      # Recursive descent parser
├── semantic.py    # Semantic analyzer
├── irgen.py       # Three-address code generator
├── codegen.py     # Stack-machine code generator
└── listing.py     # Listing file generator
```


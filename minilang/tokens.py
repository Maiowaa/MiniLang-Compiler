"""
MiniLang Token Definitions
───────────────────────────
TokenType enum  — every lexeme category the lexer can produce.
Token dataclass — (type, value, line) triple carried through the pipeline.
RESERVED_WORDS  — maps lowercased keyword → TokenType for O(1) lookup.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


# ── Token Categories ────────────────────────────────────────────────

class TokenType(Enum):
    # ── Reserved words ──
    PROGRAM   = auto()
    VAR       = auto()
    ARRAY     = auto()
    OF        = auto()
    INTEGER   = auto()
    BEGIN     = auto()
    END       = auto()
    IF        = auto()
    THEN      = auto()
    ELSE      = auto()
    WHILE     = auto()
    DO        = auto()
    READ      = auto()
    WRITE     = auto()
    PROCEDURE = auto()
    FUNCTION  = auto()
    RETURN    = auto()
    NOT       = auto()
    AND       = auto()
    OR        = auto()

    # ── Literals ──
    INTLIT    = auto()
    STRLIT    = auto()

    # ── Identifier ──
    IDENTIFIER = auto()

    # ── Operators ──
    PLUS      = auto()   # +
    MINUS     = auto()   # -
    STAR      = auto()   # *
    SLASH     = auto()   # /
    ASSIGN    = auto()   # :=
    EQ        = auto()   # =
    NEQ       = auto()   # <>
    LT        = auto()   # <
    GT        = auto()   # >
    LTE       = auto()   # <=
    GTE       = auto()   # >=

    # ── Delimiters ──
    LPAREN    = auto()   # (
    RPAREN    = auto()   # )
    LBRACKET  = auto()   # [
    RBRACKET  = auto()   # ]
    SEMICOLON = auto()   # ;
    COLON     = auto()   # :
    COMMA     = auto()   # ,
    DOT       = auto()   # .

    # ── Special ──
    EOF       = auto()
    ERROR     = auto()


# ── Token Data ──────────────────────────────────────────────────────

@dataclass
class Token:
    token_type: TokenType
    value: Any            # lexeme string, int value, or error message
    line: int

    def __repr__(self) -> str:
        return f"Token({self.token_type.name}, {self.value!r}, line={self.line})"


# ── Reserved‑word lookup (case‑insensitive) ─────────────────────────

RESERVED_WORDS: dict[str, TokenType] = {
    "program":   TokenType.PROGRAM,
    "var":       TokenType.VAR,
    "array":     TokenType.ARRAY,
    "of":        TokenType.OF,
    "integer":   TokenType.INTEGER,
    "begin":     TokenType.BEGIN,
    "end":       TokenType.END,
    "if":        TokenType.IF,
    "then":      TokenType.THEN,
    "else":      TokenType.ELSE,
    "while":     TokenType.WHILE,
    "do":        TokenType.DO,
    "read":      TokenType.READ,
    "write":     TokenType.WRITE,
    "procedure": TokenType.PROCEDURE,
    "function":  TokenType.FUNCTION,
    "return":    TokenType.RETURN,
    "not":       TokenType.NOT,
    "and":       TokenType.AND,
    "or":        TokenType.OR,
}

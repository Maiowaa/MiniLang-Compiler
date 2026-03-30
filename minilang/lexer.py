"""
MiniLang Lexer
──────────────
Transforms raw source text into a stream of Token objects.

Key design points
  • Case-insensitive identifiers (folded to lowercase).
  • Identifier length significant only up to 32 characters.
  • Comments start with '!' and run to end-of-line.
  • Strings delimited by single quotes with \\n, \\t, \\' escapes.
  • Errors produce ERROR tokens; scanning always continues.
"""

from minilang.tokens import Token, TokenType, RESERVED_WORDS
from minilang.suggestions import SuggestionEngine


class Lexer:
    """Scan MiniLang source and yield tokens one at a time."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos    = 0          # current index into source
        self.line   = 1          # current line number
        self.errors: list[str] = []
        self.suggestions: dict[int, list[str]] = {}

    # ── helpers ──────────────────────────────────────────────────

    def _current(self) -> str:
        """Return current char or empty string at EOF."""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return ""

    def _peek(self) -> str:
        """Return next char (one ahead) without advancing."""
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return ""

    def _advance(self) -> str:
        """Consume and return the current character."""
        ch = self._current()
        if ch == "\n":
            self.line += 1
        self.pos += 1
        return ch

    def _match(self, expected: str) -> bool:
        """Consume next char only if it matches `expected`."""
        if self._current() == expected:
            self._advance()
            return True
        return False

    # ── skip whitespace & comments ───────────────────────────────

    def skip_ws_and_c(self) -> None:
        """Skip whitespace and '!' line‑comments."""
        while self.pos < len(self.source):
            ch = self._current()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "!":
                # comment runs until end of line
                while self.pos < len(self.source) and self._current() != "\n":
                    self._advance()
            else:
                break

    # ── identifier / reserved word ───────────────────────────────

    def read_identifier(self) -> Token:
        start = self.pos
        line  = self.line
        while self._current().isalnum() or self._current() == "_":
            self._advance()
        text = self.source[start:self.pos].lower()   # case-fold
        text = text[:32]                              # significant length
        ttype = RESERVED_WORDS.get(text, TokenType.IDENTIFIER)
        return Token(ttype, text, line)

    # ── integer literal ──────────────────────────────────────────

    def read_number(self) -> Token:
        start = self.pos
        line  = self.line
        while self._current().isdigit():
            self._advance()
        return Token(TokenType.INTLIT, int(self.source[start:self.pos]), line)

    # ── string literal ───────────────────────────────────────────

    def read_string(self) -> Token:
        line = self.line
        self._advance()                     # consume opening '
        chars: list[str] = []
        while self.pos < len(self.source) and self._current() != "'":
            if self._current() == "\n":
                # unterminated string (hit newline)
                msg = f"[line {line}] Unterminated string"
                self.errors.append(msg)
                self._add_suggestion(msg, line)
                return Token(TokenType.ERROR, msg, line)
            if self._current() == "\\":
                self._advance()             # consume backslash
                esc = self._advance()       # consume escape char
                if esc == "n":
                    chars.append("\n")
                elif esc == "t":
                    chars.append("\t")
                elif esc == "'":
                    chars.append("'")
                elif esc == "\\":
                    chars.append("\\")
                else:
                    chars.append(esc)       # unknown escape — keep literal
            else:
                chars.append(self._advance())
        if self.pos >= len(self.source):
            msg = f"[line {line}] Unterminated string (hit EOF)"
            self.errors.append(msg)
            self._add_suggestion(msg, line)
            return Token(TokenType.ERROR, msg, line)
        self._advance()                     # consume closing '
        return Token(TokenType.STRLIT, "".join(chars), line)

    # ── operators & delimiters ───────────────────────────────────

    def read_op_or_delim(self) -> Token:
        line = self.line
        ch   = self._advance()

        # ── compound operators ──
        if ch == ":" and self._match("="):
            return Token(TokenType.ASSIGN, ":=", line)
        if ch == "<":
            if self._match("="):
                return Token(TokenType.LTE, "<=", line)
            if self._match(">"):
                return Token(TokenType.NEQ, "<>", line)
            return Token(TokenType.LT, "<", line)
        if ch == ">":
            if self._match("="):
                return Token(TokenType.GTE, ">=", line)
            return Token(TokenType.GT, ">", line)

        # ── single‑character tokens ──
        simple = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "=": TokenType.EQ,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ";": TokenType.SEMICOLON,
            ":": TokenType.COLON,
            ",": TokenType.COMMA,
            ".": TokenType.DOT,
        }
        if ch in simple:
            return Token(simple[ch], ch, line)

        # ── unrecognised character ──
        msg = f"[line {line}] Unexpected character: {ch!r}"
        self.errors.append(msg)
        self._add_suggestion(msg, line)
        return Token(TokenType.ERROR, msg, line)

    # ── AI suggestion hook ───────────────────────────────────────

    def _add_suggestion(self, error_msg: str, line: int) -> None:
        """Generate AI suggestions for a lexer error."""
        source_lines = self.source.splitlines()
        engine = SuggestionEngine(source_lines=source_lines)
        hints = engine.suggest_for_error(error_msg, line)
        if hints:
            self.suggestions.setdefault(line, []).extend(hints)

    # ── main dispatch ────────────────────────────────────────────

    def next_token(self) -> Token:
        """Return the next token from the source."""
        self.skip_ws_and_c()

        if self.pos >= len(self.source):
            return Token(TokenType.EOF, "", self.line)

        ch = self._current()

        if ch.isalpha() or ch == "_":
            return self.read_identifier()

        if ch.isdigit():
            return self.read_number()

        if ch == "'":
            return self.read_string()

        return self.read_op_or_delim()

    # ── tokenize entire source ───────────────────────────────────

    def tokenize(self) -> list[Token]:
        """Scan the full source and return the complete token list."""
        tokens: list[Token] = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.token_type == TokenType.EOF:
                break
        return tokens

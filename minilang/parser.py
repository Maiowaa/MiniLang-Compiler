"""
MiniLang Recursive‑Descent Parser
──────────────────────────────────
Consumes a list[Token] and builds an AST.
Errors are collected (with line numbers) and parsing continues.
"""

from minilang.tokens import Token, TokenType
from minilang.suggestions import SuggestionEngine
from minilang.ast_nodes import (
    Program, VarDecl, ArrayType, Compound,
    Assign, IfStmt, WhileStmt, ReadStmt, WriteStmt, ProcCall,
    BinOp, UnaryOp, Num, Str, Identifier, ArrayAccess, FuncCall,
)


class Parser:
    """Recursive‑descent parser for MiniLang."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos    = 0
        self.errors: list[str] = []
        self.suggestions: dict[int, list[str]] = {}
        self._engine = SuggestionEngine()

    # ── token helpers ────────────────────────────────────────────

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]             # EOF sentinel

    def _peek(self) -> Token:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return self.tokens[-1]

    def _advance(self) -> Token:
        tok = self._current()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _match(self, *types: TokenType) -> Token | None:
        """If current token matches any of `types`, consume and return it."""
        if self._current().token_type in types:
            return self._advance()
        return None

    def _expect(self, ttype: TokenType) -> Token:
        """Consume if match; otherwise record error and return a dummy."""
        tok = self._match(ttype)
        if tok is not None:
            return tok
        cur = self._current()
        msg = f"[line {cur.line}] Expected {ttype.name}, got {cur.token_type.name} ({cur.value!r})"
        self.errors.append(msg)
        # generate AI suggestions for this parse error
        hints = self._engine.suggest_for_error(msg, cur.line)
        if hints:
            self.suggestions.setdefault(cur.line, []).extend(hints)
        return cur                         # return without advancing

    def _error(self, msg: str) -> None:
        self.errors.append(msg)

    # ── program ──────────────────────────────────────────────────

    def parse(self) -> Program:
        """Entry point — parse full program."""
        return self.parse_program()

    def parse_program(self) -> Program:
        line = self._current().line
        self._expect(TokenType.PROGRAM)
        name_tok = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.SEMICOLON)
        decls = self.parse_declarations()
        body  = self.parse_compound()
        self._expect(TokenType.DOT)
        return Program(line=line, name=name_tok.value, declarations=decls, body=body)

    # ── declarations ─────────────────────────────────────────────

    def parse_declarations(self) -> list:
        decls: list = []
        while self._current().token_type == TokenType.VAR:
            decls.append(self.parse_var_decl())
        return decls

    def parse_var_decl(self) -> VarDecl:
        line = self._current().line
        self._expect(TokenType.VAR)
        names = self.parse_id_list()
        self._expect(TokenType.COLON)
        var_type = self.parse_type()
        self._expect(TokenType.SEMICOLON)
        return VarDecl(line=line, names=names, var_type=var_type)

    def parse_id_list(self) -> list[str]:
        names: list[str] = []
        tok = self._expect(TokenType.IDENTIFIER)
        names.append(tok.value)
        while self._match(TokenType.COMMA):
            tok = self._expect(TokenType.IDENTIFIER)
            names.append(tok.value)
        return names

    def parse_type(self):
        if self._match(TokenType.ARRAY):
            line = self._current().line
            self._expect(TokenType.LBRACKET)
            size_tok = self._expect(TokenType.INTLIT)
            self._expect(TokenType.RBRACKET)
            self._expect(TokenType.OF)
            self._expect(TokenType.INTEGER)
            return ArrayType(line=line, size=size_tok.value, elem_type="integer")
        self._expect(TokenType.INTEGER)
        return "integer"

    # ── compound statement ───────────────────────────────────────

    def parse_compound(self) -> Compound:
        line = self._current().line
        self._expect(TokenType.BEGIN)
        stmts = self.parse_stmt_list()
        self._expect(TokenType.END)
        return Compound(line=line, statements=stmts)

    def parse_stmt_list(self) -> list:
        stmts: list = []
        stmt = self.parse_statement()
        if stmt is not None:
            stmts.append(stmt)
        while self._match(TokenType.SEMICOLON):
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return stmts

    # ── statement dispatch ───────────────────────────────────────

    def parse_statement(self):
        cur = self._current()

        if cur.token_type == TokenType.IDENTIFIER:
            # look ahead: assignment (:= or [) vs procedure call
            nxt = self._peek()
            if nxt.token_type in (TokenType.ASSIGN, TokenType.LBRACKET):
                return self.parse_assignment()
            if nxt.token_type == TokenType.LPAREN:
                return self.parse_proc_call()
            # default: assume assignment (will error at :=)
            return self.parse_assignment()

        if cur.token_type == TokenType.IF:
            return self.parse_if()

        if cur.token_type == TokenType.WHILE:
            return self.parse_while()

        if cur.token_type == TokenType.READ:
            return self.parse_read()

        if cur.token_type == TokenType.WRITE:
            return self.parse_write()

        if cur.token_type == TokenType.BEGIN:
            return self.parse_compound()

        # ε  (empty statement) — nothing to consume
        return None

    # ── procedure call (statement) ───────────────────────────────

    def parse_proc_call(self):
        line   = self._current().line
        id_tok = self._advance()              # consume IDENTIFIER
        self._expect(TokenType.LPAREN)
        args   = self.parse_arg_list()
        self._expect(TokenType.RPAREN)
        return ProcCall(line=line, name=id_tok.value, args=args)

    # ── assignment ───────────────────────────────────────────────

    def parse_assignment(self):
        line    = self._current().line
        id_tok  = self._advance()                     # consume IDENTIFIER
        name    = id_tok.value

        if self._match(TokenType.LBRACKET):
            # array element:  id '[' expr ']' ':=' expr
            index = self.parse_expr()
            self._expect(TokenType.RBRACKET)
            target = ArrayAccess(line=line, name=name, index=index)
        else:
            target = Identifier(line=line, name=name)

        self._expect(TokenType.ASSIGN)
        value = self.parse_expr()
        return Assign(line=line, target=target, value=value)

    # ── if ───────────────────────────────────────────────────────

    def parse_if(self) -> IfStmt:
        line = self._current().line
        self._expect(TokenType.IF)
        cond = self.parse_expr()
        self._expect(TokenType.THEN)
        then_b = self.parse_statement()
        else_b = None
        if self._match(TokenType.ELSE):
            else_b = self.parse_statement()
        return IfStmt(line=line, condition=cond, then_branch=then_b, else_branch=else_b)

    # ── while ────────────────────────────────────────────────────

    def parse_while(self) -> WhileStmt:
        line = self._current().line
        self._expect(TokenType.WHILE)
        cond = self.parse_expr()
        self._expect(TokenType.DO)
        body = self.parse_statement()
        return WhileStmt(line=line, condition=cond, body=body)

    # ── read / write ─────────────────────────────────────────────

    def parse_read(self) -> ReadStmt:
        line = self._current().line
        self._expect(TokenType.READ)
        self._expect(TokenType.LPAREN)
        variables: list = []
        id_tok = self._expect(TokenType.IDENTIFIER)
        variables.append(Identifier(line=id_tok.line, name=id_tok.value))
        while self._match(TokenType.COMMA):
            id_tok = self._expect(TokenType.IDENTIFIER)
            variables.append(Identifier(line=id_tok.line, name=id_tok.value))
        self._expect(TokenType.RPAREN)
        return ReadStmt(line=line, variables=variables)

    def parse_write(self) -> WriteStmt:
        line = self._current().line
        self._expect(TokenType.WRITE)
        self._expect(TokenType.LPAREN)
        items: list = []
        items.append(self.parse_expr())
        while self._match(TokenType.COMMA):
            items.append(self.parse_expr())
        self._expect(TokenType.RPAREN)
        return WriteStmt(line=line, items=items)

    # ── expressions ──────────────────────────────────────────────

    _RELOPS = {
        TokenType.LT, TokenType.GT, TokenType.LTE,
        TokenType.GTE, TokenType.EQ, TokenType.NEQ,
    }

    def parse_expr(self):
        left = self.parse_simple_expr()
        if self._current().token_type in self._RELOPS:
            op_tok = self._advance()
            right = self.parse_simple_expr()
            return BinOp(line=op_tok.line, op=op_tok.value, left=left, right=right)
        return left

    _ADDOPS = {TokenType.PLUS, TokenType.MINUS, TokenType.OR}

    def parse_simple_expr(self):
        node = self.parse_term()
        while self._current().token_type in self._ADDOPS:
            op_tok = self._advance()
            right = self.parse_term()
            node = BinOp(line=op_tok.line, op=op_tok.value, left=node, right=right)
        return node

    _MULOPS = {TokenType.STAR, TokenType.SLASH, TokenType.AND}

    def parse_term(self):
        node = self.parse_factor()
        while self._current().token_type in self._MULOPS:
            op_tok = self._advance()
            right = self.parse_factor()
            node = BinOp(line=op_tok.line, op=op_tok.value, left=node, right=right)
        return node

    def parse_factor(self):
        cur = self._current()

        # integer literal
        if cur.token_type == TokenType.INTLIT:
            self._advance()
            return Num(line=cur.line, value=cur.value)

        # string literal
        if cur.token_type == TokenType.STRLIT:
            self._advance()
            return Str(line=cur.line, value=cur.value)

        # identifier, array access, or function call
        if cur.token_type == TokenType.IDENTIFIER:
            self._advance()
            # array access:  id '[' expr ']'
            if self._current().token_type == TokenType.LBRACKET:
                self._advance()
                index = self.parse_expr()
                self._expect(TokenType.RBRACKET)
                return ArrayAccess(line=cur.line, name=cur.value, index=index)
            # function call:  id '(' args ')'
            if self._current().token_type == TokenType.LPAREN:
                self._advance()
                args = self.parse_arg_list()
                self._expect(TokenType.RPAREN)
                return FuncCall(line=cur.line, name=cur.value, args=args)
            return Identifier(line=cur.line, name=cur.value)

        # parenthesised expression
        if cur.token_type == TokenType.LPAREN:
            self._advance()
            node = self.parse_expr()
            self._expect(TokenType.RPAREN)
            return node

        # unary 'not'
        if cur.token_type == TokenType.NOT:
            self._advance()
            operand = self.parse_factor()
            return UnaryOp(line=cur.line, op="not", operand=operand)

        # error — unexpected token in factor
        self._error(f"[line {cur.line}] Unexpected token in expression: "
                    f"{cur.token_type.name} ({cur.value!r})")
        # generate AI suggestions
        hints = self._engine.suggest_for_error(
            f"Unexpected token in expression: {cur.token_type.name} ({cur.value!r})",
            cur.line)
        if hints:
            self.suggestions.setdefault(cur.line, []).extend(hints)
        self._advance()                    # skip bad token
        return Num(line=cur.line, value=0)  # dummy node

    def parse_arg_list(self) -> list:
        args: list = []
        if self._current().token_type == TokenType.RPAREN:
            return args                    # empty arg list
        args.append(self.parse_expr())
        while self._match(TokenType.COMMA):
            args.append(self.parse_expr())
        return args

import re

from compiler.lexer import tokenize

class Parser:

    VALID_STRATEGIES = {

        "automatic",

        "token insertion",

        "phrase-level recovery",

        "panic mode",

    }

    def __init__(self, tokens, source, strategy="automatic"):

        self.tokens = tokens

        self.source = source

        self.pos = 0

        requested = strategy.lower().strip()

        self.strategy = requested if requested in self.VALID_STRATEGIES else "automatic"

        self.errors = []

        self.trace = []

        self.insertions = []

        self.deletions = []

        self.statement_start_offset = 0

        self.statement_start_line = 1

        self.block_depth = 0

    # -------------------- Token handling --------------------

    def current(self):

        return self.tokens[min(self.pos, len(self.tokens) - 1)]

    def advance(self):

        token = self.current()

        if token["type"] != "EOF":

            self.pos += 1

        return token

    def check(self, *values):

        return self.current()["value"] in values

    def match(self, *values):

        if self.check(*values):

            return self.advance()

        return None

    def source_offset(self, line, column):

        lines = self.source.splitlines(keepends=True)

        offset = sum(len(item) for item in lines[:max(0, line - 1)])

        return min(offset + column - 1, len(self.source))

    def token_offset(self, token=None):

        token = token or self.current()

        return self.source_offset(token["line"], token["column"])

    # -------------------- Source edits --------------------

    def insert_text(self, offset, text):

        self.insertions.append({"offset": max(0, min(offset, len(self.source)),), "text": text})

    def delete_range(self, start, end):

        start = max(0, min(start, len(self.source)))

        end = max(start, min(end, len(self.source)))

        if end > start:

            self.deletions.append({"start": start, "end": end})

    def corrected_source(self):

        insertions_by_offset = {}

        for item in self.insertions:

            offset = item["offset"]

            insertions_by_offset.setdefault(offset, [])

            insertions_by_offset[offset].append(item["text"])

        edits = []

        for item in self.deletions:

            edits.append((item["start"], item["end"], ""))

        for offset, pieces in insertions_by_offset.items():

            edits.append((offset, offset, "".join(pieces)))


        edits.sort(key=lambda item: (item[0], item[1]), reverse=True)

        corrected = self.source

        for start, end, text in edits:

            corrected = corrected[:start] + text + corrected[end:]


        if self.strategy == "panic mode":

            corrected = re.sub(
                r"(?m)^[ \t]*;[ \t]*(?=\r?$)",
                "",
                corrected,
            )

        return corrected

    def record(self, message, expected, action, recovered=True):

        token = self.current()

        self.errors.append({

            "line": token["line"],

            "column": token["column"],

            "unexpected": token["value"],

            "message": message,

            "expected": expected,

            "strategy": self.strategy,

            "action": action,

            "recovered": recovered,

        })

        self.trace.append({

            "line": token["line"],

            "token": token["value"],

            "action": action,

        })

    def trace_action(self, action):

        token = self.current()

        self.trace.append({

            "line": token["line"],

            "token": token["value"],

            "action": action,

        })

    # -------------------- Recovery strategies --------------------

    def insert_token(self, value):

        token = self.current()

        offset = self.token_offset(token)

        if value == ";":

            line_start = self.source.rfind("\n", 0, offset) + 1

            prefix = self.source[line_start:offset]

            if prefix.strip() == "" and line_start > 0:

                previous = line_start - 1

                while previous >= 0 and self.source[previous].isspace():

                    previous -= 1

                if previous >= 0:

                    offset = previous + 1

        self.insert_text(offset, value)

        self.record(

            f"Missing '{value}'",

            [value],

            f"Token insertion: inserted '{value}'",

        )

        return {"type": "RECOVERED", "value": value,

                "line": token["line"], "column": token["column"]}

    def recover_missing_operand(self):

        token = self.current()
        offset = self.token_offset(token)
        # If the next token begins a new statement, insert the operand after
        # the preceding operator instead of at the statement token's offset.
        # This avoids competing insertions at the same source position.
        add_leading_space = False
        if token.get("value") in {"int", "float", "void", "return", "if", "while", "print", "{"} and self.pos > 0:
            previous = self.tokens[self.pos - 1]
            if previous.get("type") == "OPERATOR":
                offset = self.token_offset(previous) + len(previous.get("value", ""))
                add_leading_space = True

        if self.strategy == "panic mode":
            # Panic mode first synchronizes at statement boundaries, but when
            # the missing operand is immediately before a safe delimiter we
            # can make a minimal placeholder repair without discarding the
            # surrounding statement. This keeps the recovered output parseable.
            self.insert_text(offset, "0")
            self.record(
                "Missing expression operand",
                ["identifier", "number", "("],
                "Panic mode: inserted fallback operand '0' at a safe delimiter",
            )
            return

        # Prefer an identifier declared before this error; use 0 only when no
        # safe in-scope-looking candidate exists. This is heuristic, not full scope analysis.
        prefix = self.source[:offset]
        declared = []
        # Read every name in simple comma-separated int/float declarations,
        # rather than capturing only the first identifier in each declaration.
        declaration_pattern = re.compile(
            r"\b(?:int|float)\s+([^;{}]+)"
        )
        for match in declaration_pattern.finditer(prefix):
            declaration = match.group(1)
            # Function parameter lists are not variable declaration lists here;
            # only collect comma-separated simple identifier names.
            for part in declaration.split(","):
                name_match = re.match(r"\s*([A-Za-z_]\w*)\s*$", part)
                if name_match:
                    name = name_match.group(1)
                    if name not in declared:
                        declared.append(name)
        target = None
        for i in range(self.pos - 1, max(-1, self.pos - 8), -1):
            if self.tokens[i]["value"] == "=":
                if i > 0:
                    target = self.tokens[i - 1].get("value")
                break
            if self.tokens[i]["value"] in (";", "{", "}"):
                break
        candidates = [name for name in declared if name != target]
        replacement = candidates[-1] if candidates else "0"
        self.insert_text(offset, (" " if add_leading_space else "") + replacement)

        strategy_label = {

            "token insertion": "Token insertion",

            "phrase-level recovery": "Phrase-level recovery",

            "panic mode": "Panic-mode recovery",

            "automatic": "Automatic recovery",

        }.get(self.strategy, "Automatic recovery")

        self.record(

            "Missing expression operand",

            ["identifier", "number", "("],

            f"{strategy_label}: inserted suggested operand '{replacement}'",

        )

    def expect(self, value):

        if self.check(value):

            return self.advance()

        if (

            self.strategy == "panic mode"

            and value == ")"

            and (

                self.check(";", "{", "}", "else", "$", "int", "float",

                           "if", "while", "print")

                or self.current()["type"] == "EOF"

            )

        ):

            token = self.current()

            offset = self.token_offset(token)

            self.insert_text(offset, ")")

            self.record(

                "Missing ')'",

                [")"],

                "Panic mode: inserted missing closing parenthesis and preserved statement",

            )

            return {

                "type": "RECOVERED",

                "value": ")",

                "line": token["line"],

                "column": token["column"],

            }

        if (

            self.strategy == "panic mode"

            and value == "}"

            and self.current()["type"] == "EOF"

        ):

            token = self.current()

            offset = len(self.source.rstrip())

            self.insert_text(offset, "}" if offset == 0 or self.source[offset - 1] != "\n" else "}")

            self.record(

                "Missing '}'",

                ["}"],

                "Panic mode: inserted missing closing brace at end of input",

            )

            return {

                "type": "RECOVERED",

                "value": "}",

                "line": token["line"],

                "column": token["column"],

            }

        if self.strategy in ("automatic", "token insertion", "phrase-level recovery"):

            if value in (";", ")", "}"):

                return self.insert_token(value)

        raise SyntaxError(f"Expected '{value}', got '{self.current()['value']}'")

    def expect_identifier(self):

        if self.current()["type"] == "IDENTIFIER":

            return self.advance()

        raise SyntaxError(f"Expected identifier, got '{self.current()['value']}'")

    def recover_unexpected_operator(self):

        """Delete a misplaced operator when an operand is expected."""

        token = self.current()

        start = self.token_offset(token)

        end = start + len(token["value"])

        value = token["value"]

        self.delete_range(start, end)

        self.record(

            f"Unexpected operator '{value}'",

            ["identifier", "number", "("],

            f"Phrase-level recovery: deleted unexpected operator '{value}'",

        )

        self.advance()


        following = self.current()


        is_operand = (

            following["type"] in ("NUMBER", "IDENTIFIER")

            or following["value"] == "("

            or following["value"].replace(".", "", 1).isdigit()

            or (

                following["type"] != "EOF"

                and following["value"] not in (

                    ";", ")", "}", "{", "=", "+", "-", "*", "/", ">", "<",

                    ">=", "<=", "==", "!=", ","

                )

            )

        )

        if following["value"] == "(":

            self.factor()

        elif is_operand:


            self.advance()

        elif following["value"] in (";", ")", "}", "$") or following["type"] == "EOF":


            offset = self.token_offset(following)

            self.insert_text(offset, "0")

            self.record(

                "Missing expression operand after unexpected operator",

                ["identifier", "number", "("],

                "Phrase-level recovery: inserted placeholder '0' after deleting unexpected operator",

            )

    def synchronize(self):

        """Panic-mode recovery that discards malformed statements but preserves later valid ones."""

        start_pos = self.pos

        start_offset = self.statement_start_offset

        start_line = self.statement_start_line

        statement_starters = {"int", "float", "void", "return", "if", "while", "for", "print", "{"}

        current = self.current()

        last_message = self.errors[-1]["message"] if self.errors else ""

        expected_semicolon = "Expected ';'" in last_message


        at_new_statement = (

            current["type"] != "EOF"

            and current["line"] > start_line

            and (current["type"] == "IDENTIFIER" or current["value"] in statement_starters)

        )

        at_eof = current["type"] == "EOF" or self.check("$")
        at_closing_brace = self.check("}") and self.block_depth > 0

        if (
            self.strategy == "panic mode"
            and expected_semicolon
            and (at_new_statement or at_eof or at_closing_brace)
        ):
            if at_eof:
                insert_at = len(self.source.rstrip())
            elif at_closing_brace:
                brace_offset = self.token_offset(current)
                line_start = self.source.rfind("\n", 0, brace_offset) + 1
                insert_at = line_start - 1 if line_start > 0 else brace_offset
                
                while insert_at > 0 and self.source[insert_at - 1] in " \t\r\n":
                    insert_at -= 1
            else:
                insert_at = self.source_offset(current["line"], 1)
                while insert_at > 0 and self.source[insert_at - 1] in " \t\r\n":
                    insert_at -= 1
            if insert_at > 0 and self.source[insert_at - 1] != ";":
                self.insert_text(insert_at, ";")
            self.trace_action("Panic mode: inserted missing semicolon and preserved statement")
            return

       

        if at_new_statement:

            end_offset = self.source_offset(current["line"], 1)

            if self.strategy == "panic mode" and end_offset > start_offset:

                self.delete_range(start_offset, end_offset)

            self.trace_action("Panic mode: synchronized before the next statement")

            return

        

        while not self.check("$", "}", "else", ";"):

            token = self.current()

            if (

                token["line"] > start_line

                and (token["type"] == "IDENTIFIER" or token["value"] in statement_starters)

            ):

                end_offset = self.source_offset(token["line"], 1)

                if self.strategy == "panic mode" and end_offset > start_offset:

                    self.delete_range(start_offset, end_offset)

                self.trace_action("Panic mode: synchronized before the next statement")

                return

            self.advance()

        if self.check(";"):

            semicolon = self.current()

            end_offset = self.token_offset(semicolon) + len(semicolon["value"])

            self.advance()

            action = "Panic mode: discarded malformed statement through ';'"

        else:

            end_offset = self.token_offset()

            action = "Panic mode: synchronized at a statement boundary"

        if self.strategy == "panic mode" and end_offset > start_offset:

            self.delete_range(start_offset, end_offset)

        if self.pos == start_pos and not self.check("$", "}", "else"):

            self.advance()

        self.trace_action(action)

    def handle_syntax_error(self, exc):

        self.record(

            str(exc),

            ["valid statement or expected token"],

            "Panic-mode synchronization",

        )

        self.synchronize()

    # -------------------- Grammar --------------------

    def statement(self):

        if self.check("int", "float", "void"):
            self.declaration()

        elif self.match("return"):
            if not self.check(";", "}", "$"):
                self.expression()
            self.expect(";")

        elif self.match(";"):
            self.trace_action("Accepted empty statement")

        elif self.match("if"):

            self.if_statement()

        elif self.match("while"):

            self.while_statement()

        elif self.match("for"):

            self.for_statement()

        elif self.match("print"):

            self.print_statement()

        elif self.current()["type"] == "IDENTIFIER":
            # Assignment or function-call/expression statement.
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1]["value"] == "=":
                self.assignment()
            else:
                self.expression()
                # Support simple postfix increment/decrement statements.
                if self.check("++", "--"):
                    self.advance()
                self.expect(";")

        elif self.match("{"):

            self.block()

        else:

            raise SyntaxError(f"Unexpected token '{self.current()['value']}'")

    def declaration(self):
        type_token = self.advance()
        # Function definitions: int main() { ... } or void helper() { ... }
        if self.current()["type"] == "IDENTIFIER":
            name_token = self.advance()
        else:
            current = self.current()
            if current["value"] in (";", ")", "}", "$") or current["type"] == "EOF":
                offset = self.token_offset(current)
                self.insert_text(offset, " recovered_var")
                self.record("Missing identifier in declaration", ["identifier"],
                            "Declaration recovery: inserted placeholder identifier 'recovered_var'")
                name_token = {"type": "IDENTIFIER", "value": "recovered_var", "line": current["line"], "column": current["column"]}
            else:
                self.expect_identifier()
                return

        if self.match("("):
            # Lightweight parameter grammar: type name pairs, optionally comma-separated.
            if not self.check(")"):
                # C-style `void` alone denotes a function with no parameters.
                if (self.check("void") and self.pos + 1 < len(self.tokens)
                        and self.tokens[self.pos + 1]["value"] == ")"):
                    self.advance()
                else:
                    while True:
                        if self.check("int", "float", "void"):
                            self.advance()
                        self.expect_identifier()
                        if not self.match(","):
                            break
            self.expect(")")
            if self.match("{"):
                self.block()
            else:
                self.expect(";")
            return

        while self.match(","):
            self.expect_identifier()
            if self.match("="):
                self.expression()
        if self.match("="):
            self.expression()
        self.expect(";")

    def assignment(self):

        self.expect_identifier()

        self.expect("=")

        self.expression()

        self.expect(";")

    def print_statement(self):

        self.expect("(")

        self.expression()

        self.expect(")")

        self.expect(";")

    def if_statement(self):

        self.expect("(")

        self.condition()

        self.expect(")")

        self.block_or_statement()

        if self.match("else"):

            self.block_or_statement()

    def while_statement(self):

        self.expect("(")

        self.condition()

        self.expect(")")

        self.block_or_statement()

    def for_statement(self):
        self.expect("(")
        if not self.check(";"):
            if self.check("int", "float"):
                self.declaration()
            elif self.current()["type"] == "IDENTIFIER" and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1]["value"] == "=":
                self.assignment()
            else:
                self.expression()
                self.expect(";")
        else:
            self.expect(";")
        if not self.check(";"):
            self.condition()
        self.expect(";")
        if not self.check(")"):
            if self.current()["type"] == "IDENTIFIER":
                self.advance()
                if self.check("++", "--"):
                    self.advance()
                elif self.match("="):
                    self.expression()
                else:
                    raise SyntaxError("Expected increment/decrement or assignment in for-loop")
            else:
                self.expression()
        self.expect(")")
        self.block_or_statement()

    def block_or_statement(self):

        if self.match("{"):

            self.block()

        else:

            self.statement()

    def block(self):

        self.block_depth += 1

        try:

            while not self.check("}", "$"):

                old_pos = self.pos

                self.statement_start_offset = self.token_offset()

                self.statement_start_line = self.current()["line"]

                try:

                    self.statement()

                except SyntaxError as exc:

                    self.handle_syntax_error(exc)

                if self.pos == old_pos and not self.check("$", "}"):

                    self.advance()

            self.expect("}")

        finally:

            self.block_depth = max(0, self.block_depth - 1)

    # -------------------- Expressions --------------------

    def condition(self):

        self.expression()

        if self.check(">", "<", ">=", "<=", "==", "!="):

            self.advance()

            self.expression()

    def expression(self):

        self.term()

        while self.check("+", "-"):

            self.advance()

            self.term()

    def term(self):

        self.factor()

        while self.check("*", "/", "%"):

            self.advance()

            self.factor()

    def factor(self):
        """Parse a number, variable, parenthesized expression, or function call."""
        statement_starters = {"int", "float", "void", "return", "if", "while", "for", "print", "{"}
        if self.current()["value"] in statement_starters:
            if self.strategy in ("automatic", "token insertion", "phrase-level recovery", "panic mode"):
                self.recover_missing_operand()
                return

        if self.current()["type"] in ("NUMBER", "STRING"):
            self.advance()
            return

        if self.current()["type"] == "IDENTIFIER":
            self.advance()
            # Identifier followed by '(' is a function call: f(), f(x), f(x, y).
            if self.match("("):
                if not self.check(")"):
                    self.expression()
                    while self.match(","):
                        self.expression()
                self.expect(")")
            return

        if self.match("("):
            self.expression()
            self.expect(")")
            return

        if self.strategy in ("automatic", "phrase-level recovery", "panic mode"):
            if self.check(";", ")", "}", "$") or self.current()["type"] == "EOF":
                self.recover_missing_operand()
                return
            if self.strategy != "panic mode" and self.current()["type"] == "OPERATOR":
                self.recover_unexpected_operator()
                return

        if self.strategy == "token insertion":
            if self.check(";", ")", "}", "$") or self.current()["type"] == "EOF":
                self.recover_missing_operand()
                return
            if self.current()["type"] == "OPERATOR":
                self.recover_missing_operand()
                return

        raise SyntaxError(
            "Expected an identifier, number, string, or '('; "
            f"got '{self.current()['value']}'"
        )

    # -------------------- Main parse loop --------------------

    def parse(self):

        while not self.check("$"):



            if self.check("}") and self.block_depth == 0:

                token = self.current()

                start = self.token_offset(token)

                self.delete_range(start, start + len(token["value"]))

                self.record(

                    "Unexpected closing brace at top level",

                    ["statement", "end of input"],

                    f"{self.strategy.capitalize()}: removed unmatched closing brace "

                    "and preserved following input",

                )

                self.advance()

                continue

            old_pos = self.pos

            self.statement_start_offset = self.token_offset()

            self.statement_start_line = self.current()["line"]

            try:

                self.statement()

            except SyntaxError as exc:

                self.handle_syntax_error(exc)

            if self.pos == old_pos and not self.check("$"):

                self.advance()

        return {

            "errors": self.errors,

            "trace": self.trace,

            "success": len(self.errors) == 0,

            "recovery_success": len(self.errors) == 0,

            "recovered_source": self.corrected_source(),

        }

def validate_source(source):

    tokens, lexical_errors = tokenize(source)

    if lexical_errors:

        return False

    validator = Parser(tokens, source, "panic mode")

    result = validator.parse()

    return len(result["errors"]) == 0

def analyze_source(source, strategy="automatic"):

    tokens, lexical_errors = tokenize(source)

    parser = Parser(tokens, source, strategy)

    result = parser.parse()

    result["tokens"] = tokens

    result["lexical_errors"] = lexical_errors

    result["success"] = (

        len(result["errors"]) == 0 and len(lexical_errors) == 0

    )

    recovered_source = result["recovered_source"]

    if result["success"]:

        result["recovery_success"] = True

    else:

        try:

            result["recovery_success"] = validate_source(recovered_source)

        except Exception:

            result["recovery_success"] = False

    return result

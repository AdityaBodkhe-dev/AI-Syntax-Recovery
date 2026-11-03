
import re

KEYWORDS = {
    "int", "float", "void", "return", "if", "else", "while", "for", "print"
}

TOKEN_SPEC = [
    ("DIRECTIVE",  r"#[^\n]*"),
    ("COMMENT",    r"//[^\n]*"),
    ("BLOCK_COMMENT", r"/\*[\s\S]*?\*/"),
    ("WHITESPACE", r"[ \t\r\n]+"),
    ("STRING",     r'"(?:\\.|[^"\\])*"'),
    ("NUMBER",     r"\d+(\.\d+)?"),
    ("IDENTIFIER", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OPERATOR",   r"\+\+|--|==|!=|<=|>=|[=+\-*/<>%]"),
    ("PUNCTUATION", r"[;(),{}]"),
]

TOKEN_REGEX = re.compile(
    "|".join(
        f"(?P<{name}>{pattern})"
        for name, pattern in TOKEN_SPEC
    )
)


def tokenize(source):
    """Convert source code into tokens with line and column positions."""

    tokens = []
    errors = []

    line = 1
    column = 1
    position = 0

    while position < len(source):
        match = TOKEN_REGEX.match(source, position)

        if not match:
            char = source[position]

            errors.append({
                "message": f"Unexpected character: {char!r}",
                "line": line,
                "column": column,
            })

            position += 1

            if char == "\n":
                line += 1
                column = 1
            else:
                column += 1

            continue

        kind = match.lastgroup
        value = match.group()
        start_line = line
        start_column = column

        if kind not in {
            "WHITESPACE", "COMMENT", "BLOCK_COMMENT", "DIRECTIVE"
        }:
            if kind == "IDENTIFIER" and value in KEYWORDS:
                kind = "KEYWORD"

            if kind == "PUNCTUATION":
                kind = {
                    ";": "SEMICOLON",
                    "(": "LPAREN",
                    ")": "RPAREN",
                    "{": "LBRACE",
                    "}": "RBRACE",
                    ",": "COMMA",
                }[value]

            tokens.append({
                "type": kind,
                "value": value,
                "line": start_line,
                "column": start_column,
            })

        line_breaks = value.count("\n")

        if line_breaks:
            line += line_breaks
            column = len(value.rsplit("\n", 1)[-1]) + 1
        else:
            column += len(value)

        position = match.end()

    tokens.append({
        "type": "EOF",
        "value": "$",
        "line": line,
        "column": column,
    })

    return tokens, errors

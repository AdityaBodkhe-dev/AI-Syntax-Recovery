
from compiler.lexer import tokenize

source = """int a;
a = 10 + 5;
if (a > 10) {
    print(a);
}
"""

tokens, errors = tokenize(source)

print("\n--- TOKEN STREAM ---")

for token in tokens:
    print(
        f"{token['type']:12} "
        f"{token['value']:10} "
        f"Line: {token['line']}, "
        f"Column: {token['column']}"
    )

print("\n--- LEXICAL ERRORS ---")

if errors:
    for error in errors:
        print(error)
else:
    print("No lexical errors found.")

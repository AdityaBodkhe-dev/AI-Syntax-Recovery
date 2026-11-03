
print("Parser test started!")

from compiler.parser import analyze_source


# Test program: the semicolon after "int a" is missing.
source = """int a
a = 10 + ;
if (a > 10 {
    print(a);
}
"""

result = analyze_source(source, strategy="automatic")

print("\n--- PARSER RESULT ---")
print("Syntax valid:", result["success"])
print("Recovery successful:", result["recovery_success"])

print("\n--- TOKENS ---")
for token in result["tokens"]:
    print(token)

print("\n--- LEXICAL ERRORS ---")
if result["lexical_errors"]:
    for error in result["lexical_errors"]:
        print(error)
else:
    print("No lexical errors found.")

print("\n--- SYNTAX ERRORS ---")
if result["errors"]:
    for error in result["errors"]:
        print(error)
else:
    print("No syntax errors found.")

print("\n--- PARSER TRACE ---")
if result["trace"]:
    for step in result["trace"]:
        print(step)
else:
    print("No recovery actions were needed.")

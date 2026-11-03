
from compiler.parser import analyze_source


TEST_CASES = [
    {
        "name": "Missing declaration semicolon",
        "source": "int a\na = 5;\n",
    },
    {
        "name": "Missing assignment semicolon",
        "source": "int a;\na = 5\nprint(a);\n",
    },
    {
        "name": "Missing operand after plus",
        "source": "int a;\na = 10 + ;\n",
    },
    {
        "name": "Missing operand after minus",
        "source": "int a;\na = 10 - ;\n",
    },
    {
        "name": "Missing if closing parenthesis",
        "source": "int a;\nif (a > 10 {\nprint(a);\n}\n",
    },
    {
        "name": "Missing print closing parenthesis",
        "source": "print(10;\n",
    },
    {
        "name": "Missing print semicolon",
        "source": "print(10)\n",
    },
    {
        "name": "Missing float declaration semicolon",
        "source": "float price\n",
    },
    {
        "name": "Multiple syntax errors",
        "source": (
            "int a\n"
            "a = 10 + ;\n"
            "if (a > 10 {\n"
            "print(a);\n"
            "}\n"
        ),
    },
    {
        "name": "Missing operand inside print",
        "source": "print( );\n",
    },
]


def main():
    print("=" * 65)
    print("RECOVERED SOURCE VALIDATION")
    print("=" * 65)

    passed = 0
    failed = 0

    for test in TEST_CASES:
        print(f"\nTest: {test['name']}")

        # First parse the original invalid source.
        original = analyze_source(
            test["source"],
            strategy="automatic",
        )

        recovered_source = original["recovered_source"]

        # Then parse the proposed recovered source again.
        validation = analyze_source(
            recovered_source,
            strategy="automatic",
        )

        has_lexical_errors = bool(validation["lexical_errors"])
        has_syntax_errors = bool(validation["errors"])

        valid = not has_lexical_errors and not has_syntax_errors

        print(f"Original errors: {len(original['errors'])}")
        print(f"Recovered source:\n{recovered_source}")
        print(f"Remaining syntax errors: {len(validation['errors'])}")
        print(f"Remaining lexical errors: {len(validation['lexical_errors'])}")

        if valid:
            print("Result: PASS — recovered source parses without errors")
            passed += 1
        else:
            print("Result: FAIL — recovered source still has errors")
            failed += 1

            for error in validation["errors"]:
                print(
                    f"  Syntax error at line {error['line']}, "
                    f"column {error['column']}: {error['message']}"
                )

            for error in validation["lexical_errors"]:
                print(
                    f"  Lexical error at line {error['line']}, "
                    f"column {error['column']}: {error['message']}"
                )

    print("\n" + "=" * 65)
    print("VALIDATION SUMMARY")
    print("=" * 65)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")

    if failed == 0:
        print("All recovered programs passed validation.")
    else:
        print(
            "Some recovered programs still contain errors. "
            "Use the failures to improve the recovery engine."
        )


if __name__ == "__main__":
    main()

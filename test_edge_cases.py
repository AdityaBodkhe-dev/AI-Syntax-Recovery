
from compiler.lexer import tokenize
from compiler.parser import Parser, analyze_source, validate_source


def run_test(name, source, strategy="automatic",
             expected_errors=None, expected_valid=None,
             expected_later_statement=None):
    print("\n" + "=" * 72)
    print(f"TEST: {name}")
    print(f"STRATEGY: {strategy}")
    print("=" * 72)

    result = analyze_source(source, strategy)
    recovered = result.get("recovered_source", source)
    errors = result.get("errors", [])
    lexical_errors = result.get("lexical_errors", [])

    print("\nOriginal source:")
    print(source)

    print("Recovered source:")
    print(recovered)

    print("Syntax errors:", len(errors))
    for error in errors:
        print(
            f"  Line {error['line']}, token "
            f"{error['unexpected']!r}: {error['message']}"
        )

    print("Lexical errors:", len(lexical_errors))
    print("Recovery trace:")
    for item in result.get("trace", []):
        print(" ", item)

    actual_valid = validate_source(recovered)
    print("Recovered source valid:", actual_valid)

    checks = []

    if expected_errors is not None:
        checks.append(len(errors) == expected_errors)

    if expected_valid is not None:
        checks.append(actual_valid == expected_valid)

    if expected_later_statement is not None:
        tokens, token_errors = tokenize(source)
        parser = Parser(tokens, source, strategy)
        completed = []
        original_statement = Parser.statement

        def tracked_statement(current_parser):
            token = current_parser.current()
            line = token["line"]
            value = token["value"]

            original_statement(current_parser)

            completed.append({
                "line": line,
                "token": value,
            })

        Parser.statement = tracked_statement
        try:
            parser.parse()
        finally:
            Parser.statement = original_statement

        target_line, target_token = expected_later_statement
        found = any(
            item["line"] == target_line
            and item["token"] == target_token
            for item in completed
        )

        print("\nCompleted statements:")
        for item in completed:
            print(f"  Line {item['line']}: {item['token']}")

        print(
            f"Expected statement at line {target_line} "
            f"({target_token}):",
            found,
        )

        checks.append(found and not token_errors)

    passed = (
        bool(checks)
        and all(checks)
        and not lexical_errors
    )

    print("\nTEST RESULT:", "PASS" if passed else "FAIL")
    return passed


def main():
    results = []

    # 1. Missing semicolon immediately before a closing brace.
    results.append(
        run_test(
            "Missing semicolon before closing brace",
            "if (a > 0) {\n    int b\n}\n",
            expected_errors=1,
            expected_valid=True,
        )
    )

    # 2. A malformed statement inside a block should not prevent
    # a later valid statement in that block from being parsed.
    results.append(
        run_test(
            "Continue after malformed statement inside block",
            "if (a > 0) {\n"
            "    a = 5 + ;\n"
            "    print(7);\n"
            "}\n",
            strategy="panic mode",
            expected_errors=1,
            expected_valid=True,
            expected_later_statement=(3, "print"),
        )
    )

    # 3. An unmatched closing brace should be reported.
    results.append(
        run_test(
            "Unexpected closing brace",
            "int a;\n}\nprint(a);\n",
            expected_errors=1,
            expected_valid=True,
        )
    )

    # 4. A missing closing brace should be reported or repaired.
    results.append(
        run_test(
            "Missing closing brace at end of input",
            "if (a > 0) {\n    print(a);\n",
            expected_errors=1,
            expected_valid=True,
        )
    )

    # 5. Multiple malformed statements inside a nested block.
    results.append(
        run_test(
            "Multiple errors inside nested block",
            "if (a > 0) {\n"
            "    int b\n"
            "    b = 10 + ;\n"
            "    print(b);\n"
            "}\n",
            strategy="automatic",
            expected_errors=2,
            expected_valid=True,
            expected_later_statement=(4, "print"),
        )
    )

    print("\n" + "=" * 72)
    print("EDGE-CASE TEST SUMMARY")
    print("=" * 72)
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print(f"Total:  {len(results)}")

    if not all(results):
        print(
            "\nSome expectations were not met. "
            "Inspect each failing test before changing parser.py."
        )


if __name__ == "__main__":
    main()

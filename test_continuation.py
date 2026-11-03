
from compiler.parser import Parser
from compiler.lexer import tokenize


def run_test(name, source, expected_statements, expected_errors):
    print("\n" + "=" * 70)
    print(f"TEST: {name}")
    print("=" * 70)

    tokens, lexical_errors = tokenize(source)
    parser = Parser(tokens, source, "panic mode")

    completed_statements = []
    original_statement = Parser.statement

    def tracked_statement(current_parser):
        token = current_parser.current()
        start_line = token["line"]
        start_token = token["value"]

        # Record only statements that return without a syntax error.
        original_statement(current_parser)

        completed_statements.append({
            "line": start_line,
            "token": start_token,
        })

    Parser.statement = tracked_statement

    try:
        result = parser.parse()
    finally:
        Parser.statement = original_statement

    errors = result["errors"]
    trace = result["trace"]

    print("\nOriginal source:")
    print(source)

    print("Recovered source:")
    print(result["recovered_source"])

    print("\nSuccessfully completed statements:")
    for statement in completed_statements:
        print(
            f"  Line {statement['line']}: "
            f"{statement['token']}"
        )

    print("\nSyntax errors:")
    for error in errors:
        print(
            f"  Line {error['line']}, "
            f"token {error['unexpected']!r}: "
            f"{error['message']}"
        )

    print("\nLexical errors:", len(lexical_errors))
    print("Recovery actions:", len(trace))

    statements_found = all(
        any(
            actual["line"] == expected["line"]
            and actual["token"] == expected["token"]
            for actual in completed_statements
        )
        for expected in expected_statements
    )

    error_count_correct = len(errors) == expected_errors
    recovery_recorded = len(trace) > 0

    print("\nChecks:")
    print("Expected statements completed:", statements_found)
    print("Expected error count:", error_count_correct)
    print("Recovery actions recorded:", recovery_recorded)

    passed = (
        statements_found
        and error_count_correct
        and recovery_recorded
        and not lexical_errors
    )

    print("\nTEST RESULT:", "PASS" if passed else "FAIL")
    return passed


def main():
    results = []

    results.append(
        run_test(
            "Resume after malformed assignment",
            "int a;\na = 10 + ;\nprint(7);\n",
            [
                {"line": 1, "token": "int"},
                {"line": 3, "token": "print"},
            ],
            1,
        )
    )

    results.append(
        run_test(
            "Resume after multiple malformed statements",
            "int a;\na = 10 + ;\nprint(5 + );\nprint(9);\n",
            [
                {"line": 1, "token": "int"},
                {"line": 4, "token": "print"},
            ],
            2,
        )
    )

    print("\n" + "=" * 70)
    print("STATEMENT-CONTINUATION TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print(f"Total:  {len(results)}")


if __name__ == "__main__":
    main()

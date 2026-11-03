
from compiler.lexer import tokenize
from compiler.parser import Parser, analyze_source, validate_source


def run_test(name, source, strategy, expected):
    print("\n" + "=" * 70)
    print(f"TEST: {name}")
    print(f"STRATEGY: {strategy.upper()}")
    print("=" * 70)

    result = analyze_source(source, strategy)
    recovered_source = result.get("recovered_source", source)

    print("\nOriginal source:")
    print(source)

    print("Recovered source:")
    print(recovered_source)

    print("Syntax errors detected:", len(result.get("errors", [])))
    print("Lexical errors detected:", len(result.get("lexical_errors", [])))
    print("Source changed:", recovered_source != source)
    print("Recovery trace:")

    for item in result.get("trace", []):
        print(item)

    validation_pass = validate_source(recovered_source)
    print("\nRecovered-source validation:")
    print("PASS" if validation_pass else "FAIL")

    checks = []

    if "source_changed" in expected:
        checks.append(
            (recovered_source != source) == expected["source_changed"]
        )

    if "validation" in expected:
        checks.append(validation_pass == expected["validation"])

    if "syntax_errors" in expected:
        checks.append(
            len(result.get("errors", [])) == expected["syntax_errors"]
        )

    if "trace_action_contains" in expected:
        actions = [
            item.get("action", "")
            for item in result.get("trace", [])
        ]
        checks.append(
            any(
                expected["trace_action_contains"] in action
                for action in actions
            )
        )

    if "completed_statement" in expected:
        tokens, lexical_errors = tokenize(source)
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

        target = expected["completed_statement"]
        statement_found = any(
            item["line"] == target["line"]
            and item["token"] == target["token"]
            for item in completed
        )

        checks.append(statement_found and not lexical_errors)

        print("\nCompleted statements during initial parse:")
        for item in completed:
            print(f"  Line {item['line']}: {item['token']}")

        print("Expected later statement completed:", statement_found)

    passed = all(checks) if checks else False
    print("\nTEST RESULT:", "PASS" if passed else "FAIL")
    return passed


def main():
    results = []

    results.append(
        run_test(
            "Missing semicolon",
            "int a\na = 5;\n",
            "token insertion",
            {
                "source_changed": True,
                "validation": True,
                "syntax_errors": 1,
                "trace_action_contains": "Token insertion",
            },
        )
    )

    results.append(
        run_test(
            "Missing expression operand",
            "int a;\na = 10 + ;\n",
            "phrase-level recovery",
            {
                "source_changed": True,
                "validation": True,
                "syntax_errors": 1,
                "trace_action_contains": "Phrase-level recovery",
            },
        )
    )

    results.append(
        run_test(
            "Panic-mode synchronization and continuation",
            "int a;\na = 10 + ;\nprint(7);\n",
            "panic mode",
            {
                "source_changed": True,
                "validation": True,
                "syntax_errors": 1,
                "trace_action_contains": "Panic mode",
                "completed_statement": {
                    "line": 3,
                    "token": "print",
                },
            },
        )
    )

    results.append(
        run_test(
            "Multiple syntax errors",
            "int a\na = 10 + ;\nprint(a)\n",
            "automatic",
            {
                "source_changed": True,
                "validation": True,
                "syntax_errors": 3,
                "trace_action_contains": "Token insertion",
            },
        )
    )

    print("\n" + "=" * 70)
    print("TARGETED STRATEGY TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print(f"Total:  {len(results)}")


if __name__ == "__main__":
    main()

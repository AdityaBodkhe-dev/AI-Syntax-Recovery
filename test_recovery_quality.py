
from compiler.lexer import tokenize
from compiler.parser import analyze_source, validate_source


STRATEGIES = [
    "automatic",
    "token insertion",
    "phrase-level recovery",
    "panic mode",
]

TEST_CASES = [
    {
        "name": "Valid program",
        "source": "int a;\na = 5;\nprint(a);",
    },
    {
        "name": "Missing semicolon",
        "source": "int a\na = 5;\nprint(a);",
    },
    {
        "name": "Missing closing parenthesis",
        "source": "int a;\nprint(a;\n",
    },
    {
        "name": "Missing closing brace",
        "source": "if (a > 0) {\nprint(a);",
    },
    {
        "name": "Missing expression operand",
        "source": "int a;\na = 5 + ;\nprint(a);",
    },
    {
        "name": "Unexpected operator",
        "source": "int a;\na = 5 + * 2;\nprint(a);",
    },
    {
        "name": "Malformed print statement",
        "source": "print(;\nprint(2);",
    },
    {
        "name": "Multiple syntax errors",
        "source": "int a\na = + ;\nprint(7);",
    },
    {
        "name": "Valid statement after malformed input",
        "source": "a = 5 + ;\nprint(9);",
    },
    {
        "name": "Incomplete expression at EOF",
        "source": "int a;\na = 5 +",
    },
]


def count_print_tokens(source):
    tokens, _ = tokenize(source)
    return sum(
        1 for token in tokens
        if token.get("value") == "print"
    )


def run_test(case, strategy):
    source = case["source"]

    result = analyze_source(source, strategy)
    recovered = result.get("recovered_source", "")

    # Validate the actual recovered source independently.
    recovered_is_valid = validate_source(recovered)

    original_prints = count_print_tokens(source)
    recovered_prints = count_print_tokens(recovered)

    # This counts preserved print keywords, not full statement equivalence.
    preserved_prints = min(original_prints, recovered_prints)

    return {
        "name": case["name"],
        "strategy": strategy,
        "original_valid": result.get("success", False),
        "recovered_valid": recovered_is_valid,
        "errors": len(result.get("errors", [])),
        "lexical_errors": len(result.get("lexical_errors", [])),
        "original_prints": original_prints,
        "recovered_prints": recovered_prints,
        "preserved_prints": preserved_prints,
        "recovered_source": recovered,
    }


def main():
    results = []
    crashes = 0
    total = len(TEST_CASES) * len(STRATEGIES)

    print("=" * 90)
    print("SYNTAX RECOVERY QUALITY COMPARISON")
    print("=" * 90)
    print("Test cases:", len(TEST_CASES))
    print("Strategies:", len(STRATEGIES))
    print("Total experiments:", total)

    for case in TEST_CASES:
        for strategy in STRATEGIES:
            print("\n" + "-" * 90)
            print("CASE:", case["name"])
            print("STRATEGY:", strategy)

            try:
                result = run_test(case, strategy)
                results.append(result)

                print("Original valid:", result["original_valid"])
                print("Recovered valid:", result["recovered_valid"])
                print("Syntax errors:", result["errors"])
                print("Lexical errors:", result["lexical_errors"])
                print(
                    "Print keywords preserved:",
                    f'{result["preserved_prints"]}/'
                    f'{result["original_prints"]}',
                )
                print("Recovered source:")
                print(result["recovered_source"])
                print(
                    "QUALITY RESULT:",
                    "RECOVERED VALID"
                    if result["recovered_valid"]
                    else "STILL INVALID",
                )

            except Exception as exc:
                crashes += 1
                print("QUALITY RESULT: ERROR")
                print(type(exc).__name__ + ":", str(exc))

    print("\n" + "=" * 90)
    print("SUMMARY BY STRATEGY")
    print("=" * 90)
    print(
        f'{"Strategy":<24}'
        f'{"Valid recovered":<20}'
        f'{"Errors total":<16}'
        f'{"Crashes":<10}'
    )

    for strategy in STRATEGIES:
        strategy_results = [
            item for item in results
            if item["strategy"] == strategy
        ]

        valid_count = sum(
            item["recovered_valid"]
            for item in strategy_results
        )
        error_count = sum(
            item["errors"] for item in strategy_results
        )

        print(
            f"{strategy:<24}"
            f"{valid_count}/{len(strategy_results):<18}"
            f"{error_count:<16}"
            f'{sum(1 for _ in []):<10}'
        )

    valid_total = sum(
        item["recovered_valid"] for item in results
    )

    print("\n" + "=" * 90)
    print("OVERALL RESULTS")
    print("=" * 90)
    print("Experiments completed:", len(results), "of", total)
    print("Recovered programs that validate:", valid_total)
    print("Unhandled exceptions:", crashes)

    if results:
        print(
            "Recovery validation rate:",
            f"{valid_total / len(results) * 100:.1f}%",
        )

    print(
        "\nNote: A valid recovered program is not necessarily "
        "semantically equivalent to the original."
    )
    print(
        "Print-keyword counts are a basic preservation indicator, "
        "not proof that complete statements were preserved."
    )


if __name__ == "__main__":
    main()

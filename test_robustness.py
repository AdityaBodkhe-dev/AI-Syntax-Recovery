
from compiler.parser import analyze_source


STRATEGIES = [
    "automatic",
    "token insertion",
    "phrase-level recovery",
    "panic mode",
]

TEST_CASES = [
    {
        "name": "Empty input",
        "source": "",
    },
    {
        "name": "Whitespace-only input",
        "source": "   \n\t\n   ",
    },
    {
        "name": "Incomplete declaration",
        "source": "int",
    },
    {
        "name": "Incomplete assignment",
        "source": "int a;\na =",
    },
    {
        "name": "Repeated operators",
        "source": "int a;\na = 5 + * 2;",
    },
    {
        "name": "Incomplete if condition",
        "source": "if (a > ) {\n    print(a);\n}",
    },
    {
        "name": "Several malformed statements",
        "source": "int;\na = + ;\nprint(;\n}",
    },
    {
        "name": "Unclosed block",
        "source": "if (a > 0) {\nprint(a);",
    },
    {
        "name": "Unexpected closing brace",
        "source": "}\n}\nprint(1);",
    },
    {
        "name": "Only operators and punctuation",
        "source": "+ * / = ; ) }",
    },
]


def check_result_structure(result):
    required_keys = {
        "errors",
        "trace",
        "success",
        "recovery_success",
        "recovered_source",
        "tokens",
        "lexical_errors",
    }

    if not isinstance(result, dict):
        return False, "Result is not a dictionary"

    missing = required_keys - set(result.keys())

    if missing:
        return False, f"Missing result fields: {sorted(missing)}"

    if not isinstance(result["errors"], list):
        return False, "'errors' is not a list"

    if not isinstance(result["trace"], list):
        return False, "'trace' is not a list"

    if not isinstance(result["tokens"], list):
        return False, "'tokens' is not a list"

    if not isinstance(result["lexical_errors"], list):
        return False, "'lexical_errors' is not a list"

    if not isinstance(result["recovered_source"], str):
        return False, "'recovered_source' is not a string"

    if not isinstance(result["success"], bool):
        return False, "'success' is not a boolean"

    if not isinstance(result["recovery_success"], bool):
        return False, "'recovery_success' is not a boolean"

    return True, "Result structure is valid"


def run_test(test_case, strategy):
    name = test_case["name"]
    source = test_case["source"]

    print("\n" + "-" * 72)
    print(f"TEST: {name}")
    print(f"STRATEGY: {strategy}")
    print("-" * 72)

    try:
        result = analyze_source(source, strategy)

        structure_ok, structure_message = check_result_structure(result)

        print("Input length:", len(source))
        print("Syntax errors:", len(result.get("errors", [])))
        print("Lexical errors:", len(result.get("lexical_errors", [])))
        print("Recovery trace entries:", len(result.get("trace", [])))
        print("Original syntax valid:", result.get("success"))
        print("Recovered source valid:", result.get("recovery_success"))
        print("Recovered source:")
        print(repr(result.get("recovered_source")))

        print("Structure check:", structure_message)

        # This suite checks robustness, not whether every malformed
        # program can be repaired into valid source code.
        passed = structure_ok

        if passed:
            print("TEST RESULT: PASS")
        else:
            print("TEST RESULT: FAIL")

        return passed

    except Exception as exc:
        print("TEST RESULT: FAIL")
        print("Unhandled exception:", type(exc).__name__, str(exc))
        return False


def main():
    passed = 0
    failed = 0
    total = len(TEST_CASES) * len(STRATEGIES)

    print("=" * 72)
    print("SYNTAX RECOVERY ROBUSTNESS TEST SUITE")
    print("=" * 72)
    print("Test cases:", len(TEST_CASES))
    print("Strategies:", len(STRATEGIES))
    print("Total checks:", total)

    for test_case in TEST_CASES:
        for strategy in STRATEGIES:
            if run_test(test_case, strategy):
                passed += 1
            else:
                failed += 1

    print("\n" + "=" * 72)
    print("ROBUSTNESS TEST SUMMARY")
    print("=" * 72)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {total}")

    if failed == 0:
        print("\nAll robustness checks passed.")
    else:
        print("\nSome checks failed. Inspect the exceptions and result structures.")


if __name__ == "__main__":
    main()

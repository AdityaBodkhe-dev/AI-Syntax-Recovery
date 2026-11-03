from compiler.parser import analyze_source, validate_source


STRATEGIES = [
    "automatic",
    "token insertion",
    "phrase-level recovery",
    "panic mode",
]

# These cases test the current intended behavior of each recovery strategy.
# Validity and preservation are checked independently: a valid output is not
# considered a successful recovery if it removes required useful statements.
TEST_CASES = [
    {
        "name": "Missing semicolon",
        "source": "int a\na = 5;\n",
        "expected_valid": {
            "automatic": True,
            "token insertion": True,
            "phrase-level recovery": True,
            "panic mode": True,
        },
        "must_preserve": ["a = 5;"],
    },
    {
        "name": "Missing expression operand",
        "source": "int a;\na = 10 + ;\n",
        "expected_valid": {
            "automatic": True,
            "token insertion": True,
            "phrase-level recovery": True,
            "panic mode": True,
        },
        "must_preserve": ["int a;"],
        "must_recover_with": {
            "token insertion": ["a = 10 + 0;"],
        },
    },
    {
        "name": "Multiple syntax errors",
        "source": "int a\na = 10 + ;\nprint(a)\n",
        "expected_valid": {
            "automatic": True,
            "token insertion": True,
            "phrase-level recovery": True,
            "panic mode": True,
        },
        "must_preserve": ["print(a)"],
        "must_recover_with": {
            "token insertion": ["a = 10 + 0;", "print(a);"],
        },
    },
]


def is_valid(source):
    """Return False if validation raises an exception."""
    try:
        return bool(validate_source(source))
    except Exception:
        return False


def run_case(test_case):
    print("\\n" + "=" * 76)
    print(f"TEST CASE: {test_case['name']}")
    print("=" * 76)
    print("Original source:")
    print(test_case["source"])

    results = {}

    for strategy in STRATEGIES:
        result = analyze_source(test_case["source"], strategy)
        recovered_source = result.get("recovered_source", test_case["source"])
        validation_pass = is_valid(recovered_source)
        expected_valid = test_case["expected_valid"][strategy]
        validity_matches = validation_pass == expected_valid

        missing_preserved = [
            fragment
            for fragment in test_case.get("must_preserve", [])
            if fragment not in recovered_source
        ]

        required_recovery = test_case.get("must_recover_with", {}).get(strategy, [])
        missing_recovery = [
            fragment for fragment in required_recovery
            if fragment not in recovered_source
        ]

        preservation_pass = not missing_preserved
        recovery_behavior_pass = not missing_recovery
        passed = validity_matches and preservation_pass and recovery_behavior_pass

        results[strategy] = {
            "errors": len(result.get("errors", [])),
            "trace": len(result.get("trace", [])),
            "source_changed": recovered_source != test_case["source"],
            "validation": validation_pass,
            "expected_valid": expected_valid,
            "validity_matches": validity_matches,
            "preservation_pass": preservation_pass,
            "recovery_behavior_pass": recovery_behavior_pass,
            "missing_preserved": missing_preserved,
            "missing_recovery": missing_recovery,
            "passed": passed,
        }

        print("\\n" + "-" * 76)
        print(f"Strategy: {strategy.upper()}")
        print("Errors detected:", results[strategy]["errors"])
        print("Recovery trace entries:", results[strategy]["trace"])
        print("Source changed:", results[strategy]["source_changed"])
        print("Recovered source validation:", "PASS" if validation_pass else "FAIL")
        print("Expected validity:", "VALID" if expected_valid else "INVALID")
        print("Validity expectation:", "PASS" if validity_matches else "FAIL")
        print("Required statements preserved:", "PASS" if preservation_pass else "FAIL")
        if missing_preserved:
            print("Missing required text:", missing_preserved)
        print("Required recovery behavior:", "PASS" if recovery_behavior_pass else "FAIL")
        if missing_recovery:
            print("Missing expected recovered text:", missing_recovery)
        print("Overall case result:", "PASS" if passed else "FAIL")
        print("Recovered source:")
        print(recovered_source)

        if result.get("lexical_errors"):
            print("Lexical errors:", result["lexical_errors"])

    return results


def main():
    all_results = {
        case["name"]: run_case(case)
        for case in TEST_CASES
    }

    print("\\n" + "=" * 76)
    print("FINAL STRATEGY COMPARISON")
    print("=" * 76)
    print(f"{'Strategy':<25}{'Passed checks':<20}{'Valid outputs':<18}")
    print("-" * 63)

    for strategy in STRATEGIES:
        passed = sum(
            all_results[case_name][strategy]["passed"]
            for case_name in all_results
        )
        valid = sum(
            all_results[case_name][strategy]["validation"]
            for case_name in all_results
        )
        print(f"{strategy:<25}{passed}/3{'':<15}{valid}/3")

    total_checks = len(TEST_CASES) * len(STRATEGIES)
    passed_checks = sum(
        all_results[case_name][strategy]["passed"]
        for case_name in all_results
        for strategy in STRATEGIES
    )

    print("\\nOverall checks:")
    print(f"Passed: {passed_checks}/{total_checks}")
    print(f"Failed: {total_checks - passed_checks}/{total_checks}")
    print("\\nInterpretation:")
    print("- Automatic recovery combines supported local repairs.")
    print("- Token insertion inserts missing tokens, including placeholder operands.")
    print("- Phrase-level recovery attempts local repairs to malformed phrases.")
    print("- Panic mode skips malformed input to synchronization points.")
    print("- Validity alone is not enough: required later statements must survive.")
    print("- Recovery tests check output behavior, not semantic equivalence.")
    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())

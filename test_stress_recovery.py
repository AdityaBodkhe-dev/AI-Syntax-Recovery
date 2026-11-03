"""Stress tests for syntax-error recovery across multiple combined errors.

Run from the project root:
    python test_stress_recovery.py

This script reports syntax validity and preservation indicators. A valid
recovered program is not proof that its meaning matches the original source.
"""

from compiler.parser import analyze_source, validate_source

STRATEGIES = (
    "automatic",
    "token insertion",
    "phrase-level recovery",
    "panic mode",
)

CASES = (
    {
        "name": "Missing semicolon and closing parenthesis",
        "source": "int a;\nprint(a;\nprint(2);",
        "preserve": ("print(2);",),
    },
    {
        "name": "Missing declaration semicolon and missing operand",
        "source": "int a\na = 10 + ;\nprint(a);",
        "preserve": ("print(a);",),
    },
    {
        "name": "Nested block with malformed print",
        "source": "if (a > 0) {\n    print(a;\n    print(2);\n}\nprint(3);",
        "preserve": ("print(2);", "print(3);"),
    },
    {
        "name": "Several malformed statements before valid print",
        "source": "int a\na = 5 + * ;\nprint(7);",
        "preserve": ("print(7);",),
    },
    {
        "name": "Unexpected brace followed by valid statements",
        "source": "}\nint a;\na = 4;\nprint(a);",
        "preserve": ("int a;", "print(a);"),
    },
    {
        "name": "Missing closing brace and malformed assignment",
        "source": "if (a > 0) {\n    int b;\n    b = 5 + ;\n    print(b);",
        "preserve": ("print(b);",),
    },
)


def main():
    total = 0
    valid_count = 0
    preservation_count = 0
    crash_count = 0

    print("=" * 88)
    print("COMBINED-ERROR SYNTAX RECOVERY STRESS TESTS")
    print("=" * 88)
    print(f"Cases: {len(CASES)} | Strategies: {len(STRATEGIES)} | Experiments: {len(CASES) * len(STRATEGIES)}")

    for case in CASES:
        print("\n" + "-" * 88)
        print(f"CASE: {case['name']}")
        print("Original source:")
        print(case["source"])

        for strategy in STRATEGIES:
            total += 1
            print(f"\n[{strategy.upper()}]")
            try:
                result = analyze_source(case["source"], strategy)
                recovered = result.get("recovered_source", "")
                try:
                    is_valid = validate_source(recovered)
                except Exception:
                    is_valid = False

                preserved = all(fragment in recovered for fragment in case["preserve"])
                valid_count += int(is_valid)
                preservation_count += int(preserved)

                print(f"Syntax errors reported: {len(result.get('errors', []))}")
                print(f"Recovered source valid: {'YES' if is_valid else 'NO'}")
                print(f"Required fragments preserved: {'YES' if preserved else 'NO'}")
                print("Recovered source:")
                print(recovered if recovered else "<empty>")
            except Exception as exc:
                crash_count += 1
                print(f"CRASH: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 88)
    print("SUMMARY")
    print("=" * 88)
    print(f"Experiments: {total}")
    print(f"Recovered programs that validate: {valid_count}/{total}")
    print(f"Required-fragment preservation checks passed: {preservation_count}/{total}")
    print(f"Unhandled exceptions: {crash_count}")
    print("\nNote: fragment checks are simple preservation indicators, not proof of semantic equivalence.")

    return 1 if crash_count else 0


if __name__ == "__main__":
    raise SystemExit(main())

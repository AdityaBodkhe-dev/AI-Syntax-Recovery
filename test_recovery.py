
from compiler.parser import analyze_source


def run_test(name, source, expected_recovery=None, expected_errors=1):
    """Run one syntax-recovery test and print its result."""

    result = analyze_source(source, strategy="automatic")

    errors = result["errors"]
    recovered = result["recovered_source"]

    passed = len(errors) >= expected_errors

    if expected_recovery is not None:
        passed = passed and expected_recovery in recovered

    status = "PASS" if passed else "FAIL"

    print(f"\n[{status}] {name}")
    print(f"  Syntax errors reported: {len(errors)}")
    print(f"  Recovery actions: {len(result['trace'])}")

    if expected_recovery is not None:
        print(f"  Expected correction: {expected_recovery!r}")
        print(f"  Correction present: {expected_recovery in recovered}")

    if errors:
        for error in errors:
            print(
                f"  Line {error['line']}, column {error['column']}: "
                f"{error['message']} -> {error['action']}"
            )

    if not passed:
        print("  Recovered source:")
        print(recovered)

    return passed


def run_valid_test(name, source):
    """Check that a valid program has no reported parser errors."""

    result = analyze_source(source, strategy="automatic")

    passed = (
        result["success"]
        and not result["errors"]
        and not result["lexical_errors"]
        and result["recovered_source"] == source
    )

    print(f"\n[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"  Syntax valid: {result['success']}")
    print(f"  Errors: {len(result['errors'])}")
    print(
        "  Source unchanged: "
        f"{result['recovered_source'] == source}"
    )

    if not passed:
        print("  Diagnostics:", result["errors"])
        print("  Recovered source:", repr(result["recovered_source"]))

    return passed


def main():
    print("=" * 60)
    print("SYNTAX RECOVERY AUTOMATED TEST SUITE")
    print("=" * 60)

    passed = 0
    failed = 0

    # ---------------------------------------------------------
    # VALID PROGRAM TESTS
    # ---------------------------------------------------------

    valid_tests = [
        (
            "Valid declaration",
            "int a;\n",
        ),
        (
            "Valid assignment",
            "int a;\na = 10 + 5;\n",
        ),
        (
            "Valid print statement",
            "print(10);\n",
        ),
        (
            "Valid if statement",
            "int a;\nif (a > 10) {\n    print(a);\n}\n",
        ),
    ]

    for name, source in valid_tests:
        if run_valid_test(name, source):
            passed += 1
        else:
            failed += 1

    # ---------------------------------------------------------
    # INVALID PROGRAM TESTS
    # ---------------------------------------------------------

    invalid_tests = [
        (
            "Missing semicolon after declaration",
            "int a\na = 5;\n",
            "int a;",
            1,
        ),
        (
            "Missing semicolon after assignment",
            "int a;\na = 5\nprint(a);\n",
            "a = 5;",
            1,
        ),
        (
            "Missing operand after plus",
            "int a;\na = 10 + ;\n",
            "10 + 0",
            1,
        ),
        (
            "Missing operand after minus",
            "int a;\na = 10 - ;\n",
            "10 - 0",
            1,
        ),
        (
            "Missing closing parenthesis in if",
            "int a;\nif (a > 10 {\nprint(a);\n}\n",
            "if (a > 10 )",
            1,
        ),
        (
            "Missing closing parenthesis in print",
            "print(10;\n",
            "print(10);",
            1,
        ),
        (
            "Missing semicolon after print",
            "print(10)\n",
            "print(10);",
            1,
        ),
        (
            "Missing semicolon after float declaration",
            "float price\n",
            "float price;",
            1,
        ),
        (
            "Multiple syntax errors",
            "int a\na = 10 + ;\nif (a > 10 {\nprint(a);\n}\n",
            "10 + 0",
            3,
        ),
        (
            "Missing operand before closing parenthesis",
            "print( );\n",
            "print( 0);",
            1,
        ),
    ]

    for name, source, expected_recovery, expected_errors in invalid_tests:
        if run_test(
            name,
            source,
            expected_recovery,
            expected_errors,
        ):
            passed += 1
        else:
            failed += 1

    # ---------------------------------------------------------
    # LEXICAL ERROR TEST
    # ---------------------------------------------------------

    lexical_source = "int a;\na = 5 @ 2;\n"
    lexical_result = analyze_source(lexical_source)

    lexical_passed = len(lexical_result["lexical_errors"]) > 0

    print(f"\n[{'PASS' if lexical_passed else 'FAIL'}] Invalid character")
    print(
        "  Lexical errors detected:",
        len(lexical_result["lexical_errors"]),
    )

    if lexical_passed:
        passed += 1
    else:
        failed += 1

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    total = passed + failed

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {total}")

    if failed == 0:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed. Review the results above.")


if __name__ == "__main__":
    main()

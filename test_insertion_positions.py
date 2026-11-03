
from compiler.parser import analyze_source, validate_source


def main():
    source = (
        "if (a > 0) {\n"
        "    int b\n"
        "    b = 10 + ;\n"
        "    print(b);\n"
        "}\n"
    )

    print("=" * 70)
    print("MISSING SEMICOLON INSERTION POSITION TEST")
    print("=" * 70)

    result = analyze_source(source, "automatic")
    recovered = result["recovered_source"]

    print("\nOriginal source:")
    print(source)

    print("Recovered source:")
    print(recovered)

    expected_fragment = "int b;\n"
    correct_position = expected_fragment in recovered

    misplaced_fragment = "\n    ;b = " in recovered
    valid_source = validate_source(recovered)

    print("\nChecks:")
    print("Semicolon follows declaration:", correct_position)
    print("Semicolon misplaced before assignment:", misplaced_fragment)
    print("Recovered source validates:", valid_source)

    passed = (
        correct_position
        and not misplaced_fragment
        and valid_source
    )

    print("\nTEST RESULT:", "PASS" if passed else "FAIL")


if __name__ == "__main__":
    main()

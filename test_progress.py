
import json
import subprocess
import sys


STRATEGIES = [
    "automatic",
    "token insertion",
    "phrase-level recovery",
    "panic mode",
]

TEST_CASES = [
    {
        "name": "Continue after malformed assignment",
        "source": "int a;\na = 10 + ;\nprint(7);\n",
        "expected_line": 3,
    },
    {
        "name": "Continue after multiple malformed statements",
        "source": "int a;\na = 10 + ;\nprint(5 + );\nprint(9);\n",
        "expected_line": 4,
    },
    {
        "name": "Continue inside a malformed block",
        "source": "if (a > 0) {\n a = 5 + ;\n print(7);\n}\n",
        "expected_line": 3,
    },
    {
        "name": "Repeated malformed punctuation",
        "source": "+ * / = ; ) }",
        "expected_line": None,
    },
    {
        "name": "Incomplete expression at end of input",
        "source": "int a;\na = 10 +",
        "expected_line": None,
    },
]


CHILD_SCRIPT = r'''
import json
import sys

from compiler.lexer import tokenize
from compiler.parser import Parser

strategy = sys.argv[1]
source = sys.argv[2]

tokens, lexical_errors = tokenize(source)
parser = Parser(tokens, source, strategy)

completed_statements = []
original_statement = Parser.statement


def tracked_statement(current_parser):
    token = current_parser.current()

    # Tokens are dictionaries, not objects with token attributes.
    token_line = token.get("line")
    token_type = token.get("type")
    token_value = token.get("value")

    original_statement(current_parser)

    completed_statements.append({
        "line": token_line,
        "type": token_type,
        "value": token_value,
    })


Parser.statement = tracked_statement

try:
    parser.parse()
finally:
    Parser.statement = original_statement

result = {
    "errors": parser.errors,
    "trace": parser.trace,
    "completed_statements": completed_statements,
    "token_count": max(0, len(tokens) - 1),
    "lexical_errors": lexical_errors,
    "recovered_source": parser.corrected_source(),
}

print(json.dumps(result, default=str))
'''


def run_case(test_case, strategy):
    print("\n" + "-" * 72)
    print("TEST:", test_case["name"])
    print("STRATEGY:", strategy)
    print("-" * 72)

    try:
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                CHILD_SCRIPT,
                strategy,
                test_case["source"],
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: Parser exceeded the 3-second timeout.")
        return False

    if process.returncode != 0:
        print("FAIL: Parser process exited with an error.")
        print(process.stderr)
        return False

    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError:
        print("FAIL: Parser did not return valid JSON.")
        print("Output:", process.stdout)
        print("Error:", process.stderr)
        return False

    errors = result.get("errors")
    trace = result.get("trace")
    completed = result.get("completed_statements")
    token_count = result.get("token_count")

    if not all([
        isinstance(errors, list),
        isinstance(trace, list),
        isinstance(completed, list),
        isinstance(token_count, int),
    ]):
        print("FAIL: Invalid parser result structure.")
        return False

    limit = max(10, token_count * 4 + 10)

    print("Input tokens:", token_count)
    print("Syntax errors:", len(errors))
    print("Recovery trace entries:", len(trace))
    print("Successfully completed statements:", len(completed))

    if len(errors) > limit or len(trace) > limit:
        print("FAIL: Recovery activity exceeded the safety limit.")
        return False

    expected_line = test_case["expected_line"]

    if expected_line is not None:
        continued = any(
            item.get("line") == expected_line
            and item.get("value") == "print"
            for item in completed
        )

        print("Expected later print statement parsed:", continued)

        if not continued:
            print("Recorded statements:")
            for item in completed:
                print(" ", item)

            print("FAIL: Expected statement was not completed.")
            return False

    print("PASS: Progress checks passed.")
    return True


def main():
    total = len(TEST_CASES) * len(STRATEGIES)
    passed = 0
    failed = 0

    print("=" * 72)
    print("SYNTAX RECOVERY PROGRESS TEST SUITE")
    print("=" * 72)
    print("Test cases:", len(TEST_CASES))
    print("Strategies:", len(STRATEGIES))
    print("Total checks:", total)
    print("Timeout per check: 3 seconds")

    for test_case in TEST_CASES:
        for strategy in STRATEGIES:
            if run_case(test_case, strategy):
                passed += 1
            else:
                failed += 1

    print("\n" + "=" * 72)
    print("PROGRESS TEST SUMMARY")
    print("=" * 72)
    print("Passed:", passed)
    print("Failed:", failed)
    print("Total:", total)

    if failed == 0:
        print("All progress checks passed.")
    else:
        print("Some checks failed. Review the details above.")


if __name__ == "__main__":
    main()

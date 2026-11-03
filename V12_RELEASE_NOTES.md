# V12 Release Notes — Whole-Program Repair Quality

## Fixes
- Supports C-style empty parameter lists written as `main(void)`.
- Parses function-call expressions such as `add(2, 3)` and comma-separated arguments.
- Adds a targeted candidate for the common malformed call `add;(x y)`, proposing `add(x, y)`.
- Promotes a repair candidate to the recommended recovered source only after whole-program Mini-C syntax validation and a meaningful-token preservation check.
- Filters out valid-but-destructive suggestions that discard most meaningful identifiers and numeric literals, including the prior empty-body alternative.
- Keeps correction suggestions limited to three unique, changed, fully validated candidates.
- Adds regression tests for valid code, missing semicolons, missing operators, malformed calls, candidate validation, and destructive alternatives.

## Validation scope
The parser validates the project's configured Mini-C grammar, not all ISO C semantics. Function names are not checked against declarations, so `add(x, y)` may pass syntax validation even if `add` is not defined. The malformed-call rule is a heuristic suggestion, not proof of intended semantics.

## Run
1. Extract the ZIP.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Run regression tests: `python -m unittest test_release_quality -v`
4. Launch the app using `run.bat`.

# V13 Release Notes — Multi-Error Repair

V13 extends the V12-1 project to cover the comprehensive multi-error example that previously returned the input unchanged.

## Changes
- Lexer support for `#include` directives, string literals, `for`, postfix `++`/`--`, and `%`.
- Parser support for `for` loops and expression/function-call statements such as `printf(...)`.
- Conservative iterative repairs for missing semicolons, a malformed call like `add;(x y)`, a missing condition parenthesis, adjacent invalid operators, missing operands, and unmatched closing braces.
- A candidate is only accepted when the complete source passes the configured Mini-C validator and the meaningful-token preservation threshold.
- Updated regression test for the previously failing multi-error example and added `test_comprehensive_repair.py`.

## Run
```powershell
python -m pip install -r requirements.txt
python -m unittest discover -v
```

The parser checks the project's supported C-like subset, not all ISO C grammar, type correctness, function declaration consistency, or runtime behavior. Some repairs (such as inserting `0` or choosing `+` for a malformed expression) are heuristics and may not reflect intended program semantics.

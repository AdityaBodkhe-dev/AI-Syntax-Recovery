# Syntax Recovery Studio V10 — Release Notes

## Included improvements

1. **Context-aware candidate ranking:** retains the existing learned ranker and contextual feature adjustments. Candidate list is capped at three unique, changed, parser-valid options; fewer options are shown when fewer candidates qualify.
2. **Before/after diff:** the analysis response includes a unified line diff and the UI highlights inserted and removed lines.
3. **Error localization and structure view:** existing parser line/column diagnostics remain visible. A compact Mini-C structural outline displays detected functions, declaration names, and line-level statement categories. It is explicitly approximate, not a full AST.
4. **Built-in smoke benchmark:** `/benchmark` and the UI button run eight fixed Mini-C sanity cases. This is a small regression benchmark, not a real-world repair-accuracy claim.
5. **Multiple-error handling:** the UI retains parser diagnostics and recovery trace for the whole submitted program, and the regression suite includes a multi-error no-crash case. Repairs are proposals, not guarantees of intent.
6. **UI polish:** added line-diff review, parse outline, benchmark panel, and clear-editor action while preserving original source separately from proposals.
7. **Explainable ranking:** candidate cards show relative rank score and notes about syntax validation, delimiter balance, declared-operand preference, generic fallback use, and statement preservation. The score is labelled as a relative ranking score, not a calibrated probability.

## Validation

- Added `test_v10_features.py` covering response fields, outline basics, benchmark case count, multi-error handling, valid-source suggestion behavior, and ranking explanation metadata.
- Existing regression tests are retained.
- Run on Windows with Flask installed:

```powershell
python -m pip install -r requirements.txt
python -m unittest test_full_upgrade test_correction_options test_final_features test_engine_quality test_v4_improvements test_v6_optimizations test_v10_features -v
```

## Scope and limitations

- This is an educational Mini-C parser, not a complete ISO C compiler.
- The structural outline is heuristic and not a full abstract syntax tree.
- A parser-valid repair can still alter intended program meaning.
- The eight-case benchmark is a sanity check only and must not be presented as general model accuracy.
- The ranker is a lightweight learned ranking model with rules; it is not a generative AI code model.

## Whole-program validation gate (final hardening update)

- The parser's attempted recovery is now checked against the complete configured Mini-C grammar before it is displayed as recovered code.
- If the attempt fails whole-program validation, the UI displays the original source rather than presenting an invalid attempt as corrected code, sets `recovery_success` to false, and explains the validation limitation.
- Each suggested candidate continues to be independently validated as a complete program; only changed, unique, syntax-valid suggestions are returned, with a maximum of three.
- Added `test_whole_program_gate.py`, including a regression case based on the invalid output reported during manual testing.
- The validator covers the project's configured Mini-C grammar, not all ISO C features. Unsupported constructs such as preprocessor directives, `for` loops, and library calls may be rejected until explicitly added to the grammar.

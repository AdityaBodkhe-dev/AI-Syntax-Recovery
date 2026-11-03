# Optimization Roadmap — Syntax Recovery Studio V6

This release consolidates practical next steps into one prioritized checklist. Items marked implemented are included in V6; future research items are not claimed as completed.

## Implemented in V6/V7
- [x] Add a targeted candidate-generation path for a missing binary operator between adjacent expression atoms in simple assignment/return lines. Candidates are only exposed if the Mini-C parser accepts them.
- [x] Add regression tests for the operator-recovery path and evaluation harness presence.
- [x] Keep deterministic, controlled-mutation evaluation and a JSON report.
- [x] V7: return up to three unique, changed, syntax-valid suggestions; return fewer when fewer qualify, and none for already-valid source.
- [x] Keep clear disclaimers: parse validity is not semantic correctness; synthetic ranking labels are not a real-world benchmark.

## Recommended optimization priorities
1. **Candidate-generation coverage:** add bounded repair operators for missing operators, operands, delimiters, commas, colons, and statement terminators; validate every candidate.
2. **Regression corpus:** maintain hand-reviewed positive and negative cases, with exact expected repairs where intent is unambiguous.
3. **Semantic preservation:** measure unchanged AST/statement regions where a parser/AST is available; don't rank a candidate solely because it parses.
4. **Scope-aware symbol analysis:** distinguish local variables, parameters, function names, and shadowed declarations. Current regex diagnostics are intentionally approximate.
5. **Type-aware ranking:** track expression types through a real AST and use type compatibility as a soft signal, never as a guarantee.
6. **Ambiguity handling:** show multiple plausible candidates and confidence reasons rather than asserting a single intended repair.
7. **Evaluation separation:** separate train/validation/test examples by source template and mutation family to reduce synthetic leakage.
8. **Real-world benchmark:** build a manually reviewed dataset of original code, injected errors, intended repairs, and expected diagnostics before making real accuracy claims.
9. **Performance and safety:** test large inputs, malformed Unicode, repeated errors, time limits, and ensure error responses don't expose stack traces to users.
10. **Compiler-backed validation:** optionally validate generated C against a real compiler when available, while keeping the app usable without one.

## Known limitations
- This is a small educational Mini-C grammar, not a full ISO C compiler.
- The lightweight model ranks candidate repairs; it does not generate arbitrary programs.
- Regex-based semantic diagnostics can produce false positives/negatives.
- The 1,000-case report evaluates parser recovery on synthetic mutations, not the Flask candidate generator and not semantic correctness.
- The new missing-operator candidate path is a targeted heuristic and requires Windows regression confirmation; the build environment used for this package lacks Flask, so endpoint-level tests could not be executed here.

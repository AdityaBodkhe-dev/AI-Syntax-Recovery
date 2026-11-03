# Syntax Recovery Studio V10

## Quick start (Windows)
1. Extract this ZIP.
2. Open PowerShell in the extracted `AI-Syntax-Recovery-V10` folder.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000` in your browser.

You can also double-click `run.bat` to install requirements and start the app.

## V10 features
- Context-aware repair ranking with up to three unique, changed, syntax-valid suggestions.
- Original-versus-proposed line diff.
- Line/column syntax diagnostics and an approximate Mini-C parse outline.
- Eight-case smoke benchmark available through the UI and `/benchmark`.
- Whole-program diagnostic and recovery trace display for programs with multiple errors.
- Polished UI with clear-editor and one-click copying.
- Explainable ranking notes and relative rank scores (not probabilities).

## Run tests
```powershell
python -m unittest test_full_upgrade test_correction_options test_final_features test_engine_quality test_v4_improvements test_v6_optimizations test_v10_features -v
```

## Important limitations
This is an educational Mini-C grammar, not a complete ISO C compiler. The parse outline is approximate. Syntax-valid repairs may still alter intended program meaning. The included smoke benchmark is a small regression check, not a real-world accuracy estimate. The ranker is a lightweight ranking model, not a generative code model.

### Final recovery safety gate

The application validates the entire proposed program before displaying it as recovered code. If validation fails, it shows the original source and reports that no whole-program-valid recovery was produced. Suggestions are independently validated and limited to three distinct candidates. Validation is against the supported Mini-C grammar, not a complete ISO C implementation; constructs such as `#include`, `for`, and `printf` may be outside the grammar.

Run the final gate regressions with:

```powershell
python -m unittest test_whole_program_gate -v
```

## V11 final hardening
A whole-program validation gate now prevents an invalid recovery attempt from being displayed as repaired code. If the full candidate fails the configured Mini-C parser, the original input is shown and the UI reports that no validated recovery was produced. Suggested candidates are validated independently. This is not a full ISO C parser; see `V11_RELEASE_NOTES.md`.

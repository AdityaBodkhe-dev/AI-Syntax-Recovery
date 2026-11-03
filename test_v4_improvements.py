"""Focused regression tests for V4 ranking, targeted repairs, and diagnostics."""
import unittest
from correction_engine import rank_candidates, semantic_diagnostics
try:
    from app import build_correction_options
except ModuleNotFoundError:
    build_correction_options = None
from compiler.parser import validate_source

class V4ImprovementTests(unittest.TestCase):
    def test_unused_declared_operand_is_candidate_specific(self):
        original = 'int a, b, c;\na = b + ;\nprint(a);'
        options = [
            {'label': "Use declared variable 'b'", 'source': 'int a, b, c;\na = b + b;\nprint(a);', 'syntax_valid': True},
            {'label': "Use declared variable 'c'", 'source': 'int a, b, c;\na = b + c;\nprint(a);', 'syntax_valid': True},
        ]
        ranked = rank_candidates(options, original)
        by_label = {o['label']: o for o in ranked}
        self.assertFalse(by_label["Use declared variable 'b'"]['feature_summary']['unused_in_expression'])
        self.assertTrue(by_label["Use declared variable 'c'"]['feature_summary']['unused_in_expression'])

    @unittest.skipIf(build_correction_options is None, 'Flask is not installed in this test environment')
    def test_missing_semicolon_candidate(self):
        original = 'int a;\na = 2\nprint(a);'
        options = build_correction_options(original, original, 'automatic')
        self.assertTrue(any('semicolon' in o['label'].lower() and validate_source(o['source']) for o in options))

    def test_empty_assignment_diagnostic(self):
        codes = [d['code'] for d in semantic_diagnostics('int a;\na = ;')]
        self.assertIn('EMPTY_ASSIGNMENT', codes)

    def test_empty_condition_diagnostic(self):
        codes = [d['code'] for d in semantic_diagnostics('int a; if () { print(a); }')]
        self.assertIn('EMPTY_CONDITION', codes)

    def test_void_function_return_value_diagnostic(self):
        codes = [d['code'] for d in semantic_diagnostics('void f() { return 1; }')]
        self.assertIn('RETURN_TYPE_MISMATCH', codes)

    def test_nonvoid_function_bare_return_diagnostic(self):
        codes = [d['code'] for d in semantic_diagnostics('int f() { return; }')]
        self.assertIn('RETURN_TYPE_MISMATCH', codes)

if __name__ == '__main__':
    unittest.main(verbosity=2)

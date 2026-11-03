"""V6 targeted optimization tests."""
import unittest
try:
    from app import build_correction_options
except ModuleNotFoundError:
    build_correction_options = None
from compiler.parser import validate_source
from correction_engine import semantic_diagnostics

class V6OptimizationTests(unittest.TestCase):
    @unittest.skipIf(build_correction_options is None, "Flask is not installed")
    def test_missing_operator_candidate_is_offered_when_valid(self):
        source = "int a, b; a = a b; print(a);"
        options = build_correction_options(source, source, "automatic")
        self.assertTrue(any("Insert missing operator" in item["label"] and validate_source(item["source"]) for item in options))

    def test_existing_diagnostics_do_not_crash_on_nested_expression(self):
        result = semantic_diagnostics("int a, b; a = (b + 2) * 3; print(a);")
        self.assertIsInstance(result, list)

    def test_evaluation_harness_is_included(self):
        from pathlib import Path
        self.assertTrue(Path(__file__).with_name("evaluate_recovery.py").exists())

if __name__ == "__main__":
    unittest.main()

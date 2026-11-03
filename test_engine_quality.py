"""Standalone tests for ranking/diagnostics; does not require Flask."""
import unittest
from correction_engine import rank_candidates, semantic_diagnostics

class EngineQualityTests(unittest.TestCase):
    def test_contextual_unused_operand_ranks_first(self):
        original = "int a, b, c;\na = b + ;\nprint(a);"
        options = [
            {"label":"Use declared variable b", "source":"int a, b, c;\na = b + b;\nprint(a);", "syntax_valid":True},
            {"label":"Use numeric fallback 0", "source":"int a, b, c;\na = b + 0;\nprint(a);", "syntax_valid":True},
            {"label":"Use declared variable c", "source":"int a, b, c;\na = b + c;\nprint(a);", "syntax_valid":True},
        ]
        ranked = rank_candidates(options, original)
        self.assertEqual(ranked[0]["label"], "Use declared variable c")
        self.assertTrue(ranked[0]["feature_summary"]["prefers_unused_operand"])

    def test_undeclared_identifier(self):
        ds = semantic_diagnostics("int a; a = missing + 1;")
        self.assertIn("UNDECLARED_IDENTIFIER", [d["code"] for d in ds])

    def test_no_false_undeclared_warning_for_valid_simple_program(self):
        ds = semantic_diagnostics("int a, b; a = b + 1; print(a);")
        self.assertNotIn("UNDECLARED_IDENTIFIER", [d["code"] for d in ds])

    def test_duplicate_declaration(self):
        self.assertIn("DUPLICATE_DECLARATION", [d["code"] for d in semantic_diagnostics("int a, a;")])

    def test_decimal_to_int_warning(self):
        self.assertIn("POSSIBLE_TYPE_MISMATCH", [d["code"] for d in semantic_diagnostics("int a; a = 3.14;")])

    def test_comments_ignored(self):
        ds = semantic_diagnostics("int a; // fake + missing\na = 1;")
        self.assertNotIn("UNDECLARED_IDENTIFIER", [d["code"] for d in ds])

if __name__ == "__main__":
    unittest.main(verbosity=2)

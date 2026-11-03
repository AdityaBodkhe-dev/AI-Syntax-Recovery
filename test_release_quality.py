"""Regression tests for whole-program repair quality (run with python -m unittest test_release_quality -v)."""
import unittest

from app import app
from compiler.parser import validate_source


class ReleaseQualityTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def analyze(self, source):
        response = self.client.post("/analyze", json={"source": source})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_valid_main_void_program_is_not_changed(self):
        source = "int main(void) { int x = 5; return x; }"
        result = self.analyze(source)
        self.assertTrue(validate_source(source))
        self.assertTrue(result["recovery_success"])
        self.assertEqual(result["recovered_source"], source)
        self.assertEqual(result["correction_options"], [])

    def test_missing_semicolon_recovers_whole_program(self):
        source = "int main(void) { int x = 5 return x; }"
        result = self.analyze(source)
        self.assertTrue(result["recovery_success"])
        self.assertTrue(validate_source(result["recovered_source"]))
        self.assertIn("return x;", result["recovered_source"])

    def test_missing_operator_gets_valid_repair(self):
        source = "int main(void) { int a = 2; int b = 3; int c = a b; return c; }"
        result = self.analyze(source)
        self.assertTrue(result["recovery_success"])
        self.assertTrue(validate_source(result["recovered_source"]))
        self.assertIn("a + b", result["recovered_source"])

    def test_malformed_function_call_gets_valid_repair(self):
        source = "int main(void) { int x = 10; int y = 5; int answer; answer = add;(x y); return 0; }"
        result = self.analyze(source)
        self.assertTrue(result["recovery_success"])
        self.assertTrue(validate_source(result["recovered_source"]))
        self.assertIn("add(x, y)", result["recovered_source"])

    def test_every_option_is_full_program_valid_and_changed(self):
        samples = [
            "int main(void) { int x = 5 return x; }",
            "int main(void) { int a = 2; int b = 3; int c = a b; return c; }",
            "int main(void) { int x = 10; int y = 5; int answer; answer = add;(x y); return 0; }",
        ]
        for source in samples:
            with self.subTest(source=source):
                result = self.analyze(source)
                options = result["correction_options"]
                self.assertLessEqual(len(options), 3)
                for option in options:
                    self.assertTrue(option["syntax_valid"])
                    self.assertNotEqual(option["source"], source)
                    self.assertTrue(validate_source(option["source"]))

    def test_destructive_empty_body_is_not_suggested(self):
        source = "int main(void) { int x = 5 return x; }"
        result = self.analyze(source)
        for option in result["correction_options"]:
            self.assertNotEqual(option["source"], "int main(void) {  }")


if __name__ == "__main__":
    unittest.main(verbosity=2)

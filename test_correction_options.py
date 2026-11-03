"""Tests for the up-to-three-proposal recovery API (requires Flask from requirements.txt)."""
import unittest
from app import app


class CorrectionOptionTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_returns_three_distinct_options_for_missing_operand(self):
        response = self.client.post("/analyze", json={
            "source": "int a, b, c;\na = b +\nprint(a);",
            "strategy": "automatic",
        })
        self.assertEqual(response.status_code, 200)
        options = response.get_json()["correction_options"]
        self.assertEqual(len(options), 3)
        self.assertEqual(len({item["source"] for item in options}), 3)
        self.assertTrue(any("a = b + c;" in item["source"] for item in options))
        self.assertTrue(all(isinstance(item["syntax_valid"], bool) for item in options))

    def test_valid_program_has_no_repair_suggestions(self):
        response = self.client.post("/analyze", json={
            "source": "int a;\na = 2;",
            "strategy": "automatic",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["correction_options"], [])
        self.assertEqual(response.get_json()["correction_options_meta"]["returned"], 0)

    def test_suggestions_never_exceed_three_or_include_invalid_repairs(self):
        response = self.client.post("/analyze", json={
            "source": "int a, b, c;\\na = b + ;\\nprint(a);",
            "strategy": "automatic",
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        options = data["correction_options"]
        self.assertLessEqual(len(options), 3)
        self.assertEqual(len({item["source"] for item in options}), len(options))
        self.assertTrue(all(item["syntax_valid"] for item in options))


if __name__ == "__main__":
    unittest.main(verbosity=2)

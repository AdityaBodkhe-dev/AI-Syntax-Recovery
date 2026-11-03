"""Regression tests for the mandatory whole-program recovery validation gate."""
import unittest

from compiler.parser import validate_source

try:
    from app import app
except ModuleNotFoundError:
    app = None


BROKEN_MODEL_OUTPUT = '''#include <stdio.h>

// Global variable
int total = 0;

int add(int a, int b) {
    int result = a + b;
    return result;
}

int main(void) {
    int x = 10;
    int y = 5;
    int answer;

    answer = add;(x y);

    if (answer > 10 ){
        total = answer;
    } else {
        total = 0;
    }

    for (int i = 0; i < 3; i++) {
        total = total + i;
    

    while (x > 0) {
        x = x - 1;
    }

    printf("Total = %d\\n", total);

    return 0;'''


@unittest.skipIf(app is None, "Flask is not installed")
class WholeProgramGateTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_multi_error_program_gets_a_whole_program_valid_repair(self):
        response = self.client.post("/analyze", json={"source": BROKEN_MODEL_OUTPUT})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["recovery_validation"]["passed"])
        self.assertTrue(data["recovered_source_valid"])
        self.assertTrue(data["recovery_success"])
        repaired = data["recovered_source"]
        self.assertTrue(validate_source(repaired))
        self.assertIn("add(x, y)", repaired)
        self.assertIn("for (int i = 0; i < 3; i++)", repaired)
        self.assertIn('printf("Total = %d\\n", total);', repaired)
        self.assertNotIn("add;(x y)", repaired)
        self.assertTrue(all(item["syntax_valid"] for item in data["correction_options"]))

    def test_valid_program_passes_final_gate(self):
        source = "int main() { int a; a = 1; return a; }"
        response = self.client.post("/analyze", json={"source": source})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["recovery_validation"]["passed"])
        self.assertTrue(data["recovered_source_valid"])
        self.assertTrue(data["recovery_success"])
        self.assertTrue(validate_source(data["recovered_source"]))

    def test_every_returned_candidate_passes_complete_program_validation(self):
        source = "int a; a = 1 + ;"
        response = self.client.post("/analyze", json={"source": source})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertLessEqual(len(data["correction_options"]), 3)
        for option in data["correction_options"]:
            self.assertNotEqual(option["source"], source)
            self.assertTrue(option["syntax_valid"])
            self.assertTrue(validate_source(option["source"]))


class GateValidatorSanityTests(unittest.TestCase):
    def test_shown_model_output_is_not_valid_mini_c(self):
        self.assertFalse(validate_source(BROKEN_MODEL_OUTPUT))

    def test_supported_valid_program_passes(self):
        self.assertTrue(validate_source("int main() { int a; a = 1; return a; }"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

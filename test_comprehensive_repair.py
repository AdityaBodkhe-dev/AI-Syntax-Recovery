"""End-to-end regression for a source file containing multiple common syntax errors."""
import unittest
from compiler.parser import validate_source
from app import app

STRESS_SOURCE = r'''#include <stdio.h>

int total = 0;

int add(int a, int b) {
    int result = a + b;
    return result;
}

int main(void) {
    int x = 10
    int y = 5;
    int total = 0;
    int answer;

    answer = add;(x y);

    if (x > 5 {
        total = x + * y;
    }

    while (y > 0) {
        total = total + y
        y = y - 1;
    }

    for (int i = 0; i < 3; i++) {
        total = total + i;
    }

    int result = total + ;
    printf("Total = %d\\n", total);
    return result;
'''

class ComprehensiveRepairTests(unittest.TestCase):
    def test_combined_errors_are_repaired_and_program_is_preserved(self):
        client = app.test_client()
        response = client.post("/analyze", json={"source": STRESS_SOURCE})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["recovery_success"], data["recovery_validation"])
        repaired = data["recovered_source"]
        self.assertTrue(validate_source(repaired))
        self.assertIn("int x = 10;", repaired)
        self.assertIn("add(x, y)", repaired)
        self.assertIn("if (x > 5)", repaired)
        self.assertIn("total = x + y;", repaired)
        self.assertIn("total = total + y;", repaired)
        self.assertIn("int result = total + 0;", repaired)
        self.assertIn("for (int i = 0; i < 3; i++)", repaired)
        self.assertIn("printf(", repaired)
        self.assertTrue(repaired.rstrip().endswith("}"))

if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Regression tests for the consolidated syntax-recovery upgrade."""
import unittest
from compiler.parser import analyze_source, validate_source
try:
    from app import app
except ModuleNotFoundError:
    app = None


class UpgradeTests(unittest.TestCase):
    def test_comma_declarations(self):
        source = 'int a, b, c; a = b + c;'
        result = analyze_source(source)
        self.assertEqual(result['errors'], [])
        self.assertTrue(validate_source(result['recovered_source']))

    def test_function_definition_and_return(self):
        source = 'int main() { int a, b; a = 1; return a; }'
        result = analyze_source(source)
        self.assertEqual(result['errors'], [])
        self.assertTrue(validate_source(result['recovered_source']))

    def test_void_function_parameters(self):
        source = 'void helper(int x, float y) { print(x); return; }'
        result = analyze_source(source)
        self.assertEqual(result['errors'], [])
        self.assertTrue(validate_source(result['recovered_source']))

    def test_declared_operand_preferred(self):
        source = 'int a; int b; a = b + ;'
        result = analyze_source(source, 'automatic')
        self.assertIn('a = b + b;', result['recovered_source'])
        self.assertTrue(result['recovery_success'])

    def test_comma_declared_operand_preferred_before_next_statement(self):
        source = 'int a, b, c;\na = b +\nprint(a);'
        result = analyze_source(source, 'automatic')
        self.assertIn('a = b + c;', result['recovered_source'])
        self.assertIn('print(a);', result['recovered_source'])
        self.assertTrue(validate_source(result['recovered_source']))

    def test_undeclared_identifier_not_reused_as_operand(self):
        source = 'int a; a = unknown + ; print(a);'
        result = analyze_source(source, 'automatic')
        self.assertIn('unknown + 0;', result['recovered_source'])
        self.assertTrue(result['recovery_success'])

    def test_missing_closing_brace(self):
        result = analyze_source('if (a > 0) { print(a);')
        self.assertIn('}', result['recovered_source'])
        self.assertTrue(result['recovery_success'])

    def test_panic_mode_repairs_missing_operand_at_safe_delimiter(self):
        source = 'int a; a = 1 + ; print(a);'
        result = analyze_source(source, 'panic mode')
        self.assertIn('a = 1 + 0;', result['recovered_source'])
        self.assertTrue(result['recovery_success'])
        self.assertIn('print(a);', result['recovered_source'])

    @unittest.skipIf(app is None, 'Flask is not installed in this test environment')
    def test_flask_home_and_analyze_endpoint(self):
        app.config['TESTING'] = True
        client = app.test_client()
        home = client.get('/')
        self.assertEqual(home.status_code, 200)
        response = client.post('/analyze', json={'source': 'int a;', 'strategy': 'automatic'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('recovered_source', data)
        self.assertTrue(data['success'])

    @unittest.skipIf(app is None, 'Flask is not installed in this test environment')
    def test_flask_rejects_non_text_source(self):
        app.config['TESTING'] = True
        response = app.test_client().post('/analyze', json={'source': 123})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)

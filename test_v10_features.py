"""Regression tests for V10 improvements."""
import unittest
try:
    from app import app, build_parse_outline
except ModuleNotFoundError:
    app = None
    build_parse_outline = None
from compiler.parser import analyze_source, validate_source


@unittest.skipIf(app is None, "Flask is not installed")
class V10FeatureTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_analyze_returns_line_diff_and_outline(self):
        response = self.client.post('/analyze', json={'source': 'int a\na = 2;', 'strategy': 'automatic'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('source_diff', data)
        self.assertIn('parse_outline', data)
        self.assertIsInstance(data['parse_outline']['statements'], list)

    def test_outline_identifies_basic_constructs(self):
        outline = build_parse_outline('int main() {\n int a;\n a = 1;\n return a;\n}')
        self.assertIn('main', outline['functions'])
        self.assertTrue(any(row['kind'] == 'return statement' for row in outline['statements']))

    def test_benchmark_endpoint_reports_fixed_cases(self):
        response = self.client.get('/benchmark')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total'], 8)
        self.assertEqual(data['failed'], 0)

    def test_multiple_errors_are_reported_without_crashing(self):
        result = analyze_source('int a\na = 1 + ;\nif (a > 0) { print(a);', 'automatic')
        self.assertIsInstance(result['errors'], list)
        self.assertTrue(result['errors'] or result['lexical_errors'])
        self.assertIsInstance(result['recovered_source'], str)

    def test_valid_source_has_no_suggestions(self):
        response = self.client.post('/analyze', json={'source': 'int a; a = 1;', 'strategy': 'automatic'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['correction_options'], [])

    def test_candidate_explanations_and_scores_are_present(self):
        response = self.client.post('/analyze', json={'source': 'int a; a = 1 + ;', 'strategy': 'automatic'})
        self.assertEqual(response.status_code, 200)
        for item in response.get_json()['correction_options']:
            self.assertIn('rank_score', item)
            self.assertIn('ranking_notes', item)
            self.assertTrue(item['syntax_valid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

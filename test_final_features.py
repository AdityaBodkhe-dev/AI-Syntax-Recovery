import unittest
from app import app
from correction_engine import semantic_diagnostics, rank_candidates

class FinalFeatureTests(unittest.TestCase):
    def setUp(self): self.client=app.test_client()
    def test_three_distinct_contextual_options_and_rank_metadata(self):
        response=self.client.post('/analyze',json={'source':'int a, b, c;\na = b +\nprint(a);','strategy':'automatic'})
        self.assertEqual(response.status_code,200)
        data=response.get_json(); opts=data['correction_options']
        self.assertEqual(len(opts),3)
        self.assertEqual(len(set(o['source'] for o in opts)),3)
        self.assertTrue(any('a = b + c;' in o['source'] for o in opts))
        self.assertTrue(all('rank_score' in o and 'feature_summary' in o for o in opts))
    def test_ranker_artifact_reported(self):
        data=self.client.post('/analyze',json={'source':'int a; a = 2;'}).get_json()
        self.assertIn('model_info',data); self.assertTrue(data['model_info']['artifact'])
    def test_undeclared_identifier_warning(self):
        diagnostics=semantic_diagnostics('int a;\na = missing + 1;')
        self.assertTrue(any(d['code']=='UNDECLARED_IDENTIFIER' and d['identifier']=='missing' for d in diagnostics))
    def test_valid_simple_program_no_undeclared_warning(self):
        diagnostics=semantic_diagnostics('int a, b;\na = b + 1; print(a);')
        self.assertFalse(any(d['code']=='UNDECLARED_IDENTIFIER' for d in diagnostics))
    def test_duplicate_names_in_declaration(self):
        diagnostics=semantic_diagnostics('int a, a;')
        self.assertTrue(any(d['code']=='DUPLICATE_DECLARATION' for d in diagnostics))

    def test_self_assignment_warning(self):
        diagnostics=semantic_diagnostics('int a; a = a;')
        self.assertTrue(any(d['code']=='SELF_ASSIGNMENT' for d in diagnostics))

    def test_unused_declaration_information(self):
        diagnostics=semantic_diagnostics('int unused;')
        self.assertTrue(any(d['code']=='DECLARED_BUT_UNUSED' for d in diagnostics))

    def test_ranker_exposes_extended_features(self):
        options=[{'label':'Use declared variable c','source':'int a,b,c; a = b + c;','syntax_valid':True}]
        ranked=rank_candidates(options,'int a,b,c; a = b + ;')
        expected={'balanced_delimiters','local_token_edit','uses_declared_operand','has_semicolon_coverage'}
        self.assertTrue(expected.issubset(ranked[0]['feature_summary']))

    def test_ranker_prefers_unused_declared_operand_over_fallback(self):
        options=[
            {'label':'Use declared variable c','source':'int a, b, c;\na = b + c;\nprint(a);','syntax_valid':True},
            {'label':'Use numeric fallback 0','source':'int a, b, c;\na = b + 0;\nprint(a);','syntax_valid':True},
        ]
        ranked=rank_candidates(options,'int a, b, c;\na = b + ;\nprint(a);')
        self.assertEqual(ranked[0]['label'], 'Use declared variable c')
        self.assertIn('uses a declared identifier not already in the expression', ranked[0]['ranking_notes'])

    def test_type_mismatch_warning_for_decimal_to_int(self):
        diagnostics=semantic_diagnostics('int a; a = 3.14;')
        self.assertTrue(any(d['code']=='POSSIBLE_TYPE_MISMATCH' for d in diagnostics))

    def test_void_variable_assignment_warning(self):
        diagnostics=semantic_diagnostics('void item; item = 2;')
        self.assertTrue(any(d['code']=='INVALID_VOID_ASSIGNMENT' for d in diagnostics))

    def test_comments_do_not_create_undeclared_warnings(self):
        diagnostics=semantic_diagnostics('int a; // missing + other\na = 1;')
        self.assertFalse(any(d['code']=='UNDECLARED_IDENTIFIER' for d in diagnostics))

    def test_model_metadata_comes_from_artifact(self):
        data=self.client.post('/analyze',json={'source':'int a; a = 2;'}).get_json()
        self.assertEqual(data['model_info']['version'], 4)
        self.assertGreater(data['model_info']['training_examples'], 0)

if __name__=='__main__': unittest.main(verbosity=2)

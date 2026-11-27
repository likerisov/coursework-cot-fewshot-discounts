import unittest
from src.run_experiments import parse_response


class ResponseParsingTests(unittest.TestCase):
    def test_parse_json_object(self):
        value, method = parse_response('{"discount_pct": 22, "reasoning_summary": "ok"}')
        self.assertEqual(value, 22)
        self.assertEqual(method, "json")

    def test_parse_json_embedded_in_fenced_text(self):
        value, method = parse_response('```json\n{"discount_pct": 17}\n```')
        self.assertEqual(value, 17)
        self.assertEqual(method, "regex")

    def test_parse_recommendation_text(self):
        value, method = parse_response('Итоговая рекомендация: скидка 25%.')
        self.assertEqual(value, 25)
        self.assertEqual(method, "regex")

    def test_reject_out_of_range(self):
        value, method = parse_response('{"discount_pct": 120}')
        self.assertIsNone(value)
        self.assertEqual(method, "not_parsed")


if __name__ == "__main__":
    unittest.main()

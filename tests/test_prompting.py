import unittest
from src.prompting import render_prompt


class PromptRenderingTests(unittest.TestCase):
    def test_known_placeholders_replaced_json_braces_preserved(self):
        template = 'Category={category}; stock={stock_quantity}; output={"discount_pct": 0}'
        product = {
            "category": "Игрушки", "stock_quantity": 300, "days_in_stock": 200,
            "current_price": 500, "cost_price": 250, "last_month_sales": 3,
        }
        rendered = render_prompt(template, product)
        self.assertIn('Category=Игрушки; stock=300', rendered)
        self.assertIn('{"discount_pct": 0}', rendered)

    def test_missing_field_rejected(self):
        with self.assertRaises(ValueError):
            render_prompt("{category}", {"category": "Книги"})


if __name__ == "__main__":
    unittest.main()

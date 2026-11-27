import math
import tempfile
import unittest
from pathlib import Path

from src.analysis import Product, evaluate_discount, load_products, product_metrics, safe_discount_ceiling_pct

ROOT = Path(__file__).resolve().parents[1]


class ProductMathTests(unittest.TestCase):
    def setUp(self):
        self.product = Product(1, "Электроника", 50, 120, 5000, 3000, 2)

    def test_break_even_discount(self):
        self.assertAlmostEqual(safe_discount_ceiling_pct(self.product), 40.0)

    def test_discount_20_percent(self):
        result = evaluate_discount(self.product, 20)
        self.assertEqual(result["new_price"], 4000)
        self.assertEqual(result["unit_profit"], 1000)
        self.assertEqual(result["margin_on_sale_price_pct"], 25.0)
        self.assertTrue(result["covers_purchase_cost"])

    def test_discount_over_break_even_is_flagged(self):
        result = evaluate_discount(self.product, 45)
        self.assertEqual(result["new_price"], 2750)
        self.assertEqual(result["unit_profit"], -250)
        self.assertFalse(result["covers_purchase_cost"])

    def test_zero_sales_cover(self):
        zero_sales = Product(3, "Косметика", 100, 180, 800, 400, 0)
        self.assertEqual(product_metrics(zero_sales)["stock_cover_months"], "infinite")

    def test_bad_discount_rejected(self):
        for value in (-1, 101, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    evaluate_discount(self.product, value)

    def test_csv_has_eight_unique_products(self):
        products = load_products(ROOT / "data" / "slow_moving.csv")
        self.assertEqual(len(products), 8)
        self.assertEqual(len({p.product_id for p in products}), 8)

    def test_invalid_product_rejected(self):
        with self.assertRaises(ValueError):
            Product(0, "", -1, -2, 0, -1, -3).validate()


if __name__ == "__main__":
    unittest.main()

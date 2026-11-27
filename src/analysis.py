"""Deterministic unit-economics calculations for slow-moving inventory.

This module does not generate an LLM recommendation. It calculates transparent
financial guardrails against which generated recommendations can be checked.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Product:
    product_id: int
    category: str
    stock_quantity: int
    days_in_stock: int
    current_price: float
    cost_price: float
    last_month_sales: int

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Product":
        try:
            product = cls(
                product_id=int(row["product_id"]),
                category=row["category"].strip(),
                stock_quantity=int(row["stock_quantity"]),
                days_in_stock=int(row["days_in_stock"]),
                current_price=float(row["current_price"]),
                cost_price=float(row["cost_price"]),
                last_month_sales=int(row["last_month_sales"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid product row: {row!r}") from exc
        product.validate()
        return product

    def validate(self) -> None:
        if self.product_id <= 0:
            raise ValueError("product_id must be positive")
        if not self.category:
            raise ValueError("category must not be empty")
        if self.stock_quantity < 0 or self.days_in_stock < 0 or self.last_month_sales < 0:
            raise ValueError("stock, age and sales cannot be negative")
        if self.current_price <= 0 or self.cost_price < 0:
            raise ValueError("current_price must be positive and cost_price non-negative")


def load_products(path: str | Path) -> list[Product]:
    """Load and validate products from the coursework CSV file."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "product_id", "category", "stock_quantity", "days_in_stock",
            "current_price", "cost_price", "last_month_sales",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
        products = [Product.from_row(row) for row in reader]
    if not products:
        raise ValueError("Dataset is empty")
    ids = [p.product_id for p in products]
    if len(ids) != len(set(ids)):
        raise ValueError("product_id values must be unique")
    return products


def safe_discount_ceiling_pct(product: Product) -> float:
    """Maximum discount that keeps discounted price at or above unit cost.

    This is a break-even boundary before logistics, taxes, marketplace fees,
    storage costs and other operating expenses. It is not a recommended discount.
    """
    return max(0.0, min(100.0, (product.current_price - product.cost_price) / product.current_price * 100.0))


def evaluate_discount(product: Product, discount_pct: float) -> dict[str, float | bool]:
    """Calculate price/profit metrics and the simple purchase-cost safety flag."""
    if not math.isfinite(discount_pct) or not 0 <= discount_pct <= 100:
        raise ValueError("discount_pct must be between 0 and 100")
    new_price = product.current_price * (1.0 - discount_pct / 100.0)
    unit_profit = new_price - product.cost_price
    margin_on_sale_price = (unit_profit / new_price * 100.0) if new_price > 0 else -100.0
    return {
        "discount_pct": discount_pct,
        "new_price": round(new_price, 2),
        "unit_profit": round(unit_profit, 2),
        "margin_on_sale_price_pct": round(margin_on_sale_price, 2),
        "inventory_value_at_cost": round(product.stock_quantity * product.cost_price, 2),
        "projected_gross_profit_if_all_stock_sold": round(product.stock_quantity * unit_profit, 2),
        "covers_purchase_cost": new_price >= product.cost_price,
    }


def product_metrics(product: Product) -> dict[str, object]:
    """Produce transparent inventory and unit-economics metrics."""
    cover_months = (
        math.inf if product.last_month_sales == 0
        else product.stock_quantity / product.last_month_sales
    )
    gross_margin_pct = (product.current_price - product.cost_price) / product.current_price * 100.0
    return {
        "product_id": product.product_id,
        "category": product.category,
        "stock_quantity": product.stock_quantity,
        "days_in_stock": product.days_in_stock,
        "current_price": round(product.current_price, 2),
        "cost_price": round(product.cost_price, 2),
        "last_month_sales": product.last_month_sales,
        "stock_cover_months": "infinite" if math.isinf(cover_months) else round(cover_months, 2),
        "inventory_value_at_cost": round(product.stock_quantity * product.cost_price, 2),
        "gross_profit_at_current_price_per_unit": round(product.current_price - product.cost_price, 2),
        "gross_margin_on_current_price_pct": round(gross_margin_pct, 2),
        "break_even_discount_ceiling_pct": round(safe_discount_ceiling_pct(product), 2),
        # Operational costs are not in the dataset, so this is deliberately not
        # called net profit or a guaranteed safe discount.
        "age_or_cover_risk_flag": product.days_in_stock >= 90 or cover_months >= 6 or product.last_month_sales == 0,
    }


def portfolio_summary(products: Iterable[Product]) -> dict[str, object]:
    items = list(products)
    cost_locked = sum(p.stock_quantity * p.cost_price for p in items)
    no_sales = sum(p.last_month_sales == 0 for p in items)
    high_risk = sum(bool(product_metrics(p)["age_or_cover_risk_flag"]) for p in items)
    return {
        "product_count": len(items),
        "units_in_stock": sum(p.stock_quantity for p in items),
        "inventory_value_at_cost": round(cost_locked, 2),
        "products_with_zero_sales_last_month": no_sales,
        "products_flagged_by_age_or_stock_cover_rule": high_risk,
    }

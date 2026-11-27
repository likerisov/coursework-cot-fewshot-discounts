"""Prompt loading and safe placeholder substitution."""
from pathlib import Path

FIELDS = (
    "category", "stock_quantity", "days_in_stock", "current_price",
    "cost_price", "last_month_sales",
)


def render_prompt(template: str, product: dict[str, object]) -> str:
    """Replace only known {field} placeholders, preserving JSON braces."""
    missing = [field for field in FIELDS if field not in product]
    if missing:
        raise ValueError(f"Missing product fields: {', '.join(missing)}")
    rendered = template
    for field in FIELDS:
        rendered = rendered.replace("{" + field + "}", str(product[field]))
    unresolved = ["{" + field + "}" for field in FIELDS if "{" + field + "}" in rendered]
    if unresolved:
        raise ValueError(f"Unresolved placeholders: {unresolved}")
    return rendered


def load_prompt(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Prompt file is empty: {path}")
    return text

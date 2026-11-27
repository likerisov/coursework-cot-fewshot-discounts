"""Generate deterministic portfolio-analysis CSV and Markdown files."""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

try:
    from .analysis import load_products, product_metrics, portfolio_summary
except ImportError:  # Running as `python src/analyze_portfolio.py`
    from analysis import load_products, product_metrics, portfolio_summary

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "slow_moving.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()

    products = load_products(args.data)
    rows = [product_metrics(p) for p in products]
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "portfolio_analysis.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = portfolio_summary(products)
    md_path = args.out / "portfolio_analysis.md"
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# Анализ товарного портфеля\n\n")
        handle.write("> Это детерминированные расчёты по учебному CSV, а не ответы языковой модели и не реальные продажи магазина.\n\n")
        handle.write("## Сводка\n\n")
        for key, value in summary.items():
            handle.write(f"- **{key}:** {value}\n")
        handle.write("\n## Показатели по товарам\n\n")
        handle.write("| ID | Категория | Остаток | Дней на складе | Продаж/мес. | Покрытие, мес. | Стоимость остатка, руб. | Валовая маржа, % | Предельная скидка до закупки, % | Риск по возрасту/покрытию |\n")
        handle.write("|---:|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for r in rows:
            handle.write(
                f"| {r['product_id']} | {r['category']} | {r['stock_quantity']} | {r['days_in_stock']} | {r['last_month_sales']} | "
                f"{r['stock_cover_months']} | {r['inventory_value_at_cost']:.2f} | {r['gross_margin_on_current_price_pct']:.2f} | "
                f"{r['break_even_discount_ceiling_pct']:.2f} | {'да' if r['age_or_cover_risk_flag'] else 'нет'} |\n"
            )
        handle.write("\n## Интерпретация и ограничения\n\n")
        handle.write("Покрытие запасов рассчитано как текущий остаток, делённый на продажи за последний месяц. При нулевых продажах покрытие обозначено как бесконечное. Предельная скидка рассчитана по формуле (текущая цена − закупочная цена) / текущая цена × 100% и означает только точку безубыточности относительно закупочной стоимости. Она не учитывает логистику, налоги, комиссии, хранение и операционные расходы. Поэтому показатель нельзя трактовать как гарантированно безопасную скидку или готовую рекомендацию.\n\n")
        handle.write("Флаг риска включается, если товар хранится не менее 90 дней, покрытие запасов составляет не менее 6 месяцев или за последний месяц не было продаж. Это условная исследовательская эвристика, а не универсальный отраслевой норматив.\n")

    print(f"Созданы файлы: {csv_path} и {md_path}")
    print(f"Сводка: {summary}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""Evaluate recorded LLM outputs against simple purchase-cost constraints."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

try:
    from .analysis import load_products, evaluate_discount, safe_discount_ceiling_pct
except ImportError:
    from analysis import load_products, evaluate_discount, safe_discount_ceiling_pct

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=ROOT / "results" / "llm_runs.jsonl")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "slow_moving.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    if not args.runs.exists():
        parser.error(f"Run log does not exist: {args.runs}")

    products = {p.product_id: p for p in load_products(args.data)}
    details: list[dict[str, object]] = []
    with args.runs.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
            if item.get("status") != "ok" or item.get("discount_pct") is None:
                details.append({
                    "product_id": item.get("product_id"), "approach": item.get("approach"),
                    "repetition": item.get("repetition"), "status": item.get("status"),
                    "discount_pct": "", "break_even_discount_ceiling_pct": "",
                    "unit_profit": "", "margin_on_sale_price_pct": "", "purchase_cost_safe": False,
                    "latency_seconds": item.get("latency_seconds", ""),
                    "error": item.get("error") or item.get("parse_method", ""),
                })
                continue
            product_id = int(item["product_id"])
            if product_id not in products:
                raise ValueError(f"Unknown product_id {product_id} in run log")
            discount = float(item["discount_pct"])
            metrics = evaluate_discount(products[product_id], discount)
            details.append({
                "product_id": product_id, "approach": item.get("approach"),
                "repetition": item.get("repetition"), "status": "ok",
                "discount_pct": discount,
                "break_even_discount_ceiling_pct": round(safe_discount_ceiling_pct(products[product_id]), 2),
                "new_price": metrics["new_price"], "unit_profit": metrics["unit_profit"],
                "margin_on_sale_price_pct": metrics["margin_on_sale_price_pct"],
                "purchase_cost_safe": metrics["covers_purchase_cost"],
                "latency_seconds": item.get("latency_seconds", ""), "error": "",
            })

    if not details:
        parser.error("The run log contains no records")

    args.out.mkdir(parents=True, exist_ok=True)
    detail_path = args.out / "llm_evaluation.csv"
    columns = list(dict.fromkeys(k for row in details for k in row.keys()))
    with detail_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(details)

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in details:
        if row.get("status") == "ok":
            groups[str(row["approach"])].append(row)
    summary_rows = []
    for approach in ("zero_shot", "few_shot", "cot", "few_shot_cot"):
        rows = groups.get(approach, [])
        summary_rows.append({
            "approach": approach,
            "valid_outputs": len(rows),
            "mean_discount_pct": round(sum(float(r["discount_pct"]) for r in rows) / len(rows), 2) if rows else "",
            "purchase_cost_safe_share_pct": round(sum(bool(r["purchase_cost_safe"]) for r in rows) / len(rows) * 100, 2) if rows else "",
            "mean_unit_profit": round(sum(float(r["unit_profit"]) for r in rows) / len(rows), 2) if rows else "",
            "mean_latency_seconds": round(sum(float(r["latency_seconds"] or 0) for r in rows) / len(rows), 3) if rows else "",
        })
    summary_path = args.out / "llm_evaluation_summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    md_path = args.out / "llm_evaluation.md"
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# Оценка запусков LLM\n\n")
        handle.write("> Таблица строится только по фактически записанным ответам из `llm_runs.jsonl`. Пустые или ошибочные ответы не засчитываются как успешные.\n\n")
        handle.write("| Подход | Валидных ответов | Средняя скидка, % | Ответы без ухода ниже закупки, % | Средняя валовая прибыль/шт., руб. | Среднее время, с |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for r in summary_rows:
            handle.write("| " + " | ".join(str(r[k]) for k in r) + " |\n")
        handle.write("\nОграничение: проверка `purchase_cost_safe` сравнивает цену после скидки только с закупочной стоимостью. Она не учитывает прочие издержки и не доказывает, что выбранная скидка увеличит продажи. Для вывода о влиянии на спрос нужны фактические данные о продажах до и после изменения цены.\n")

    print(f"Созданы: {detail_path}, {summary_path}, {md_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

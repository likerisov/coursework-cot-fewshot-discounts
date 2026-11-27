"""Run the four prompt variants against an OpenAI-compatible chat-completions API.

The script requires user-supplied credentials in environment variables or a local
.env file. It never writes secrets to the repository or to experiment logs.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from .analysis import load_products
    from .prompting import load_prompt, render_prompt
except ImportError:
    from analysis import load_products
    from prompting import load_prompt, render_prompt

ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILES = {
    "zero_shot": ROOT / "prompts" / "v2_zero_shot.txt",
    "few_shot": ROOT / "prompts" / "v2_few_shot.txt",
    "cot": ROOT / "prompts" / "v2_cot.txt",
    "few_shot_cot": ROOT / "prompts" / "v2_few_shot_cot.txt",
}


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def parse_response(text: str) -> tuple[float | None, str]:
    """Extract discount_pct from JSON, with a conservative prose fallback."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "discount_pct" in obj:
            value = float(obj["discount_pct"])
            if 0 <= value <= 100:
                return value, "json"
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    patterns = [
        r'"discount_pct"\s*:\s*(\d+(?:\.\d+)?)',
        r"(?:итоговая\s+)?рекомендованн\w*\s+скидк\w*\s*[:—-]?\s*(\d+(?:\.\d+)?)\s*%",
        r"скидк\w*\s+(\d+(?:\.\d+)?)\s*%",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            value = float(matches[-1])
            if 0 <= value <= 100:
                return value, "regex"
    return None, "not_parsed"


def call_api(base_url: str, api_key: str, model: str, prompt: str, timeout: int) -> tuple[str, float, str | None]:
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 700,
    }
    request = Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    last_error = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
            return str(content), round(time.perf_counter() - started, 3), None
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:1500]
            last_error = f"HTTP {exc.code}: {body_text}"
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                break
        except (URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == 3:
                break
        time.sleep((2 ** attempt) + random.random() * 0.25)
    return "", round(time.perf_counter() - started, 3), last_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Limit products (0 = all)")
    parser.add_argument("--repeat", type=int, default=1, help="Runs per product/prompt; use 3 for a more stable comparison")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--dry-run", action="store_true", help="Render prompts without calling a model")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "llm_runs.jsonl")
    args = parser.parse_args()

    if args.repeat < 1 or args.limit < 0:
        parser.error("--repeat must be >= 1 and --limit must be >= 0")

    load_dotenv()
    products = load_products(ROOT / "data" / "slow_moving.csv")
    if args.limit:
        products = products[:args.limit]
    prompts = {key: load_prompt(path) for key, path in PROMPT_FILES.items()}

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "")
    if not args.dry_run and (not api_key or not model):
        print("Не заданы LLM_API_KEY и/или LLM_MODEL. Создайте локальный .env по образцу .env.example.", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    total = len(products) * len(prompts) * args.repeat
    print(f"План: {len(products)} товаров × {len(prompts)} подхода × {args.repeat} повтор(а) = {total} запросов")
    provider_host = urlparse(base_url).netloc or "not_set"

    with args.output.open("a", encoding="utf-8") as handle:
        counter = 0
        for product in products:
            row = {
                "product_id": product.product_id,
                "category": product.category,
                "stock_quantity": product.stock_quantity,
                "days_in_stock": product.days_in_stock,
                "current_price": product.current_price,
                "cost_price": product.cost_price,
                "last_month_sales": product.last_month_sales,
            }
            for approach, template in prompts.items():
                rendered = render_prompt(template, row)
                for repetition in range(1, args.repeat + 1):
                    counter += 1
                    record = {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "product_id": product.product_id,
                        "category": product.category,
                        "approach": approach,
                        "prompt_version": "v2",
                        "repetition": repetition,
                        "model": model or None,
                        "provider_host": provider_host if not args.dry_run else None,
                    }
                    if args.dry_run:
                        record.update({"status": "dry_run", "rendered_prompt": rendered})
                    else:
                        raw, latency, error = call_api(base_url, api_key, model, rendered, args.timeout)
                        discount, parse_method = parse_response(raw) if raw else (None, "no_response")
                        record.update({
                            "status": "ok" if raw and not error else "error",
                            "latency_seconds": latency,
                            "raw_response": raw,
                            "discount_pct": discount,
                            "parse_method": parse_method,
                            "error": error,
                        })
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                    print(f"[{counter}/{total}] {product.product_id} / {approach} / run {repetition}: {record['status']}")
    print(f"Журнал сохранён: {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

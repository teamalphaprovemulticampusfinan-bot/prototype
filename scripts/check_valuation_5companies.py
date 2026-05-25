from __future__ import annotations

import argparse
import json
from pathlib import Path


COMPANIES = [
    ("nepes", "네패스"),
    ("hanmi", "한미반도체"),
    ("hansol", "한솔케미칼"),
    ("duksan", "덕산테코피아"),
    ("ltc", "엘티씨"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check valuation output status for 5 companies.")
    parser.add_argument("--field", default="반도체")
    args = parser.parse_args()

    base = Path("data") / args.field
    print("[Valuation 5개 기업 PASS 체크]")
    print("-" * 110)
    print(f"{'slug':<10} {'company':<12} {'status':<18} {'wacc':>10} {'implied_price':>15} {'price_rows':>12} {'market_cap':>18}")
    print("-" * 110)
    ok = True
    for slug, company in COMPANIES:
        folder = "엘티씨" if slug == "ltc" else company
        val_dir = base / folder / "valuation"
        metrics_path = val_dir / f"{slug}_valuation_metrics.json"
        validation_path = val_dir / f"{slug}_valuation_validation.json"
        if not metrics_path.exists() or not validation_path.exists():
            ok = False
            print(f"{slug:<10} {company:<12} {'MISSING_OUTPUT':<18}")
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
        validation = json.loads(validation_path.read_text(encoding="utf-8-sig"))
        status = validation.get("status")
        if status != "PASS":
            ok = False
        wacc = (metrics.get("wacc") or {}).get("wacc") or metrics.get("wacc")
        dcf = metrics.get("dcf") or {}
        price = metrics.get("price_summary") or {}
        implied = dcf.get("implied_price") or metrics.get("implied_price")
        rows = price.get("price_rows") or metrics.get("price_rows")
        market_cap = price.get("market_cap") or metrics.get("market_cap")

        def fmt(x, digits=2):
            try:
                return f"{float(x):,.{digits}f}"
            except Exception:
                return "확인 제한"

        print(
            f"{slug:<10} {company:<12} {str(status):<18} "
            f"{fmt(wacc,4):>10} {fmt(implied,0):>15} {fmt(rows,0):>12} {fmt(market_cap,0):>18}"
        )
    print("-" * 110)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

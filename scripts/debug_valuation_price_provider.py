from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.valuation_intake.sources import (
    resolve_company,
    fetch_price_history,
    enrich_price_history,
    compute_price_summary,
    fetch_dart_share_counts,
    latest_share_count,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug Valuation Agent independent price providers.")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--years", type=int, default=5)
    args = parser.parse_args()

    diagnostics: list[str] = []
    company = resolve_company(args.company_dir, args.company)
    rows = enrich_price_history(fetch_price_history(company, args.years, diagnostics))
    share_rows = fetch_dart_share_counts(company, years=args.years, diagnostics=diagnostics)
    share_summary = latest_share_count(share_rows)
    summary = compute_price_summary(rows, share_summary.get("shares_outstanding"))
    print(json.dumps({
        "company": company.name,
        "company_dir": company.slug,
        "stock_code": company.stock_code,
        "yf_ticker": company.yf_ticker,
        "rows": len(rows),
        "summary": summary,
        "share_summary": share_summary,
        "share_rows": len(share_rows),
        "diagnostics": diagnostics,
        "head": rows[:3],
        "tail": rows[-3:],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

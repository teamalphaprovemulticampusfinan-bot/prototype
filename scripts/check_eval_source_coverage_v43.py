from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from evaluation.source_materializer import materialize_eval_sources, read_universe_rows


def _exists(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "rows": 0}
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        return {"exists": True, "rows": len(df), "cols": list(df.columns[:20])}
    except Exception as e:
        return {"exists": True, "rows": None, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--company", default=None)
    ap.add_argument("--materialize", action="store_true")
    ns = ap.parse_args()
    root = Path.cwd().resolve()
    rows = read_universe_rows(ns.universe_csv)
    if ns.company:
        rows = [r for r in rows if ns.company in str(r.get("company") or "") or ns.company.lower() in str(r.get("company_dir") or "").lower() or ns.company in str(r.get("ticker") or "")]
    if ns.materialize:
        materialize_eval_sources(root, ns.field, rows, ns.start, ns.end, ns.frequency)
    report = {"companies": []}
    for r in rows:
        company = str(r.get("company") or "")
        cdir = root / "data" / ns.field / company
        if not cdir.exists():
            cdir = root / "data" / ns.field / str(r.get("company_dir") or "")
        report["companies"].append({
            "company": company,
            "ticker": r.get("ticker"),
            "finance_daily": _exists(cdir / "finance" / "eval_finance_daily_v43.csv"),
            "valuation_price": _exists(cdir / "valuation" / "intake" / "eval_price_history_v43.csv"),
        })
    report["common"] = {
        "issue_daily": _exists(root / "data" / ns.field / "_sector_common" / "issue" / "issue_events_daily.csv"),
        "macro_external_daily": _exists(root / "data" / "_global_common" / "macro" / "macro_external_daily_v43.csv"),
        "market_external_daily": _exists(root / "data" / ns.field / "_sector_common" / "market" / "market_external_daily_v43.csv"),
        "tech_patent_monthly": _exists(root / "data" / ns.field / "_sector_common" / "tech" / "monthly" / "tech_patent_quality_monthly.csv"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

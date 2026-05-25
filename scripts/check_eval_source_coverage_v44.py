from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from evaluation.source_materializer import _read_table, read_universe_rows


def _exists(path: Path) -> dict[str, Any]:
    df = _read_table(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "rows": int(len(df)) if not df.empty else 0,
        "cols": list(map(str, df.columns)) if not df.empty else [],
    }


def _company_match(row: dict[str, Any], company: str) -> bool:
    vals = [str(v) for v in row.values() if v is not None]
    return any(company in v for v in vals)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check src_eval actual source coverage after v44 materialization.")
    ap.add_argument("--field", required=True)
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--company", default="")
    ap.add_argument("--limit", type=int, default=None)
    ns = ap.parse_args()

    root = Path.cwd()
    rows = read_universe_rows(ns.universe_csv, limit=ns.limit)
    if ns.company:
        rows = [r for r in rows if _company_match(r, ns.company)]
    companies = []
    for r in rows:
        company = str(r.get("company") or "")
        cdir_name = str(r.get("company_dir") or company)
        cdir = root / "data" / ns.field / company
        if not cdir.exists():
            alt = root / "data" / ns.field / cdir_name
            cdir = alt if alt.exists() else cdir
        companies.append({
            "company": company,
            "ticker": str(r.get("ticker") or ""),
            "finance_daily_v43": _exists(cdir / "finance" / "eval_finance_daily_v43.csv"),
            "finance_daily_v44": _exists(cdir / "finance" / "eval_finance_daily_v44.csv"),
            "valuation_price_v43": _exists(cdir / "valuation" / "intake" / "eval_price_history_v43.csv"),
            "valuation_price_v44": _exists(cdir / "valuation" / "intake" / "eval_price_history_v44.csv"),
        })

    common = {
        "issue_daily": _exists(root / "data" / ns.field / "_sector_common" / "issue" / "issue_events_daily.csv"),
        "issue_daily_v44": _exists(root / "data" / ns.field / "_sector_common" / "issue" / "issue_events_daily_v44.csv"),
        "issue_monthly": _exists(root / "data" / ns.field / "_sector_common" / "issue" / "issue_events_monthly.csv"),
        "macro_external_daily_v43": _exists(root / "data" / "_global_common" / "macro" / "macro_external_daily_v43.csv"),
        "macro_external_daily_v44": _exists(root / "data" / "_global_common" / "macro" / "macro_external_daily_v44.csv"),
        "market_external_daily_v43": _exists(root / "data" / ns.field / "_sector_common" / "market" / "market_external_daily_v43.csv"),
        "market_external_daily_v44": _exists(root / "data" / ns.field / "_sector_common" / "market" / "market_external_daily_v44.csv"),
        "tech_patent_monthly": _exists(root / "data" / ns.field / "_sector_common" / "tech" / "monthly" / "tech_patent_quality_monthly.csv"),
        "tech_patent_monthly_v44": _exists(root / "data" / ns.field / "_sector_common" / "tech" / "monthly" / "tech_patent_quality_monthly_v44.csv"),
    }

    # Lightweight diagnostics so failures are visible before running full backtest.
    diagnostics: dict[str, Any] = {}
    issue = _read_table(root / "data" / ns.field / "_sector_common" / "issue" / "issue_events_daily.csv")
    if not issue.empty:
        diagnostics["issue_rows_by_company_top10"] = issue.get("company", pd.Series(dtype=str)).value_counts().head(10).to_dict()
        diagnostics["issue_date_minmax"] = [str(issue.get("published_at", issue.get("date", pd.Series(dtype=str))).min()), str(issue.get("published_at", issue.get("date", pd.Series(dtype=str))).max())]
    tech = _read_table(root / "data" / ns.field / "_sector_common" / "tech" / "monthly" / "tech_patent_quality_monthly.csv")
    if not tech.empty:
        diagnostics["tech_months"] = int(pd.to_datetime(tech.get("date"), errors="coerce").dt.to_period("M").nunique())
        diagnostics["tech_rows_by_company_top10"] = tech.get("company", pd.Series(dtype=str)).value_counts().head(10).to_dict()

    print(json.dumps({"companies": companies, "common": common, "diagnostics": diagnostics}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

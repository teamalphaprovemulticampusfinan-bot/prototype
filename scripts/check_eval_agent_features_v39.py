from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def _ensure_path() -> None:
    import sys
    for p in [ROOT / "src_eval", ROOT / "src"]:
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


def _find_target(universe: str, company: str | None, limit: int | None = None) -> list[dict[str, Any]]:
    from evaluation.utils import read_universe
    rows = read_universe(universe, limit=limit)
    if not company:
        return rows
    out = []
    for r in rows:
        hay = " ".join(str(r.get(k, "")) for k in ["company", "company_dir", "ticker", "stock_code"])
        if company.lower() in hay.lower():
            out.append(r)
    if not out:
        raise SystemExit(f"company not found in universe: {company}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check src_eval feature signals for all six agents at one as_of date.")
    ap.add_argument("--field", required=True)
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--company", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ns = ap.parse_args()
    _ensure_path()
    os.environ["ALPHAPROVE_EVAL_AS_OF_DATE"] = ns.as_of
    os.environ["ALPHAPROVE_DATA_CUTOFF_DATE"] = ns.as_of
    for k in ["FINANCE", "VALUATION", "TECH", "MARKET", "ISSUE", "MACRO"]:
        os.environ[f"{k}_AS_OF_DATE"] = ns.as_of
        os.environ[f"{k}_END_DATE"] = ns.as_of
    as_of = pd.Timestamp(ns.as_of)

    from evaluation.features_finance import build_finance_signal
    from evaluation.features_market import build_market_signal
    from evaluation.features_valuation import build_valuation_features
    from evaluation.features_tech import build_tech_signal
    from evaluation.features_issue import build_issue_signal
    from evaluation.features_macro import build_macro_signal

    targets = _find_target(ns.universe_csv, ns.company, ns.limit)
    rows = []
    for target in targets:
        funcs = {
            "finance": build_finance_signal,
            "market": build_market_signal,
            "valuation": build_valuation_features,
            "tech": build_tech_signal,
            "issue": build_issue_signal,
            "macro": build_macro_signal,
        }
        for agent, fn in funcs.items():
            try:
                res = fn(ROOT, ns.field, target, as_of)
            except Exception as e:
                res = {"signal": 0.0, "status": f"ERROR: {e}", "source": ""}
            rows.append({
                "company": target.get("company", ""),
                "ticker": target.get("ticker", ""),
                "agent": agent,
                "signal": res.get("signal", ""),
                "recommendation": res.get("recommendation", ""),
                "status": res.get("status", ""),
                "reliability": res.get("reliability", res.get("finance_reliability", "")),
                "source": str(res.get("source", res.get("source_files", "")))[:240],
            })
    print(json.dumps({"as_of": ns.as_of, "n": len(rows), "rows": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

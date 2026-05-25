from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from evaluation.features_finance import build_finance_signal
from evaluation.features_market import build_market_signal
from evaluation.features_valuation import build_valuation_signal
from evaluation.features_tech import build_tech_signal
from evaluation.features_issue import build_issue_signal
from evaluation.features_macro import build_macro_signal
from evaluation.decision_labels import ensure_decision_fields

AGENTS = (
    ("finance", build_finance_signal),
    ("market", build_market_signal),
    ("valuation", build_valuation_signal),
    ("tech", build_tech_signal),
    ("issue", build_issue_signal),
    ("macro", build_macro_signal),
)


def read_universe(path: str | Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    rows = []
    for _, r in df.iterrows():
        d = {str(k): ("" if pd.isna(v) else v) for k, v in r.to_dict().items()}
        d.setdefault("company", d.get("company_name") or d.get("name") or d.get("종목명") or "")
        d.setdefault("company_dir", d.get("slug") or d.get("company_dir") or "")
        d.setdefault("ticker", str(d.get("ticker") or d.get("stock_code") or d.get("종목코드") or "").zfill(6))
        d.setdefault("stock_code", d.get("ticker"))
        rows.append(d)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Check src_eval agent feature signals/recommendations as of a date.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--company", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    ns = ap.parse_args()

    root = Path.cwd().resolve()
    as_of = pd.Timestamp(ns.as_of)
    targets = read_universe(ns.universe_csv)
    if ns.company:
        targets = [t for t in targets if ns.company in str(t.get("company", "")) or ns.company in str(t.get("company_dir", ""))]
    if ns.limit:
        targets = targets[: ns.limit]

    records = []
    for t in targets:
        t["frequency"] = "monthly"
        for agent, fn in AGENTS:
            try:
                p = ensure_decision_fields(fn(root, ns.field, t, as_of))
            except Exception as exc:
                p = ensure_decision_fields({"signal": 0.0, "status": f"CHECK_ERROR: {exc}", "reliability": 0.0})
            records.append({
                "as_of_date": str(as_of.date()),
                "field": ns.field,
                "company": t.get("company", ""),
                "company_dir": t.get("company_dir", ""),
                "ticker": t.get("ticker", ""),
                "agent": agent,
                "signal": p.get("signal"),
                "weighted_signal": p.get("weighted_signal", p.get("signal")),
                "recommendation": p.get("recommendation"),
                "prob_sell": (p.get("probabilities") or {}).get("매도", ""),
                "prob_hold": (p.get("probabilities") or {}).get("보유", ""),
                "prob_buy": (p.get("probabilities") or {}).get("매수", ""),
                "status": p.get("status", ""),
                "source": p.get("source", ""),
                "raw_json": json.dumps(p, ensure_ascii=False, default=str),
            })

    df = pd.DataFrame(records)
    out = Path(ns.out) if ns.out else root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / "monthly" / "debug" / f"agent_feature_check_{as_of.date()}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")

    blanks = df[(df["recommendation"].astype(str).str.strip() == "") | (df["signal"].isna())]
    zeros = df[pd.to_numeric(df["signal"], errors="coerce").fillna(0).eq(0)]
    print(f"[OK] saved: {out}")
    print(f"rows={len(df)} blank_or_missing={len(blanks)} zero_signal={len(zeros)}")
    if len(blanks):
        print("[blank/missing]")
        print(blanks[["company", "agent", "signal", "recommendation", "status"]].to_string(index=False))
    if len(zeros):
        print("[zero signals]")
        print(zeros[["company", "agent", "signal", "recommendation", "status"]].head(80).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

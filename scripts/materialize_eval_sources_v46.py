from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_EVAL = ROOT / "src_eval"
SRC = ROOT / "src"
for p in (SRC_EVAL, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.source_materializer import materialize_eval_sources


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize actual evaluation source CSVs with v46 env loading.")
    ap.add_argument("--field", required=True)
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    args = ap.parse_args()

    summary = materialize_eval_sources(
        root=ROOT,
        field=args.field,
        targets_or_universe=args.universe_csv,
        start=args.start,
        end=args.end,
        frequency=args.frequency,
        limit=args.limit,
        output_root=args.output_root,
    )
    print("[OK] source materialization complete v46")
    print("manifest=", summary.get("manifest"))
    for key in ["company_market_finance", "macro_external", "market_external", "issue_sources", "tech_patent_sources"]:
        val = summary.get(key, {}) or {}
        print(f"[{key}] status={val.get('status')} created={len(val.get('created', []) or [])}")
    print("[env]", json.dumps(summary.get("env", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

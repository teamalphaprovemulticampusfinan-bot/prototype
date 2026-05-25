from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.source_materializer import materialize_eval_sources


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch/transform actual raw sources for src_eval history runs.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    ns = ap.parse_args()
    result = materialize_eval_sources(
        Path.cwd(), ns.field, ns.universe_csv, ns.start, ns.end, ns.frequency,
        limit=ns.limit, output_root=ns.output_root,
    )
    print("[OK] source materialization complete")
    print("manifest=", result.get("manifest"))
    for key in ["company_market_finance", "macro_external", "market_external", "issue_sources", "tech_patent_sources"]:
        v = result.get(key, {})
        print(f"[{key}] created={len(v.get('created', []) or [])} status={v.get('status', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

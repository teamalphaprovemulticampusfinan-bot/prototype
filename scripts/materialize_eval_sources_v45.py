from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.source_materializer import materialize_eval_sources


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize actual source CSVs for src_eval history/backtest v45.")
    ap.add_argument("--field", required=True)
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True, help="monthly: YYYY-MM, daily: YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="monthly: YYYY-MM, daily: YYYY-MM-DD")
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    ns = ap.parse_args()

    # v45: disable the slow all-market KRX cap fallback by default;
    # use local actual stock CSV/yfinance fallback instead if pykrx partially fails.
    import os
    os.environ.setdefault("ALPHAPROVE_KRX_CAP_FALLBACK_ENABLE", "0")

    summary = materialize_eval_sources(
        Path.cwd(),
        ns.field,
        ns.universe_csv,
        ns.start,
        ns.end,
        ns.frequency,
        limit=ns.limit,
        output_root=ns.output_root,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

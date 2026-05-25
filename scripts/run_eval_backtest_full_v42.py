from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in [ROOT / "src_eval", ROOT / "src"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.history_runner import run_range  # noqa: E402
from evaluation.null_fill import postprocess_output_root  # noqa: E402


def _slug(s: str) -> str:
    s = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", str(s)).strip("_")
    return s[:80] or "run"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run evaluation backtest into a clean monthly/backtest folder and fill nulls.")
    ap.add_argument("--field", required=True)
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--history-csv", default=None)
    ap.add_argument("--write-sheets", action="store_true")
    ap.add_argument("--output-root", default="")
    ns = ap.parse_args()

    if ns.output_root:
        out_root = Path(ns.output_root)
        if not out_root.is_absolute():
            out_root = ROOT / out_root
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out_root = ROOT / "data" / ns.field / "_sector_common" / "history_sheets_exports" / ns.frequency / "backtest" / f"{stamp}_{_slug(ns.run_id)}"

    print(f"[v42-backtest] output_root={out_root}")
    out = run_range(
        field=ns.field,
        frequency=ns.frequency,
        start=ns.start,
        end=ns.end,
        universe_csv=ns.universe_csv,
        run_id=ns.run_id,
        history_csv=ns.history_csv,
        limit=ns.limit,
        write_sheets=ns.write_sheets,
        output_root=str(out_root),
    )
    reports = postprocess_output_root(out)
    print(f"[v42-backtest] null_fill_files={len(reports)}")
    for r in reports:
        print(r)
    print(f"[v42-backtest] done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

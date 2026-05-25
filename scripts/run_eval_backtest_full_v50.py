from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# This script is intentionally thin: all agent logic stays in src_eval.
from evaluation.history_runner import run_range
from evaluation.pipeline_executor import month_ends, daily_dates, read_universe_rows, run_real_pipeline_for_window

DEFAULT_AGENTS = "data-intake,finance,valuation,tech,market,issue,macro,auditor,chair"


def _safe_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "run"


def _window_keys(frequency: str, start: str, end: str) -> list[str]:
    if frequency == "monthly":
        return month_ends(start, end)
    return daily_dates(start, end)


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run src_eval real pipeline + history evaluation in a clean backtest folder.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True, help="monthly: YYYY-MM, daily: YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="monthly: YYYY-MM, daily: YYYY-MM-DD")
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--run-id", default=None, help="Short name under monthly/backtest/<stamp>/<run-id>")
    ap.add_argument("--run-stamp", default=None, help="Optional fixed folder stamp, e.g. 20260522_0930")
    ap.add_argument("--agents", default=DEFAULT_AGENTS)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout-sec", type=int, default=900)
    ap.add_argument("--write-sheets", action="store_true")
    ap.add_argument("--skip-real-pipeline", action="store_true", help="Only rebuild standardized evaluation CSV/XLSX from existing as-of source data.")
    ap.add_argument("--keep-local-outputs", action="store_true", help="Do not restore operational company folders after each company. Default is safer for history runs.")
    ap.add_argument("--stop-on-error", action="store_true")
    ap.add_argument("--hold-policy", choices=["reject_option_directional_argmax", "directional_argmax", "max_posterior"], default="reject_option_directional_argmax")
    ns = ap.parse_args(argv)

    root = Path.cwd().resolve()
    run_id = _safe_name(ns.run_id or f"{ns.frequency}_{ns.start}_{ns.end}_v50")
    stamp = _safe_name(ns.run_stamp or datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_root = root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / ns.frequency / "backtest" / stamp / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    # No fixed Buy/Hold/Sell threshold. Reject-option directional argmax follows the larger Buy-vs-Sell posterior mass and uses Hold only for exact ties or missing direction.
    os.environ["ALPHAPROVE_EVAL_HOLD_POLICY"] = ns.hold_policy
    os.environ["ALPHAPROVE_EVAL_OUTPUT_ROOT"] = str(out_root)
    os.environ["ALPHAPROVE_EVAL_FREQUENCY"] = ns.frequency
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ["PYTHONPATH"] = str(root / "src_eval") + os.pathsep + str(root / "src") + (os.pathsep + os.environ.get("PYTHONPATH", "") if os.environ.get("PYTHONPATH") else "")

    targets = read_universe_rows(ns.universe_csv, limit=ns.limit)
    windows = _window_keys(ns.frequency, ns.start, ns.end)
    agents = [a.strip() for a in ns.agents.split(",") if a.strip()]

    _json_write(out_root / "run_manifest_pre.json", {
        "run_id": run_id,
        "run_stamp": stamp,
        "field": ns.field,
        "frequency": ns.frequency,
        "start": ns.start,
        "end": ns.end,
        "windows": windows,
        "universe_csv": ns.universe_csv,
        "targets": len(targets),
        "agents": agents,
        "output_root": str(out_root),
        "hold_policy": ns.hold_policy,
        "schema_policy": "Main team output keeps only date..macro_weight columns. stock_return_1m and diagnostics are written to detail files, not the team schema.",
        "decision_policy": "No numeric Buy/Hold/Sell threshold is used. Recommendation is generated from DMA/posterior probabilities and the selected hold policy.",
    })

    print(f"[eval-backtest-v50] output={out_root}")
    print(f"[eval-backtest-v50] windows={len(windows)} targets={len(targets)} agents={agents}")

    if not ns.skip_real_pipeline:
        for i, as_of in enumerate(windows, 1):
            print(f"[eval-backtest-v50] real-pipeline {i}/{len(windows)} as_of={as_of}")
            run_real_pipeline_for_window(
                root=root,
                field=ns.field,
                frequency=ns.frequency,
                as_of_date=as_of,
                run_id=run_id,
                targets=targets,
                agents=agents,
                timeout_sec=ns.timeout_sec,
                continue_on_error=not ns.stop_on_error,
                out_root=out_root,
                keep_local_outputs=ns.keep_local_outputs,
            )
    else:
        print("[eval-backtest-v50] skip-real-pipeline enabled; rebuilding standardized evaluation files only.")

    print("[eval-backtest-v50] building standardized evaluation CSV/XLSX ...")
    final_root = run_range(
        ns.field,
        ns.frequency,
        ns.start,
        ns.end,
        ns.universe_csv,
        run_id,
        history_csv=None,
        limit=ns.limit,
        write_sheets=ns.write_sheets,
        output_root=str(out_root),
    )

    # Convenience pointer for the latest run.
    latest = out_root.parent.parent / "LATEST_BACKTEST_RUN.txt"
    latest.write_text(str(final_root), encoding="utf-8")
    print(f"[eval-backtest-v50] DONE output_root={final_root}")
    print(f"[eval-backtest-v50] open: {final_root / f'eval_history_outputs_{ns.frequency}_{ns.start}_to_{ns.end}.xlsx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.history_runner import run_range
from evaluation.pipeline_executor import month_ends, daily_dates, read_universe_rows, run_real_pipeline_for_window
from evaluation.source_materializer import materialize_eval_sources

DEFAULT_AGENTS = "data-intake,finance,valuation,tech,market,issue,macro,auditor,chair"


def _safe_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "run"


def _window_keys(frequency: str, start: str, end: str) -> list[str]:
    return month_ends(start, end) if frequency == "monthly" else daily_dates(start, end)


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run actual-source src_eval backtest with clean monthly/backtest folder layout.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True, help="monthly: YYYY-MM, daily: YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="monthly: YYYY-MM, daily: YYYY-MM-DD")
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--run-stamp", default=None)
    ap.add_argument("--agents", default=DEFAULT_AGENTS)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout-sec", type=int, default=900)
    ap.add_argument("--write-sheets", action="store_true")
    ap.add_argument("--skip-real-pipeline", action="store_true", help="Only rebuild standardized evaluation CSV/XLSX after source materialization.")
    ap.add_argument("--skip-source-materialize", action="store_true", help="Do not fetch/transform raw data first.")
    ap.add_argument("--keep-local-outputs", action="store_true")
    ap.add_argument("--stop-on-error", action="store_true")
    ap.add_argument("--hold-policy", choices=["directional_argmax", "max_posterior"], default="directional_argmax")
    ns = ap.parse_args(argv)

    root = Path.cwd().resolve()
    run_id = _safe_name(ns.run_id or f"{ns.frequency}_{ns.start}_{ns.end}_v43")
    stamp = _safe_name(ns.run_stamp or datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_root = root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / ns.frequency / "backtest" / stamp / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    os.environ["ALPHAPROVE_EVAL_HOLD_POLICY"] = ns.hold_policy
    os.environ["ALPHAPROVE_EVAL_OUTPUT_ROOT"] = str(out_root)
    os.environ["ALPHAPROVE_EVAL_FREQUENCY"] = ns.frequency
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ["PYTHONPATH"] = str(root / "src_eval") + os.pathsep + str(root / "src") + (os.pathsep + os.environ.get("PYTHONPATH", "") if os.environ.get("PYTHONPATH") else "")

    targets = read_universe_rows(ns.universe_csv, limit=ns.limit)
    windows = _window_keys(ns.frequency, ns.start, ns.end)
    agents = [a.strip() for a in ns.agents.split(",") if a.strip()]

    manifest = {
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
        "decision_policy": "No fixed Buy/Hold/Sell return threshold. Recommendation comes from DMA/posterior probabilities; directional_argmax suppresses HOLD only when Buy/Sell posterior masses are not tied.",
        "source_policy": "v43 materializes actual source CSVs first: KRX/pykrx price+fundamental, FRED macro, yfinance external market if available, local Issue_Integration.xlsx, local KIPRIS/patent files.",
    }
    _json_write(out_root / "run_manifest_pre.json", manifest)

    print(f"[eval-backtest-v43] output={out_root}")
    print(f"[eval-backtest-v43] windows={len(windows)} targets={len(targets)} agents={agents}")

    if not ns.skip_source_materialize:
        src_summary = materialize_eval_sources(root, ns.field, targets, ns.start, ns.end, ns.frequency, output_root=out_root)
        _json_write(out_root / "source_materialize_summary_v43.json", src_summary)
    else:
        print("[eval-backtest-v43] skip-source-materialize enabled")

    if not ns.skip_real_pipeline:
        for i, as_of in enumerate(windows, 1):
            print(f"[eval-backtest-v43] real-pipeline {i}/{len(windows)} as_of={as_of}")
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
        print("[eval-backtest-v43] skip-real-pipeline enabled; standardized outputs only.")

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
    latest = out_root.parent.parent / "LATEST_BACKTEST_RUN.txt"
    latest.write_text(str(final_root), encoding="utf-8")
    print(f"[eval-backtest-v43] DONE output_root={final_root}")
    print(f"[eval-backtest-v43] open: {final_root / f'eval_history_outputs_{ns.frequency}_{ns.start}_to_{ns.end}.xlsx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

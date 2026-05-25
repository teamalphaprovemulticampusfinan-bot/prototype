from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src_eval"))
sys.path.insert(1, str(ROOT / "src"))

from evaluation.pipeline_executor import (
    AGENT_SEQUENCE_DEFAULT,
    daily_dates,
    month_ends,
    read_universe_rows,
    run_real_pipeline_for_window,
)
from evaluation.history_runner import run_range


def _window_iter(frequency: str, start: str, end: str) -> list[str]:
    if frequency == "monthly":
        return month_ends(start, end)
    return daily_dates(start, end)


def _window_label(frequency: str, as_of_date: str) -> str:
    return as_of_date[:7] if frequency == "monthly" else as_of_date


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "v30: run real src_eval monthly/daily data_intake -> agents -> auditor -> chair first, "
            "copy outputs to history_sheets_exports, then build evaluation files."
        )
    )
    ap.add_argument("--field", required=True)
    ap.add_argument("--frequency", choices=["monthly", "daily"], default="monthly")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout-sec", type=int, default=900)
    ap.add_argument(
        "--agents",
        default=",".join(AGENT_SEQUENCE_DEFAULT),
        help="Comma-separated agents. Default: data-intake,finance,valuation,tech,market,issue,macro,auditor,chair",
    )
    ap.add_argument("--stop-on-error", action="store_true")
    ap.add_argument("--write-sheets", action="store_true")
    ap.add_argument("--skip-real-pipeline", action="store_true", help="Debug only: rebuild evaluation from existing files.")
    ap.add_argument(
        "--keep-local-outputs",
        action="store_true",
        help="Debug only: do not restore operational data/<field>/<company>/<agent> folders after real pipeline.",
    )
    ns = ap.parse_args(argv)

    root = ROOT
    os.chdir(root)

    os.environ["PYTHONPATH"] = str(root / "src_eval") + os.pathsep + str(root / "src") + (
        os.pathsep + os.environ.get("PYTHONPATH", "") if os.environ.get("PYTHONPATH") else ""
    )
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    targets = read_universe_rows(ns.universe_csv, limit=ns.limit)
    agents = [x.strip() for x in ns.agents.split(",") if x.strip()]
    out_root = root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / ns.frequency / ns.run_id
    out_root.mkdir(parents=True, exist_ok=True)

    history_csv: str | None = None
    for as_of_date in _window_iter(ns.frequency, ns.start, ns.end):
        label = _window_label(ns.frequency, as_of_date)
        print(f"[eval-real-v30] window={label} as_of={as_of_date} targets={len(targets)} agents={agents}")

        if not ns.skip_real_pipeline:
            run_real_pipeline_for_window(
                root=root,
                field=ns.field,
                frequency=ns.frequency,
                as_of_date=as_of_date,
                run_id=ns.run_id,
                targets=targets,
                agents=agents,
                timeout_sec=ns.timeout_sec,
                continue_on_error=not ns.stop_on_error,
                out_root=out_root,
                keep_local_outputs=ns.keep_local_outputs,
            )
        else:
            print("[eval-real-v30] skip real pipeline; rebuilding evaluation from existing outputs only")

        # Build team/evaluation files after the real outputs for this exact window exist.
        run_range(
            field=ns.field,
            frequency=ns.frequency,
            start=label,
            end=label,
            universe_csv=ns.universe_csv,
            run_id=ns.run_id,
            history_csv=history_csv,
            limit=ns.limit,
            write_sheets=ns.write_sheets,
        )

        candidate = out_root / "_dma_history_until_previous_window.csv"
        if candidate.exists():
            history_csv = str(candidate)

    print(f"[eval-real-v30] done: {out_root}")
    print("[eval-real-v30] real pipeline log: " + str(out_root / "real_pipeline_agent_run_log.csv"))
    print("[eval-real-v30] cutoff audit: " + str(out_root / "real_pipeline_cutoff_audit.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

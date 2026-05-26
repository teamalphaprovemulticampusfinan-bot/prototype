from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.signal_df_exporter import export_signal_df

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


def _log(message: str) -> None:
    print(f"[monthly-cutoff-live-checkpoint] {datetime.now().isoformat(timespec='seconds')} {message}", flush=True)


def _read_manifest_status(out_root: Path) -> str:
    path = out_root / "run_manifest.json"
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return ""
    return str(payload.get("status") or "").strip().upper()


def _count_log_rows(log_csv: Path) -> int:
    if not log_csv.exists():
        return 0
    try:
        with log_csv.open("r", encoding="utf-8-sig", newline="") as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return 0


def _signature(out_root: Path) -> tuple[int, int, int]:
    log_csv = out_root / "monthly_cutoff_pipeline_run_log.csv"
    if not log_csv.exists():
        return (0, 0, 0)
    stat = log_csv.stat()
    return (int(stat.st_mtime), int(stat.st_size), _count_log_rows(log_csv))


def refresh(out_root: Path, *, field: str, run_id: str) -> bool:
    log_csv = out_root / "monthly_cutoff_pipeline_run_log.csv"
    wrote_any = False

    if pd is not None and log_csv.exists():
        try:
            df = pd.read_csv(log_csv, encoding="utf-8-sig")
            target = out_root / "monthly_cutoff_pipeline_run_log_live_checkpoint.xlsx"
            tmp = out_root / "monthly_cutoff_pipeline_run_log_live_checkpoint.tmp.xlsx"
            df.to_excel(tmp, index=False)
            tmp.replace(target)
            wrote_any = True
        except Exception as exc:
            _log(f"WARN run-log live checkpoint failed: {exc}")

    try:
        signal_export = export_signal_df(
            out_root=out_root,
            field=field,
            run_id=run_id,
            stamp="live_checkpoint",
            manifest_name="signal_df_live_checkpoint_manifest.json",
        )
        combined_xlsx = Path(str(signal_export.get("combined_xlsx") or ""))
        combined_csv = Path(str(signal_export.get("combined_csv") or ""))
        latest_xlsx = out_root / "signal_df_latest_live_checkpoint.xlsx"
        latest_csv = out_root / "signal_df_latest_live_checkpoint.csv"
        if combined_xlsx.exists():
            tmp_xlsx = out_root / "signal_df_latest_live_checkpoint.tmp.xlsx"
            shutil.copy2(combined_xlsx, tmp_xlsx)
            tmp_xlsx.replace(latest_xlsx)
            wrote_any = True
        if combined_csv.exists():
            tmp_csv = out_root / "signal_df_latest_live_checkpoint.tmp.csv"
            shutil.copy2(combined_csv, tmp_csv)
            tmp_csv.replace(latest_csv)
            wrote_any = True
        _log(f"refreshed rows={signal_export.get('rows')} xlsx={latest_xlsx}")
    except Exception as exc:
        _log(f"WARN signal_df live checkpoint failed: {exc}")

    return wrote_any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh monthly cutoff live checkpoint Excel files without touching the running pipeline.")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--poll-sec", type=float, default=20.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)

    out_root = Path(args.out_root).resolve()
    if not out_root.exists():
        raise FileNotFoundError(f"out-root not found: {out_root}")

    last_sig: tuple[int, int, int] | None = None
    idle_after_done = 0
    _log(f"watching out_root={out_root}")

    while True:
        sig = _signature(out_root)
        if sig != last_sig:
            # Give the parent process a brief moment to finish writing CSV/snapshot files.
            time.sleep(1.0)
            refresh(out_root, field=args.field, run_id=args.run_id)
            last_sig = _signature(out_root)

        if args.once:
            return 0

        status = _read_manifest_status(out_root)
        if status == "DONE":
            idle_after_done += 1
            if idle_after_done >= 2:
                _log("manifest status DONE; exiting")
                return 0
        else:
            idle_after_done = 0

        time.sleep(max(5.0, float(args.poll_sec)))


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def iter_dates(start: date, end: date, *, business_days_only: bool) -> list[date]:
    out = []
    cur = start
    while cur <= end:
        if not business_days_only or cur.weekday() < 5:
            out.append(cur)
        cur += timedelta(days=1)
    return out


def run_one(cmd: list[str], log_path: Path, timeout_sec: int) -> int:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_sec,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stdout or "", encoding="utf-8")
    return proc.returncode


def write_master_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["as_of_date", "status", "returncode", "run_id", "result_csv", "log_path"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="기간 단위로 DB snapshot -> Chair DB-only -> auditor_chair_packet DB 저장 -> CSV export를 일괄 실행합니다."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--universe-csv", default="")
    parser.add_argument("--business-days-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--fail-open", action="store_true")
    parser.add_argument("--allow-missing-snapshot", action="store_true")
    parser.add_argument("--timeout-sec-per-date", type=int, default=7200)
    args = parser.parse_args()

    start = parse_date(args.start_date)
    end = parse_date(args.end_date)
    dates = iter_dates(start, end, business_days_only=args.business_days_only)
    master_run_id = f"date_range_{args.start_date}_{args.end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_dir = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_db_logs" / master_run_id
    master_csv = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_db_exports" / f"history_date_range_master_{master_run_id}.csv"

    print("=" * 80)
    print("[History DB-only Date Range Run]")
    print(f"field             : {args.field}")
    print(f"start_date        : {args.start_date}")
    print(f"end_date          : {args.end_date}")
    print(f"dates             : {len(dates)}")
    print(f"business_days_only: {args.business_days_only}")
    print(f"master_run_id     : {master_run_id}")
    print(f"master_csv        : {master_csv}")
    print("=" * 80)

    rows: list[dict[str, str]] = []
    failures = 0

    for i, d in enumerate(dates, start=1):
        as_of_date = d.isoformat()
        run_id = f"chair_db_only_{as_of_date}_{master_run_id}"
        result_csv = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_db_exports" / f"chair_db_only_results_{as_of_date}_{run_id}.csv"
        log_path = log_dir / f"{i:04d}_{as_of_date}.log"

        cmd = [
            sys.executable,
            "scripts/run_chair_history_db_only_all.py",
            "--field",
            args.field,
            "--as-of-date",
            as_of_date,
            "--run-id",
            run_id,
            "--timeout-sec",
            str(args.timeout_sec_per_date),
        ]
        if args.universe_csv:
            cmd.extend(["--universe-csv", args.universe_csv])
        if args.limit > 0:
            cmd.extend(["--limit", str(args.limit)])
        if args.start_index > 1:
            cmd.extend(["--start-index", str(args.start_index)])
        if args.fail_open:
            cmd.append("--fail-open")
        if args.allow_missing_snapshot:
            cmd.append("--allow-missing-snapshot")

        print(f"[{i}/{len(dates)}] {as_of_date} 실행 중...")
        try:
            code = run_one(cmd, log_path, timeout_sec=args.timeout_sec_per_date + 300)
        except subprocess.TimeoutExpired:
            code = 124
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(f"[TIMEOUT] {as_of_date}\n", encoding="utf-8")

        status = "OK" if code == 0 else "FAILED"
        if code != 0:
            failures += 1
        row = {
            "as_of_date": as_of_date,
            "status": status,
            "returncode": str(code),
            "run_id": run_id,
            "result_csv": str(result_csv),
            "log_path": str(log_path),
        }
        rows.append(row)
        write_master_csv(master_csv, rows)
        print(f"  -> {status}, log={log_path}")

    print("=" * 80)
    print("[DONE]")
    print(f"master_csv: {master_csv}")
    print(f"failures  : {failures}")
    print("=" * 80)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

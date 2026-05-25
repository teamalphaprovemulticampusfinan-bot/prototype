from __future__ import annotations

"""Run AlphaProve history pipeline over a monthly or daily date range.

The runner only automates repeated calls.  It does not change DMA formulas.

For each period, it finds the latest previous-period history CSV and sets
ALPHAPROVE_DMA_HISTORY_CSV.  When --with-data-intake is used, the called
pipeline uses fast history intake by default: date-aware source-file filtering
rather than slow full local pipeline reruns.
"""

import argparse
import calendar
import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = PROJECT_ROOT / "scripts" / "run_history_sheets_only_pipeline.py"


@dataclass(frozen=True)
class Period:
    label: str
    as_of_date: str
    previous_label: str | None
    frequency: str


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_month(value: str) -> tuple[int, int]:
    if len(value) >= 7:
        return int(value[:4]), int(value[5:7])
    raise ValueError(f"monthly start/end must be YYYY-MM or YYYY-MM-DD: {value}")


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _add_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _monthly_periods(start: str, end: str) -> list[Period]:
    sy, sm = _parse_month(start)
    ey, em = _parse_month(end)
    periods: list[Period] = []
    prev_label: str | None = None
    y, m = sy, sm
    while (y, m) <= (ey, em):
        label = f"{y:04d}-{m:02d}"
        periods.append(Period(label=label, as_of_date=_month_end(y, m).isoformat(), previous_label=prev_label, frequency="monthly"))
        prev_label = label
        y, m = _add_month(y, m)
    return periods


def _daily_periods(start: str, end: str, *, business_days_only: bool) -> list[Period]:
    cur = _parse_date(start)
    end_d = _parse_date(end)
    periods: list[Period] = []
    prev_label: str | None = None
    while cur <= end_d:
        if (not business_days_only) or cur.weekday() < 5:
            label = cur.isoformat()
            periods.append(Period(label=label, as_of_date=label, previous_label=prev_label, frequency="daily"))
            prev_label = label
        cur += timedelta(days=1)
    return periods


def _export_root(field: str, frequency: str, override: str | None = None) -> Path:
    return Path(override) if override else PROJECT_ROOT / "data" / field / "_sector_common" / "history_sheets_exports" / frequency


def _find_latest_history_csv(*, field: str, frequency: str, period_label: str, export_root_override: str | None = None) -> Path | None:
    root = _export_root(field, frequency, export_root_override)
    if not root.exists():
        return None
    compact = period_label.replace("-", "")
    underscore = period_label.replace("-", "_")
    patterns = [
        f"**/signal_df_{frequency}_{period_label}*.csv",
        f"**/*{frequency}*{period_label}*.csv",
        f"**/*{underscore}*.csv",
        f"**/*{compact}*.csv",
    ]
    candidates: list[Path] = []
    seen: set[Path] = set()
    for pat in patterns:
        for p in root.glob(pat):
            if not p.is_file() or p in seen:
                continue
            if "signal_df" not in p.name.lower() and period_label not in p.name and underscore not in p.name:
                continue
            candidates.append(p)
            seen.add(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _set_history_env(env: dict[str, str], *, spreadsheet_id: str | None, service_account_file: str | None, dma_alpha: str) -> None:
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    env["ALPHAPROVE_HISTORY_BACKEND"] = "sheets"
    env["ALPHAPROVE_SHEETS_DB_ONLY"] = "1"
    env["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "1"
    env["ALPHAPROVE_USE_AGENT_HISTORY"] = "1"
    env["ALPHAPROVE_HISTORY_STRICT"] = "1"
    env["ALPHAPROVE_DMA_ALPHA"] = dma_alpha
    if spreadsheet_id:
        env["ALPHAPROVE_HISTORY_SPREADSHEET_ID"] = spreadsheet_id
    if service_account_file:
        env["ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE"] = service_account_file


def _write_run_log(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["frequency", "period", "as_of_date", "previous_period", "dma_history_csv", "status", "exit_code", "timestamp"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _run_one_period(
    *,
    period: Period,
    field: str,
    universe_csv: str,
    continue_on_error: bool,
    with_data_intake: bool,
    data_intake_mode: str,
    data_intake_agents: str,
    data_intake_force_fetch: bool,
    data_intake_skip_network: bool,
    data_intake_skip_agent: bool,
    run_id_prefix: str | None,
    initial_history_csv: str | None,
    export_root_override: str | None,
    spreadsheet_id: str | None,
    service_account_file: str | None,
    dma_alpha: str,
    dry_run: bool,
) -> tuple[int, str | None, str]:
    env = os.environ.copy()
    _set_history_env(env, spreadsheet_id=spreadsheet_id, service_account_file=service_account_file, dma_alpha=dma_alpha)

    history_csv: Path | None = None
    if period.previous_label:
        history_csv = _find_latest_history_csv(field=field, frequency=period.frequency, period_label=period.previous_label, export_root_override=export_root_override)
    elif initial_history_csv:
        history_csv = Path(initial_history_csv)

    if history_csv and history_csv.exists():
        env["ALPHAPROVE_DMA_HISTORY_CSV"] = str(history_csv)
        history_note = str(history_csv)
    else:
        env.pop("ALPHAPROVE_DMA_HISTORY_CSV", None)
        history_note = "<none; equal-prior fallback>"

    run_id = f"{run_id_prefix}_{period.frequency}_{period.as_of_date.replace('-', '')}" if run_id_prefix else None

    cmd = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        "--field",
        field,
        "--as-of-date",
        period.as_of_date,
        "--frequency",
        period.frequency,
        "--universe-csv",
        universe_csv,
    ]
    if continue_on_error:
        cmd.append("--continue-on-error")
    if run_id:
        cmd.extend(["--run-id", run_id])
    if with_data_intake:
        cmd.append("--with-data-intake")
        cmd.extend(["--data-intake-mode", data_intake_mode])
        cmd.extend(["--data-intake-agents", data_intake_agents])
        if data_intake_force_fetch:
            cmd.append("--data-intake-force-fetch")
        if data_intake_skip_network:
            cmd.append("--data-intake-skip-network")
        if data_intake_skip_agent:
            cmd.append("--data-intake-skip-agent")

    print("=" * 100)
    print(f"[RUN] {period.frequency} {period.label} as_of_date={period.as_of_date}")
    print(f"[DMA_HISTORY] {history_note}")
    print("[CMD]", " ".join(cmd))

    if dry_run:
        return 0, history_note, "DRY_RUN"

    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return proc.returncode, history_note, ("OK" if proc.returncode == 0 else "FAIL")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automate monthly/daily AlphaProve history runs.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--frequency", choices=["monthly", "daily"], required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--universe-csv", required=True)
    parser.add_argument("--business-days-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--with-data-intake", action="store_true", help="Use fast history intake by default")
    parser.add_argument("--data-intake-mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--data-intake-agents", default="macro,finance,tech,valuation,market,issue")
    parser.add_argument("--data-intake-force-fetch", action="store_true")
    parser.add_argument("--data-intake-skip-network", action="store_true")
    parser.add_argument("--data-intake-skip-agent", action="store_true")
    parser.add_argument("--initial-history-csv", default="")
    parser.add_argument("--history-export-root", default="")
    parser.add_argument("--spreadsheet-id", default=os.environ.get("ALPHAPROVE_HISTORY_SPREADSHEET_ID", ""))
    parser.add_argument("--service-account-file", default=os.environ.get("ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE", ""))
    parser.add_argument("--dma-alpha", default=os.environ.get("ALPHAPROVE_DMA_ALPHA", "0.99"))
    parser.add_argument("--run-id-prefix", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-csv", default="")
    args = parser.parse_args(argv)

    periods = _monthly_periods(args.start, args.end) if args.frequency == "monthly" else _daily_periods(args.start, args.end, business_days_only=args.business_days_only)
    if not periods:
        print("[NO PERIODS] Nothing to run.")
        return 0

    print(f"[PERIODS] {len(periods)} periods: {periods[0].label} -> {periods[-1].label}")
    rows: list[dict[str, str]] = []
    failed: list[tuple[Period, int]] = []

    for period in periods:
        code, history_csv, status = _run_one_period(
            period=period,
            field=args.field,
            universe_csv=args.universe_csv,
            continue_on_error=args.continue_on_error,
            with_data_intake=args.with_data_intake,
            data_intake_mode=args.data_intake_mode,
            data_intake_agents=args.data_intake_agents,
            data_intake_force_fetch=args.data_intake_force_fetch,
            data_intake_skip_network=args.data_intake_skip_network,
            data_intake_skip_agent=args.data_intake_skip_agent,
            run_id_prefix=args.run_id_prefix or None,
            initial_history_csv=args.initial_history_csv or None,
            export_root_override=args.history_export_root or None,
            spreadsheet_id=args.spreadsheet_id or None,
            service_account_file=args.service_account_file or None,
            dma_alpha=args.dma_alpha,
            dry_run=args.dry_run,
        )
        rows.append(
            {
                "frequency": period.frequency,
                "period": period.label,
                "as_of_date": period.as_of_date,
                "previous_period": period.previous_label or "",
                "dma_history_csv": history_csv or "",
                "status": status,
                "exit_code": str(code),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
        if code != 0:
            failed.append((period, code))
            if not args.continue_on_error:
                break

    log_csv = Path(args.log_csv) if args.log_csv else PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_sheets_exports" / "run_logs" / f"history_range_{args.frequency}_{periods[0].label}_to_{periods[-1].label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    _write_run_log(log_csv, rows)
    print(f"[RUN LOG] {log_csv}")

    if failed:
        print(f"[DONE WITH FAILURES] {len(failed)} failed")
        for period, code in failed:
            print(f"- {period.label} / {period.as_of_date}: exit={code}")
        return 1
    print("[ALL DONE] history range run complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

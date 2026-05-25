from __future__ import annotations

"""Run Google Sheets history replay for daily/monthly evaluation.

Fast default
------------
The script does NOT run the normal slow local pipeline by default.

When --with-data-intake / --run-data-intake is supplied, the default intake mode
is still "fast": date-aware history snapshots are built from objective source
files and uploaded to Google Sheets, without writing normal local agent folders.

Use --data-intake-mode full only if you explicitly want to call main.py
data-intake before archiving.  market/issue are always handled by the history
fast-intake archive step because they do not have normal data_intake modules in
the existing pipeline.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from archive_history_snapshots_to_google_sheets import AGENTS, _read_universe, archive_snapshots  # noqa: E402
from export_history_sheets_signal_dataset import export_signal_dataset  # noqa: E402


def _month_start(as_of_date: str) -> str:
    return f"{as_of_date[:7]}-01"


def _set_asof_env(env: dict[str, str], *, field: str, as_of_date: str, frequency: str, run_id: str) -> dict[str, str]:
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["PYTHONPATH"] = str(SRC_DIR)

    env["ALPHAPROVE_AS_OF_DATE"] = as_of_date
    env["ALPHAPROVE_DATA_CUTOFF_DATE"] = as_of_date
    env["ALPHAPROVE_HISTORY_AS_OF_DATE"] = as_of_date
    env["ALPHAPROVE_HISTORY_FREQUENCY"] = frequency
    env["ALPHAPROVE_FIELD"] = field
    env["ALPHAPROVE_HISTORY_RUN_ID"] = run_id

    start_date = _month_start(as_of_date) if frequency == "monthly" else as_of_date
    for prefix in ("FINANCE", "MARKET", "ISSUE", "MACRO", "VALUATION", "TECH"):
        env[f"{prefix}_AS_OF_DATE"] = as_of_date
        env[f"{prefix}_END_DATE"] = as_of_date
        env[f"{prefix}_START_DATE"] = start_date

    env["ALPHAPROVE_PERIOD_START_DATE"] = start_date
    env["ALPHAPROVE_PERIOD_END_DATE"] = as_of_date
    env["MARKET_DATE"] = as_of_date
    env["MACRO_DATE"] = as_of_date
    env["VALUATION_DATE"] = as_of_date
    env["ISSUE_DATE"] = as_of_date
    env["FINANCE_DATE"] = as_of_date
    env["TECH_DATE"] = as_of_date
    if frequency == "monthly":
        env["ALPHAPROVE_MONTH"] = as_of_date[:7]
    else:
        env["ALPHAPROVE_DAY"] = as_of_date
    return env


def _set_history_env(*, field: str, as_of_date: str, frequency: str, run_id: str) -> dict[str, str]:
    env = os.environ.copy()
    _set_asof_env(env, field=field, as_of_date=as_of_date, frequency=frequency, run_id=run_id)

    env["ALPHAPROVE_HISTORY_BACKEND"] = "sheets"
    env["ALPHAPROVE_SHEETS_DB_ONLY"] = "1"
    env["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "1"
    env["ALPHAPROVE_USE_AGENT_HISTORY"] = "1"
    env["ALPHAPROVE_HISTORY_STRICT"] = "1"

    # Chair replay should not launch another implicit data-intake phase.
    env["CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS"] = "1"
    env["CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS"] = "0"
    return env


def _split_agents(value: str) -> list[str]:
    return [x.strip().lower() for x in value.replace(";", ",").split(",") if x.strip()]


def _run_full_data_intake_for_history(
    *,
    field: str,
    as_of_date: str,
    frequency: str,
    run_id: str,
    companies: list[dict[str, str]],
    agents: list[str],
    force_fetch: bool,
    skip_network: bool,
    skip_agent: bool,
    continue_on_error: bool,
) -> list[tuple[str, str, int]]:
    """Optional slow path.

    This is kept only for explicit opt-in.  It calls main.py data-intake for
    agents that support it.  market/issue are excluded and handled in archive
    fast-intake so the normal pipeline remains unchanged.
    """
    supported = [a for a in agents if a not in {"market", "issue"}]
    unsupported = [a for a in agents if a in {"market", "issue"}]
    if unsupported:
        print(
            "[History Intake] market/issue는 일반 data_intake로 실행하지 않고 "
            f"archive 단계에서 월별/일별 source-file filtering으로 처리합니다: {','.join(unsupported)}"
        )
    if not supported:
        print("[History Intake] full data_intake 대상 agent가 없습니다. archive fast-intake만 수행합니다.")
        return []

    env = os.environ.copy()
    _set_asof_env(env, field=field, as_of_date=as_of_date, frequency=frequency, run_id=run_id)
    env["ALPHAPROVE_SHEETS_DB_ONLY"] = "0"
    env["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "0"

    failed: list[tuple[str, str, int]] = []
    for idx, item in enumerate(companies, 1):
        company_dir = item["company_dir"]
        company = item["company"]
        print("-" * 80)
        print(
            f"[{idx}/{len(companies)}] Full Data Intake history refresh: "
            f"{company}/{company_dir}, frequency={frequency}, as_of_date={as_of_date}, agents={','.join(supported)}"
        )

        cmd = [
            sys.executable,
            "main.py",
            "data-intake",
            "--company-dir",
            company_dir,
            "--company",
            company,
            "--field",
            field,
            "--agents",
            ",".join(supported),
        ]
        if force_fetch:
            cmd.append("--force-fetch")
        if skip_network:
            cmd.append("--skip-network")
        if skip_agent:
            cmd.append("--skip-agent")
        if not continue_on_error:
            cmd.append("--stop-on-error")

        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
        if proc.returncode != 0:
            failed.append((company_dir, company, proc.returncode))
            if not continue_on_error:
                raise SystemExit(proc.returncode)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Google Sheets daily/monthly history replay pipeline.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--frequency", choices=["daily", "monthly"], default="daily")
    parser.add_argument("--universe-csv")
    parser.add_argument("--default-five", action="store_true")
    parser.add_argument("--agents", default=",".join(AGENTS), help="Agents to archive into Sheets snapshots")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--skip-archive", action="store_true", help="이미 Sheets snapshot이 있을 때 Chair replay만 실행")

    parser.add_argument("--with-data-intake", action="store_true", help="history fast-intake를 명시적으로 사용합니다.")
    parser.add_argument("--run-data-intake", action="store_true", help="--with-data-intake alias")
    parser.add_argument(
        "--data-intake-mode",
        choices=["fast", "full"],
        default="fast",
        help="fast=source-file filtering only, full=main.py data-intake for supported agents + fast archive",
    )
    parser.add_argument(
        "--data-intake-agents",
        default="macro,finance,tech,valuation,market,issue",
        help="full mode에서 main.py data-intake 대상 후보. market/issue는 항상 fast archive로 처리.",
    )
    parser.add_argument("--data-intake-force-fetch", action="store_true")
    parser.add_argument("--data-intake-skip-network", action="store_true")
    parser.add_argument("--data-intake-skip-agent", action="store_true")
    parser.add_argument("--no-history-fast-intake", action="store_true")
    args = parser.parse_args(argv)

    companies = _read_universe(Path(args.universe_csv) if args.universe_csv else None, default_five=args.default_five)
    agents = _split_agents(args.agents)
    intake_agents = _split_agents(args.data_intake_agents)
    run_id = args.run_id or f"history_{args.frequency}_{args.as_of_date.replace('-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    failed: list[tuple[str, str, int]] = []

    if (args.with_data_intake or args.run_data_intake) and args.data_intake_mode == "full":
        failed.extend(
            _run_full_data_intake_for_history(
                field=args.field,
                as_of_date=args.as_of_date,
                frequency=args.frequency,
                run_id=run_id,
                companies=companies,
                agents=intake_agents,
                force_fetch=args.data_intake_force_fetch,
                skip_network=args.data_intake_skip_network,
                skip_agent=args.data_intake_skip_agent,
                continue_on_error=args.continue_on_error,
            )
        )
    elif args.with_data_intake or args.run_data_intake:
        print(
            "[History Intake] fast mode: 일반 pipeline data_intake를 호출하지 않고 "
            "archive 단계에서 월별/일별 source-file filtering으로 처리합니다."
        )

    if not args.skip_archive:
        archive_snapshots(
            field=args.field,
            as_of_date=args.as_of_date,
            frequency=args.frequency,
            companies=companies,
            agents=agents,
            overwrite=True,
            history_fast_intake=not args.no_history_fast_intake,
        )

    env = _set_history_env(field=args.field, as_of_date=args.as_of_date, frequency=args.frequency, run_id=run_id)

    for idx, item in enumerate(companies, 1):
        company_dir = item["company_dir"]
        company = item["company"]
        print("=" * 80)
        print(f"[{idx}/{len(companies)}] Chair history replay: {company}/{company_dir} run_id={run_id}")
        cmd = [sys.executable, "main.py", "chair", "--company-dir", company_dir, "--company", company, "--no-intake"]
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
        if proc.returncode != 0:
            failed.append((company_dir, company, proc.returncode))
            if not args.continue_on_error:
                raise SystemExit(proc.returncode)

    export_signal_dataset(
        field=args.field,
        as_of_date=args.as_of_date,
        frequency=args.frequency,
        run_id=run_id,
        universe_csv=args.universe_csv,
    )

    if failed:
        print(f"[DONE WITH FAILURES] {len(failed)} failed")
        for slug, name, code in failed:
            print(f"- {slug} / {name}: exit={code}")
        return 1
    print("[ALL DONE] history Google Sheets replay complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

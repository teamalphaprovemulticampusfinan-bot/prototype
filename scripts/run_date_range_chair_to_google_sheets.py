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


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end-date가 start-date보다 빠릅니다.")
    out: list[date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def read_universe_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_dir = (row.get("company_dir") or row.get("slug") or row.get("company_slug") or "").strip()
            company = (row.get("company") or row.get("company_name") or row.get("name") or row.get("기업명") or "").strip()
            if company_dir and company:
                rows.append({"company_dir": company_dir, "company": company})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "지정 기간의 각 일자별로 Chair를 실행하고 auditor/chair 결과 JSON은 Google Sheets에 저장합니다. "
            "Google Sheets에 저장하면서 auditor/chair 로컬 JSON/MD도 함께 남기는 흐름입니다."
        )
    )
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--start-date", required=True)
    ap.add_argument("--end-date", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--fail-open", action="store_true")
    ap.add_argument("--continue-on-error", action="store_true", default=True)
    ap.add_argument("--skip-weekends", action="store_true")
    ap.add_argument("--history-replay", action="store_true", help="이미 Google Sheets에 저장된 agent snapshot을 읽어서 Chair만 재실행합니다. 기본값은 live 재실행입니다.")
    args = ap.parse_args()

    targets = read_universe_csv(Path(args.universe_csv))
    if args.limit:
        targets = targets[: args.limit]

    days = date_range(parse_date(args.start_date), parse_date(args.end_date))
    if args.skip_weekends:
        days = [d for d in days if d.weekday() < 5]

    base_env = os.environ.copy()
    base_env["PYTHONUTF8"] = "1"
    base_env["PYTHONIOENCODING"] = "utf-8"
    base_env["ALPHAPROVE_HISTORY_BACKEND"] = "sheets"
    base_env["ALPHAPROVE_SHEETS_DB_ONLY"] = "1"
    base_env["ALPHAPROVE_FIELD"] = args.field
    base_env["CHAIR_DATA_INTAKE_FIELD"] = args.field
    base_env.setdefault("ALPHAPROVE_HISTORY_REQUIRED_AGENTS", "finance,market,tech,valuation,issue,macro")
    if args.fail_open:
        base_env["AUDITOR_FIRST_FAIL_OPEN"] = "1"
    if args.history_replay:
        base_env["ALPHAPROVE_USE_AGENT_HISTORY"] = "1"
        base_env["ALPHAPROVE_HISTORY_STRICT"] = "1"
    else:
        base_env.pop("ALPHAPROVE_USE_AGENT_HISTORY", None)
        base_env.pop("ALPHAPROVE_HISTORY_STRICT", None)

    print("=" * 100)
    print("[Date Range Chair → Google Sheets]")
    print(f"field        : {args.field}")
    print(f"date_range   : {args.start_date} ~ {args.end_date}")
    print(f"days         : {len(days)}")
    print(f"targets      : {len(targets)}")
    print(f"mode         : {'HISTORY_REPLAY' if args.history_replay else 'LIVE_RECALC_WITH_DATE_ENV'}")
    print("local chair json/md: disabled by ALPHAPROVE_SHEETS_DB_ONLY=1")
    print("주의: finance/market/issue/macro가 아래 date env를 실제로 읽도록 구현되어 있어야 완전한 과거 재계산이 됩니다.")
    print("=" * 100)

    ok = 0
    fail = 0
    run_ids: list[str] = []

    for d in days:
        ds = d.isoformat()
        run_id = f"chair_sheets_{ds}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_ids.append(run_id)
        for i, t in enumerate(targets, start=1):
            env = base_env.copy()
            env["ALPHAPROVE_AS_OF_DATE"] = ds
            env["ALPHAPROVE_HISTORY_RUN_ID"] = run_id

            # 각 agent가 지원하면 이 값으로 일자 제한을 걸 수 있게 공통 env를 모두 같이 전달합니다.
            env["ALPHAPROVE_DATA_AS_OF_DATE"] = ds
            env["ALPHAPROVE_DATA_CUTOFF_DATE"] = ds
            env["FINANCE_AS_OF_DATE"] = ds
            env["MARKET_AS_OF_DATE"] = ds
            env["MARKET_END_DATE"] = ds
            env["MACRO_AS_OF_DATE"] = ds
            env["MACRO_END_DATE"] = ds
            env["ISSUE_AS_OF_DATE"] = ds
            env["ISSUE_START_DATE"] = ds
            env["ISSUE_END_DATE"] = ds
            env["VALUATION_AS_OF_DATE"] = ds
            env["VALUATION_END_DATE"] = ds

            print("\n" + "-" * 100)
            print(f"[{ds}] [{i}/{len(targets)}] {t['company']} / {t['company_dir']} | run_id={run_id}")
            cmd = [
                args.python,
                "main.py",
                "chair",
                "--company-dir",
                t["company_dir"],
                "--company",
                t["company"],
            ]
            if args.history_replay:
                cmd.append("--no-intake")
            proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, text=True)
            if proc.returncode == 0:
                ok += 1
            else:
                fail += 1
                print(f"[FAILED] date={ds} company={t['company']} returncode={proc.returncode}")
                if not args.continue_on_error:
                    print("[STOP] continue-on-error가 꺼져 있어 중단합니다.")
                    print("run_ids:", ",".join(run_ids))
                    return proc.returncode

    print("\n" + "=" * 100)
    print("[DONE]")
    print(f"ok      : {ok}")
    print(f"fail    : {fail}")
    print("run_ids :")
    for rid in run_ids:
        print(f"- {rid}")
    print("\nCSV 추출 예:")
    print(f"python .\\scripts\\export_google_sheets_auditor_chair_signals_exact.py --field \"{args.field}\" --as-of-date \"{args.start_date}\" --include-all-runs")
    print("=" * 100)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

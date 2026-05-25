from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_universe_csv(path: Path) -> list[dict[str, str]]:
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_dir = (
                row.get("company_dir")
                or row.get("slug")
                or row.get("company_slug")
                or row.get("ticker_slug")
                or ""
            ).strip()
            company = (
                row.get("company")
                or row.get("company_name")
                or row.get("name")
                or row.get("기업명")
                or ""
            ).strip()
            if company_dir and company:
                rows.append({"company_dir": company_dir, "company": company})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Google Sheets snapshot을 입력으로 Chair를 재실행하고 auditor/chair 결과를 Google Sheets에 저장합니다."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--universe-csv", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--fail-open", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true", default=True)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    targets = read_universe_csv(Path(args.universe_csv))
    if args.limit and args.limit > 0:
        targets = targets[: args.limit]

    run_id = args.run_id.strip() or f"chair_sheets_{args.as_of_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["ALPHAPROVE_HISTORY_BACKEND"] = "sheets"
    env["ALPHAPROVE_USE_AGENT_HISTORY"] = "1"
    env["ALPHAPROVE_SHEETS_DB_ONLY"] = "1"
    env["ALPHAPROVE_HISTORY_STRICT"] = "1"
    env["ALPHAPROVE_AS_OF_DATE"] = args.as_of_date
    env["ALPHAPROVE_FIELD"] = args.field
    env["ALPHAPROVE_HISTORY_RUN_ID"] = run_id
    env.setdefault("ALPHAPROVE_HISTORY_REQUIRED_AGENTS", "finance,market,tech,valuation,issue,macro")
    if args.fail_open:
        env["AUDITOR_FIRST_FAIL_OPEN"] = "1"

    print("=" * 100)
    print("[Chair Google Sheets dual-save Run]")
    print(f"field        : {args.field}")
    print(f"as_of_date   : {args.as_of_date}")
    print(f"run_id       : {run_id}")
    print(f"targets      : {len(targets)}")
    print(f"universe_csv : {args.universe_csv}")
    print("local json/md: disabled by ALPHAPROVE_SHEETS_DB_ONLY=1")
    print("=" * 100)

    ok = 0
    fail = 0

    for i, t in enumerate(targets, start=1):
        print("\n" + "-" * 100)
        print(f"[{i}/{len(targets)}] {t['company']} / {t['company_dir']}")
        cmd = [
            args.python,
            "main.py",
            "chair",
            "--company-dir",
            t["company_dir"],
            "--company",
            t["company"],
            "--no-intake",
        ]
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, text=True)
        if proc.returncode == 0:
            ok += 1
        else:
            fail += 1
            print(f"[FAILED] {t['company']} / returncode={proc.returncode}")
            if not args.continue_on_error:
                print("[STOP] continue-on-error가 꺼져 있어 중단합니다.")
                break

    print("\n" + "=" * 100)
    print("[Chair Google Sheets dual-save Summary]")
    print(f"run_id : {run_id}")
    print(f"ok     : {ok}")
    print(f"fail   : {fail}")
    print("=" * 100)
    print("다음 단계 CSV 추출 예:")
    print(f"python .\\scripts\\export_google_sheets_history_date_to_csv.py --field \"{args.field}\" --as-of-date \"{args.as_of_date}\" --run-id \"{run_id}\"")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

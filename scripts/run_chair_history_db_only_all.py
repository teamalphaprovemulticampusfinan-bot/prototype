from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from src.common.agent_history import (  # noqa: E402
    extract_chair_result_row,
    extract_auditor_chair_packet_row,
    list_agent_snapshots,
    list_agent_run_results,
    load_agent_run_result,
    load_auditor_chair_packet_result,
)


REQUIRED_AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def norm_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def read_csv_flexible(path: Path) -> list[dict[str, str]]:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            continue
    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}")


def get_value(row: dict[str, str], candidates: list[str]) -> str:
    mapped = {norm_key(k): v for k, v in row.items()}
    for cand in candidates:
        v = mapped.get(norm_key(cand))
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def resolve_universe_csv(field: str, universe_csv: str | None) -> Path:
    if universe_csv:
        p = Path(universe_csv)
        if not p.exists():
            raise FileNotFoundError(f"universe CSV가 없습니다: {p}")
        return p

    base = PROJECT_ROOT / "data" / field / "_sector_common" / "universe"
    preferred = base / "universe_30_semiconductor_20260514.csv"
    if preferred.exists():
        return preferred

    candidates = sorted(base.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"universe CSV를 찾지 못했습니다: {base}")
    return candidates[0]


def parse_companies(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in rows:
        company_dir = get_value(row, ["company_dir", "slug", "company_slug", "dir", "폴더명", "기업폴더"])
        company = get_value(row, ["company", "company_name", "name", "corp_name", "기업명", "종목명", "회사명"])
        ticker = get_value(row, ["ticker", "stock_code", "code", "종목코드", "단축코드"])
        if company_dir and company:
            result.append({"company_dir": company_dir, "company": company, "ticker": ticker})
        else:
            print(f"[SKIP] company_dir/company 컬럼을 찾지 못했습니다: {row}")
    return result


def ensure_snapshots(*, as_of_date: str, field: str, company_dir: str, required_agents: list[str]) -> tuple[bool, str]:
    rows = list_agent_snapshots(as_of_date=as_of_date, field=field, company_dir=company_dir)
    found = {str(r.get("agent")) for r in rows}
    missing = [a for a in required_agents if a not in found]
    if missing:
        return False, ",".join(missing)
    return True, ""


def run_chair_db_only(
    *,
    field: str,
    as_of_date: str,
    run_id: str,
    company_dir: str,
    company: str,
    fail_open: bool,
    timeout_sec: int,
) -> tuple[int, float, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # 핵심: 입력은 history DB에서 읽고, Chair 산출물은 DB에만 저장한다.
    env["ALPHAPROVE_USE_AGENT_HISTORY"] = "1"
    env["ALPHAPROVE_AS_OF_DATE"] = as_of_date
    env["ALPHAPROVE_FIELD"] = field
    env["ALPHAPROVE_DB_ONLY_OUTPUT"] = "1"
    env["ALPHAPROVE_SAVE_AUDITOR_CHAIR_PACKET_TO_DB"] = "1"
    env["ALPHAPROVE_HISTORY_RUN_ID"] = run_id

    if fail_open:
        env["AUDITOR_FIRST_FAIL_OPEN"] = "1"
    else:
        env.pop("AUDITOR_FIRST_FAIL_OPEN", None)

    cmd = [
        sys.executable,
        "main.py",
        "chair",
        "--company-dir",
        company_dir,
        "--company",
        company,
        "--no-intake",
    ]

    start = time.time()
    try:
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
        elapsed = time.time() - start
        return proc.returncode, elapsed, proc.stdout or ""
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - start
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        return 124, elapsed, output + f"\n[TIMEOUT] {timeout_sec}s exceeded"


def read_result_from_db(*, run_id: str, as_of_date: str, field: str, company_dir: str) -> dict[str, Any] | None:
    item = load_agent_run_result(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent="chair",
        output_kind="chair_json",
    )
    if not item:
        return None
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return None
    row = extract_chair_result_row(payload, fallback=item)
    row.update(
        {
            "db_payload_hash": item.get("payload_hash", ""),
            "db_created_at": item.get("created_at", ""),
            "db_output_kind": item.get("output_kind", ""),
        }
    )
    return row




def read_auditor_packet_from_db(*, run_id: str, as_of_date: str, field: str, company_dir: str) -> dict[str, Any] | None:
    packet = load_auditor_chair_packet_result(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
    )
    if not isinstance(packet, dict):
        return None
    row = extract_auditor_chair_packet_row(packet, fallback={"company_dir": company_dir})
    item = load_agent_run_result(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent="auditor",
        output_kind="auditor_chair_packet_json",
    )
    if item:
        row.update(
            {
                "auditor_packet_hash": item.get("payload_hash", ""),
                "auditor_packet_created_at": item.get("created_at", ""),
                "auditor_packet_output_kind": item.get("output_kind", ""),
            }
        )
    return row

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "as_of_date",
        "field",
        "company",
        "company_dir",
        "ticker",
        "status",
        "returncode",
        "elapsed_sec",
        "final_recommendation",
        "weighted_signal",
        "auditor_passed",
        "failed_agents",
        "min_actual_match",
        "avg_actual_match",
        "threshold",
        "chair_report_chars",
        "db_payload_hash",
        "db_created_at",
        "db_output_kind",
        "auditor_packet_hash",
        "auditor_packet_created_at",
        "auditor_packet_output_kind",
        "packet_agent_count",
        "packet_agents",
        "packet_signals",
        "packet_recommendations",
        "auditor_final_recommendation",
        "auditor_weighted_signal",
        "missing_snapshots",
        "error_tail",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="agent_history.db snapshot을 입력으로 Chair를 실행하고, Chair JSON/MD를 파일이 아니라 DB에 저장한 뒤 CSV만 export합니다."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--universe-csv", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--fail-open", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--allow-missing-snapshot", action="store_true")
    args = parser.parse_args()

    universe_csv = resolve_universe_csv(args.field, args.universe_csv or None)
    companies = parse_companies(read_csv_flexible(universe_csv))
    if args.start_index > 1:
        companies = companies[args.start_index - 1 :]
    if args.limit > 0:
        companies = companies[: args.limit]

    if not companies:
        raise RuntimeError("실행 대상 기업이 없습니다.")

    run_id = args.run_id.strip() or f"chair_db_only_{args.as_of_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    csv_path = (
        PROJECT_ROOT
        / "data"
        / args.field
        / "_sector_common"
        / "history_db_exports"
        / f"chair_db_only_results_{args.as_of_date}_{run_id}.csv"
    )

    print("=" * 80)
    print("[Chair DB-only History Run]")
    print(f"field        : {args.field}")
    print(f"as_of_date   : {args.as_of_date}")
    print(f"run_id       : {run_id}")
    print(f"universe_csv : {universe_csv}")
    print(f"companies    : {len(companies)}")
    print(f"output_csv   : {csv_path}")
    print("=" * 80)

    result_rows: list[dict[str, Any]] = []
    failures = 0

    for idx, item in enumerate(companies, start=1):
        company_dir = item["company_dir"]
        company = item["company"]
        ticker = item.get("ticker", "")

        print()
        print("=" * 80)
        print(f"[{idx}/{len(companies)}] {company} / {company_dir}")
        print("=" * 80)

        snapshot_ok, missing = ensure_snapshots(
            as_of_date=args.as_of_date,
            field=args.field,
            company_dir=company_dir,
            required_agents=REQUIRED_AGENTS,
        )
        if not snapshot_ok and not args.allow_missing_snapshot:
            print(f"[SKIP] missing snapshots: {missing}")
            row = {
                "run_id": run_id,
                "as_of_date": args.as_of_date,
                "field": args.field,
                "company": company,
                "company_dir": company_dir,
                "ticker": ticker,
                "status": "SKIPPED_MISSING_SNAPSHOT",
                "returncode": "",
                "elapsed_sec": "",
                "missing_snapshots": missing,
                "error_tail": "",
            }
            result_rows.append(row)
            write_csv(csv_path, result_rows)
            failures += 1
            continue

        code, elapsed, output = run_chair_db_only(
            field=args.field,
            as_of_date=args.as_of_date,
            run_id=run_id,
            company_dir=company_dir,
            company=company,
            fail_open=args.fail_open,
            timeout_sec=args.timeout_sec,
        )

        db_row = read_result_from_db(
            run_id=run_id,
            as_of_date=args.as_of_date,
            field=args.field,
            company_dir=company_dir,
        )

        if db_row is None:
            db_row = {}

        auditor_packet_row = read_auditor_packet_from_db(
            run_id=run_id,
            as_of_date=args.as_of_date,
            field=args.field,
            company_dir=company_dir,
        ) or {}

        status = "OK" if code == 0 and db_row else "FAILED"
        if status != "OK":
            failures += 1

        row = {
            "run_id": run_id,
            "as_of_date": args.as_of_date,
            "field": args.field,
            "company": company,
            "company_dir": company_dir,
            "ticker": ticker,
            "status": status,
            "returncode": code,
            "elapsed_sec": round(elapsed, 2),
            "missing_snapshots": missing,
            "error_tail": "\n".join((output or "").splitlines()[-12:]),
        }
        row.update(auditor_packet_row)
        row.update(db_row)
        result_rows.append(row)
        write_csv(csv_path, result_rows)

        print(
            f"[Result] status={status}, returncode={code}, "
            f"recommendation={row.get('final_recommendation')}, "
            f"auditor_passed={row.get('auditor_passed')}, "
            f"report_chars={row.get('chair_report_chars')}"
        )

    stored = list_agent_run_results(run_id=run_id, as_of_date=args.as_of_date, field=args.field, agent="chair")
    stored_auditor_packets = list_agent_run_results(
        run_id=run_id,
        as_of_date=args.as_of_date,
        field=args.field,
        agent="auditor",
        output_kind="auditor_chair_packet_json",
    )

    print()
    print("=" * 80)
    print("[DONE]")
    print(f"CSV          : {csv_path}")
    print(f"DB chair rows: {len(stored)}")
    print(f"DB auditor_chair_packet rows: {len(stored_auditor_packets)}")
    print(f"failures     : {failures}")
    print("=" * 80)

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

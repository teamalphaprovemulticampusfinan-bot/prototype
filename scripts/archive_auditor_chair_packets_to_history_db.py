from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from src.common.agent_history import save_auditor_chair_packet_result, list_auditor_chair_packet_results  # noqa: E402


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
    out = []
    for row in rows:
        company_dir = get_value(row, ["company_dir", "slug", "company_slug", "dir", "폴더명", "기업폴더"])
        company = get_value(row, ["company", "company_name", "name", "corp_name", "기업명", "종목명", "회사명"])
        if company_dir and company:
            out.append({"company_dir": company_dir, "company": company})
        else:
            print(f"[SKIP] company_dir/company 누락: {row}")
    return out


def company_base_dir(field: str, company: str, company_dir: str) -> Path:
    for p in [PROJECT_ROOT / "data" / field / company, PROJECT_ROOT / "data" / field / company_dir]:
        if p.exists():
            return p
    return PROJECT_ROOT / "data" / field / company


def read_json(path: Path) -> dict[str, Any]:
    for enc in ["utf-8", "utf-8-sig", "cp949"]:
        try:
            value = json.loads(path.read_text(encoding=enc))
            return value if isinstance(value, dict) else {"payload": value}
        except Exception:
            continue
    raise RuntimeError(f"JSON을 읽지 못했습니다: {path}")


def find_packet_path(field: str, company: str, company_dir: str) -> Path | None:
    base = company_base_dir(field, company, company_dir)
    candidates = [
        base / "auditor" / "first_auditor" / "compact_agent_packets" / "auditor_chair_packet.json",
        base / "auditor" / "compact_agent_packets" / "auditor_chair_packet.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    found = sorted(base.glob("**/auditor_chair_packet.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0] if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description="기존 로컬 auditor_chair_packet.json을 agent_history.db에 저장합니다.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--universe-csv", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--company-dir", default="")
    parser.add_argument("--company", default="")
    args = parser.parse_args()

    run_id = args.run_id.strip() or f"auditor_chair_packet_archive_{args.as_of_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if args.company_dir and args.company:
        companies = [{"company_dir": args.company_dir, "company": args.company}]
    else:
        universe_csv = resolve_universe_csv(args.field, args.universe_csv or None)
        companies = parse_companies(read_csv_flexible(universe_csv))

    print("=" * 80)
    print("[Archive auditor_chair_packet.json -> agent_history.db]")
    print(f"field      : {args.field}")
    print(f"as_of_date : {args.as_of_date}")
    print(f"run_id     : {run_id}")
    print(f"companies  : {len(companies)}")
    print("=" * 80)

    saved = 0
    missing = 0
    errors = 0

    for item in companies:
        company_dir = item["company_dir"]
        company = item["company"]
        path = find_packet_path(args.field, company, company_dir)
        if not path:
            print(f"[MISSING] {company} / {company_dir}: auditor_chair_packet.json")
            missing += 1
            continue
        try:
            payload = read_json(path)
            payload.setdefault("company", company)
            payload.setdefault("company_dir", company_dir)
            payload.setdefault("field", args.field)
            payload.setdefault("as_of_date", args.as_of_date)
            payload.setdefault("run_id", run_id)
            save_auditor_chair_packet_result(
                run_id=run_id,
                as_of_date=args.as_of_date,
                field=args.field,
                company_dir=company_dir,
                company_name=company,
                packet=payload,
                source_mode="archived_local_auditor_chair_packet_json",
                metadata={"source_file": str(path), "archived_at": datetime.now().isoformat(timespec="seconds")},
            )
            print(f"[SAVED] {company_dir}: {path}")
            saved += 1
        except Exception as exc:
            print(f"[ERROR] {company_dir}: {exc}")
            errors += 1

    rows = list_auditor_chair_packet_results(run_id=run_id, as_of_date=args.as_of_date, field=args.field)
    print("=" * 80)
    print(f"saved={saved}, missing={missing}, errors={errors}, db_rows={len(rows)}")
    print("=" * 80)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

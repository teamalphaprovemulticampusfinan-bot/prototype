from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

os.environ.setdefault("ALPHAPROVE_HISTORY_BACKEND", "sheets")

from common.agent_history import list_agent_snapshots, save_agent_snapshot, history_source_label  # noqa: E402


AGENT_FILE_CANDIDATES: dict[str, list[str]] = {
    "finance": ["finance/*_finance_agent_packet.json", "finance/*_finance.json"],
    "market": ["market/*_market_agent_packet.json", "market/*_market.json"],
    "issue": ["issue/*_issue_agent_packet.json", "issue/*_issue.json"],
    "macro": ["macro/*_macro_agent_packet.json", "macro/*_macro.json", "macro/macro_signal_*.json"],
    "tech": ["tech/*_tech_agent_packet.json", "tech/*_tech.json", "tech/tech.json"],
    "valuation": ["valuation/*_valuation_agent_packet.json", "valuation/*_valuation_metrics.json", "valuation/*_dashboard_payload.json"],
    "chair": ["chair/*_chair_agent_packet.json", "chair/*_chair.json"],
}

DEFAULT_AGENTS = ["finance", "market", "issue", "macro", "tech", "valuation", "chair"]


def read_json_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    payload = json.loads(text)
    if isinstance(payload, dict):
        return payload
    return {"_wrapped_non_dict_payload": True, "payload": payload}


def resolve_company_root(*, field: str, company_dir: str, company_name: str) -> Path:
    field_root = PROJECT_ROOT / "data" / field
    candidates = [field_root / company_name, field_root / company_dir]
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    raise FileNotFoundError(
        "기업 데이터 폴더를 찾지 못했습니다.\n"
        f"- field_root: {field_root}\n"
        f"- tried: {candidates}"
    )


def find_agent_json_file(company_root: Path, agent: str) -> Path | None:
    for pattern in AGENT_FILE_CANDIDATES.get(agent, []):
        matches = [p for p in sorted(company_root.glob(pattern)) if p.is_file()]
        if matches:
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return matches[0]
    return None


def archive_one_company(
    *,
    field: str,
    company_dir: str,
    company_name: str,
    as_of_date: str,
    agents: list[str],
    strict: bool,
) -> dict[str, Any]:
    company_root = resolve_company_root(field=field, company_dir=company_dir, company_name=company_name)
    result: dict[str, Any] = {
        "field": field,
        "company_dir": company_dir,
        "company_name": company_name,
        "as_of_date": as_of_date,
        "company_root": str(company_root),
        "saved": [],
        "missing": [],
        "errors": [],
    }

    for agent in agents:
        source_path = find_agent_json_file(company_root, agent)
        if source_path is None:
            msg = f"[MISSING] {company_name}/{agent}: 저장할 JSON 파일을 찾지 못했습니다."
            result["missing"].append({"agent": agent, "message": msg})
            print(msg)
            if strict:
                raise FileNotFoundError(msg)
            continue

        try:
            payload = read_json_file(source_path)
            saved = save_agent_snapshot(
                as_of_date=as_of_date,
                field=field,
                company_dir=company_dir,
                company_name=company_name,
                agent=agent,
                payload=payload,
                source_file=str(source_path.relative_to(PROJECT_ROOT)),
                source_mode="archived_current_json_to_google_sheets_as_of_placeholder",
                overwrite=True,
            )
            item = {
                "agent": agent,
                "source_file": str(source_path.relative_to(PROJECT_ROOT)),
                "record_key": saved.get("record_key") if isinstance(saved, dict) else "",
                "chunk_count": saved.get("chunk_count") if isinstance(saved, dict) else "",
            }
            result["saved"].append(item)
            print(f"[SAVED→Sheets] {company_name}/{agent}: {item['source_file']} | chunks={item['chunk_count']}")
        except Exception as exc:
            msg = f"[ERROR] {company_name}/{agent}: {source_path} / {exc}"
            result["errors"].append({"agent": agent, "source_file": str(source_path), "error": str(exc)})
            print(msg)
            if strict:
                raise
    return result


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
    parser = argparse.ArgumentParser(description="현재 로컬 agent JSON을 Google Sheets history에 날짜별 snapshot으로 저장합니다.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--company-dir", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--universe-csv", default="")
    parser.add_argument("--agents", nargs="*", default=DEFAULT_AGENTS)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    targets: list[dict[str, str]] = []
    if args.universe_csv:
        targets = read_universe_csv(Path(args.universe_csv))
    elif args.company_dir and args.company:
        targets = [{"company_dir": args.company_dir, "company": args.company}]
    else:
        raise SystemExit("--universe-csv 또는 --company-dir/--company 중 하나를 입력하세요.")

    if args.limit and args.limit > 0:
        targets = targets[: args.limit]

    print("=" * 100)
    print("[Agent History Archive → Google Sheets]")
    print(f"backend    : {history_source_label()}")
    print(f"field      : {args.field}")
    print(f"as_of_date : {args.as_of_date}")
    print(f"targets    : {len(targets)}")
    print(f"agents     : {args.agents}")
    print("=" * 100)

    total_saved = 0
    total_missing = 0
    total_errors = 0

    for i, target in enumerate(targets, start=1):
        print("\n" + "-" * 100)
        print(f"[{i}/{len(targets)}] {target['company']} / {target['company_dir']}")
        result = archive_one_company(
            field=args.field,
            company_dir=target["company_dir"],
            company_name=target["company"],
            as_of_date=args.as_of_date,
            agents=args.agents,
            strict=args.strict,
        )
        total_saved += len(result["saved"])
        total_missing += len(result["missing"])
        total_errors += len(result["errors"])

    print("\n" + "=" * 100)
    print("[Archive Summary]")
    print(f"saved   : {total_saved}")
    print(f"missing : {total_missing}")
    print(f"errors  : {total_errors}")
    print("=" * 100)

    if len(targets) == 1:
        rows = list_agent_snapshots(
            as_of_date=args.as_of_date,
            field=args.field,
            company_dir=targets[0]["company_dir"],
        )
        print("[Snapshot List]")
        for row in rows:
            print(f"- {row.get('as_of_date')} | {row.get('field')} | {row.get('company_dir')} | {row.get('agent')} | {row.get('payload_bytes')} bytes")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

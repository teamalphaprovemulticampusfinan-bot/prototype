from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from src.common.agent_history import list_agent_snapshots, save_agent_snapshot  # noqa: E402


AGENT_FILE_CANDIDATES: dict[str, list[str]] = {
    "finance": [
        "finance/*_finance_agent_packet.json",
        "finance/*_finance.json",
    ],
    "market": [
        "market/*_market_agent_packet.json",
        "market/*_market.json",
    ],
    "issue": [
        "issue/*_issue_agent_packet.json",
        "issue/*_issue.json",
    ],
    "macro": [
        "macro/*_macro_agent_packet.json",
        "macro/*_macro.json",
        "macro/macro_signal_*.json",
    ],
    "tech": [
        "tech/*_tech_agent_packet.json",
        "tech/*_tech.json",
        "tech/tech.json",
    ],
    "valuation": [
        "valuation/*_valuation_agent_packet.json",
        "valuation/*_valuation_metrics.json",
        "valuation/*_dashboard_payload.json",
    ],
    "chair": [
        "chair/*_chair_agent_packet.json",
        "chair/*_chair.json",
    ],
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
        matches = [p for p in company_root.glob(pattern) if p.is_file()]
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
    overwrite: bool,
    strict: bool,
) -> dict[str, Any]:
    company_root = resolve_company_root(field=field, company_dir=company_dir, company_name=company_name)
    result = {
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
            msg = f"[MISSING] {agent}: 저장할 JSON 파일을 찾지 못했습니다."
            result["missing"].append({"agent": agent, "message": msg})
            print(msg)
            if strict:
                raise FileNotFoundError(msg)
            continue

        try:
            payload = read_json_file(source_path)
            save_agent_snapshot(
                as_of_date=as_of_date,
                field=field,
                company_dir=company_dir,
                company_name=company_name,
                agent=agent,
                payload=payload,
                source_file=str(source_path.relative_to(PROJECT_ROOT)),
                source_mode="archived_current_json_payload_into_db",
                overwrite=overwrite,
            )
            item = {
                "agent": agent,
                "source_file": str(source_path.relative_to(PROJECT_ROOT)),
                "payload_bytes": len(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
            }
            result["saved"].append(item)
            print(f"[SAVED] {agent}: {item['source_file']} -> DB payload_bytes={item['payload_bytes']}")
        except Exception as exc:
            msg = f"[ERROR] {agent}: {source_path} / {exc}"
            result["errors"].append({"agent": agent, "source_file": str(source_path), "error": str(exc)})
            print(msg)
            if strict:
                raise

    return result


def read_csv_flexible(path: Path) -> list[dict[str, str]]:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            continue
    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}")


def norm_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def get_value(row: dict[str, str], candidates: list[str]) -> str:
    mapped = {norm_key(k): v for k, v in row.items()}
    for cand in candidates:
        v = mapped.get(norm_key(cand))
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def archive_from_universe_csv(args: argparse.Namespace) -> int:
    rows = read_csv_flexible(Path(args.universe_csv))
    total_saved = 0
    total_missing = 0
    total_errors = 0

    for idx, row in enumerate(rows, start=1):
        company_dir = get_value(row, ["company_dir", "slug", "company_slug", "dir", "폴더명", "기업폴더"])
        company_name = get_value(row, ["company", "company_name", "name", "corp_name", "기업명", "종목명", "회사명"])
        if not company_dir or not company_name:
            print(f"[SKIP] {idx}: company_dir/company를 찾지 못했습니다: {row}")
            continue

        print("=" * 80)
        print(f"[{idx}] {company_name} / {company_dir}")
        print("=" * 80)
        result = archive_one_company(
            field=args.field,
            company_dir=company_dir,
            company_name=company_name,
            as_of_date=args.as_of_date,
            agents=args.agents,
            overwrite=not args.no_overwrite,
            strict=args.strict,
        )
        total_saved += len(result["saved"])
        total_missing += len(result["missing"])
        total_errors += len(result["errors"])

    print("=" * 80)
    print("[Universe Archive Summary]")
    print(f"saved={total_saved}, missing={total_missing}, errors={total_errors}")
    print("=" * 80)
    return 0 if total_errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="현재 파일 시스템의 agent JSON 결과를 data/agent_history.db payload_json에 날짜별 snapshot으로 저장합니다."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--universe-csv", default="", help="지정하면 CSV의 모든 기업을 일괄 저장합니다.")
    parser.add_argument("--agents", nargs="*", default=DEFAULT_AGENTS)
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.universe_csv:
        return archive_from_universe_csv(args)

    if not args.company_dir or not args.company:
        raise SystemExit("단일 기업 저장은 --company-dir 와 --company 가 필요합니다. 전체 저장은 --universe-csv를 사용하세요.")

    print("=" * 80)
    print("[Agent History Archive]")
    print(f"field       : {args.field}")
    print(f"company_dir : {args.company_dir}")
    print(f"company     : {args.company}")
    print(f"as_of_date  : {args.as_of_date}")
    print(f"agents      : {args.agents}")
    print("=" * 80)

    result = archive_one_company(
        field=args.field,
        company_dir=args.company_dir,
        company_name=args.company,
        as_of_date=args.as_of_date,
        agents=args.agents,
        overwrite=not args.no_overwrite,
        strict=args.strict,
    )

    print()
    print("=" * 80)
    print("[Archive Summary]")
    print(f"saved   : {len(result['saved'])}")
    print(f"missing : {len(result['missing'])}")
    print(f"errors  : {len(result['errors'])}")
    print("=" * 80)

    print()
    print("[DB Snapshot List]")
    rows = list_agent_snapshots(as_of_date=args.as_of_date, field=args.field, company_dir=args.company_dir)
    for row in rows:
        print(
            f"- {row['as_of_date']} | {row['field']} | {row['company_dir']} | "
            f"{row['agent']} | payload_bytes={row.get('payload_bytes')} | source={row['source_file']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

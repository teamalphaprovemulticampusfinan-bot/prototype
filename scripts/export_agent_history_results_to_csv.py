from __future__ import annotations

import argparse
import csv
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

from src.common.agent_history import extract_chair_result_row, list_agent_run_results, load_agent_run_result  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "as_of_date",
        "field",
        "company",
        "company_dir",
        "final_recommendation",
        "weighted_signal",
        "auditor_passed",
        "failed_agents",
        "min_actual_match",
        "avg_actual_match",
        "threshold",
        "chair_report_chars",
        "payload_hash",
        "created_at",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="agent_history.db에 저장된 Chair 결과를 CSV로 export합니다.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-csv", default="")
    args = parser.parse_args()

    meta_rows = list_agent_run_results(
        run_id=args.run_id,
        as_of_date=args.as_of_date,
        field=args.field,
        agent="chair",
        output_kind="chair_json",
    )

    rows: list[dict[str, Any]] = []
    for meta in meta_rows:
        item = load_agent_run_result(
            run_id=args.run_id,
            as_of_date=args.as_of_date,
            field=args.field,
            company_dir=meta["company_dir"],
            agent="chair",
            output_kind="chair_json",
        )
        if not item or not isinstance(item.get("payload"), dict):
            continue
        row = extract_chair_result_row(item["payload"], fallback=item)
        row.update(
            {
                "run_id": args.run_id,
                "as_of_date": args.as_of_date,
                "field": args.field,
                "payload_hash": item.get("payload_hash", ""),
                "created_at": item.get("created_at", ""),
            }
        )
        rows.append(row)

    if args.output_csv:
        out = Path(args.output_csv)
    else:
        out = (
            PROJECT_ROOT
            / "data"
            / args.field
            / "_sector_common"
            / "history_db_exports"
            / f"chair_db_export_{args.as_of_date}_{args.run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    write_csv(out, rows)
    print(f"[OK] exported {len(rows)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

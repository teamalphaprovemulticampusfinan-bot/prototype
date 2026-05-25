from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _join_list(value):
    if isinstance(value, list):
        return "; ".join(str(x) for x in value[:5])
    return value or ""


def main() -> int:
    root = project_root()
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from evaluation.monthly_eval import build_all_snapshots, parse_month, read_universe

    parser = argparse.ArgumentParser(description="Chair 실행 전 월별 snapshot source/data_quality만 점검")
    parser.add_argument("--month", required=True)
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--universe-csv", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    window = parse_month(args.month)
    targets = read_universe(args.universe_csv, field=args.field)
    if args.limit:
        targets = targets[: args.limit]

    rows = []
    for target in targets:
        snaps = build_all_snapshots(target, window)
        row = {"company": target.company_name, "company_dir": target.company_dir, "month": window.month}
        for agent, snap in snaps.items():
            dq = snap.get("data_quality") if isinstance(snap.get("data_quality"), dict) else {}
            metrics = snap.get("metrics") if isinstance(snap.get("metrics"), dict) else {}
            source_file = dq.get("source_file") or dq.get("workbook_source_file") or ""
            if not source_file and isinstance(dq.get("source_files"), list):
                source_file = "; ".join(dq.get("source_files")[:3])
            row[f"{agent}_status"] = dq.get("status", "")
            row[f"{agent}_monthly_rows"] = dq.get("monthly_rows") or dq.get("monthly_rows_total") or metrics.get("price_monthly_rows") or metrics.get("monthly_issue_count") or ""
            row[f"{agent}_asof_date_used"] = dq.get("asof_date_used") or metrics.get("price_asof_date_used") or ""
            row[f"{agent}_source_file"] = source_file

            if agent == "market":
                price_q = dq.get("price_quality") if isinstance(dq.get("price_quality"), dict) else {}
                excel_q = dq.get("market_excel_quality") if isinstance(dq.get("market_excel_quality"), dict) else {}
                row["market_price_status"] = price_q.get("status", "")
                row["market_price_monthly_rows"] = price_q.get("monthly_rows", "")
                row["market_price_source_file"] = price_q.get("source_file", "")
                row["market_excel_status"] = excel_q.get("status", "")
                row["market_excel_source_file"] = excel_q.get("source_file", "")
                row["market_excel_total_score_raw"] = metrics.get("market_excel_total_score_raw", "")
                row["market_excel_recommendation_raw"] = metrics.get("market_excel_recommendation_raw", "")
                row["market_excel_vc_role_raw"] = metrics.get("market_excel_vc_role_raw", "")
        rows.append(row)

    out = Path(args.output) if args.output else (root / "data" / args.field / "_sector_common" / "history_sheets_exports" / f"monthly_source_audit_{window.month}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    all_fields = []
    for r in rows:
        for k in r.keys():
            if k not in all_fields:
                all_fields.append(k)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[DONE] source audit saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

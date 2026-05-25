from __future__ import annotations

import argparse
from pathlib import Path
import sys
import pandas as pd

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_latest_daily_csv(root: Path, field: str, month: str) -> Path:
    base = root / "data" / field / "_sector_common" / "history_sheets_exports" / "daily" / month
    files = sorted(base.rglob(f"signal_df_daily_{month}.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        # 이미 front-fixed 파일만 있는 경우도 허용
        files = sorted(base.rglob(f"signal_df_daily_{month}_signals_front*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"daily CSV를 찾지 못했습니다: {base}")
    return files[0]


def reorder_csv(input_csv: Path, output_csv: Path | None = None) -> Path:
    df = pd.read_csv(input_csv, encoding="utf-8-sig")

    signal_front = ["date", "ticker", "recommendation", "weighted_signal", "auditor_qd_status", "auditor_qd_source"]
    for agent in AGENTS:
        signal_front.extend([
            f"{agent}_signal",
            f"{agent}_weighted_signal",
            f"{agent}_recommendation",
            f"{agent}_weight",
            f"{agent}_signal_source",
        ])

    evidence_front = [
        "stock_code", "company_dir", "field", "as_of_date", "run_id",
        "market_price_status", "market_price_daily_rows", "market_price_source_file",
        "market_excel_status", "market_excel_source_file", "market_excel_total_score_raw",
        "market_excel_recommendation_raw", "market_excel_vc_role_raw",
        "valuation_workbook_status", "valuation_workbook_source_file",
        "valuation_workbook_daily_rows", "valuation_workbook_sheets", "valuation_workbook_date_column",
        "issue_status", "issue_news_count", "issue_source_file",
        "macro_score", "macro_source_files",
        "finance_fiscal_year_used", "finance_source_file", "finance_sales_growth_pct",
        "finance_operating_margin_pct", "finance_debt_ratio_pct",
        "tech_source_file", "tech_final_score", "tech_ip_evidence_score",
    ]

    front = [c for c in signal_front + evidence_front if c in df.columns]
    df = df[front + [c for c in df.columns if c not in front]]

    if output_csv is None:
        output_csv = input_csv.with_name(input_csv.stem + "_signals_front.csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"[OK] reordered: {output_csv}")
    print(f"[rows] {len(df)}")
    for agent in AGENTS:
        col = f"{agent}_signal"
        if col in df.columns:
            nonblank = df[col].notna() & (df[col].astype(str).str.strip() != "")
            print(f"[signal] {col}: {int(nonblank.sum())}/{len(df)} nonblank")
    return output_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="일별 signal_df에서 agent signal 컬럼을 앞쪽으로 재정렬")
    parser.add_argument("--input-csv", default="")
    parser.add_argument("--output-csv", default="")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--month", default="2025-01")
    args = parser.parse_args(argv)

    root = project_root()
    input_csv = Path(args.input_csv) if args.input_csv else _find_latest_daily_csv(root, args.field, args.month)
    output_csv = Path(args.output_csv) if args.output_csv else None
    reorder_csv(input_csv, output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

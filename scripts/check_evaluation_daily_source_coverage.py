from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description="Check daily evaluation CSV source coverage")
    parser.add_argument("--csv", required=True, help="signal_df_daily_YYYY-MM.csv path")
    args = parser.parse_args()

    p = Path(args.csv)
    if not p.exists():
        raise FileNotFoundError(p)

    df = pd.read_csv(p)
    print(f"[file] {p}")
    print(f"[shape] rows={len(df)}, cols={len(df.columns)}")

    status_cols = [
        "auditor_qd_status",
        "market_price_status",
        "market_excel_status",
        "valuation_workbook_status",
        "finance_daily_status",
        "issue_status",
        "macro_daily_status",
    ]
    for col in status_cols:
        if col in df.columns:
            print(f"\n[{col}]")
            print(df[col].fillna("<blank>").value_counts(dropna=False).to_string())
        else:
            print(f"\n[{col}] MISSING")

    signal_cols = [
        "finance_signal", "market_signal", "tech_signal", "valuation_signal", "issue_signal", "macro_signal"
    ]
    print("\n[signal nonblank counts]")
    for col in signal_cols:
        if col in df.columns:
            nonblank = df[col].notna() & (df[col].astype(str).str.strip() != "")
            print(f"{col}: {int(nonblank.sum())}/{len(df)}")
        else:
            print(f"{col}: MISSING")

    preview_cols = [c for c in [
        "date", "ticker", "recommendation", "weighted_signal",
        "finance_signal", "market_signal", "valuation_signal", "issue_signal", "macro_signal",
        "market_price_status", "market_excel_status", "valuation_workbook_status",
        "valuation_workbook_daily_rows", "macro_daily_status", "macro_daily_rows",
    ] if c in df.columns]
    print("\n[preview]")
    print(df[preview_cols].head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

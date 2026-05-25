from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = [
    "date",
    "field",
    "company",
    "ticker",
    "stock_code",
    "recommendation",
    "weighted_signal",
    "as_of_date",
    "signal_source",
    "finance_signal",
    "finance_weighted_signal",
    "finance_recommendation",
    "finance_weight",
    "market_signal",
    "market_weighted_signal",
    "market_recommendation",
    "market_weight",
    "tech_signal",
    "tech_weighted_signal",
    "tech_recommendation",
    "tech_weight",
    "valuation_signal",
    "valuation_weighted_signal",
    "valuation_recommendation",
    "valuation_weight",
    "issue_signal",
    "issue_weighted_signal",
    "issue_recommendation",
    "issue_weight",
    "macro_signal",
    "macro_weighted_signal",
    "macro_recommendation",
    "macro_weight",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate signal_df-style monthly cutoff output schema.")
    parser.add_argument("csv_path")
    ns = parser.parse_args()

    path = Path(ns.csv_path)
    df = pd.read_csv(path, encoding="utf-8-sig")
    cols = list(df.columns)
    missing = [c for c in EXPECTED_COLUMNS if c not in cols]
    extra_after_macro = cols[cols.index("macro_weight") + 1:] if "macro_weight" in cols else cols
    ordered_ok = cols[: len(EXPECTED_COLUMNS)] == EXPECTED_COLUMNS

    signal_cols = [
        "weighted_signal",
        "finance_signal",
        "market_signal",
        "tech_signal",
        "valuation_signal",
        "issue_signal",
        "macro_signal",
    ]
    nonnull = {c: int(df[c].notna().sum()) if c in df.columns else 0 for c in signal_cols}

    result = {
        "path": str(path),
        "rows": int(len(df)),
        "columns": int(len(cols)),
        "missing_expected_columns": missing,
        "ordered_ok": bool(ordered_ok),
        "extra_columns_after_macro_weight": extra_after_macro,
        "signal_nonnull_counts": nonnull,
        "overall_ok": not missing and ordered_ok and len(extra_after_macro) == 0,
    }
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

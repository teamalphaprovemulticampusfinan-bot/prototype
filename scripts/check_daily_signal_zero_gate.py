from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def _to_float(v):
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    try:
        return float(str(v).replace(',', '').replace('%', '').strip())
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check zero/missing agent signals in daily signal_df CSV")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--strict", action="store_true", help="exit 2 if any source-backed zero signal remains")
    args = ap.parse_args(argv)

    path = Path(args.csv)
    df = pd.read_csv(path, encoding="utf-8-sig")
    print(f"[file] {path}")
    print(f"[shape] rows={len(df)}, cols={len(df.columns)}")

    problems = []
    for agent in AGENTS:
        col = f"{agent}_signal"
        if col not in df.columns:
            print(f"[MISSING] {col}")
            problems.append((agent, "MISSING_COLUMN", len(df)))
            continue
        vals = df[col].map(_to_float)
        zero = vals.map(lambda x: x is not None and abs(x) < 1e-12)
        missing = vals.isna()
        print(f"[{agent}] nonnull={len(df)-missing.sum()} zero={zero.sum()} missing={missing.sum()} unique={sorted(v for v in vals.dropna().unique())[:20]}")

        if agent == "valuation":
            source_backed_zero = zero & df.get("valuation_workbook_status", pd.Series([""]*len(df))).astype(str).str.startswith("FOUND")
            if source_backed_zero.any():
                problems.append((agent, "ZERO_WITH_VALUATION_WORKBOOK_FOUND", int(source_backed_zero.sum())))
        elif agent == "macro":
            source_backed_zero = zero & df.get("macro_daily_status", pd.Series([""]*len(df))).astype(str).str.startswith("FOUND")
            if source_backed_zero.any():
                problems.append((agent, "ZERO_WITH_DAILY_MACRO_FOUND", int(source_backed_zero.sum())))
        elif agent == "issue":
            # issue zero is only a problem if the day has issue rows.
            cnt = df.get("issue_daily_count", df.get("issue_news_count", pd.Series([0]*len(df)))).map(_to_float).fillna(0)
            source_backed_zero = zero & (cnt > 0)
            if source_backed_zero.any():
                problems.append((agent, "ZERO_WITH_DAILY_ISSUE_ROWS", int(source_backed_zero.sum())))
        else:
            if zero.any():
                problems.append((agent, "ZERO_SIGNAL", int(zero.sum())))

    if problems:
        print("\n[PROBLEMS]")
        for agent, reason, count in problems:
            print(f"- {agent}: {reason} count={count}")
        if args.strict:
            return 2
    else:
        print("\n[OK] source-backed zero signal problem 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

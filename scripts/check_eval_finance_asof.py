from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd


def _bootstrap(root: Path) -> None:
    src_eval = root / "src_eval"
    src = root / "src"
    for p in [src_eval, src]:
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


def _read_universe(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def _target_from_row(row: pd.Series) -> dict:
    lower = {str(c).lower(): c for c in row.index}
    def pick(*names: str) -> str:
        for name in names:
            col = lower.get(name.lower())
            if col is not None:
                return str(row.get(col) or "").strip()
        return ""
    return {
        "company": pick("company", "company_name", "회사명", "name"),
        "company_dir": pick("company_dir", "slug", "company_slug"),
        "ticker": pick("ticker", "stock_code", "종목코드", "code"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check src_eval Finance as-of cutoff signal inputs")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    parser.add_argument("--universe-csv", required=True)
    parser.add_argument("--company", default="", help="Optional company name/slug/ticker filter")
    args = parser.parse_args()

    root = Path.cwd()
    _bootstrap(root)
    os.environ["FINANCE_AS_OF_DATE"] = args.as_of
    os.environ["FINANCE_END_DATE"] = args.as_of
    os.environ["ALPHAPROVE_DATA_CUTOFF_DATE"] = args.as_of
    os.environ.setdefault("ALPHAPROVE_FIELD", args.field)

    from finance_agent.eval_finance_signal_model import build_finance_feature_packet, get_as_of

    uni = _read_universe(Path(args.universe_csv))
    rows = []
    if args.company:
        needle = args.company.lower()
        for _, row in uni.iterrows():
            text = " ".join(str(v) for v in row.values).lower()
            if needle in text:
                rows.append(row)
                break
    else:
        rows = [uni.iloc[0]] if not uni.empty else []

    if not rows:
        raise SystemExit("No matching company row found in universe CSV")

    target = _target_from_row(rows[0])
    result = build_finance_feature_packet(root, args.field, target, get_as_of(args.as_of))
    print(json.dumps({"target": target, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

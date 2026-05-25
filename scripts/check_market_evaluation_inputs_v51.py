from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC_EVAL = ROOT / "src_eval"
SRC = ROOT / "src"
if SRC_EVAL.exists() and str(SRC_EVAL) not in sys.path:
    sys.path.insert(0, str(SRC_EVAL))
# operational src is fallback only; never let it shadow src_eval packages
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from market_agent.history_market_features import MARKET_COLUMNS, market_input_paths


def _read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path)


def _check_file(name: str, path: Path, required: bool = True) -> dict[str, Any]:
    df = _read_csv_any(path)
    info = {"file": name, "path": str(path), "exists": path.exists(), "rows": int(len(df)), "cols": int(len(df.columns))}
    if required and not path.exists():
        info["problem"] = "MISSING_FILE"
    elif required and df.empty:
        info["problem"] = "EMPTY_FILE"
    else:
        info["problem"] = ""
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description="Check v51 src_eval Market evaluation intake CSVs")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--start", default="")
    ap.add_argument("--end", default="")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    paths = market_input_paths(root, args.field)
    required_keys = ["daily", "monthly", "company_sensitivity", "cycle_daily", "cycle_monthly", "news_daily", "news_monthly", "manifest"]
    checks = [_check_file(k, paths[k], required=True) for k in required_keys]

    problems: list[str] = []
    for item in checks:
        if item.get("problem"):
            problems.append(f"{item['file']}: {item['problem']} ({item['path']})")

    daily = _read_csv_any(paths["daily"])
    monthly = _read_csv_any(paths["monthly"])
    sens = _read_csv_any(paths["company_sensitivity"])
    news_d = _read_csv_any(paths["news_daily"])
    cycle_d = _read_csv_any(paths["cycle_daily"])

    for name, df in (("daily", daily), ("monthly", monthly)):
        if not df.empty:
            missing = [c for c in ["date", "company", "stock_code", "market_signal", "market_recommendation", "prob_sell", "prob_hold", "prob_buy"] if c not in df.columns]
            if missing:
                problems.append(f"{name}: missing columns {missing}")
            for c in ("market_signal", "technical_signal", "signal_reliability"):
                if c in df.columns:
                    nonnull = int(pd.to_numeric(df[c], errors="coerce").notna().sum())
                    if nonnull == 0:
                        problems.append(f"{name}: {c} has no numeric values")
            if "data_cutoff_ok" in df.columns:
                vals = df["data_cutoff_ok"].astype(str).str.lower()
                if not vals.isin(["true", "1", "yes"]).any():
                    problems.append(f"{name}: data_cutoff_ok is not marked true")

    if not sens.empty:
        numeric_cols = ["fx_beta", "raw_material_beta", "sox_beta", "krx_sector_beta", "export_sensitivity", "import_cost_sensitivity", "rate_sensitivity", "supply_chain_sensitivity"]
        available = [c for c in numeric_cols if c in sens.columns]
        filled = int(sens[available].apply(pd.to_numeric, errors="coerce").notna().sum().sum()) if available else 0
        if filled == 0:
            problems.append("company_sensitivity: sensitivity proxy columns are all empty")

    if not news_d.empty and "news_cutoff_applied" in news_d.columns:
        if not news_d["news_cutoff_applied"].astype(str).str.lower().isin(["true", "1", "yes"]).any():
            problems.append("news_daily: news_cutoff_applied is not true")

    if not cycle_d.empty and "sector_cycle_signal" in cycle_d.columns:
        filled = int(pd.to_numeric(cycle_d["sector_cycle_signal"], errors="coerce").notna().sum())
        if filled == 0:
            problems.append("cycle_daily: sector_cycle_signal has no numeric values")

    if args.start or args.end:
        for name, df in (("daily", daily), ("monthly", monthly), ("news_daily", news_d), ("cycle_daily", cycle_d)):
            if df.empty or "date" not in df.columns:
                continue
            dates = pd.to_datetime(df["date"], errors="coerce")
            if args.start and (dates.dropna() < pd.to_datetime(args.start)).any():
                problems.append(f"{name}: contains date before start")
            if args.end and (dates.dropna() > pd.to_datetime(args.end)).any():
                problems.append(f"{name}: contains date after end")

    print("=" * 80)
    print("[v51 Market evaluation input check]")
    print(f"root: {root}")
    print(f"field: {args.field}")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print("=" * 80)
    if problems:
        print("[PROBLEMS]")
        for p in problems:
            print("-", p)
        return 1 if args.strict else 0
    print("status: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _blank_count(df: pd.DataFrame) -> int:
    return int((df.astype(str).apply(lambda s: s.str.strip().eq("") | s.str.strip().str.lower().isin(["nan", "none", "null", "nat"]))).sum().sum())


def _raw_json_nulls(df: pd.DataFrame) -> int:
    if "raw_json" not in df.columns:
        return 0
    return int(df["raw_json"].astype(str).str.count(r"\bnull\b").sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--strict", action="store_true")
    ns = ap.parse_args()
    root = Path(ns.output_root)
    files = []
    if root.is_file():
        files = [root]
    else:
        for pat in ["agent_features/**/*.csv", "agent_features_all.csv", "eval_team_schema_*.csv", "eval_close_direction_detail_*.csv", "eval_excess20d_direction_detail_*.csv"]:
            files.extend(root.glob(pat))
    problems = []
    for f in sorted(set(files)):
        try:
            df = pd.read_csv(f, encoding="utf-8-sig", dtype=str, keep_default_na=False)
            blank = _blank_count(df)
            raw_null = _raw_json_nulls(df)
            signal_missing = 0
            rec_missing = 0
            if "signal" in df.columns:
                signal_missing = int(df["signal"].astype(str).str.strip().eq("").sum())
            if "recommendation" in df.columns:
                rec_missing = int(df["recommendation"].astype(str).str.strip().eq("").sum())
            row = {"file": str(f), "rows": len(df), "blank_like_cells": blank, "raw_json_null_tokens": raw_null, "signal_missing": signal_missing, "recommendation_missing": rec_missing}
            print(json.dumps(row, ensure_ascii=False))
            if blank or raw_null or signal_missing or rec_missing:
                problems.append(row)
        except Exception as exc:
            row = {"file": str(f), "error": f"{type(exc).__name__}: {exc}"}
            print(json.dumps(row, ensure_ascii=False))
            problems.append(row)
    print(f"[v42-null-check] files={len(files)} problems={len(problems)}")
    return 1 if ns.strict and problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

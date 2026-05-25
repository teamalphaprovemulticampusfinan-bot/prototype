from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def num(s: Any) -> float | None:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return None
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None


def pct(n: Any, d: Any) -> float | None:
    n1, d1 = num(n), num(d)
    if n1 is None or d1 in (None, 0):
        return None
    return n1 / d1 * 100.0


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)


def first_existing(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def latest_file(patterns: list[str], base: Path) -> Path | None:
    files: list[Path] = []
    for pat in patterns:
        files.extend(base.glob(pat))
    files = [p for p in files if p.is_file() and p.stat().st_size > 0]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def standardize_financial(finance_dir: Path, company: str) -> tuple[str, int]:
    src = first_existing([
        finance_dir / f"{company}_재무데이터.csv",
        finance_dir / f"{company}_financial.csv",
        finance_dir / f"{company}_재무.csv",
    ]) or latest_file(["*_재무데이터.csv", "*_financial.csv"], finance_dir)

    if src is None:
        raise FileNotFoundError(f"financial source not found in {finance_dir}")

    df = read_csv_any(src)
    if df.empty:
        raise ValueError(f"financial source is empty: {src}")

    df.columns = [str(c).strip() for c in df.columns]
    if "year" not in df.columns:
        raise ValueError(f"financial source has no year column: {src}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"]).copy()
    df["year"] = df["year"].astype(int)
    df = df.sort_values("year")

    out = pd.DataFrame()
    out["company"] = company
    out["year"] = df["year"]
    out["fs_div_used"] = df.get("fs_div_used", "CFS")

    for c in [
        "sales", "operating_income", "net_income", "total_assets", "total_liabilities", "total_equity",
        "current_assets", "current_liabilities", "ocf", "capex", "fcf",
    ]:
        out[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.NA

    if out["sales"].notna().any():
        out["sales_growth_%"] = out["sales"].pct_change().fillna(0) * 100
    else:
        out["sales_growth_%"] = pd.NA

    if "operating_margin_%" in df.columns:
        out["operating_margin_%"] = pd.to_numeric(df["operating_margin_%"], errors="coerce")
    elif "영업이익률" in df.columns:
        out["operating_margin_%"] = pd.to_numeric(df["영업이익률"], errors="coerce")
    else:
        out["operating_margin_%"] = [pct(a, b) for a, b in zip(out["operating_income"], out["sales"])]

    out["net_margin_%"] = [pct(a, b) for a, b in zip(out["net_income"], out["sales"])]

    if "debt_ratio_%" in df.columns:
        out["debt_ratio_%"] = pd.to_numeric(df["debt_ratio_%"], errors="coerce")
    elif "부채비율" in df.columns:
        out["debt_ratio_%"] = pd.to_numeric(df["부채비율"], errors="coerce")
    else:
        out["debt_ratio_%"] = [pct(a, b) for a, b in zip(out["total_liabilities"], out["total_equity"])]

    out["current_ratio_%"] = [pct(a, b) for a, b in zip(out["current_assets"], out["current_liabilities"])]

    if "ROE_%" in df.columns:
        out["ROE_%"] = pd.to_numeric(df["ROE_%"], errors="coerce")
    elif "ROE" in df.columns:
        out["ROE_%"] = pd.to_numeric(df["ROE"], errors="coerce")
    else:
        out["ROE_%"] = [pct(a, b) for a, b in zip(out["net_income"], out["total_equity"])]

    target = finance_dir / f"{company}_재무.csv"
    out.to_csv(target, index=False, encoding="utf-8-sig")
    return str(target), len(out)


def standardize_stock(finance_dir: Path, company: str, stock_code: str, market: str) -> tuple[str, int]:
    src = first_existing([
        finance_dir / f"{company}_stock.csv",
        finance_dir / f"{company}_주식.csv",
    ]) or latest_file(["*_stock.csv", "*_price*.csv"], finance_dir)

    if src is None:
        raise FileNotFoundError(f"stock source not found in {finance_dir}")

    df = read_csv_any(src)
    if df.empty:
        raise ValueError(f"stock source is empty: {src}")
    df.columns = [str(c).strip() for c in df.columns]

    colmap = {
        "날짜": "Date",
        "시가": "Open",
        "고가": "High",
        "저가": "Low",
        "종가": "Close",
        "거래량": "Volume",
        "수익률": "Change",
    }
    for old, new in colmap.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    if "Date" not in df.columns:
        raise ValueError(f"stock source has no Date/날짜 column: {src}")
    if "Close" not in df.columns:
        raise ValueError(f"stock source has no Close/종가 column: {src}")

    out = pd.DataFrame()
    out["회사명"] = company
    out["종목코드"] = str(stock_code).zfill(6)
    out["시장"] = str(market or "")
    out["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        out[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.NA

    close = pd.to_numeric(out["Close"], errors="coerce")
    change = pd.to_numeric(df["Change"], errors="coerce") if "Change" in df.columns else close.pct_change()
    out["Change"] = change.fillna(0)
    out["VKOSPI"] = pd.to_numeric(df["VKOSPI"], errors="coerce") if "VKOSPI" in df.columns else pd.NA
    out["일수익률_%"] = out["Change"] * 100
    out["누적최고가"] = close.cummax()
    out["드로다운_%"] = ((close / close.cummax()) - 1.0) * 100
    out["거래량_20일평균"] = pd.to_numeric(out["Volume"], errors="coerce").rolling(20, min_periods=1).mean()
    out["거래량_이동평균대비비율"] = pd.to_numeric(out["Volume"], errors="coerce") / out["거래량_20일평균"].replace(0, pd.NA)
    out = out.dropna(subset=["Date", "Close"]).sort_values("Date")

    target = finance_dir / f"{company}_주식.csv"
    out.to_csv(target, index=False, encoding="utf-8-sig")
    return str(target), len(out)


def main() -> int:
    p = argparse.ArgumentParser(description="Convert finance_intake outputs into finance_agent input CSV names/schema.")
    p.add_argument("--company-dir", required=True)
    p.add_argument("--company", required=True)
    p.add_argument("--stock-code", required=True)
    p.add_argument("--market", default="")
    p.add_argument("--field", default="반도체")
    args = p.parse_args()

    finance_dir = DATA / args.field / args.company / "finance"
    finance_dir.mkdir(parents=True, exist_ok=True)

    financial_path, financial_rows = standardize_financial(finance_dir, args.company)
    stock_path, stock_rows = standardize_stock(finance_dir, args.company, args.stock_code, args.market)

    manifest = {
        "status": "OK",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_dir": args.company_dir,
        "company": args.company,
        "stock_code": str(args.stock_code).zfill(6),
        "market": args.market,
        "financial_path": financial_path,
        "financial_rows": financial_rows,
        "stock_path": stock_path,
        "stock_rows": stock_rows,
    }
    path = finance_dir / "finance_standardize_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

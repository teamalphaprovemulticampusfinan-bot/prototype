from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd


COLUMN_ALIASES = {
    "날짜": "date",
    "일자": "date",
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "수정종가": "close",
    "현재가": "close",
    "거래량": "volume",
    "시가총액": "market_cap",
    "수익률": "return",
    "시장수익률": "market_return",
    "이상수익률": "abnormal_return",
    "최대낙폭": "mdd",
    "20일이동평균": "ma20",
    "60일이동평균": "ma60",
    "20일이평비율": "ma20_ratio",
    "60일이평비율": "ma60_ratio",
    "VIX": "vix",
    "VKOSPI": "vkospi",
    "EPS": "eps",
    "PSR": "psr",
    "누적이상수익률_3일": "car_3",
    "누적이상수익률_5일": "car_5",
    "기관_순매매": "inst_net_buy",
    "외국인_순매매": "foreign_net_buy",
    "보유주수": "foreign_holding_shares",
    "보유율_%": "foreign_holding_pct",
}


def _read_csv_any(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    last_error: Exception | None = None

    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(p, encoding=enc)
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error

    return pd.read_csv(p)


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lstrip("\ufeff") for c in out.columns]
    existing = set(out.columns)
    rename_map = {
        col: alias
        for col in out.columns
        if (alias := COLUMN_ALIASES.get(col)) and alias not in existing
    }
    if rename_map:
        out = out.rename(columns=rename_map)
    return out


def _infer_company_name_from_path(path: str | Path) -> str:
    p = Path(path)
    stem = p.stem

    for suffix in (
        "_재무데이터",
        "_finance",
        "_stock",
        "_주가",
        "_재무",
        "_주식",
    ):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    if stem:
        return stem

    if p.parent.name and p.parent.name != "finance":
        return p.parent.name

    if p.parent.parent.name:
        return p.parent.parent.name

    return "unknown_company"


def _ensure_finance_agent_columns(df: pd.DataFrame, path: str | Path) -> pd.DataFrame:
    """Add metadata columns that are not part of the fixed finance CSV schema."""
    out = _clean_columns(df)

    if "company" not in out.columns:
        out["company"] = _infer_company_name_from_path(path)

    if "fs_div_used" not in out.columns:
        out["fs_div_used"] = "CFS"

    return out


def calculate_annual_stock_metrics(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date")
    df["year"] = df["date"].dt.year

    results = []

    for year, group in df.groupby("year"):
        group = group.sort_values("date")
        close = pd.to_numeric(group["close"], errors="coerce").dropna()

        if close.empty:
            continue

        start_price = close.iloc[0]
        end_price = close.iloc[-1]

        if start_price in (0, None) or pd.isna(start_price):
            annual_return = 0.0
        else:
            annual_return = ((end_price / start_price) - 1) * 100

        cumulative_max = close.cummax()
        drawdown = ((close - cumulative_max) / cumulative_max) * 100
        annual_mdd = drawdown.min()

        results.append({
            "year": int(year),
            "annual_return_%": round(float(annual_return), 2),
            "annual_mdd_%": round(float(annual_mdd), 2),
        })

    return results


def _summarize_stock_by_year(df: pd.DataFrame) -> list[dict]:
    """연도별 주가·거래량·변동성 핵심 통계를 집계합니다."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["year"] = df["date"].dt.year
    summaries = []

    for year, grp in df.groupby("year"):
        grp = grp.sort_values("date")
        close = pd.to_numeric(grp["close"], errors="coerce").dropna()

        if close.empty:
            continue

        entry: dict[str, Any] = {"year": int(year)}
        entry["close_start"] = round(float(close.iloc[0]), 2)
        entry["close_end"] = round(float(close.iloc[-1]), 2)
        entry["close_high"] = round(float(close.max()), 2)
        entry["close_low"] = round(float(close.min()), 2)

        if "volume" in grp.columns:
            entry["volume_mean"] = round(float(pd.to_numeric(grp["volume"], errors="coerce").mean()), 0)

        if "sales_growth" in grp.columns:
            sales_growth = pd.to_numeric(grp["sales_growth"], errors="coerce").dropna()
            if not sales_growth.empty:
                entry["sales_growth"] = round(float(sales_growth.iloc[-1]), 2)

        if "ma20_ratio" in grp.columns:
            entry["ma20_ratio_mean"] = round(float(pd.to_numeric(grp["ma20_ratio"], errors="coerce").mean()), 4)

        if "vkospi" in grp.columns and grp["vkospi"].notna().any():
            entry["vkospi_mean"] = round(float(pd.to_numeric(grp["vkospi"], errors="coerce").mean()), 2)

        summaries.append(entry)

    return summaries


# 데이터 입력 기간 로직 추가
# 기준 연도(year)까지만 재무 데이터 사용
# 예: year=2024 -> 2024년 이하만 유지, 2025 이후 제거
def load_finance_data(path: str, year: int = 2024) -> dict[str, Any]:
    df = _read_csv_any(path)
    df = _ensure_finance_agent_columns(df, path)

    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")

    if df.empty:
        raise ValueError(f"finance csv is empty after cleaning: {path}")

    if "year" not in df.columns:
        raise KeyError(f"finance csv has no 'year' column: {path}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"]).copy()
    df["year"] = df["year"].astype(int)
    df = df[df["year"] <= year]

    if df.empty:
        raise ValueError(f"finance csv has no usable rows up to {year}: {path}")

    meta = {
        "company_name": str(df.iloc[0].get("company") or _infer_company_name_from_path(path)),
        "classification": str(df.iloc[0].get("fs_div_used") or "CFS"),
    }

    df = df.drop(["company", "fs_div_used"], axis=1, errors="ignore")
    finance_data = df.to_dict(orient="records")

    return {
        "meta": meta,
        "finance_data": finance_data,
    }


# 데이터 입력 기간 로직 추가
# 기준 월(year_month) 이전 데이터만 사용
# 예: year_month="2025-07"
# -> 2025-06-30까지 유지
# -> 2025-07-01 이후 데이터 제거
def load_stock_data(path: str, year_month: str = "2025-06") -> dict[str, Any]:
    df = _read_csv_any(path)
    df = _clean_columns(df)

    if "date" not in df.columns:
        raise KeyError(f"stock csv has no 'date' column: {path}")

    if "close" not in df.columns:
        raise KeyError(f"stock csv has no 'close' column: {path}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df[df["date"] >= "2023-01-01"]

    month_start = pd.to_datetime(f"{year_month}-01", format="%Y-%m-%d", errors="raise")
    df = df[df["date"] < month_start]

    df = df.sort_values("date")

    if df.empty:
        raise ValueError(f"stock csv has no usable rows after 2023-01-01 before {year_month}: {path}")

    annual_metrics = calculate_annual_stock_metrics(df)
    yearly_summary = _summarize_stock_by_year(df)

    inferred_company = _infer_company_name_from_path(path)

    meta = {
        "company_name": str(df.iloc[0].get("company") or inferred_company),
        "ticker": str(df.iloc[0].get("ticker") or ""),
        "market": str(df.iloc[0].get("market") or ""),
    }

    df_clean = df.drop(["company", "ticker", "market"], axis=1, errors="ignore")

    latest_date = df_clean["date"].max()
    month_ago = latest_date - timedelta(days=30)
    recent_df = df_clean[df_clean["date"] >= month_ago].copy()
    recent_df["date"] = recent_df["date"].dt.strftime("%Y-%m-%d")
    recent_1m = recent_df.to_dict(orient="records")

    return {
        "meta": meta,
        "recent_1m": recent_1m,
        "yearly_summary": yearly_summary,
        "annual_metrics": annual_metrics,
    }


def get_stock_data_range(path: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """에이전트가 추가 요청한 기간의 원 데이터를 반환합니다."""
    df = _read_csv_any(path)
    df = _clean_columns(df)

    if "date" not in df.columns:
        raise KeyError(f"stock csv has no 'date' column: {path}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    df = df.sort_values("date")
    df = df.drop(["company", "ticker", "market"], axis=1, errors="ignore")
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")


def check_warning_stock(path: str, company_name: str) -> dict[str, Any]:
    df = _read_csv_any(path)
    df = _clean_columns(df)

    if "종목명" not in df.columns:
        return {
            "warning": False,
            "message": None,
            "source_date": None,
        }

    matched = df[df["종목명"].astype(str).str.strip() == company_name.strip()]

    if matched.empty:
        return {
            "warning": False,
            "message": None,
            "source_date": None,
        }

    latest_row = matched.iloc[0]

    return {
        "warning": True,
        "message": f"{company_name}: 투자경고종목 목록에 포함되어 있으므로 단기 과열 및 변동성 확대 가능성에 유의해야 합니다.",
        "date": str(latest_row.get("공시일")),
        "source": str(latest_row.get("출처")),
    }

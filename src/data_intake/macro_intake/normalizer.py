# normalizer.py

from __future__ import annotations

import re
from typing import Any

import pandas as pd


_TEXT_COLUMNS = {"title", "url", "source", "domain", "category", "country", "type", "status", "summary", "note", "metric"}
_BAD_CHARS = ("�", "瑜", "섏", "寃", "낃", "?ы", "#U")


_KNOWN_MOJIBAKE_REPLACEMENTS = {
    "?ы넗瑜섏닔?낃?寃⑹???": "희토류수입가격지수",
    "?토류수??격???": "희토류수입가격지수",
    "?토류수입가격지수": "희토류수입가격지수",
    "?ы넗瑜": "희토류",
    "?토류": "희토류",
    "수??격": "수입가격",
    "寃⑹": "가격",
}


def _korean_score(text: str) -> int:
    return sum(1 for ch in text if "가" <= ch <= "힣") - sum(text.count(ch) * 3 for ch in _BAD_CHARS)


def repair_mojibake(value: Any) -> Any:
    """Repair common UTF-8/CP949 mojibake before macro_공통.csv is written.

    The rare-earth collector occasionally produced already-corrupted Korean text such as
    '?ы넗瑜섏닔?낃?寃⑹???'. Once '?' replaces bytes the original first syllable cannot be
    recovered algorithmically, so we combine safe codec round-trips with a tiny known-term
    dictionary for the macro domain.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    if not isinstance(value, str):
        return value

    text = re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), value)
    for bad, good in _KNOWN_MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)

    candidates = [text]
    for enc, dec in (("cp949", "utf-8"), ("euc-kr", "utf-8"), ("utf-8", "cp949")):
        try:
            candidates.append(text.encode(enc, errors="ignore").decode(dec, errors="ignore"))
        except Exception:
            pass

    best = max(candidates, key=_korean_score)
    for bad, good in _KNOWN_MOJIBAKE_REPLACEMENTS.items():
        best = best.replace(bad, good)
    best = re.sub(r"\s+", " ", best).strip()
    return best


def clean_text_frame(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return df
    out = df.copy()
    out.columns = [str(repair_mojibake(c)).strip() for c in out.columns]
    for col in out.columns:
        if out[col].dtype == "object" or col.lower() in _TEXT_COLUMNS:
            out[col] = out[col].map(repair_mojibake)
    return out


def parse_date_value(x):
    """
    ECOS 분기/월/일자 형식 처리.
    이미 datetime이면 그대로 반환.
    """
    if pd.isna(x):
        return pd.NaT

    if isinstance(x, pd.Timestamp):
        return x

    raw = str(x).strip()

    for q, m in [("Q1", "01"), ("Q2", "04"), ("Q3", "07"), ("Q4", "10")]:
        if q in raw:
            return raw.replace(q, "") + m + "01"

    if len(raw) == 6 and raw.isdigit():
        return raw + "01"

    return raw


def normalize_date(df):
    if df is None or df.empty:
        return df

    if "date" in df.columns:
        df["date"] = df["date"].apply(parse_date_value)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["date"] = df["date"].dt.tz_localize(None)

    return df


def normalize_numeric(df):
    if df is None or df.empty:
        return df

    for col in df.columns:
        if col != "date" and str(col).lower() not in _TEXT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def drop_invalid_dates(df):
    if df is None or df.empty:
        return df

    if "date" in df.columns:
        df = df.dropna(subset=["date"])

    return df


def aggregate_duplicate_dates(df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Keep one row per date for time-series frames.

    Multiple ECOS/FRED/yfinance calls can occasionally return duplicate dates after date
    normalization. Duplicates slow down outer merges and create day/month mismatches, so numeric
    columns are averaged and text columns keep the first non-empty value.
    """
    if df is None or df.empty or "date" not in df.columns:
        return df
    if not df["date"].duplicated().any():
        return df

    numeric_cols = [c for c in df.columns if c != "date" and pd.api.types.is_numeric_dtype(df[c])]
    text_cols = [c for c in df.columns if c != "date" and c not in numeric_cols]

    agg: dict[str, Any] = {c: "mean" for c in numeric_cols}
    for col in text_cols:
        agg[col] = lambda s: next((x for x in s if pd.notna(x) and str(x).strip()), pd.NA)
    return df.groupby("date", as_index=False).agg(agg)


def sort_by_date(df, ascending=True):
    if df is None or df.empty:
        return df

    if "date" in df.columns:
        df = df.sort_values("date", ascending=ascending).reset_index(drop=True)

    return df


def normalize(df):
    """
    일반 시계열 데이터 정리용.
    ECOS, FRED, yfinance, OECD, 희토류, 헬륨 수치 데이터에 사용.
    """
    if df is None or df.empty:
        return df

    df = clean_text_frame(df.copy())
    df = normalize_date(df)
    df = normalize_numeric(df)
    df = drop_invalid_dates(df)
    df = aggregate_duplicate_dates(df)
    df = sort_by_date(df, ascending=True)

    return df


def normalize_news(df):
    """뉴스 / 규제 데이터 정리용."""
    if df is None or df.empty:
        return df

    df = clean_text_frame(df.copy())

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

    text_cols = ["title", "url", "source", "domain", "category", "country", "type", "status"]

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).map(repair_mojibake).str.strip()

    if "title" in df.columns:
        df = df[df["title"] != ""]

    if "date" in df.columns:
        df = df.sort_values("date", ascending=False).reset_index(drop=True)

    return df


def normalize_regulation(df):
    """규제 공고 데이터 정리용."""
    return normalize_news(df)


def normalize_rare_earth(df):
    """희토류 데이터 정리용."""
    return normalize(df)


def normalize_helium(df):
    """헬륨 데이터 정리용."""
    return normalize(df)

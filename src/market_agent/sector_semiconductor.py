from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import re

import pandas as pd

from common.data_paths import ROOT_DIR, field_common_dir, rel_project_path


DAILY_FILENAME = "market_semiconductor_daily.csv"


def _decode_escaped_unicode(text: Any) -> str:
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text or ""))


def _sector_market_dir(field: str = "반도체") -> Path:
    canonical = field_common_dir("market", field=field, create=False)
    if canonical.exists():
        return canonical
    data_dir = ROOT_DIR / "data"
    if data_dir.exists():
        for child in data_dir.iterdir():
            if child.is_dir() and _decode_escaped_unicode(child.name) == field:
                candidate = child / "_sector_common" / "market"
                if candidate.exists():
                    return candidate
    return field_common_dir("market", field=field, create=True)


def _read_csv_safe(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    return pd.DataFrame()


def resolve_market_semiconductor_daily_path(field: str = "반도체") -> Path | None:
    env_path = os.getenv("MARKET_SEMICONDUCTOR_DAILY_PATH", "").strip()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend([
        ROOT_DIR / "data" / "market_excel" / DAILY_FILENAME,
        _sector_market_dir(field) / DAILY_FILENAME,
        ROOT_DIR / "data" / "market_excel" / "market_external_daily_v44.csv",
        _sector_market_dir(field) / "market_external_daily_v44.csv",
    ])
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                return path
        except Exception:
            continue
    return None


def _as_number(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        value = float(value)
        return int(value) if value.is_integer() else value
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        num = float(text)
    except Exception:
        return None
    return int(num) if num.is_integer() else num


def _pick(row: dict[str, Any], candidates: list[str]) -> Any:
    lower_map = {str(k).lower(): k for k in row.keys()}
    for name in candidates:
        key = lower_map.get(name.lower())
        if key is not None:
            value = row.get(key)
            if value is not None and not (isinstance(value, float) and pd.isna(value)) and str(value).strip() != "":
                return value
    # Last resort: suffix match because data_intake prefixes columns.
    for name in candidates:
        needle = name.lower()
        for lk, original in lower_map.items():
            if lk.endswith("__" + needle) or lk.endswith(needle):
                value = row.get(original)
                if value is not None and not (isinstance(value, float) and pd.isna(value)) and str(value).strip() != "":
                    return value
    return None


def load_market_semiconductor_snapshot(
    *,
    company: str | None = None,
    as_of_date: str | None = None,
    field: str = "반도체",
) -> dict[str, Any]:
    """Load one compact market-sector snapshot for market_agent evidence.

    The Market Agent uses this as an additional local source. It does not replace
    the existing workbook/DART/stock collection logic; it simply makes the new
    market_semiconductor_daily.csv visible to the market packet and auditor.
    """

    path = resolve_market_semiconductor_daily_path(field=field)
    if path is None:
        return {}

    df = _read_csv_safe(path)
    if df.empty or "date" not in df.columns:
        return {}

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    if as_of_date:
        cutoff = pd.to_datetime(as_of_date, errors="coerce")
        if not pd.isna(cutoff):
            df = df[df["date"] <= cutoff]
    if df.empty:
        return {}

    row = df.iloc[-1].to_dict()
    latest_date = pd.Timestamp(row.get("date")).strftime("%Y-%m-%d")

    mapping = {
        "sox_close": ["external__sox_close", "sox_close"],
        "nasdaq_close": ["external__nasdaq_close", "nasdaq_close"],
        "sp500_close": ["external__sp500_close", "sp500_close"],
        "vix_close": ["external__vix_yf_close", "vix_yf_close"],
        "korea_semiconductor_etf_close": ["external__korea_etf_close", "korea_etf_close"],
        "sector_cycle_signal": ["cycle__sector_cycle_signal", "sector_cycle_signal"],
        "sector_cycle_reliability": ["cycle__sector_cycle_reliability", "sector_cycle_reliability"],
        "sox_momentum": ["cycle__sox_momentum", "sox_momentum"],
        "chip_sales_momentum": ["cycle__chip_sales_momentum", "chip_sales_momentum"],
        "news_attention_signal": ["news__news_attention_signal", "news_attention_signal"],
        "news_count_current": ["news__news_count_current", "news_count_current"],
        "lag_window_news_signal": ["news__lag_window_news_signal", "lag_window_news_signal"],
        "market_signal": ["news__market_signal", "cycle__market_signal", "market_signal"],
        "market_weighted_signal": ["news__market_weighted_signal", "cycle__market_weighted_signal", "market_weighted_signal"],
    }

    compact: dict[str, Any] = {
        "latest_date": latest_date,
        "source_file": rel_project_path(path),
        "available_columns": int(len(df.columns)),
        "data_status": str(_pick(row, ["market_semiconductor_data_status"]) or "source_or_merged"),
        "source_min_date": str(_pick(row, ["market_semiconductor_source_min_date"]) or ""),
        "source_max_date": str(_pick(row, ["market_semiconductor_source_max_date"]) or ""),
    }

    for out_key, candidates in mapping.items():
        value = _pick(row, candidates)
        num = _as_number(value)
        compact[out_key] = num if num is not None else value

    # Include a few additional numeric fields if the expected names are absent.
    added = 0
    for col, value in row.items():
        if col == "date" or col in compact:
            continue
        num = _as_number(value)
        if num is None:
            continue
        simple = str(col).split("__")[-1]
        if simple in compact:
            continue
        compact[f"extra_{simple}"] = num
        added += 1
        if added >= 8:
            break

    return {k: v for k, v in compact.items() if v is not None and str(v) != "nan"}

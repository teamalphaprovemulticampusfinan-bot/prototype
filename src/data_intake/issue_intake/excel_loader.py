from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[3]
SECTOR_ISSUE_FILE = BASE_DIR / "data" / "반도체" / "_sector_common" / "data" / "Issue_Integration.xlsx"
LEGACY_ISSUE_FILE = BASE_DIR / "Issue_Integration.xlsx"
DEFAULT_ISSUE_FILE = SECTOR_ISSUE_FILE if SECTOR_ISSUE_FILE.exists() else LEGACY_ISSUE_FILE
DOWNLOAD_URL = "https://raw.githubusercontent.com/MuticampusFinance/IssueAgent_files/main/Issue_Integration.xlsx"

_cache: dict[tuple[str, str], dict[str, pd.DataFrame]] = {}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _resolve_as_of_date(as_of_date: str | None = None) -> str:
    return (
        _safe_str(as_of_date)
        or _safe_str(os.getenv("ISSUE_AS_OF_DATE"))
        or _safe_str(os.getenv("ISSUE_END_DATE"))
        or _safe_str(os.getenv("ALPHAPROVE_DATA_CUTOFF_DATE"))
    )


def filter_by_cutoff(df: pd.DataFrame, as_of_date: str | None, date_col: str = "date") -> pd.DataFrame:
    """Keep only rows whose date column is <= as_of_date.

    This mirrors src/issue_agent/excel_loader.py and is intentionally kept here
    so issue_intake and issue_agent use the same no-look-ahead rule.
    """
    cutoff_str = _resolve_as_of_date(as_of_date)
    if df is None or df.empty or not cutoff_str:
        return df
    if date_col not in df.columns:
        return df
    cutoff = pd.to_datetime(cutoff_str, errors="coerce")
    if pd.isna(cutoff):
        return df
    work = df.copy()
    dates = pd.to_datetime(work[date_col], errors="coerce")
    return work[(dates.isna()) | (dates <= cutoff)].copy()


def _download_file(path: Path) -> None:
    try:
        import requests

        print(f"[엑셀] 파일 없음 → 다운로드 시도: {DOWNLOAD_URL}")
        response = requests.get(DOWNLOAD_URL, timeout=30)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        print(f"[엑셀] 다운로드 완료: {path}")
    except Exception as exc:
        print(f"[엑셀] 다운로드 실패: {exc}")


def _resolve_excel_path(path: str | Path | None = None) -> Path:
    if path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
    for candidate in [SECTOR_ISSUE_FILE, LEGACY_ISSUE_FILE, DEFAULT_ISSUE_FILE]:
        if candidate.exists():
            return candidate
    _download_file(SECTOR_ISSUE_FILE)
    if SECTOR_ISSUE_FILE.exists():
        return SECTOR_ISSUE_FILE
    return DEFAULT_ISSUE_FILE


def _sheet_or_empty(xls: pd.ExcelFile, names: list[str]) -> pd.DataFrame:
    for name in names:
        if name in xls.sheet_names:
            return pd.read_excel(xls, sheet_name=name)
    return pd.DataFrame()


def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in ["date", "published_date", "일자", "날짜", "등록일", "게시일"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def load_excel(path: str | Path | None = None, as_of_date: str | None = None) -> dict[str, pd.DataFrame]:
    excel_path = _resolve_excel_path(path)
    cutoff = _resolve_as_of_date(as_of_date)
    cache_key = (str(excel_path.resolve()) if excel_path.exists() else str(excel_path), cutoff)
    if cache_key in _cache:
        return {k: v.copy() for k, v in _cache[cache_key].items()}

    if not excel_path.exists():
        print(f"[Issue Intake] 엑셀 원천 파일 없음: {excel_path}")
        payload = {"keywords": pd.DataFrame(), "news": pd.DataFrame(), "events": pd.DataFrame()}
        _cache[cache_key] = payload
        return {k: v.copy() for k, v in payload.items()}

    xls = pd.ExcelFile(excel_path)
    keywords = _sheet_or_empty(xls, ["keywords", "keyword", "키워드", "IssueKeywords"])
    news = _sheet_or_empty(xls, ["news", "뉴스", "IssueNews", "articles"])
    events = _sheet_or_empty(xls, ["events", "이벤트", "IssueEvents", "event"])

    keywords = _normalize_dates(keywords)
    news = _normalize_dates(news)
    events = _normalize_dates(events)

    # Apply no-look-ahead filtering only when date columns exist.
    keywords = filter_by_cutoff(keywords, cutoff, "date")
    news = filter_by_cutoff(news, cutoff, "published_date")
    if "published_date" not in news.columns:
        news = filter_by_cutoff(news, cutoff, "date")
    events = filter_by_cutoff(events, cutoff, "date")

    payload = {"keywords": keywords, "news": news, "events": events}
    _cache[cache_key] = {k: v.copy() for k, v in payload.items()}
    return {k: v.copy() for k, v in payload.items()}


def copy_to_sector_common(src: str | Path | None = None) -> Path:
    source = _resolve_excel_path(src)
    SECTOR_ISSUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if source.exists() and source.resolve() != SECTOR_ISSUE_FILE.resolve():
        shutil.copy2(source, SECTOR_ISSUE_FILE)
    return SECTOR_ISSUE_FILE

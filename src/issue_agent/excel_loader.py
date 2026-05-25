from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from .config import SETTINGS


ROOT_DIR = Path(__file__).resolve().parents[2]


def _resolve_excel_path() -> Path:
    configured_path = Path(SETTINGS.excel_path)
    if not configured_path.is_absolute():
        configured_path = ROOT_DIR / configured_path
    return configured_path


LOCAL_EXCEL_PATH = _resolve_excel_path()
EXCEL_URL = SETTINGS.excel_url


def ensure_excel_file() -> Path:
    if LOCAL_EXCEL_PATH.exists():
        return LOCAL_EXCEL_PATH

    LOCAL_EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not EXCEL_URL:
        raise FileNotFoundError(
            f"엑셀 파일이 없고 다운로드 URL도 없습니다: {LOCAL_EXCEL_PATH}"
        )

    response = requests.get(EXCEL_URL, timeout=30)
    response.raise_for_status()
    LOCAL_EXCEL_PATH.write_bytes(response.content)

    return LOCAL_EXCEL_PATH


def load_issue_frames():
    excel_path = ensure_excel_file()
    xls = pd.ExcelFile(excel_path)

    if len(xls.sheet_names) < 2:
        raise ValueError(f"엑셀 시트가 2개 이상 필요합니다. 현재 시트: {xls.sheet_names}")

    df_keywords = pd.read_excel(excel_path, sheet_name=xls.sheet_names[0])
    df_news = pd.read_excel(excel_path, sheet_name=xls.sheet_names[1])

    return df_keywords, df_news


def load_issue_data():
    return load_issue_frames()
def filter_by_cutoff(df: "pd.DataFrame", as_of_date: str, date_col: str = "date") -> "pd.DataFrame":
    import os
    import pandas as pd
    cutoff_str = as_of_date or os.getenv("ISSUE_AS_OF_DATE", "")
    if not cutoff_str:
        return df
    cutoff = pd.to_datetime(cutoff_str)
    if date_col not in df.columns:
        return df
    return df[pd.to_datetime(df[date_col], errors="coerce") <= cutoff].copy()

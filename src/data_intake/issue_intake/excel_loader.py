from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from .config import SETTINGS


ROOT_DIR = Path(__file__).resolve().parents[1]

_excel_cache: tuple[pd.DataFrame, pd.DataFrame] | None = None


def _resolve_excel_path() -> Path:
    path = Path(SETTINGS.excel_path)

    if not path.is_absolute():
        path = ROOT_DIR / path

    return path


def _download_excel(path: Path) -> None:
    print(f"[엑셀] 파일 없음 → 다운로드 시도: {SETTINGS.excel_url}")

    path.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(
        SETTINGS.excel_url,
        timeout=SETTINGS.request_timeout,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    path.write_bytes(response.content)

    print(f"[엑셀] 다운로드 완료: {path}")


def load_excel() -> tuple[pd.DataFrame, pd.DataFrame]:
    global _excel_cache

    if _excel_cache is not None:
        return _excel_cache

    path = _resolve_excel_path()

    if not path.exists():
        _download_excel(path)

    xls = pd.ExcelFile(path)

    if len(xls.sheet_names) < 2:
        raise ValueError(
            f"엑셀 시트가 2개 이상 필요합니다. 현재 시트: {xls.sheet_names}"
        )

    df_keywords = pd.read_excel(path, sheet_name=xls.sheet_names[0])
    df_news = pd.read_excel(path, sheet_name=xls.sheet_names[1])

    _excel_cache = (df_keywords, df_news)
    return _excel_cache


def load_company_names() -> list[str]:
    df_keywords, _ = load_excel()

    if df_keywords.empty or "기업명" not in df_keywords.columns:
        raise ValueError(
            "엑셀 시트1에 '기업명' 컬럼이 없습니다. "
            f"현재 컬럼: {list(df_keywords.columns)}"
        )

    companies = sorted(
        {
            str(name).strip()
            for name in df_keywords["기업명"].dropna().tolist()
            if str(name).strip()
        }
    )

    return companies


def load_keywords_for_company(company_name: str) -> list[dict]:
    df_keywords, _ = load_excel()

    if df_keywords.empty or "기업명" not in df_keywords.columns:
        return []

    company = str(company_name).strip()

    filtered = df_keywords[
        df_keywords["기업명"].astype(str).str.strip() == company
    ]

    return filtered.fillna("").to_dict(orient="records")
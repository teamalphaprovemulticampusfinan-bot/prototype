from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


DEFAULT_EXCEL_URL = (
    "https://raw.githubusercontent.com/MuticampusFinance/"
    "IssueAgent_files/main/Issue_Integration.xlsx"
)

RSS_SOURCES = {
    "Semiconductor Engineering": "https://semiengineering.com/feed/",
    "EE Times": "https://www.eetimes.com/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "MarketWatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "한국경제": "https://www.hankyung.com/feed/all-news",
}

DEFAULT_RSS_KEYWORDS = [
    "반도체",
    "semiconductor",
    "memory",
    "foundry",
    "HBM",
    "AI chip",
]

COMPANY_RSS_KEYWORDS = {
    "삼성전자": ["삼성전자", "samsung electronics", "HBM", "foundry"],
    "SK하이닉스": ["sk hynix", "dram", "HBM"],
}


@dataclass(frozen=True)
class Settings:
    enable_naver_news: bool = _env_bool("ENABLE_NAVER_NEWS", True)
    naver_client_id: str = _env_first("NAVER_CLIENT_ID", "NAVER_ID")
    naver_client_secret: str = _env_first("NAVER_CLIENT_SECRET", "NAVER_SECRET")

    request_timeout: int = _env_int("REQUEST_TIMEOUT", 15)

    excel_url: str = os.getenv("EXCEL_URL", DEFAULT_EXCEL_URL)
    excel_path: str = os.getenv("EXCEL_PATH", "workspace/data/Issue_Integration.xlsx")

    default_company: str = os.getenv("DEFAULT_COMPANY", "삼성전자")


SETTINGS = Settings()


def get_company_keywords(company_name: str) -> list[str]:
    custom = COMPANY_RSS_KEYWORDS.get(company_name, [])
    merged = [company_name, *custom, *DEFAULT_RSS_KEYWORDS]

    seen: set[str] = set()
    result: list[str] = []

    for keyword in merged:
        text = str(keyword).lower().strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)

    return result
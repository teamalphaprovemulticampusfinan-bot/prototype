from __future__ import annotations

import os
from dataclasses import dataclass

# Support both PYTHONPATH=<project_root> and PYTHONPATH=<project_root>/src.
try:
    from src.common.data_paths import field_data_file
except ModuleNotFoundError:
    from common.data_paths import field_data_file

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
    "삼성전자": ["삼성전자", "samsung electronics", "삼성 반도체", "foundry", "HBM"],
    "SK하이닉스": ["sk hynix", "sk하이닉스", "메모리", "HBM", "dram"],
    "한미반도체": ["한미반도체", "hanmi semiconductor", "tc bonder"],
    "하나머티리얼즈": ["하나머티리얼즈", "silicon parts", "반도체 소재"],
    "두산테스나": ["두산테스나", "테스트", "system semiconductor"],
    "리노공업": ["리노공업", "probe pin", "반도체 검사"],
    "네패스": ["네패스", "advanced packaging", "fan-out"],
    "하나마이크론": ["하나마이크론", "osat", "패키징"],
    "ISC": ["isc", "test socket", "반도체 소켓"],
    "원익IPS": ["원익ips", "반도체 장비"],
}


@dataclass(frozen=True)
class Settings:
    # Issue Agent LLM - 병렬 에이전트용 NVIDIA 설정 사용
    nvidia_api_key: str = _env_first(
        "ISSUE_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "OPENAI_API_KEY",
    )
    nvidia_base_url: str = _env_first(
        "ISSUE_NVIDIA_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "OPENAI_BASE_URL",
        default="https://integrate.api.nvidia.com/v1",
    )
    nvidia_model: str = _env_first(
        "ISSUE_NVIDIA_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        "OPENAI_MODEL",
        default="qwen/qwen3.5-122b-a10b",
    )

    # 뉴스 수집
    enable_naver_news: bool = _env_bool("ISSUE_ENABLE_NAVER_NEWS", True)
    naver_client_id: str = os.getenv("NAVER_CLIENT_ID", "").strip()
    naver_client_secret: str = os.getenv("NAVER_CLIENT_SECRET", "").strip()

    # NewsAPI는 429가 잦아서 기본 OFF. 나중에 필요하면 ISSUE_ENABLE_NEWS_API=1로 켜면 됨.
    enable_news_api: bool = _env_bool("ISSUE_ENABLE_NEWS_API", False)
    news_api_key: str = os.getenv("NEWS_API_KEY", "").strip()

    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15") or 15)

    excel_url: str = os.getenv("ISSUE_EXCEL_URL", DEFAULT_EXCEL_URL)
    excel_path: str = os.getenv("ISSUE_EXCEL_PATH", str(field_data_file("Issue_Integration.xlsx")))
    # 기본값은 삼성전자 대신 현재 micro-MVP 첫 기업인 네패스로 둔다.
    # 실제 실행은 `python main.py issue --company-dir nepes --company "네패스"`처럼
    # 명시 인자를 주는 것을 권장한다.
    default_company: str = os.getenv("ISSUE_COMPANY", "네패스")


SETTINGS = Settings()

# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_START ===
# Added by scripts/patch_universe30_dynamic_metadata.py
# Add generic RSS keywords for universe companies without hardcoding each one by hand.
try:
    from common.company_metadata import iter_company_metadata

    if "COMPANY_RSS_KEYWORDS" in globals():
        for _meta in iter_company_metadata():
            _keywords = [_meta.name]
            if _meta.peer_group:
                _keywords.append(_meta.peer_group)
            _keywords.extend(["반도체", "semiconductor"])
            COMPANY_RSS_KEYWORDS.setdefault(_meta.name, _keywords)

except Exception:
    pass
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_END ===

# === ALPHAPROVE_ISSUE25_DYNAMIC_METADATA_START ===
# Added by scripts/patch_issue_25_dynamic_metadata.py
# Purpose:
# - Extend Issue Agent RSS/search keywords from the locked Universe 30 CSV.
# - Avoid manually hardcoding 25 added companies into team member code.
# - Keep this block fail-safe so Issue Agent can still import even when metadata is unavailable.
try:
    from common.company_metadata import iter_company_metadata

    if "COMPANY_RSS_KEYWORDS" in globals():
        for _meta in iter_company_metadata():
            _keywords = [_meta.name]

            if _meta.peer_group:
                _keywords.append(_meta.peer_group)

                _pg = str(_meta.peer_group)
                if "후공정" in _pg or "패키징" in _pg:
                    _keywords.extend(["후공정", "패키징", "OSAT", "HBM"])
                if "테스트" in _pg or "소켓" in _pg:
                    _keywords.extend(["테스트", "검사", "소켓", "수율"])
                if "소재" in _pg:
                    _keywords.extend(["반도체 소재", "전구체", "식각", "증착", "고순도"])
                if "장비" in _pg:
                    _keywords.extend(["반도체 장비", "CAPEX", "공정장비"])
                if "팹리스" in _pg or "설계" in _pg:
                    _keywords.extend(["팹리스", "시스템반도체", "SoC", "MCU"])
                if "디자인" in _pg:
                    _keywords.extend(["디자인하우스", "디자인솔루션", "파운드리"])
                if "파운드리" in _pg:
                    _keywords.extend(["파운드리", "웨이퍼", "수율"])
                if "차량용" in _pg:
                    _keywords.extend(["차량용 반도체", "전장", "MCU"])

            _keywords.extend(["반도체", "semiconductor", "주가", "실적", "투자", "공시"])

            _deduped = []
            for _kw in _keywords:
                _kw = str(_kw).strip()
                if _kw and _kw not in _deduped:
                    _deduped.append(_kw)

            COMPANY_RSS_KEYWORDS[_meta.name] = _deduped
            COMPANY_RSS_KEYWORDS[_meta.slug] = _deduped

except Exception:
    # Issue Agent should still import even if optional universe metadata is unavailable.
    pass
# === ALPHAPROVE_ISSUE25_DYNAMIC_METADATA_END ===

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from common.data_paths import field_data_file

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
MARKET_EXCEL_DIR = Path(os.getenv("MARKET_EXCEL_DIR", "") or (BASE_DIR / "data" / "market_excel"))
MARKET_EXCEL_DIR.mkdir(parents=True, exist_ok=True)
MARKET_WORKBOOK_PATH = str(MARKET_EXCEL_DIR / "Market_통합.xlsx")

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


NVIDIA_PARALLEL_API_KEY = _env_first(
    "MARKET_NVIDIA_API_KEY",
    "NVIDIA_PARALLEL_API_KEY",
    "OPENAI_API_KEY",
)

NVIDIA_PARALLEL_BASE_URL = _env_first(
    "MARKET_NVIDIA_BASE_URL",
    "NVIDIA_PARALLEL_BASE_URL",
    "OPENAI_BASE_URL",
    default="https://integrate.api.nvidia.com/v1",
)

NVIDIA_PARALLEL_MODEL = _env_first(
    "MARKET_NVIDIA_MODEL",
    "NVIDIA_PARALLEL_MODEL",
    "OPENAI_MODEL",
    default="qwen/qwen3.5-122b-a10b",
)

OPENAI_API_KEY = NVIDIA_PARALLEL_API_KEY

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15") or 15)

MARKET_ENABLE_NAVER_NEWS = _env_bool("MARKET_ENABLE_NAVER_NEWS", True)
NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

MARKET_ENABLE_NEWS_API = _env_bool("MARKET_ENABLE_NEWS_API", False)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip()

DART_API_KEY = os.getenv("DART_API_KEY", "").strip()

PUBLIC_DATA_PORTAL_API_KEY = _env_first(
    "PUBLIC_DATA_PORTAL_API_KEY",
    "DATA_GO_KR_API_KEY",
    "MARKET_PUBLIC_DATA_API_KEY",
)
FMP_API_KEY           = _env_first("FMP_API_KEY", "FINANCIAL_MODELING_PREP_API_KEY")
FINNHUB_API_KEY       = _env_first("FINNHUB_API_KEY")
ALPHA_VANTAGE_API_KEY = _env_first("ALPHA_VANTAGE_API_KEY", "ALPHAVANTAGE_API_KEY")

STOCK_PROVIDER_ORDER = [
    item.strip()
    for item in os.getenv(
        "MARKET_STOCK_PROVIDER_ORDER",
        "public_data,fmp,finnhub,alpha_vantage",
    ).split(",")
    if item.strip()
]

MARKET_WORKBOOK_URL = os.getenv("MARKET_WORKBOOK_URL", "") 

TICKERS = {
    # 기존 반도체
    "한미반도체":  "042700.KQ",
    "덕산테코피아": "317330.KQ",
    "네패스":      "033640.KQ",
    "한솔케미칼":  "014680.KS",
    "엘티씨":      "170920.KQ",
    # 반도체 추가
    "DB하이텍":        "000990.KS",
    "미코":            "059090.KQ",
    "LX세미콘":        "108320.KS",
    "제주반도체":      "080220.KQ",
    "어보브반도체":    "102120.KQ",
    "텔레칩스":        "054450.KQ",
    "코아시아":        "045970.KQ",
    "가온칩스":        "399720.KQ",
    "원익IPS":         "240810.KQ",
    "유진테크":        "084370.KQ",
    "피에스케이":      "319660.KQ",
    "테스":            "095610.KQ",
    "GST":             "083450.KQ",
    "에스티아이":      "039440.KQ",
    "넥스틴":          "348210.KQ",
    "솔브레인":        "357780.KQ",
    "동진쎄미켐":      "005290.KQ",
    "원익머트리얼즈":  "104830.KQ",
    "이엔에프테크놀로지": "102710.KQ",
    "티씨케이":        "064760.KQ",
    "월덱스":          "101160.KQ",
    "ISC":             "095340.KQ",
    "SFA반도체":       "036540.KQ",
    "두산테스나":      "131970.KQ",
    "리노공업":        "058470.KQ",
    # 바이오
    "삼성바이오로직스": "207940.KS",
    "리가켐바이오":     "141080.KQ",
    "에스티팜":         "237690.KQ",
}

CORP_CODES = {
    # 기존 반도체
    "한미반도체":  "00109708",
    "덕산테코피아": "00164779",
    "네패스":      "00104856",
    "한솔케미칼":  "00104408",
    "엘티씨":      "00547583",
    # 반도체 추가
    "DB하이텍":        "00160843",
    "미코":            "00366942",
    "LX세미콘":        "00525934",
    "제주반도체":      "00447487",
    "어보브반도체":    "00591441",
    "텔레칩스":        "00423177",
    "코아시아":        "00271501",
    "가온칩스":        "01364747",
    "원익IPS":         "01135941",
    "유진테크":        "00531014",
    "피에스케이":      "01365825",
    "테스":            "00524421",
    "GST":             "00540863",
    "에스티아이":      "00298340",
    "넥스틴":          "01080252",
    "솔브레인":        "01489648",
    "동진쎄미켐":      "00118804",
    "원익머트리얼즈":  "00623661",
    "이엔에프테크놀로지": "00530185",
    "티씨케이":        "00245472",
    "월덱스":          "00580065",
    "ISC":             "00572905",
    "SFA반도체":       "00301246",
    "두산테스나":      "00563545",
    "리노공업":        "00369657",
    # 바이오
    "삼성바이오로직스": "00877059",
    "리가켐바이오":     "00842619",
    "에스티팜":         "00871833",
}

DEFAULT_COMPANIES = [
    # 반도체
    "네패스", "한미반도체", "덕산테코피아", "한솔케미칼", "엘티씨",
    "DB하이텍", "미코", "LX세미콘", "제주반도체", "어보브반도체",
    "텔레칩스", "코아시아", "가온칩스", "원익IPS", "유진테크",
    "피에스케이", "테스", "GST", "에스티아이", "넥스틴",
    "솔브레인", "동진쎄미켐", "원익머트리얼즈", "이엔에프테크놀로지",
    "티씨케이", "월덱스", "ISC", "SFA반도체", "두산테스나", "리노공업",
    # 바이오
    "삼성바이오로직스", "리가켐바이오", "에스티팜",
]

OECD_REGIONS = {
    "G20": "G20",
    "한국": "KOR",
    "미국": "USA",
    "중국": "CHN",
}

# === ALPHAPROVE_MARKET25_DYNAMIC_METADATA_START ===
# Added by scripts/patch_market_25_dynamic_metadata.py
# Purpose:
# - Extend Market Agent company/ticker mappings from the locked Universe 30 CSV.
# - Avoid manually hardcoding 25 additional companies into team member code.
# - Keep this block fail-safe so Market Agent can still import even when metadata is unavailable.
try:
    from common.company_metadata import iter_company_metadata

    for _meta in iter_company_metadata():
        if _meta.yf_ticker and "TICKERS" in globals():
            TICKERS[_meta.name] = _meta.yf_ticker
            TICKERS[_meta.slug] = _meta.yf_ticker

        if _meta.stock_code and "CORP_CODES" in globals():
            CORP_CODES[_meta.name] = _meta.stock_code
            CORP_CODES[_meta.slug] = _meta.stock_code

        if _meta.name and "DEFAULT_COMPANIES" in globals() and isinstance(DEFAULT_COMPANIES, list):
            if _meta.name not in DEFAULT_COMPANIES:
                DEFAULT_COMPANIES.append(_meta.name)

except Exception:
    # Market Agent should still import even if optional universe metadata is unavailable.
    pass
# === ALPHAPROVE_MARKET25_DYNAMIC_METADATA_END ===


# === ALPHAPROVE_MARKET_COMPANY_ALIAS_START ===
# Added to keep company-name variants such as "SFA 반도체" from producing
# empty ticker/corp_code lookups.  This block is intentionally additive.
import re as _re_alias

COMPANY_ALIASES = globals().get("COMPANY_ALIASES", {}) | {
    "nepes": "네패스", "hanmi": "한미반도체", "duksan": "덕산테코피아",
    "hansol": "한솔케미칼", "ltc": "엘티씨", "db_hitek": "DB하이텍",
    "dbhitek": "DB하이텍", "mico": "미코", "lxsemicon": "LX세미콘",
    "lx_semicon": "LX세미콘", "jeju": "제주반도체", "abov": "어보브반도체",
    "telechips": "텔레칩스", "coasia": "코아시아", "gaochips": "가온칩스",
    "wonik_ips": "원익IPS", "wonikips": "원익IPS", "eugene": "유진테크",
    "psk": "피에스케이", "tes": "테스", "gst": "GST", "sti": "에스티아이",
    "nextin": "넥스틴", "soulbrain": "솔브레인", "dongjin": "동진쎄미켐",
    "wonik_materials": "원익머트리얼즈", "wonikmaterials": "원익머트리얼즈",
    "enf": "이엔에프테크놀로지", "enftech": "이엔에프테크놀로지",
    "tck": "티씨케이", "worldex": "월덱스", "isc": "ISC",
    "sfa": "SFA반도체", "SFA 반도체": "SFA반도체", "sfa 반도체": "SFA반도체",
    "doosantesna": "두산테스나", "doosan_tesna": "두산테스나", "leeno": "리노공업",
}

# Keep known DART corp code for SFA반도체 even when old config did not have it.
if "TICKERS" in globals():
    TICKERS.setdefault("SFA반도체", "036540.KQ")
if "CORP_CODES" in globals():
    CORP_CODES.setdefault("SFA반도체", "00301246")


def normalize_company_token(value: object) -> str:
    text = "" if value is None else str(value).strip()
    text = text.replace("㈜", "").replace("주식회사", "")
    return _re_alias.sub(r"[^0-9A-Za-z가-힣]+", "", text).lower()


def resolve_company_key(company: object) -> str:
    raw = "" if company is None else str(company).strip()
    if raw in COMPANY_ALIASES:
        return COMPANY_ALIASES[raw]
    token = normalize_company_token(raw)
    if token in COMPANY_ALIASES:
        return COMPANY_ALIASES[token]
    if "TICKERS" in globals() and raw in TICKERS:
        return raw
    if "CORP_CODES" in globals() and raw in CORP_CODES:
        return raw
    for canonical in list(globals().get("TICKERS", {}).keys()):
        if normalize_company_token(canonical) == token:
            return canonical
    return raw


def _add_market_aliases(mapping: dict[str, str]) -> None:
    for canonical, value in list(mapping.items()):
        variants = {canonical, canonical.replace(" ", ""), normalize_company_token(canonical)}
        for alias, target in COMPANY_ALIASES.items():
            if target == canonical:
                variants.add(alias)
                variants.add(str(alias).replace(" ", ""))
                variants.add(normalize_company_token(alias))
        for variant in variants:
            if variant and variant not in mapping:
                mapping[variant] = value

if "TICKERS" in globals():
    _add_market_aliases(TICKERS)
if "CORP_CODES" in globals():
    _add_market_aliases(CORP_CODES)
# === ALPHAPROVE_MARKET_COMPANY_ALIAS_END ===

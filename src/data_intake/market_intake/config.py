from __future__ import annotations

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Path settings
# -----------------------------
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
MARKET_EXCEL_DIR = Path(os.getenv("MARKET_EXCEL_DIR", "") or (DATA_DIR / "market_excel"))
OUTPUT_DIR = MARKET_EXCEL_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MARKET_WORKBOOK_PATH = str(MARKET_EXCEL_DIR / "Market_통합.xlsx")
MARKET_WORKBOOK_URL = os.getenv(
    "MARKET_WORKBOOK_URL",
    "https://raw.githubusercontent.com/gyuhyeongkim412-creator/agent_fina/main/Market_통합.xlsx",
)

# -----------------------------
# API keys
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
DART_API_KEY = os.getenv("DART_API_KEY", "")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15") or 15)

# -----------------------------
# Company metadata
# -----------------------------
DEFAULT_COMPANIES = [
    "네패스", "한미반도체", "덕산테코피아", "한솔케미칼", "엘티씨",
    "DB하이텍", "미코", "LX세미콘", "제주반도체", "어보브반도체",
    "텔레칩스", "코아시아", "가온칩스", "원익IPS", "유진테크",
    "피에스케이", "테스", "GST", "에스티아이", "넥스틴",
    "솔브레인", "동진쎄미켐", "원익머트리얼즈", "이엔에프테크놀로지",
    "티씨케이", "월덱스", "ISC", "SFA반도체", "두산테스나", "리노공업",
]

TICKERS = {
    "네패스": "033640.KQ",
    "한미반도체": "042700.KQ",
    "덕산테코피아": "317330.KQ",
    "한솔케미칼": "014680.KS",
    "엘티씨": "170920.KQ",
    "DB하이텍": "000990.KS",
    "미코": "059090.KQ",
    "LX세미콘": "108320.KS",
    "제주반도체": "080220.KQ",
    "어보브반도체": "102120.KQ",
    "텔레칩스": "054450.KQ",
    "코아시아": "045970.KQ",
    "가온칩스": "399720.KQ",
    "원익IPS": "240810.KQ",
    "유진테크": "084370.KQ",
    "피에스케이": "319660.KQ",
    "테스": "095610.KQ",
    "GST": "083450.KQ",
    "에스티아이": "039440.KQ",
    "넥스틴": "348210.KQ",
    "솔브레인": "357780.KQ",
    "동진쎄미켐": "005290.KQ",
    "원익머트리얼즈": "104830.KQ",
    "이엔에프테크놀로지": "102710.KQ",
    "티씨케이": "064760.KQ",
    "월덱스": "101160.KQ",
    "ISC": "095340.KQ",
    "SFA반도체": "036540.KQ",
    "두산테스나": "131970.KQ",
    "리노공업": "058470.KQ",
}

# DART corp_code values used by market_intake.  Keep these separate from
# stock codes; do not overwrite them with ticker6/universe stock_code.
CORP_CODES = {
    "네패스": "00227333",
    "한미반도체": "00161383",
    "덕산테코피아": "01021666",
    "한솔케미칼": "00140955",
    "엘티씨": "00482693",
    "DB하이텍": "00160843",
    "미코": "00366942",
    "LX세미콘": "00525934",
    "제주반도체": "00447487",
    "어보브반도체": "00591441",
    "텔레칩스": "00423177",
    "코아시아": "00271501",
    "가온칩스": "01364747",
    "원익IPS": "01135941",
    "유진테크": "00531014",
    "피에스케이": "01365825",
    "테스": "00524421",
    "GST": "00540863",
    "에스티아이": "00298340",
    "넥스틴": "01080252",
    "솔브레인": "01489648",
    "동진쎄미켐": "00118804",
    "원익머트리얼즈": "00623661",
    "이엔에프테크놀로지": "00530185",
    "티씨케이": "00245472",
    "월덱스": "00580065",
    "ISC": "00572905",
    "SFA반도체": "00301246",
    "두산테스나": "00563545",
    "리노공업": "00369657",
}

COMPANY_ALIASES = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "duksan": "덕산테코피아",
    "hansol": "한솔케미칼",
    "ltc": "엘티씨",
    "db_hitek": "DB하이텍",
    "dbhitek": "DB하이텍",
    "mico": "미코",
    "lxsemicon": "LX세미콘",
    "lx_semicon": "LX세미콘",
    "jeju": "제주반도체",
    "abov": "어보브반도체",
    "telechips": "텔레칩스",
    "coasia": "코아시아",
    "gaochips": "가온칩스",
    "wonik_ips": "원익IPS",
    "wonikips": "원익IPS",
    "eugene": "유진테크",
    "psk": "피에스케이",
    "tes": "테스",
    "gst": "GST",
    "sti": "에스티아이",
    "nextin": "넥스틴",
    "soulbrain": "솔브레인",
    "dongjin": "동진쎄미켐",
    "wonik_materials": "원익머트리얼즈",
    "wonikmaterials": "원익머트리얼즈",
    "enf": "이엔에프테크놀로지",
    "enftech": "이엔에프테크놀로지",
    "tck": "티씨케이",
    "worldex": "월덱스",
    "isc": "ISC",
    "sfa": "SFA반도체",
    "SFA 반도체": "SFA반도체",
    "sfa 반도체": "SFA반도체",
    "doosantesna": "두산테스나",
    "doosan_tesna": "두산테스나",
    "leeno": "리노공업",
}


def normalize_company_token(value: object) -> str:
    text = "" if value is None else str(value).strip()
    text = text.replace("㈜", "").replace("주식회사", "")
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", text).lower()


def resolve_company_key(company: object) -> str:
    raw = "" if company is None else str(company).strip()
    if raw in COMPANY_ALIASES:
        return COMPANY_ALIASES[raw]
    token = normalize_company_token(raw)
    if token in COMPANY_ALIASES:
        return COMPANY_ALIASES[token]
    if raw in TICKERS or raw in CORP_CODES:
        return raw
    for canonical in list(TICKERS.keys()):
        if normalize_company_token(canonical) == token:
            return canonical
    return raw


def _add_aliases(mapping: dict[str, str]) -> None:
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


_add_aliases(TICKERS)
_add_aliases(CORP_CODES)

OECD_REGIONS = {
    "G20": "G20",
    "한국": "KOR",
    "미국": "USA",
    "중국": "CHN",
}

NEWS_KEYWORD = "반도체 업황"
MAX_NEWS_COUNT = 5
CSV_FILENAME = "market_dataset.csv"
CSV_ENCODING = "utf-8-sig"

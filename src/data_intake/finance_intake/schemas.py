# src/data_intake/finance_intake/schemas.py

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

WARNING_DIR  = BASE_DIR / "data" / "_global_common"
STOCK_DIR    = BASE_DIR / "data"   # runner.py에서 기업명 폴더를 붙임
FINANCIAL_DIR = BASE_DIR / "data"  # 동일
DATA_DIR = BASE_DIR / "data" / "finance_data"
VKOSPI_CSV = BASE_DIR / "data" / "_global_common" / "vkospi.csv"

CORP_CODES_PATH = Path(__file__).resolve().parent / "corp_codes.csv"
RND_PATH = Path(__file__).resolve().parent / "rnd.csv"

STOCK_CODES = [
    "000990",  # DB하이텍
    "102710",  # ENF테크놀로지
    "083450",  # GST
    "095340",  # ISC
    "108320",  # LX세미콘
    "036540",  # SFA반도체
    "399720",  # 가온칩스
    "033640",  # 네패스
    "348210",  # 넥스틴
    "213420",  # 덕산네오룩스
    "005290",  # 동진쎄미켐
    "131970",  # 두산테스나
    "187220",  # 디티앤씨
    "058470",  # 리노공업
    "059090",  # 미코
    "357780",  # 솔브레인
    "092600",  # 앤씨앤
    "102120",  # 어보브반도체
    "039440",  # 에스티아이
    "170920",  # 엘티씨
    "240810",  # 원익IPS
    "104830",  # 원익머트리얼즈
    "101160",  # 월덱스
    "084370",  # 유진테크
    "080220",  # 제주반도체
    "114570",  # 지스마트글로벌
    "045970",  # 코아시아
    "064760",  # 티씨케이
    "054450",  # 텔레칩스
    "319660",  # 피에스케이
    "042700",  # 한미반도체
    "014680",  # 한솔케미칼
]

WARNING_COLS = ["회사명", "종목코드", "구분", "지정일", "해제일", "비고"]

STOCK_DISPLAY_COLS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "market_cap",

    "return",
    "market_return",
    "abnormal_return",

    "mdd",

    "ma20",
    "ma60",

    "ma20_ratio",
    "ma60_ratio",

    "vix",
    "vkospi",

    "eps",
    "psr",

    "car_3",
    "car_5",

    "inst_net_buy",
    "foreign_net_buy",

    "foreign_holding_shares",
    "foreign_holding_pct",
]


@dataclass
class WarningConfig:
    mode: str = "update"
    days: int = 1
    url: str = "https://kind.krx.co.kr/investwarn/investattentwarnrisky.do?method=investattentwarnriskyMain"
    download_dir: Path = WARNING_DIR
    csv_path: Path = WARNING_DIR / "warning_data.csv"
    json_path: Path = WARNING_DIR / "warning_data.json"


@dataclass
class FinancialConfig:
    stock_code: str
    years: list[int]
    dart_api_key: str | None = None


@dataclass
class StockConfig:
    stock_code: str
    lookback_years: int = 3
    dart_start_year: int = 2021
    dart_api_key: str | None = None
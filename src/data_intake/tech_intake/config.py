# src/data_intake/tech_intake/config.py

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# =========================
# 기본 경로 설정
# =========================
# __file__ 기준: tech_intake → data_intake → src → project root
BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)  # API 키 읽기 전에 로드

DATA_DIR = BASE_DIR / "data" / "tech_data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DATA_DIR = DATA_DIR / "output"

for _path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DATA_DIR]:
    _path.mkdir(parents=True, exist_ok=True)


# =========================
# API 설정
# =========================
DART_API_KEY = os.getenv("DART_API_KEY")
KIPRIS_API_KEY = os.getenv("KIPRIS_API_KEY")

if not DART_API_KEY:
    raise ValueError("❌ DART_API_KEY 환경변수를 설정하세요.")

if not KIPRIS_API_KEY:
    logger.warning("KIPRIS_API_KEY가 설정되지 않았습니다. (특허 데이터 수집 비활성화)")


# =========================
# 요청 설정
# =========================
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
SLEEP_SECONDS = 0.5


# =========================
# 키워드 설정
# =========================
TECH_KEYWORDS = [
    "전구체",
    "고순도",
    "반도체",
    "배터리",
    "촉매",
    "공정",
    "소재",
    "박막",
]

PERFORMANCE_KEYWORDS = [
    "순도",
    "수율",
    "온도",
    "처리속도",
    "수명",
    "효율",
    "불량률",
]

CUSTOMER_KEYWORDS = [
    "납품",
    "공급",
    "고객사",
    "채택",
    "적용",
]


# =========================
# 정량화 기준
# =========================
RD_RATIO_THRESHOLD = {
    "high": 0.1,
    "medium": 0.05,
}

GROWTH_RATE_THRESHOLD = {
    "high": 0.2,
    "medium": 0.05,
}


# =========================
# 기타 설정
# =========================
LOG_LEVEL = "INFO"
MAX_TEXT_LENGTH = 100_000   # 가독성을 위해 언더스코어 구분
DEFAULT_ENCODING = "utf-8"


# =========================
# Extractor 키워드 설정
# =========================
PRODUCT_CONTEXT_KEYWORDS = [
    "주요 제품", "주요제품", "제품은", "제품으로", "제품으로는",
    "제품에는", "제품군", "포트폴리오", "생산ㆍ판매", "생산·판매",
]

PRODUCT_ALLOWLIST = {
    "TV", "모니터", "냉장고", "세탁기", "에어컨",
    "스마트폰", "태블릿", "웨어러블", "PC",
    "DRAM", "NAND Flash", "NAND", "Flash",
    "모바일AP", "카메라 센서칩", "System LSI",
    "Foundry", "OLED 패널", "OLED", "QD-OLED",
    "디지털 콕핏", "Digital Cockpit", "카오디오",
    "포터블 스피커", "네트워크시스템",
    "커넥티드카", "컨슈머 오디오", "프로페셔널 오디오 솔루션",
    "Galaxy", "갤럭시",
}

PRODUCT_STOPWORDS = {
    "사업", "부문", "제품", "서비스", "매출", "주요",
    "당사", "본사", "종속기업", "글로벌", "기업",
    "생산", "판매", "공급", "구성", "영위", "유지",
    "확대", "추진", "개발", "적용", "제공",
    "있습니다", "합니다", "다음과 같습니다", "또한",
    "통해", "위해", "등으로", "중심으로",
}

INDUSTRY_KEYWORDS = {
    "반도체", "모바일", "스마트폰", "가전", "디스플레이",
    "자동차", "전장", "네트워크", "통신", "AI",
    "데이터센터", "서버", "클라우드", "메모리",
    "파운드리", "오디오", "웨어러블",
}

CUSTOMER_KEYWORDS_EXTRACTOR = {
    "고객", "고객사", "거래처", "수요처", "파트너",
}

CERTIFICATION_KEYWORDS = {
    "인증", "ISO", "KS", "KC", "UL", "CE", "RoHS",
    "REACH", "환경 인증", "품질 인증", "안전 인증",
}

REFERENCE_CONTEXT_KEYWORDS = {
    "공급", "납품", "적용", "도입", "판매", "계약",
    "협력", "고객", "파트너", "사례", "레퍼런스",
}

EXPANSION_CONTEXT_KEYWORDS = {
    "신규", "확장", "진출", "적용처", "응용", "확대",
    "미래", "차세대", "성장", "신사업",
}

VALIDATION_STEP_KEYWORDS = {
    "시험", "인증", "고객평가", "고객 평가",
    "파일럿", "양산검증", "양산 검증",
    "검증", "평가", "테스트",
}
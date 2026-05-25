# src/data_intake/tech_intake/normalizer.py

import logging
import re
from dataclasses import replace
from typing import List, Optional

from .schemas import ExtractedTechItem

logger = logging.getLogger(__name__)

# 단위 추출 우선순위: 긴 단위부터 매칭해야 "백만원"이 "만원"보다 먼저 잡힘
_UNIT_PATTERNS = [
    "억원",
    "백만원",
    "만원",
    "%",
    "℃",
    "배",
    "시간",
    "개월",
    "ppm",
    "명",
    "건",
    "개",
    "회",
    "년",
    "도",
]

_UNIT_MAP = {
    "퍼센트": "%",
    "percent": "%",
    "도": "℃",
}


class TechDataNormalizer:
    """추출된 기술 데이터의 텍스트, 숫자, 단위를 정리하는 클래스"""

    def normalize(self, items: List[ExtractedTechItem]) -> List[ExtractedTechItem]:
        """ExtractedTechItem 리스트 전체 정규화 + 불량 후보 제거 + 중복 제거"""

        results = []

        for item in items:
            try:
                normalized = self.normalize_item(item)

                if not self.is_valid_item(normalized):
                    continue

                results.append(normalized)

            except Exception as e:
                logger.warning("normalize 실패, 원본 유지 — item=%s | %s", item.item_name, e)
                if self.is_valid_item(item):
                    results.append(item)

        results = self.deduplicate_items(results)

        logger.info("정규화 완료 — 입력=%d건, 출력=%d건", len(items), len(results))
        return results

    def normalize_item(self, item: ExtractedTechItem) -> ExtractedTechItem:
        """단일 항목 정규화 (원본 객체 불변, 새 객체 반환)"""

        cleaned_content = self.clean_text(item.content)
        cleaned_raw_value = self.clean_text(item.raw_value)

        value, unit = self.normalize_value_and_unit(
            raw_value=cleaned_raw_value,
            value=item.value,
            unit=item.unit,
        )

        return replace(
            item,
            content=cleaned_content,
            raw_value=cleaned_raw_value,
            value=value,
            unit=unit,
        )
    # ------------------------------------------------------------------
    # 후보 필터링 / 중복 제거
    # ------------------------------------------------------------------

    INVALID_CONTENT_PHRASES = {
        "있습니다",
        "합니다",
        "다음과 같습니다",
        "당사는",
        "또한",
        "통해",
        "위해",
        "구성되어",
        "영위",
        "생산",
        "판매",
        "제공",
        "유지",
        "확대",
        "추진",
        "및",
        "등을",
        "설계",
    }

    GENERIC_WORDS = {
        "제품",
        "서비스",
        "사업",
        "부문",
        "관련",
        "시장",
        "기술",
        "고객",
        "라인업",
        "포트폴리오",
        "기업",
        "종속기업",
    }

    def is_valid_item(self, item: ExtractedTechItem) -> bool:
        """정규화 후 실제 CSV에 저장할 만한 항목인지 검사"""

        content = self.clean_text(item.content)

        if not content:
            return False

        if len(content) < 2:
            return False

        if content in self.GENERIC_WORDS:
            return False

        # 제품명/서비스명은 문장 조각 제거를 강하게 적용
        if item.category == "핵심 제품/서비스" and item.metric == "제품명/서비스명":
            if any(p in content for p in self.INVALID_CONTENT_PHRASES):
                return False

            if len(content) > 30:
                return False

            if content.endswith(("다", "니다", "하고", "하며", "되는", "위한")):
                return False
        if item.category == "핵심 제품/서비스" and item.metric == "제품명/서비스명":
            if " 및 " in content or "등을" in content:
                return False
        return True

    def deduplicate_items(self, items: List[ExtractedTechItem]) -> List[ExtractedTechItem]:
        """company/category/item_name/content/metric 기준 중복 제거"""

        results = []
        seen = set()

        for item in items:
            key = (
                item.company,
                item.category,
                item.item_name,
                item.content,
                item.metric,
            )

            if key in seen:
                continue

            seen.add(key)
            results.append(item)

        return results
    # ------------------------------------------------------------------
    # 텍스트 정제
    # ------------------------------------------------------------------

    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """공백, 유니코드 공백, 불필요한 줄바꿈 정리"""

        if text is None:
            return None

        text = str(text)
        # 유니코드 공백 문자 전체 통일 (web_client와 동일 기준)
        text = re.sub(r"[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000\ufeff]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # ------------------------------------------------------------------
    # 값 / 단위 정규화
    # ------------------------------------------------------------------

    def normalize_value_and_unit(
        self,
        raw_value: Optional[str],
        value: Optional[float],
        unit: Optional[str],
    ) -> tuple[Optional[float], Optional[str]]:
        """
        raw_value에서 숫자와 단위 파싱

        예:
            "1,000억원" → (1000.0, "억원")
            "85%"       → (85.0, "%")
            "1.5배"     → (1.5, "배")
        """

        # raw_value 없으면 기존 value/unit 정규화만
        if not raw_value:
            return value, self.normalize_unit(unit)

        cleaned = raw_value.replace(",", "").strip()

        number_match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        parsed_value = float(number_match.group()) if number_match else value

        detected_unit = self.extract_unit(cleaned)
        resolved_unit = self.normalize_unit(detected_unit or unit)

        return parsed_value, resolved_unit

    def extract_unit(self, text: str) -> Optional[str]:
        """
        문자열에서 단위 추출 (긴 단위 우선 매칭)
        """

        for unit in _UNIT_PATTERNS:
            if unit in text:
                return unit

        return None

    # ------------------------------------------------------------------
    # 금액 단위 통일
    # ------------------------------------------------------------------

    def normalize_money_to_억원(
        self,
        value: Optional[float],
        unit: Optional[str],
    ) -> tuple[Optional[float], str]:
        """
        금액 단위를 억원으로 통일

        예:
            (100_000, "백만원") → (1_000.0, "억원")
            (1_000_000, "만원") → (100.0, "억원")
        """

        if value is None:
            return None, "억원"

        conversion = {
            "억원": 1,
            "백만원": 1 / 100,
            "만원": 1 / 10_000,
        }

        if unit in conversion:
            return value * conversion[unit], "억원"

        return value, unit or "억원"
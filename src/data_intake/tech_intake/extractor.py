# src/data_intake/tech_intake/extractor.py

import logging
import re
from typing import List, Optional, Tuple

from .config import TECH_KEYWORDS, PERFORMANCE_KEYWORDS
from .schemas import ExtractedVariable, ExtractedTechItem, RawTechData, SourceInfo

logger = logging.getLogger(__name__)


class TechDataExtractor:
    """사업보고서 XML 원문에서 기술 분석용 정보를 추출하는 클래스"""

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

    CUSTOMER_KEYWORDS = {
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

    def extract(self, raw_data: RawTechData) -> Tuple[List[ExtractedTechItem], List[ExtractedVariable]]:
        """RawTechData 1개에서 주요 항목 추출"""

        business_text = self.extract_business_section(raw_data.raw_text)
        logger.info("사업의 내용 추출 — company=%s, 길이=%d", raw_data.company, len(business_text))

        items: List[ExtractedTechItem] = []
        variables: List[ExtractedVariable] = []
        tech_items, tech_vars = self.extract_tech_keywords(raw_data, business_text)
        items.extend(tech_items)
        variables.extend(tech_vars)
        items.extend(self.extract_performance_numbers(raw_data, business_text))
        items.extend(self.extract_product_candidates(raw_data, business_text))

        # 추가 추출 항목
        items.extend(self.extract_customer_industries(raw_data, business_text))
        items.extend(self.extract_customers(raw_data, business_text))
        items.extend(self.extract_certifications(raw_data, business_text))
        items.extend(self.extract_reference_cases(raw_data, business_text))
        items.extend(self.extract_current_revenue_industries(raw_data, business_text))
        items.extend(self.extract_expansion_industries(raw_data, business_text))
        items.extend(self.extract_required_certifications(raw_data, business_text))
        items.extend(self.extract_validation_steps(raw_data, business_text))
        items.extend(self.extract_financial_numbers(raw_data, business_text))
        items.extend(self.extract_performance_comparison(raw_data, business_text))

        logger.info("추출 완료 — company=%s, 항목=%d건", raw_data.company, len(items))
        return items, variables

    # ------------------------------------------------------------------
    # 텍스트 전처리
    # ------------------------------------------------------------------

    def extract_business_section(self, xml_text: str) -> str:
        """XML 원문에서 '사업의 내용' 구간 추출"""

        text = self.clean_xml_text(xml_text)

        start_patterns = [
            "II. 사업의 내용",
            "Ⅱ. 사업의 내용",
            "사업의 내용",
        ]

        end_patterns = [
            "III. 재무에 관한 사항",
            "Ⅲ. 재무에 관한 사항",
            "재무에 관한 사항",
            "이사의 경영진단 및 분석의견",
        ]

        start_idx = self._find_first_index(text, start_patterns)
        if start_idx == -1:
            logger.warning("'사업의 내용' 섹션을 찾지 못해 전체 텍스트 사용")
            return text

        end_idx = self._find_first_index(text[start_idx:], end_patterns)
        if end_idx == -1:
            return text[start_idx:]

        return text[start_idx: start_idx + end_idx]

    # extractor.py - clean_xml_text()

    def clean_xml_text(self, xml_text: str) -> str:
        if not xml_text:
            return ""

        text = re.sub(r"<[^>]+>", " ", xml_text)

        html_entities = {
            "&nbsp;": " ",
            "&#160;": " ",
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
        }

        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        # 줄바꿈을 공백으로 통일
        text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        text = re.sub(r"\s+", " ", text)
        return text.strip()
    # ------------------------------------------------------------------
    # 키워드 추출
    # ------------------------------------------------------------------

    def extract_tech_keywords(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> Tuple[List[ExtractedTechItem], List[ExtractedVariable]]:
        """기술 키워드 등장 빈도 추출"""

        items: List[ExtractedTechItem] = []
        variables: List[ExtractedVariable] = []

        for keyword in TECH_KEYWORDS:
            count = text.count(keyword)

            if count == 0:
                continue

            evidence = self._find_evidence_sentence(text, keyword)
            safe_keyword = re.sub(r"\s+", "_", keyword.strip())

            items.append(
                ExtractedTechItem(
                    company=raw_data.company,
                    category="대표 기술",
                    item_name="핵심 기술 키워드",
                    content=keyword,
                    metric="기술 키워드 등장 빈도",
                    raw_value=str(count),
                    value=float(count),
                    unit="회",
                    formula="사업보고서 내 키워드 등장 횟수",
                    source=self._make_source(raw_data, evidence=evidence),
                    confidence="medium",
                    status="extracted",
                )
            )

            variables.append(
                ExtractedVariable(
                    company_name=raw_data.company,
                    category="대표 기술",
                    metric_name="기술 키워드 등장 빈도",
                    variable_name=f"keyword_count_{safe_keyword}",
                    raw_value=str(count),
                    value=float(count),
                    unit="회",
                    content=keyword,
                    source_type=f"{raw_data.source.major_source}|{raw_data.source.middle_source}",
                    source_name=raw_data.source.middle_source,
                    source_url=raw_data.source.source_url,
                    evidence_text=evidence,
                    confidence="medium",
                    status="extracted",
                )
            )

        logger.info("기술 키워드 추출 — items=%d건, variables=%d건", len(items), len(variables))
        return items, variables

    # ------------------------------------------------------------------
    # 성능 수치 추출
    # ------------------------------------------------------------------

    def extract_performance_numbers(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """순도 %, 온도 ℃, 수율 % 등 성능 수치 후보 추출"""

        items: List[ExtractedTechItem] = []
        seen: set[tuple[str, str, str]] = set()

        for keyword in PERFORMANCE_KEYWORDS:
            pattern = (
                rf"{re.escape(keyword)}"
                rf".{{0,40}}?"
                rf"(\d+(?:\.\d+)?)"
                rf"\s*(%|℃|도|배|시간|년|회|ppm|nm|㎚|GB|TB|ms|초)?"
            )

            matches = re.findall(pattern, text, flags=re.IGNORECASE)

            for value_str, unit in matches[:10]:
                unit = unit or None
                raw_value = f"{value_str}{unit or ''}"

                key = (keyword, value_str, unit or "")
                if key in seen:
                    continue

                seen.add(key)

                items.append(
                    ExtractedTechItem(
                        company=raw_data.company,
                        category="대표 기술",
                        item_name="핵심 성능 요소",
                        content=keyword,
                        metric="수치화 가능한 성능",
                        raw_value=raw_value,
                        value=float(value_str),
                        unit=unit,
                        formula=None,
                        source=self._make_source(
                            raw_data,
                            evidence=self._find_evidence_sentence(text, keyword),
                        ),
                        confidence="low",
                        status="extracted",
                    )
                )

        logger.info("성능 수치 추출 — %d건", len(items))
        return items

    # ------------------------------------------------------------------
    # 제품명 후보 추출
    # ------------------------------------------------------------------

    def extract_product_candidates(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """제품명/서비스명 후보 추출"""

        items: List[ExtractedTechItem] = []
        seen: set[str] = set()

        sentences = self._split_sentences(text)

        product_sentences = [
            sentence for sentence in sentences
            if any(keyword in sentence for keyword in self.PRODUCT_CONTEXT_KEYWORDS)
        ]

        if len(product_sentences) < 3:
            product_sentences.extend(
                sentence for sentence in sentences
                if "제품" in sentence and sentence not in product_sentences
            )

        for sentence in product_sentences[:40]:
            candidates = self._extract_known_products(sentence)
            candidates.extend(self._extract_comma_separated_products(sentence))

            for candidate in candidates:
                normalized = self._normalize_product_name(candidate)

                if not self._is_valid_product_name(normalized):
                    continue

                if normalized in seen:
                    continue

                seen.add(normalized)

                items.append(
                    ExtractedTechItem(
                        company=raw_data.company,
                        category="핵심 제품/서비스",
                        item_name="제품명/서비스명",
                        content=normalized,
                        metric="제품명/서비스명",
                        raw_value=None,
                        value=None,
                        unit=None,
                        formula=None,
                        source=self._make_source(raw_data, evidence=sentence[:300]),
                        confidence="medium" if normalized in self.PRODUCT_ALLOWLIST else "low",
                        status="extracted",
                    )
                )

        logger.info("제품명 후보 추출 — %d건", len(items))
        return items

    # ------------------------------------------------------------------
    # 추가 항목 추출
    # ------------------------------------------------------------------

    def extract_customer_industries(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """고객 산업/적용 산업 후보 추출"""

        items: List[ExtractedTechItem] = []

        for industry in sorted(self.INDUSTRY_KEYWORDS):
            if industry not in text:
                continue

            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="핵심 제품/서비스",
                    item_name="고객 산업",
                    content=industry,
                    metric="고객 산업",
                    evidence=self._find_evidence_sentence(text, industry),
                    confidence="low",
                )
            )

        logger.info("고객 산업 추출 — %d건", len(items))
        return items

    def extract_customers(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """고객사 후보 추출"""

        items: List[ExtractedTechItem] = []
        seen: set[str] = set()

        sentences = [
            sentence for sentence in self._split_sentences(text)
            if any(keyword in sentence for keyword in self.CUSTOMER_KEYWORDS)
        ]

        pattern = r"([가-힣A-Za-z0-9&.\- ]{2,30})\s*(?:고객사|고객|파트너|거래처)"

        for sentence in sentences[:50]:
            for match in re.findall(pattern, sentence):
                customer = match.strip()
                customer = re.sub(r"^(주요|글로벌|국내|해외)\s+", "", customer)

                if not self._is_valid_customer_name(customer):
                    continue

                if customer in seen:
                    continue

                seen.add(customer)

                items.append(
                    self._make_item(
                        raw_data=raw_data,
                        category="고객 구매 이유",
                        item_name="고객사",
                        content=customer,
                        metric="고객사",
                        evidence=sentence[:300],
                        confidence="low",
                    )
                )

        logger.info("고객사 후보 추출 — %d건", len(items))
        return items

    def extract_certifications(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """인증 관련 키워드 후보 추출"""

        items: List[ExtractedTechItem] = []

        for cert in sorted(self.CERTIFICATION_KEYWORDS):
            if cert not in text:
                continue

            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="경쟁 우위 요소/대체가능성",
                    item_name="인증",
                    content=cert,
                    metric="인증 종류",
                    evidence=self._find_evidence_sentence(text, cert),
                    confidence="low",
                )
            )

        logger.info("인증 추출 — %d건", len(items))
        return items

    def extract_reference_cases(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """공급/적용/도입 사례 문장 후보 추출"""

        items: List[ExtractedTechItem] = []
        seen: set[str] = set()

        for sentence in self._split_sentences(text):
            if not any(keyword in sentence for keyword in self.REFERENCE_CONTEXT_KEYWORDS):
                continue

            content = sentence[:300]

            if content in seen:
                continue

            seen.add(content)

            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="경쟁 우위 요소/대체가능성",
                    item_name="레퍼런스",
                    content=content,
                    metric="적용/공급 사례",
                    evidence=content,
                    confidence="low",
                )
            )

            if len(items) >= 20:
                break

        logger.info("레퍼런스 추출 — %d건", len(items))
        return items

    def extract_current_revenue_industries(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """현재 매출 발생 산업 후보 추출"""

        items: List[ExtractedTechItem] = []

        revenue_sentences = [
            sentence for sentence in self._split_sentences(text)
            if "매출" in sentence or "판매" in sentence or "생산" in sentence
        ]

        found: set[str] = set()

        for sentence in revenue_sentences:
            for industry in self.INDUSTRY_KEYWORDS:
                if industry in sentence:
                    found.add(industry)

        for industry in sorted(found):
            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="현재 활용 산업 + 확장 산업",
                    item_name="현재 매출 산업",
                    content=industry,
                    metric="현재 매출 산업",
                    evidence=self._find_evidence_sentence(text, industry),
                    confidence="low",
                )
            )

        logger.info("현재 매출 산업 추출 — %d건", len(items))
        return items

    def extract_expansion_industries(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """확장 후보 산업 추출"""

        items: List[ExtractedTechItem] = []
        found: set[str] = set()

        for sentence in self._split_sentences(text):
            if not any(keyword in sentence for keyword in self.EXPANSION_CONTEXT_KEYWORDS):
                continue

            for industry in self.INDUSTRY_KEYWORDS:
                if industry in sentence:
                    found.add(industry)

        for industry in sorted(found):
            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="현재 활용 산업 + 확장 산업",
                    item_name="확장 후보 산업",
                    content=industry,
                    metric="확장 후보 산업",
                    evidence=self._find_evidence_sentence(text, industry),
                    confidence="low",
                )
            )

        logger.info("확장 후보 산업 추출 — %d건", len(items))
        return items

    def extract_required_certifications(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """신규 산업 진입 필요 인증 후보 추출"""

        items: List[ExtractedTechItem] = []
        found: set[str] = set()

        for sentence in self._split_sentences(text):
            if not any(keyword in sentence for keyword in self.EXPANSION_CONTEXT_KEYWORDS):
                continue

            for cert in self.CERTIFICATION_KEYWORDS:
                if cert in sentence:
                    found.add(cert)

        for cert in sorted(found):
            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="신규 산업 진입 시 추가 인증/개발 부담",
                    item_name="필요 인증",
                    content=cert,
                    metric="필요 인증",
                    evidence=self._find_evidence_sentence(text, cert),
                    confidence="low",
                )
            )

        logger.info("필요 인증 추출 — %d건", len(items))
        return items

    def extract_validation_steps(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """검증 단계 후보 추출"""

        items: List[ExtractedTechItem] = []

        for step in sorted(self.VALIDATION_STEP_KEYWORDS):
            if step not in text:
                continue

            items.append(
                self._make_item(
                    raw_data=raw_data,
                    category="신규 산업 진입 시 추가 인증/개발 부담",
                    item_name="검증 단계",
                    content=step.replace(" ", ""),
                    metric="검증 단계",
                    evidence=self._find_evidence_sentence(text, step),
                    confidence="low",
                )
            )

        logger.info("검증 단계 추출 — %d건", len(items))
        return items

    def extract_financial_numbers(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """
        재무 수치 추출.

        사업보고서는 표 형태로 키워드와 숫자 사이가 멀거나
        줄바꿈이 공백으로 치환된 구조이므로 두 가지 전략을 병행:

        1) 같은 문장 내 키워드+숫자 매칭 (거리 제한 없음)
        2) 키워드가 포함된 문장에서 숫자 직접 탐색
        """

        items: List[ExtractedTechItem] = []
        seen: set[tuple] = set()

        financial_specs = [
            ("연구개발비", "연구개발비"),
            ("R&D 비용", "연구개발비"),
            ("R&D비용", "연구개발비"),
            ("당기 매출액", "당기 매출"),
            ("당기매출액", "당기 매출"),
            ("전기 매출액", "전기 매출"),
            ("전기매출액", "전기 매출"),
            ("전년 매출액", "전기 매출"),
            ("전년매출액", "전기 매출"),
            ("매출액", "매출"),
        ]

        # 숫자+단위 패턴 (쉼표 포함 숫자 + 선택적 단위)
        number_pattern = re.compile(
            r"(\d{1,3}(?:,\d{3})*|\d+)\s*(억원|백만원|천원|조원|원)?"
        )

        for keyword, metric in financial_specs:
            # 키워드가 포함된 문장들 수집
            sentences = [
                s for s in self._split_sentences(text)
                if keyword in s
            ]

            # 문장 단위 매칭 안 되면 window 방식으로 재시도
            # (표에서 키워드와 숫자가 다른 토큰으로 분리된 경우)
            if not sentences:
                idx = text.find(keyword)
                while idx != -1:
                    window = text[idx: idx + 200]
                    sentences.append(window)
                    idx = text.find(keyword, idx + 1)

            for sentence in sentences[:5]:
                matches = number_pattern.findall(sentence)

                unit_matches = [(v, u) for v, u in matches if u]          # 단위 있는 것 우선
                fallback_matches = [
                    (v, u) for v, u in matches
                    if not u and self._parse_number(v) is not None
                    and self._parse_number(v) >= 10_000                    # 단위 없으면 1만 이상만
                ]
                candidates = unit_matches or fallback_matches

                for value_str, unit in candidates[:3]:
                    value = self._parse_number(value_str)
                    if value is None:
                        continue
                    if 1900 <= value <= 2100 and not unit:                 # 연도 필터 유지
                        continue

                    # metric 보정 (매출 fallback)
                    final_metric = metric
                    if metric == "매출":
                        if "전기" in sentence or "전년" in sentence:
                            final_metric = "전기 매출"
                        else:
                            final_metric = "당기 매출"

                    key = (final_metric, value_str, unit)
                    if key in seen:
                        continue
                    seen.add(key)

                    items.append(
                        ExtractedTechItem(
                            company=raw_data.company,
                            category="재무 수치",
                            item_name=final_metric,
                            content=final_metric,
                            metric=final_metric,
                            raw_value=f"{value_str}{unit or ''}",
                            value=value,
                            unit=unit or None,
                            formula=None,
                            source=self._make_source(
                                raw_data,
                                evidence=sentence[:300],
                            ),
                            confidence="medium" if unit else "low",
                            status="extracted",
                        )
                    )

        logger.info("재무 수치 추출 — %d건", len(items))
        return items

    def extract_performance_comparison(
        self,
        raw_data: RawTechData,
        text: str,
    ) -> List[ExtractedTechItem]:
        """
        성능 개선율 / 원가 절감율 계산에 필요한 수치 추출.

        '기존 XX → 개선 후 YY' 또는 '원가 ZZ% 절감' 형태의 문장에서
        before/after 수치를 추출해 calculator가 사용하는 metric명으로 저장.
        """

        items: List[ExtractedTechItem] = []

        # ── 성능 개선 패턴 ──────────────────────────────────────────────
        # 예: "기존 85% → 99%", "순도 85%에서 99.9%로", "수율 70% → 85%"
        performance_patterns = [
            # "기존 <수치> → <수치>" 또는 "에서 <수치>로"
            (
                r"기존\s*(\d+(?:\.\d+)?)\s*(%|배|℃|도)?\s*(?:→|에서|→|->)\s*(?:개선\s*후\s*)?(\d+(?:\.\d+)?)\s*(%|배|℃|도)?",
                "성능",
            ),
            (
                r"(\d+(?:\.\d+)?)\s*(%|배|℃|도)?\s*에서\s*(\d+(?:\.\d+)?)\s*(%|배|℃|도)?\s*(?:로|로의|향상|개선)",
                "성능",
            ),
        ]

        for pattern, kind in performance_patterns:
            for m in re.finditer(pattern, text):
                groups = m.groups()
                before_val = self._parse_number(groups[0])
                after_val = self._parse_number(groups[2]) if len(groups) > 2 else None
                unit = groups[1] or groups[3] if len(groups) > 3 else groups[1]
                evidence = text[max(0, m.start() - 50): m.end() + 50]

                if before_val is not None:
                    items.append(ExtractedTechItem(
                        company=raw_data.company,
                        category="고객 구매 이유",
                        item_name="성능 비교",
                        content="기존 성능",
                        metric="기존 성능",
                        raw_value=str(groups[0]),
                        value=before_val,
                        unit=unit or None,
                        formula=None,
                        source=self._make_source(raw_data, evidence=evidence),
                        confidence="medium",
                        status="extracted",
                    ))

                if after_val is not None:
                    items.append(ExtractedTechItem(
                        company=raw_data.company,
                        category="고객 구매 이유",
                        item_name="성능 비교",
                        content="개선 후 성능",
                        metric="개선 후 성능",
                        raw_value=str(groups[2]),
                        value=after_val,
                        unit=unit or None,
                        formula=None,
                        source=self._make_source(raw_data, evidence=evidence),
                        confidence="medium",
                        status="extracted",
                    ))

        # ── 원가 절감 패턴 ──────────────────────────────────────────────
        # 예: "기존 원가 1,000억 → 800억", "원가 200억원에서 150억원으로"
        cost_patterns = [
            r"원가\s*(\d{1,3}(?:,\d{3})*)\s*(억원|백만원|원)?\s*(?:→|에서|->)\s*(\d{1,3}(?:,\d{3})*)\s*(억원|백만원|원)?",
            r"기존\s*원가\D{0,10}?(\d{1,3}(?:,\d{3})*)\s*(억원|백만원|원)?.{0,30}?(\d{1,3}(?:,\d{3})*)\s*(억원|백만원|원)?",
        ]

        for pattern in cost_patterns:
            for m in re.finditer(pattern, text):
                groups = m.groups()
                before_val = self._parse_number(groups[0])
                after_val = self._parse_number(groups[2]) if len(groups) > 2 else None
                unit = groups[1] or groups[3] if len(groups) > 3 else groups[1]
                evidence = text[max(0, m.start() - 50): m.end() + 50]

                if before_val is not None:
                    items.append(ExtractedTechItem(
                        company=raw_data.company,
                        category="고객 구매 이유",
                        item_name="원가 비교",
                        content="기존 원가",
                        metric="기존 원가",
                        raw_value=str(groups[0]),
                        value=before_val,
                        unit=unit or None,
                        formula=None,
                        source=self._make_source(raw_data, evidence=evidence),
                        confidence="medium",
                        status="extracted",
                    ))

                if after_val is not None:
                    items.append(ExtractedTechItem(
                        company=raw_data.company,
                        category="고객 구매 이유",
                        item_name="원가 비교",
                        content="적용 후 원가",
                        metric="적용 후 원가",
                        raw_value=str(groups[2]),
                        value=after_val,
                        unit=unit or None,
                        formula=None,
                        source=self._make_source(raw_data, evidence=evidence),
                        confidence="medium",
                        status="extracted",
                    ))

        logger.info("성능/원가 비교 수치 추출 — %d건", len(items))
        return items

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _make_item(
        self,
        raw_data: RawTechData,
        category: str,
        item_name: str,
        content: str,
        metric: str,
        evidence: Optional[str],
        confidence: str = "low",
    ) -> ExtractedTechItem:
        """ExtractedTechItem 생성 헬퍼"""

        return ExtractedTechItem(
            company=raw_data.company,
            category=category,
            item_name=item_name,
            content=content,
            metric=metric,
            raw_value=None,
            value=None,
            unit=None,
            formula=None,
            source=self._make_source(raw_data, evidence=evidence),
            confidence=confidence,
            status="extracted",
        )

    def _extract_known_products(self, sentence: str) -> List[str]:
        """사전에 등록된 제품/서비스명을 문장에서 추출"""

        found: List[str] = []

        for product in sorted(self.PRODUCT_ALLOWLIST, key=len, reverse=True):
            if product in sentence:
                found.append(product)

        return found

    def _extract_comma_separated_products(self, sentence: str) -> List[str]:
        """쉼표/구분자 기반 제품 후보 추출"""

        normalized_sentence = sentence.replace("ㆍ", ",").replace("·", ",")
        normalized_sentence = normalized_sentence.replace("/", ",")

        parts = re.split(r"[,，]", normalized_sentence)
        candidates: List[str] = []

        for part in parts:
            part = part.strip()

            if len(part) > 40:
                continue

            part = re.sub(r"\s*(등|및|을|를|은|는|이|가|의|으로|로)$", "", part)
            part = part.strip()

            if re.fullmatch(r"[가-힣A-Za-z0-9\- ]{2,25}", part):
                candidates.append(part)

        return candidates

    def _normalize_product_name(self, name: str) -> str:
        """제품명 표기 정리"""

        name = name.strip()
        name = re.sub(r"\s+", " ", name)

        aliases = {
            "디지털 콕핏": "Digital Cockpit",
            "갤럭시": "Galaxy",
            "NAND": "NAND Flash",
            "Flash": "NAND Flash",
        }

        return aliases.get(name, name)

    def _is_valid_product_name(self, name: str) -> bool:
        """제품명 후보 유효성 검사"""

        if not name:
            return False

        if len(name) < 2 or len(name) > 30:
            return False

        if any(stopword in name for stopword in self.PRODUCT_STOPWORDS):
            return False

        if name.endswith(("다", "니다", "하고", "하며", "되는", "위한")):
            return False

        if re.fullmatch(r"\d+", name):
            return False

        if name in {"관련", "시장", "기술", "고객", "라인업", "포트폴리오"}:
            return False

        return True

    def _is_valid_customer_name(self, name: str) -> bool:
        """고객사명 후보 유효성 검사"""

        if not name:
            return False

        if len(name) < 2 or len(name) > 30:
            return False

        bad_words = {
            "주요", "글로벌", "국내", "해외", "당사", "제품",
            "서비스", "시장", "사업", "고객", "고객사",
        }

        if any(word in name for word in bad_words):
            return False

        return True

    def _parse_number(self, value: str) -> Optional[float]:
        """쉼표 포함 숫자 문자열을 float로 변환"""

        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None

    def _make_source(
        self,
        raw_data: RawTechData,
        evidence: Optional[str] = None,
    ) -> SourceInfo:
        """RawTechData 출처 정보 복사 + evidence 추가"""

        return SourceInfo(
            major_source=raw_data.source.major_source,
            middle_source=raw_data.source.middle_source,
            source_url=raw_data.source.source_url,
            page=raw_data.source.page,
            evidence=evidence.replace('\n', ' ').replace('\r', ' ') if evidence else None,
        )

    def _find_first_index(self, text: str, patterns: List[str]) -> int:
        """여러 패턴 중 가장 먼저 등장하는 위치 반환"""

        indexes = []

        for pattern in patterns:
            idx = text.find(pattern)
            if idx != -1:
                indexes.append(idx)

        return min(indexes) if indexes else -1

    def _split_sentences(self, text: str) -> List[str]:
        """간단한 문장 분리"""

        sentences = re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+", text)
        return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 10]

    def _find_evidence_sentence(
        self,
        text: str,
        keyword: str,
    ) -> Optional[str]:
        """키워드가 포함된 근거 문장 1개 반환"""

        for sentence in self._split_sentences(text):
            if keyword in sentence:
                return sentence[:500]

        return None
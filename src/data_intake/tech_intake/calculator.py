# src/data_intake/tech_intake/calculator.py

import logging
from collections import defaultdict
from typing import Dict, List, Optional
from .schemas import ExtractedTechItem, QuantifiedMetric

logger = logging.getLogger(__name__)


class TechMetricCalculator:
    """기술 데이터 정량화 계산기"""

    def calculate(self, items: List[ExtractedTechItem]) -> List[QuantifiedMetric]:
        """ExtractedTechItem → QuantifiedMetric 변환"""

        if not items:
            logger.warning("calculate: items가 비어 있습니다.")
            return []

        metrics: List[QuantifiedMetric] = []
        metrics.extend(self.calculate_keyword_frequency(items))
        metrics.extend(self.calculate_counts(items))
        metrics.extend(self.calculate_ratio_metrics(items))

        logger.info("계산 완료 — company=%s, 지표=%d건", items[0].company, len(metrics))
        return metrics

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _company(self, items: List[ExtractedTechItem]) -> str:
        return items[0].company if items else ""

    def _filter(
        self,
        items: List[ExtractedTechItem],
        metric: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[ExtractedTechItem]:
        """metric / category 기준 필터링"""

        return [
            item for item in items
            if (metric is None or item.metric == metric)
            and (category is None or item.category == category)
        ]

    def _make(
        self,
        items: List[ExtractedTechItem],
        category: str,
        metric: str,
        value: Optional[float],
        unit: Optional[str],
        formula: str,
        source_items: Optional[List[ExtractedTechItem]] = None,
        status: str = "calculated",
        reason: Optional[str] = None,
    ) -> QuantifiedMetric:
        """QuantifiedMetric 생성 헬퍼"""

        return QuantifiedMetric(
            company=self._company(items),
            category=category,
            metric=metric,
            value=value,
            unit=unit,
            formula=formula,
            source_items=source_items or [],
            status=status,
            reason=reason,
        )

    # ------------------------------------------------------------------
    # 1. 키워드 등장 빈도
    # ------------------------------------------------------------------

    def calculate_keyword_frequency(
        self,
        items: List[ExtractedTechItem],
    ) -> List[QuantifiedMetric]:
        """기술 키워드별 등장 빈도 합산"""

        keyword_map: Dict[str, List[ExtractedTechItem]] = defaultdict(list)

        for item in self._filter(items, metric="기술 키워드 등장 빈도"):
            if item.content and item.value is not None:
                keyword_map[item.content].append(item)

        results = []
        for keyword, src_items in keyword_map.items():
            total = sum(i.value for i in src_items if i.value is not None)
            results.append(
                self._make(
                    items=items,
                    category="대표 기술",
                    metric=f"{keyword} 키워드 빈도",
                    value=total,
                    unit="회",
                    formula="사업보고서 + 홈페이지 + 특허 내 키워드 등장 횟수 합산",
                    source_items=src_items,
                )
            )

        return results

    # ------------------------------------------------------------------
    # 2. 개수 기반 지표
    # ------------------------------------------------------------------

    def calculate_counts(
        self,
        items: List[ExtractedTechItem],
        ) -> List[QuantifiedMetric]:
        """고유 개수 기반 지표 일괄 계산"""

        results: List[QuantifiedMetric] = []

        count_specs = [
            (
                "핵심 제품/서비스", "제품 수",
                "제품명/서비스명", "핵심 제품/서비스", "개",
                "고유 제품 목록 개수",
            ),
            (
                "핵심 제품/서비스", "고객 산업 수",
                "고객 산업", None, "개",
                "사업보고서 ∪ 홈페이지 ∪ IR 고유 고객 산업 개수",
            ),
            (
                "고객 구매 이유", "고객사 수",
                "고객사", None, "개",
                "IR ∪ 홍보자료 ∪ 기사 내 언급 고객사 고유 개수",
            ),
            (
                "경쟁 우위 요소/대체가능성", "등록 특허 수",
                "등록 특허", None, "건",
                "상태=등록인 특허 개수",
            ),
            (
                "경쟁 우위 요소/대체가능성", "인증 수",
                "인증 종류", None, "건",
                "확인된 인증 종류 고유 개수",
            ),
            (
                "경쟁 우위 요소/대체가능성", "레퍼런스 건수",
                "적용/공급 사례", None, "건",
                "적용 사례 / 공급 사례 고유 개수",
            ),
            (
                "현재 활용 산업 + 확장 산업", "현재 매출 산업 수",
                "현재 매출 산업", None, "개",
                "현재 매출 발생 산업 고유 개수",
            ),
            (
                "현재 활용 산업 + 확장 산업", "확장 후보 산업 수",
                "확장 후보 산업", None, "개",
                "신규 적용처 / 확장 산업 고유 개수",
            ),
            (
                "신규 산업 진입 시 추가 인증/개발 부담", "필요 인증 수",
                "필요 인증", None, "개",
                "신규 산업 진입 필요 인증 종류 고유 개수",
            ),
            (
                "신규 산업 진입 시 추가 인증/개발 부담", "검증 단계 수",
                "검증 단계", None, "단계",
                "시험 / 인증 / 고객평가 / 파일럿 / 양산검증 단계 고유 개수",
            ),
        ]

        for category, metric_name, filter_metric, filter_cat, unit, formula in count_specs:
            src_items = self._filter(items, metric=filter_metric, category=filter_cat)
            unique_values = {i.content for i in src_items if i.content}

            if unique_values:
                results.append(
                    self._make(
                        items=items,
                        category=category,
                        metric=metric_name,
                        value=float(len(unique_values)),
                        unit=unit,
                        formula=formula,
                        source_items=src_items,
                    )
                )
            else:
                results.append(
                    self._make(
                        items=items,
                        category=category,
                        metric=metric_name,
                        value=None,
                        unit=unit,
                        formula=formula,
                        source_items=src_items,
                        status="missing",
                        reason="추출된 항목 없음",
                    )
                )

        return results

    # ------------------------------------------------------------------
    # 3. 비율 / 증감률 지표
    # ------------------------------------------------------------------

    def calculate_ratio_metrics(
        self,
        items: List[ExtractedTechItem],
    ) -> List[QuantifiedMetric]:
        """비율 및 증감률 기반 지표 계산"""

        results: List[QuantifiedMetric] = []

        # --- R&D 비율 ---
        results.append(self._ratio(
            items=items,
            numerator_metric="연구개발비",
            denominator_metric=["당기 매출", "당기 매출액", "매출액"],
            category="회사의 기술 투자 수준 - R&D 강도",
            metric="매출 대비 R&D 비율",
            unit="%",
            formula="연구개발비 ÷ 매출 × 100",
            scale=100,
        ))

        # --- 매출 성장률 ---
        results.append(self._growth(
            items=items,
            current_metric=["당기 매출", "당기 매출액", "매출액"],
            prior_metric=["전기 매출", "전기 매출액", "전년 매출"],
            category="핵심 제품/서비스",
            metric="전년 성장률",
            unit="%",
            formula="(당기 매출 - 전기 매출) ÷ 전기 매출 × 100",
        ))

        # --- 성능 개선율 ---
        results.append(self._growth(
            items=items,
            current_metric="개선 후 성능",
            prior_metric="기존 성능",
            category="고객 구매 이유",
            metric="성능 개선율",
            unit="%",
            formula="(개선 후 성능 - 기존 성능) ÷ 기존 성능 × 100",
        ))

        # --- 원가 절감율 ---
        results.append(self._growth(
            items=items,
            current_metric="적용 후 원가",
            prior_metric="기존 원가",
            category="고객 구매 이유",
            metric="원가 절감율",
            unit="%",
            formula="(기존 원가 - 적용 후 원가) ÷ 기존 원가 × 100",
            inverted=True,   # 감소가 긍정적인 지표
        ))

        return results

    # ------------------------------------------------------------------
    # 비율/증감 계산 내부 헬퍼
    # ------------------------------------------------------------------

    def _get_value(
        self,
        items: List[ExtractedTechItem],
        metric,
    ) -> tuple[Optional[float], List[ExtractedTechItem]]:
        """
        metric명으로 첫 번째 유효 value 반환
        metric: str or list
        """

        # 1. metric alias 처리
        if isinstance(metric, str):
            metric_names = [metric]
        else:
            metric_names = list(metric)

        # 2. 후보 수집
        src = []
        for name in metric_names:
            src.extend(self._filter(items, metric=name))

        # 3. 값 변환 함수
        def to_float(value):
            if value is None:
                return None

            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                value = value.replace(",", "").replace("%", "").strip()
                try:
                    return float(value)
                except:
                    return None

            return None

        # 4. 값 찾기
        # 단위 있는 것 우선, 없으면 값이 큰 것 우선
        candidates = [item for item in src if item.unit]
        if not candidates:
            candidates = src

        candidates = [item for item in candidates if to_float(item.value) is not None]
        if not candidates:
            return None, src

        # 단위 있으면 그 중 첫 번째, 없으면 가장 큰 값
        best = max(candidates, key=lambda i: to_float(i.value) or 0)
        return to_float(best.value), [best]

    def _ratio(
        self,
        items: List[ExtractedTechItem],
        numerator_metric: str,
        denominator_metric: str,
        category: str,
        metric: str,
        unit: str,
        formula: str,
        scale: float = 100,
    ) -> QuantifiedMetric:
        """분자 / 분모 × scale 계산"""

        numerator, n_src = self._get_value(items, numerator_metric)
        denominator, d_src = self._get_value(items, denominator_metric)

        if numerator is not None and denominator and denominator != 0:
            return self._make(
                items=items,
                category=category,
                metric=metric,
                value=round((numerator / denominator) * scale, 2),
                unit=unit,
                formula=formula,
                source_items=n_src + d_src,
            )

        return self._make(
            items=items,
            category=category,
            metric=metric,
            value=None,
            unit=unit,
            formula=formula,
            source_items=n_src + d_src,
            status="missing",
            reason=f"{numerator_metric} 또는 {denominator_metric} 값 없음",
        )

    def _growth(
        self,
        items: List[ExtractedTechItem],
        current_metric,
        prior_metric,
        category: str,
        metric: str,
        unit: str,
        formula: str,
        inverted: bool = False,
    ) -> QuantifiedMetric:

        current, c_src = self._get_value(items, current_metric)
        prior, p_src = self._get_value(items, prior_metric)

        if current is not None and prior is not None and prior != 0:
            raw = (current - prior) / prior * 100
            value = round(-raw if inverted else raw, 2)

            return self._make(
                items=items,
                category=category,
                metric=metric,
                value=value,
                unit=unit,
                formula=formula,
                source_items=c_src + p_src,
            )

        return self._make(
            items=items,
            category=category,
            metric=metric,
            value=None,
            unit=unit,
            formula=formula,
            source_items=c_src + p_src,
            status="missing",
            reason=f"{current_metric} 또는 {prior_metric} 값 없음",
        )
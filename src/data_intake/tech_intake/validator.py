# src/data_intake/tech_intake/validator.py

import logging
from typing import Any, Dict, List, Optional

from .schemas import ExtractedTechItem, QuantifiedMetric

logger = logging.getLogger(__name__)

# 음수가 정상인 지표 (원가절감율, 성장률 등)
_NEGATIVE_ALLOWED_METRICS = {
    "원가 절감율",
    "전년 성장률",
    "성능 개선율",
    "불량률 감소",
}


class TechDataValidator:
    """
    기술 데이터 검증기

    역할:
    - 필수값 누락 확인
    - 숫자 이상치 확인
    - 근거(evidence) 존재 여부 확인
    - 계산 상태 확인
    """

    # ------------------------------------------------------------------
    # 추출 데이터 검증
    # ------------------------------------------------------------------

    def validate_extracted_items(
        self,
        items: List[ExtractedTechItem],
    ) -> List[Dict[str, Any]]:
        """추출 데이터 검증"""

        issues = []

        for idx, item in enumerate(items):
            ctx = {"company": item.company, "item_name": item.item_name}

            if not item.company:
                issues.append(self._issue(idx, "missing_company", "기업명이 없습니다.", ctx))

            if not item.category:
                issues.append(self._issue(idx, "missing_category", "대분류가 없습니다.", ctx))

            if not item.item_name:
                issues.append(self._issue(idx, "missing_item_name", "항목명이 없습니다.", ctx))

            if (
                item.value is not None
                and item.value < 0
                and item.metric not in _NEGATIVE_ALLOWED_METRICS
            ):
                issues.append(self._issue(idx, "negative_value", f"음수 값: {item.value}", ctx))

            if not item.source:
                issues.append(self._issue(idx, "missing_source", "출처 정보가 없습니다.", ctx))
            elif not item.source.evidence:
                issues.append(self._issue(idx, "missing_evidence", "근거 문장이 없습니다.", ctx))

        return issues

    # ------------------------------------------------------------------
    # 정량화 결과 검증
    # ------------------------------------------------------------------

    def validate_metrics(
        self,
        metrics: List[QuantifiedMetric],
    ) -> List[Dict[str, Any]]:
        """정량화 결과 검증"""

        issues = []

        for idx, metric in enumerate(metrics):
            ctx = {"company": metric.company, "metric": metric.metric}

            if not metric.company:
                issues.append(self._issue(idx, "missing_company", "기업명이 없습니다.", ctx))

            if not metric.category:
                issues.append(self._issue(idx, "missing_category", "대분류가 없습니다.", ctx))

            if not metric.metric:
                issues.append(self._issue(idx, "missing_metric", "지표명이 없습니다.", ctx))

            # status="missing" / "not_disclosed"이면 value=None이 정상
            if metric.status == "calculated" and metric.value is None:
                issues.append(self._issue(idx, "missing_value", "계산값이 없습니다.", ctx))

            if (
                metric.value is not None
                and metric.value < 0
                and metric.metric not in _NEGATIVE_ALLOWED_METRICS
            ):
                issues.append(self._issue(idx, "negative_value", f"음수 값: {metric.value}", ctx))

            if metric.status == "calculated" and metric.unit is None:
                issues.append(self._issue(idx, "missing_unit", "단위가 없습니다.", ctx))

            if not metric.formula:
                issues.append(self._issue(idx, "missing_formula", "계산식이 없습니다.", ctx))

            if metric.status == "calculated" and not metric.source_items:
                issues.append(self._issue(idx, "missing_source_items", "근거 항목이 없습니다.", ctx))

        return issues

    # ------------------------------------------------------------------
    # 통합 검증
    # ------------------------------------------------------------------

    def validation_summary(
        self,
        extracted_items: List[ExtractedTechItem],
        metrics: List[QuantifiedMetric],
    ) -> Dict[str, Any]:
        """검증 요약 결과 반환"""

        extracted_issues = self.validate_extracted_items(extracted_items)
        metric_issues = self.validate_metrics(metrics)
        is_valid = not extracted_issues and not metric_issues

        logger.info(
            "검증 완료 — is_valid=%s, 추출이슈=%d건, 지표이슈=%d건",
            is_valid, len(extracted_issues), len(metric_issues),
        )

        return {
            "is_valid": is_valid,
            "extracted_item_count": len(extracted_items),
            "metric_count": len(metrics),
            "extracted_issue_count": len(extracted_issues),
            "metric_issue_count": len(metric_issues),
            "extracted_issues": extracted_issues,
            "metric_issues": metric_issues,
        }

    def is_valid(
        self,
        extracted_items: List[ExtractedTechItem],
        metrics: List[QuantifiedMetric],
    ) -> bool:
        """전체 데이터가 사용 가능한지 True/False 반환"""

        # validation_summary 재사용으로 중복 검증 제거
        return self.validation_summary(extracted_items, metrics)["is_valid"]

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _issue(
        self,
        index: int,
        issue_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """검증 이슈 포맷 통일"""

        return {
            "index": index,
            "issue_type": issue_type,
            "message": message,
            "context": context or {},
        }
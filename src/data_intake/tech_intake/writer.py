# src/data_intake/tech_intake/writer.py

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .config import OUTPUT_DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from .schemas import ExtractedTechItem, ExtractedVariable, QuantifiedMetric, RawTechData
logger = logging.getLogger(__name__)


class TechDataWriter:
    """
    기술 데이터 저장 클래스

    저장 대상:
    - RawTechData      → raw/
    - ExtractedTechItem → processed/
    - QuantifiedMetric  → output/
    - ValidationSummary → output/
    """

    # ------------------------------------------------------------------
    # 공개 저장 메서드
    # ------------------------------------------------------------------

    def save_raw_data(
        self,
        raw_data_list: List[RawTechData],
        filename: str = "raw_tech_data.json",
    ) -> Path:
        """원천 데이터 JSON 저장"""

        path = RAW_DATA_DIR / filename

        if not raw_data_list:
            logger.warning("save_raw_data: 저장할 데이터 없음 — %s", path)
            return path

        data = [self._serialize(asdict(item)) for item in raw_data_list]
        self._save_json(data, path)
        return path

    def save_extracted_items(
        self,
        items: List[ExtractedTechItem],
        filename: str = "extracted_tech_items.csv",
    ) -> Path:
        """추출 결과 CSV 저장"""

        path = PROCESSED_DATA_DIR / filename

        if not items:
            logger.warning("save_extracted_items: 저장할 항목 없음 — %s", path)
            return path

        self._save_csv([asdict(item) for item in items], path)
        return path

    def save_metrics(
        self,
        metrics: List[QuantifiedMetric],
        filename: str = "quantified_metrics.csv",
    ) -> Path:
        """정량화 결과 CSV 저장"""

        path = OUTPUT_DATA_DIR / filename

        if not metrics:
            logger.warning("save_metrics: 저장할 지표 없음 — %s", path)
            return path

        self._save_csv([asdict(m) for m in metrics], path)
        return path

    def save_validation_summary(
        self,
        summary: Dict[str, Any],
        filename: str = "validation_summary.json",
    ) -> Path:
        """검증 요약 JSON 저장"""

        path = OUTPUT_DATA_DIR / filename
        self._save_json(summary, path)
        return path

    # ------------------------------------------------------------------
    # 내부 저장 헬퍼
    # ------------------------------------------------------------------

    def _save_json(self, data: Any, path: Path) -> None:
        """JSON 저장 (공통)"""

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            logger.info("JSON 저장 완료 — %s", path)

        except Exception as e:
            logger.error("JSON 저장 실패 — %s | %s", path, e)
            raise RuntimeError(f"JSON 저장 실패: {path}") from e

    def _save_csv(self, data: List[Dict], path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.json_normalize(data)

            # ── 추가: 문자열 컬럼 내 줄바꿈 제거 ──────────────────
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].apply(
                        lambda x: str(x).replace('\n', ' ').replace('\r', ' ')
                        if x is not None else x
                    )
            # ────────────────────────────────────────────────────

            df.to_csv(path, index=False, encoding="utf-8-sig")
            logger.info("CSV 저장 완료 — %s (%d행)", path, len(df))

        except Exception as e:
            logger.error("CSV 저장 실패 — %s | %s", path, e)
            raise RuntimeError(f"CSV 저장 실패: {path}") from e

    def _serialize(self, data: Any) -> Any:
        """datetime 등 JSON 비직렬화 타입 명시 변환"""

        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._serialize(v) for v in data]
        return data
    def save_variables(
        self,
        variables: List[ExtractedVariable],
        filename: str = "raw_variables.csv",
    ) -> Path: 
        """CSV 계산용 원천 변수 저장"""

        path = PROCESSED_DATA_DIR / filename

        if not variables:
            logger.warning("save_variables: 저장할 변수 없음 — %s", path)
            return path

        self._save_csv([asdict(v) for v in variables], path)
        return path
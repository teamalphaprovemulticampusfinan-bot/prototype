# src/data_intake/tech_intake/schemas.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal


@dataclass
class SourceInfo:
    """데이터 출처 정보"""

    major_source: str          # 대 출처: 사업보고서, 홈페이지, 특허 등
    middle_source: str         # 중 출처: 사업의 내용, IR Product Portfolio 등
    source_url: Optional[str] = None
    page: Optional[str] = None
    evidence: Optional[str] = None


@dataclass
class RawTechData:
    """수집된 원천 데이터"""

    company: str
    source: SourceInfo
    raw_text: str
    collected_at: Optional[datetime] = None   # str → datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTechItem:
    """원문에서 추출한 항목"""

    company: str
    category: str                              # 대분류
    item_name: str                             # 항목명
    source: SourceInfo

    content: Optional[str] = None             # 기본값 추가 (순서 오류 방지)
    metric: Optional[str] = None              # 정량화 가능한 부분
    raw_value: Optional[str] = None           # 원문 값: "1,000억원", "수율 85%"
    value: Optional[float] = None             # 정제된 숫자
    unit: Optional[str] = None                # %, 억원, 회, 개, 명 등
    formula: Optional[str] = None             # 계산식

    confidence: Literal["high", "medium", "low"] = "medium"
    status: Literal["extracted", "calculated", "missing", "not_disclosed"] = "extracted"


@dataclass
class QuantifiedMetric:
    """정량화 완료된 지표"""

    company: str
    category: str
    metric: str

    value: Optional[float] = None
    unit: Optional[str] = None
    formula: Optional[str] = None

    source_items: List[ExtractedTechItem] = field(default_factory=list)
    evidence: Optional[str] = None
    status: Literal["calculated", "missing", "not_disclosed", "error"] = "calculated"
    reason: Optional[str] = None


@dataclass
class ReportReadyItem:
    """리포트 생성용 최종 데이터"""

    company: str
    category: str
    summary_template: str                      # 기본값 없는 필드를 앞으로 이동

    summary: Optional[str] = None
    metrics: List[QuantifiedMetric] = field(default_factory=list)
    key_contents: List[str] = field(default_factory=list)
    evidences: List[str] = field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"

@dataclass
class ExtractedVariable:
    """CSV 저장용 원천 변수"""

    company_name: str
    category: str
    metric_name: str
    variable_name: str
    source_type: str

    value: Optional[float] = None
    raw_value: Optional[str] = None
    unit: Optional[str] = None
    content: Optional[str] = None

    source_name: Optional[str] = None
    source_url: Optional[str] = None
    evidence_text: Optional[str] = None
    year: Optional[int] = None

    confidence: Literal["high", "medium", "low"] = "medium"
    status: Literal["extracted", "calculated", "missing", "not_disclosed"] = "extracted"
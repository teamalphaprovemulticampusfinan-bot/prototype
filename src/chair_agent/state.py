from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class ChairState(TypedDict, total=False):
    """Chair 그래프 전체 상태."""

    # ── 입력 ──
    company_dir: str
    company: str
    run_data_intake: bool
    data_intake_result: dict[str, Any]

    # ── 병렬 노드가 누적하는 의견서 목록 ──
    # 각 노드는 {"opinions": [dict]} 를 반환하고, reducer가 list를 합친다.
    opinions: Annotated[list[dict[str, Any]], operator.add]

    # ── Auditor 관련 ──
    auditor_result: dict[str, Any]
    audited_opinions: list[dict[str, Any]]

    # ── Chair 최종 출력 ──
    chair_report: str

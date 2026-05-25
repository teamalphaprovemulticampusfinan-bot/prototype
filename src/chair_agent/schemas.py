from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


AGENT_IDS = ("finance", "market", "tech", "issue", "macro")


class AgentOpinion(BaseModel):
    """하위 에이전트가 Chair에 전달하는 표준 의견서."""

    agent: Literal["finance", "market", "tech", "issue", "macro"] = Field(
        description="의견서를 생성한 에이전트 식별자",
    )
    company: str = Field(description="분석 대상 기업명")
    opinion: str = Field(
        description="매수 / 보유 / 매도 / 해당없음 중 하나",
    )
    summary: str = Field(description="핵심 요약 (1~3문장)")
    key_points: List[str] = Field(default_factory=list, description="핵심 포인트")
    risks: List[str] = Field(default_factory=list, description="리스크 요인")


def error_opinion(agent: str, company: str, error: str) -> dict:
    """에이전트 실행 실패 시 반환하는 fallback 의견서."""
    return {
        "agent": agent,
        "company": company,
        "opinion": "판단불가",
        "summary": f"분석 중 오류 발생: {error}",
        "key_points": [],
        "risks": [f"에이전트 실행 오류: {error}"],
    }

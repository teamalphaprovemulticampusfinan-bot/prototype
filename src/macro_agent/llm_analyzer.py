from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from macro_agent.scorer import _interpret_score
from common.llm_clients import build_gemini_chat_client, is_gemini_provider

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", override=True)
load_dotenv(ROOT_DIR / "src" / ".env", override=True)


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def _safe_int(value: str | None, default: int) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _provider() -> str:
    return _env_first("MACRO_LLM_PROVIDER", "PARALLEL_LLM_PROVIDER", default="openai_compatible").lower()


MODEL = _env_first(
    "MACRO_LLM_MODEL",
    "NVIDIA_PARALLEL_MODEL",
    "OPENAI_MODEL",
    default="deepseek-ai/deepseek-v4-pro",
)
BASE_URL = _env_first(
    "MACRO_LLM_BASE_URL",
    "NVIDIA_PARALLEL_BASE_URL",
    "OPENAI_BASE_URL",
    default="https://integrate.api.nvidia.com/v1",
)
API_KEY = _env_first("MACRO_LLM_API_KEY", "NVIDIA_PARALLEL_API_KEY", "OPENAI_API_KEY")


def get_client() -> OpenAI:
    if not API_KEY:
        raise ValueError("NVIDIA_PARALLEL_API_KEY 또는 OPENAI_API_KEY를 찾을 수 없습니다.")
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def _strip_json_fence(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_llm_json(text: str) -> Dict[str, Any]:
    cleaned = _strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
        return {
            "llm_summary": cleaned,
            "macro_interpretation": "",
            "sector_impact": "",
            "key_risks": [],
            "watch_points": [],
            "evidence_links": [],
        }


# ============================================================
# score_breakdown 추출
# scorer.py의 calculate_macro_score() 반환값에서
# 항목별 기여도를 정리해 프롬프트에 전달한다.
# ============================================================

def _build_score_breakdown(score_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    breakdown = []
    details = score_result.get("details") or {}

    section_order = [
        "ecos_일별", "ext_일별",
        "ecos_월별", "ecos_분기별", "ext_월별",
        "뉴스", "규제",
    ]

    for section in section_order:
        if section not in details:
            continue
        d = details[section]
        if not isinstance(d, dict):
            continue

        # _zone 제외하고 수치 전체 전달
        key_values = {
            k: round(float(v), 4) if isinstance(v, (int, float)) else v
            for k, v in d.items()
            if not str(k).endswith("_zone")
        }

        breakdown.append({
            "section": section,
            "key_values": key_values,
        })

    return breakdown


# ============================================================
# 프롬프트 빌더
# ============================================================

def _build_prompt(score_result: Dict[str, Any]) -> str:
    score = score_result.get("score", 0)
    reasons = score_result.get("reasons") or []
    coverage = score_result.get("data_coverage") or {}
    breakdown = _build_score_breakdown(score_result)
    interpretation = _interpret_score(score)

    # 커버리지 항상 명시
    coverage_ratio = coverage.get("coverage_ratio", 1.0)
    missing = coverage.get("missing") or []
    coverage_note = f"※ 데이터 커버리지 {int(coverage_ratio * 100)}%"
    if missing:
        coverage_note += f" — 누락 항목: {missing}. 누락된 항목은 분석에서 제외하고 확인된 데이터만으로 해석할 것."

    return f"""
너는 국내 반도체 딥테크 상장기업 투자 분석을 지원하는 금융 매크로 리포트 보조 분석가다.

== 섹터 컨텍스트 ==
분석 대상: 국내 반도체 딥테크 상장기업 (네패스, 한미반도체, 한솔케미칼, 덕산테코피아, 엘티씨 등)
섹터 특성:
- 원달러 환율에 민감 (수출 비중 높음 → 원화 약세는 단기 실적 긍정, 과도한 강세는 수요 둔화 우려)
- 미중 반도체 수출규제가 직접적 사업 리스크
- 글로벌 AI Capex 사이클 → HBM/첨단패키징 수요와 연결
- 고금리 장기화 → 성장주 밸류에이션 할인 요인
- 구리/천연가스 가격 → 제조원가 간접 영향

== 역할 ==
- 이미 계산된 rule-based 결과를 설명하는 보조 분석만 수행한다.
- condition, score, risk_level을 절대 변경하거나 반박하지 않는다.
- 투자 행동을 직접 유도하지 않는다.
- 분석 톤은 항상 중립적이고 일관되게 유지한다.
{coverage_note}

== 중요 원칙 ==
1. 중립 비우호 환경에서는 관망/확인/리스크 관리 중심으로 설명한다.
2. 과장 표현을 금지한다: 급락, 붕괴, 패닉, 쇼크, 심각한 위기, 강한 매도 압력
3. 같은 입력이면 유사한 톤과 구조를 유지한다.
4. macro_interpretation은 반드시 아래 순서로 작성한다:
   유동성 → 신용 리스크 → 환율/달러 → 인플레이션 → 투자심리/뉴스 → 규제 리스크
5. 각 해석 단계 끝에 반도체 섹터에 미치는 영향을 한 문장으로 추가한다.

== 입력: rule-based 점수 결과 ==
총점: {score}
매크로 환경: {interpretation['condition']}
리스크 레벨: {interpretation['risk_level']}

항목별 핵심 수치 (score_breakdown):
{json.dumps(breakdown, ensure_ascii=False, indent=2)}

== 출력 규칙 ==
- 반드시 JSON만 출력
- 설명 문장 금지, 코드블록 금지
- key_risks 최대 3개
- watch_points 최대 3개 (구조화된 객체 형태)
- evidence_links: breakdown 수치와 매크로 해석을 연결 (최대 5개)

출력 JSON 형식:
{{
  "llm_summary": "반도체 섹터 관점을 포함한 한 문단 요약",
  "macro_interpretation": "유동성 → 신용 → 환율 → 인플레이션 → 투자심리 → 규제 순서 해석. 각 단계에 반도체 섹터 영향 포함",
  "sector_impact": "현재 매크로 환경이 반도체 딥테크 기업에 미치는 종합 영향 (2~3문장)",
  "key_risks": [
    "리스크1 (구체적 지표명 포함)",
    "리스크2",
    "리스크3"
  ],
  "watch_points": [
    {{
      "indicator": "모니터링할 지표명",
      "current": "현재 상태 한 줄",
      "threshold": "주의가 필요한 수준 또는 방향",
      "semiconductor_relevance": "반도체 섹터 관련성"
    }}
  ],
  "evidence_links": [
    {{
      "evidence_id": "macro_ev_1",
      "claim": "주장 한 문장",
      "source_section": "ecos_일별 또는 ext_월별 등"
    }}
  ]
}}
""".strip()

# ============================================================
# 메인 함수
# ============================================================

def analyze_with_llm(score_result: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based macro score를 보조 설명으로만 해석한다.

    변경 사항:
    - 프롬프트에 반도체 섹터 컨텍스트 주입
    - score_breakdown을 compact하게 전달 (전체 details 대신)
    - watch_points 구조화 출력
    - evidence_links 추가

    LLM 오류가 나더라도 Macro Agent 전체가 죽지 않도록
    caller(runner.py)에서 잡을 수 있게 예외를 발생시킨다.
    MACRO_LLM_PROVIDER=gemini이면 Gemini 백업을 사용한다.
    """
    prompt = _build_prompt(score_result)
    provider = _provider()

    if is_gemini_provider(provider):
        llm = build_gemini_chat_client(
            agent_name="macro",
            model_env_names=("MACRO_GEMINI_MODEL",),
            max_tokens_env_names=("MACRO_MAX_TOKENS",),
            temperature=0,
        )
        print(f"[macro] LLM provider=gemini model={llm.model} timeout={llm.timeout}")
        response = llm.invoke(prompt)
        return _parse_llm_json(response.content)

    client = get_client()
    timeout = _safe_int(os.getenv("REQUEST_TIMEOUT"), 80)
    print(f"[macro] LLM provider=openai_compatible base_url={BASE_URL} model={MODEL} timeout={timeout}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 국내 반도체 딥테크 상장기업 투자 분석을 지원하는 "
                    "금융 매크로 리포트 보조 분석가다. "
                    "항상 중립적이고 일관된 톤으로 설명하며, "
                    "매크로 지표가 반도체 섹터에 미치는 영향을 구체적으로 연결한다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        timeout=timeout,
    )

    text = response.choices[0].message.content or ""
    return _parse_llm_json(text)
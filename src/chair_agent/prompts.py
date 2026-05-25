from __future__ import annotations

import json
from typing import Any

try:
    from auditor_agent.quantity_prompts import CHAIR_PROMPT_INSERT
except Exception:
    CHAIR_PROMPT_INSERT = ""

END_MARKER = ""

INVESTOR_FRIENDLY_REPORT_POLICY = """
[Chair report policy for retail investors]
- The final Chair report is an investment-analysis report for retail investors.
- Do not modify the raw JSON produced by specialist agents. Only reorganize it into easier language at the Chair stage.
- Do not expose internal validation scores, raw_passed, stage scores, confidence internals, claim/evidence dumps, or unexplained machine labels.
- Keep signal and weighted_signal only as supporting information, described as domain-level direction and aggregate direction.
- Watch for mechanical Hold concentration, but do not reduce Hold arbitrarily. Explain Hold only when it is supported as a reject/no-trade option caused by tied posterior direction, missing/unreliable data, strong evidence conflict, or too-small expected edge after risk/transaction-cost considerations.
- If the evidence is mixed but one direction is clearer, do not hide it as Hold. State the clearer Buy or Sell edge and explain the remaining risks.
- Do not print metric keys without explanation. Convert key metrics into readable sentences with units and thousands separators where possible.
""".strip()

DMA_REPORTING_POLICY = """
[DMA result interpretation and reject/no-trade policy]
- Report DMA weights exactly as the code-produced posterior weights. Do not recompute them in the prompt.
- The final recommendation should prioritize the code-produced categorical posterior and reject-option decision policy. Do not create weighted_signal thresholds or new agent weights inside the prompt.
- Hold is not a neutral score band. It is a no-trade choice only when transaction costs, information uncertainty, strong evidence conflict, or a tied/unidentified direction make a new Buy/Sell decision unjustified.
- When agents disagree, do not end with "views are mixed, so wait." Explain whether the DMA posterior supports Buy or Sell more strongly, and if Hold is necessary, state the objective reject/no-trade reason.
""".strip()

REPORT_STRUCTURE_TEMPLATE = f"""
[출력 형식]
# {{company}} 개인투자자용 종합 투자 보고서

## 1. 최종 의견
- 최종 의견: 매수/보유/매도 중 코드가 제공한 최종 label을 그대로 사용
- 한 줄 결론:
- 판단 근거 요약:

## 2. 종합 방향성 신호 요약
- 종합 방향성 신호:
- DMA label posterior 또는 Auditor 판단:
- 주의: 방향성 신호는 보조 지표이며 최종 label을 재계산하는 기준이 아님

## 3. 영역별 요약
### 3-1. 재무
- 요약:
- 핵심 thesis:
- 주요 risk:
- 다음 확인 포인트:

### 3-2. 시장
- 요약:
- 핵심 thesis:
- 주요 risk:
- 다음 확인 포인트:

### 3-3. 기술
- 요약:
- 핵심 thesis:
- 주요 risk:
- 다음 확인 포인트:

### 3-4. 가치평가
- 요약:
- 핵심 thesis:
- 주요 risk:
- 다음 확인 포인트:

### 3-5. 이슈
- 요약:
- 핵심 thesis:
- 주요 risk:
- 다음 확인 포인트:

### 3-6. 거시
- 요약:
- 핵심 thesis:
- 주요 risk:
- 다음 확인 포인트:

## 4. Agent 간 충돌 지점과 해석
- valuation과 finance가 충돌하는 경우:
- tech와 valuation이 충돌하는 경우:
- issue와 market/macro가 충돌하는 경우:
- 종합 해석:

## 5. 투자 전 체크포인트
- 가격:
- 재무:
- 기술/사업화:
- 수급/시장:
- 거시/업황:

## 6. 종합 의견
- 5~8문장으로 정리
- 마지막 문장은 개인투자자가 다음에 확인해야 할 포인트로 마무리

{END_MARKER}
""".strip()


def _to_json_text(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    except TypeError:
        return json.dumps(str(obj), ensure_ascii=False, indent=2)


def _extract_final_label(auditor_summary: Any, opinions: Any) -> str:
    candidates: list[Any] = []
    if isinstance(auditor_summary, dict):
        candidates.extend([
            auditor_summary.get("final_recommendation"),
            auditor_summary.get("recommendation"),
            auditor_summary.get("auditor_recommendation"),
        ])
        decision = auditor_summary.get("decision")
        if isinstance(decision, dict):
            candidates.extend([
                decision.get("final_recommendation"),
                decision.get("recommendation"),
                decision.get("auditor_recommendation"),
            ])
    if isinstance(opinions, dict):
        for value in opinions.values():
            if isinstance(value, dict):
                candidates.extend([
                    value.get("final_recommendation"),
                    value.get("auditor_recommendation"),
                    value.get("recommendation"),
                ])
    for item in candidates:
        text = str(item or "").strip()
        if text in {"매수", "보유", "매도", "BUY", "HOLD", "SELL"}:
            return {"BUY": "매수", "HOLD": "보유", "SELL": "매도"}.get(text, text)
    return "Use the DMA/reject-option final label in the packet"


def build_chair_prompt(company: str, opinions: Any, auditor_summary: Any | None = None) -> str:
    final_label_hint = _extract_final_label(auditor_summary, opinions)

    return "\n\n".join([
        "You are the AlphaProve Chair Agent.",
        INVESTOR_FRIENDLY_REPORT_POLICY,
        DMA_REPORTING_POLICY,
        CHAIR_PROMPT_INSERT,
        f"[Company]\n{company}",
        f"[Code-produced final label hint]\n{final_label_hint}",
        "[Auditor summary]\n" + _to_json_text(auditor_summary or {}),
        "[Agent compact packets]\n" + _to_json_text(opinions or {}),
        REPORT_STRUCTURE_TEMPLATE.format(company=company),
        "[Important instructions]\n"
        "- Do not propose new numeric agent weights or mathematical label thresholds in the prompt.\n"
        "- If Hold appears, do not use it as a default. Explain whether the reject/no-trade reason is tied posterior direction, missing data, or balanced risk. Do not switch Hold to Buy/Sell merely to reduce Hold counts.\n"
        "- Write Markdown only; do not wrap the output in a code block.\n"
        f"- Print the completion marker {END_MARKER} alone on the final line.",
    ])

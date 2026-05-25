from pathlib import Path
import re

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

helper_marker = "def _build_safe_market_summary_for_final_report"
insert_before = "def _enrich_market_report_fields_from_summary_dict"

helper_code = r'''
def _first_complete_sentence(value: Any, *, max_chars: int = 180) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = " ".join(text.split())

    # 첫 문장 우선
    for ending in ["다.", "니다.", "입니다.", "합니다.", "있습니다.", "습니다.", "."]:
        idx = text.find(ending)
        if idx >= 0:
            sentence = text[: idx + len(ending)].strip()
            return _trim_to_complete_sentence(sentence, max_chars=max_chars)

    return _trim_to_complete_sentence(text, max_chars=max_chars)


def _build_safe_market_summary_for_final_report(
    *,
    base_summary: str,
    summary_dict: dict,
    company: str,
) -> str:
    """
    Chair 보고서의 시장 분석 '요약' 전용 문장 생성.

    목적:
    - 요약이 길어져서 '52주…', 'WLP 패키지…'처럼 끊기는 문제 방지
    - 시장 분석 전체 길이는 thesis/risk에서 유지
    - 요약은 2문장 내외, 450~520자 이내로 제한
    """
    if not isinstance(summary_dict, dict):
        safe = _trim_to_complete_sentence(base_summary, max_chars=460)
        return safe.replace("…", "").replace("...", "").strip()

    industry = _first_complete_sentence(summary_dict.get("industry_stage"), max_chars=190)
    value_chain = _first_complete_sentence(summary_dict.get("value_chain_position"), max_chars=190)
    oecd = _first_complete_sentence(summary_dict.get("oecd_interpretation"), max_chars=150)
    momentum = _first_complete_sentence(summary_dict.get("market_momentum"), max_chars=150)
    competition = _first_complete_sentence(summary_dict.get("competitive_position"), max_chars=150)

    positive_parts = []
    if industry:
        positive_parts.append(industry)
    if value_chain:
        positive_parts.append(value_chain)

    risk_parts = []
    if momentum:
        risk_parts.append("최근 주가 흐름과 변동성은 단기 점검 요인입니다.")
    if competition:
        risk_parts.append("후공정 패키징 시장 내 경쟁 강도도 함께 확인할 필요가 있습니다.")

    if positive_parts:
        first_sentence = "시장 측면에서는 " + " ".join(positive_parts)
    else:
        first_sentence = _trim_to_complete_sentence(base_summary, max_chars=260)

    second_bits = []
    if oecd:
        second_bits.append("거시·경기 신호는 반도체 업황 회복 가능성을 일부 뒷받침합니다.")
    if risk_parts:
        second_bits.extend(risk_parts)

    if second_bits:
        second_sentence = "다만 " + " ".join(second_bits)
    else:
        second_sentence = "다만 단기 주가 흐름과 산업 경쟁 강도는 계속 확인해야 합니다."

    summary = f"{first_sentence} {second_sentence}".strip()

    # 최종 방어: 요약은 반드시 완결 문장으로, 말줄임표 없이 제한
    summary = _trim_to_complete_sentence(summary, max_chars=520)
    summary = summary.replace("…", "").replace("...", "").strip()

    return summary

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _enrich_market_report_fields_from_summary_dict")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


old = '''    compact["summary"] = _build_rich_market_summary(
        base_summary=compact.get("summary") or "",
        summary_dict=summary_dict,
        company=company,
    )
'''

new = '''    compact["summary"] = _build_safe_market_summary_for_final_report(
        base_summary=compact.get("summary") or "",
        summary_dict=summary_dict,
        company=company,
    )
'''

if old not in text:
    raise RuntimeError("market summary assignment block not found")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("[OK] market summary is now short, complete, and no-ellipsis safe.")

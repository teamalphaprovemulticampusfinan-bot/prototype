from pathlib import Path
import re

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 1) concise original summary 선택 helper 추가
# ------------------------------------------------------------
helper_marker = "def _pick_concise_original_summary_for_report"
insert_before = "def _restore_original_history_report_fields"

helper_code = r'''
def _pick_concise_original_summary_for_report(
    source: dict,
    *,
    agent_name: str,
    company: str,
) -> str:
    """
    Chair 보고서용 summary는 길게 이어붙인 dict 설명보다
    원래 agent가 만든 짧고 완결된 summary 문장을 우선 사용한다.

    특히 market history replay에서 아래와 같은 끊김을 방지한다.
    - 산업 단계: ... 경쟁 구도: ... 고성능 WLP 패키지…

    원칙:
    - summary / *_summary / report_summary 계열의 문자열만 후보로 사용
    - dict를 렌더링한 '산업 단계: ... 밸류체인 포지션: ...' 형태는 제외
    - compact fallback 문구도 제외
    - 60~800자 사이의 완결 문장 우선
    """
    if not isinstance(source, dict):
        return ""

    candidate_keys = {
        "summary",
        "market_summary",
        "tech_summary",
        "finance_summary",
        "issue_summary",
        "macro_summary",
        "valuation_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
    }

    label_markers = (
        "산업 단계:",
        "밸류체인 포지션:",
        "거시·경기 신호:",
        "시장 모멘텀:",
        "경쟁 구도:",
        "competitive_position:",
        "industry_stage:",
        "market_momentum:",
        "value_chain_position:",
    )

    compact_markers = (
        "검증 가능한 핵심 근거는 다음과 같습니다",
        "compact packet",
        "Auditor용",
        "history snapshot은",
        "market return metrics",
        "market drawdown metrics",
        "market liquidity metrics",
    )

    candidates: list[tuple[int, str]] = []

    def add_candidate(value: Any, *, direct_bonus: int = 0):
        if not isinstance(value, str):
            return

        cleaned = _clean_report_text(value, max_chars=900)
        if not cleaned:
            return

        if len(cleaned) < 50:
            return

        if any(marker in cleaned for marker in label_markers):
            return

        if any(marker in cleaned for marker in compact_markers):
            return

        if _is_compact_fallback_text(cleaned):
            return

        score = direct_bonus

        if company and company in cleaned:
            score += 20

        if 80 <= len(cleaned) <= 500:
            score += 30
        elif 500 < len(cleaned) <= 800:
            score += 10

        if "다만" in cleaned or "그러나" in cleaned:
            score += 8

        if "보유" in cleaned or "매수" in cleaned or "매도" in cleaned:
            score += 5

        if cleaned.endswith(("다.", "습니다.", "합니다.", "입니다.")):
            score += 8

        # 너무 길어서 다시 잘릴 가능성이 있는 문장은 감점
        if len(cleaned) > 700:
            score -= 20

        candidates.append((score, _trim_to_complete_sentence(cleaned, max_chars=700)))

    # top-level summary를 가장 우선
    for key in candidate_keys:
        add_candidate(source.get(key), direct_bonus=100)

    # raw_payload / result / packet 내부에 있는 원래 summary도 탐색
    for container_key in ("raw_payload", "result", "packet", "agent_packet", "original_payload"):
        container = source.get(container_key)
        if isinstance(container, dict):
            for key in candidate_keys:
                add_candidate(container.get(key), direct_bonus=80)

    # 마지막으로 전체 nested 탐색
    for value in _iter_report_field_values(source, candidate_keys):
        add_candidate(value, direct_bonus=20)

    if not candidates:
        return ""

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _restore_original_history_report_fields")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


# ------------------------------------------------------------
# 2) _restore_original_history_report_fields 안에서
#    restored_summary 계산 직후 concise summary로 override
# ------------------------------------------------------------
needle = '''    restored_summary = _pick_report_summary_from_source(
        source,
        fallback=fallback_summary,
    )

'''

replacement = '''    restored_summary = _pick_report_summary_from_source(
        source,
        fallback=fallback_summary,
    )

    concise_original_summary = _pick_concise_original_summary_for_report(
        source,
        agent_name=agent_name,
        company=company,
    )

    if concise_original_summary:
        restored_summary = concise_original_summary

'''

if replacement.strip() not in text:
    if needle not in text:
        raise RuntimeError("summary restore block not found")
    text = text.replace(needle, replacement, 1)

path.write_text(text, encoding="utf-8")
print("[OK] concise original summary is now preferred for Chair report.")

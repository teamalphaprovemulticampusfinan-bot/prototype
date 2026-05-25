from pathlib import Path
import re

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------
# 1) _clean_report_text 교체: dict summary를 문장형으로 렌더링
# ---------------------------------------------------------------------
pattern = r'''def _clean_report_text\(value: Any, \*, max_chars: int = 2400\) -> str:\n.*?\n\n(?=def _is_compact_fallback_text)'''

replacement = r'''def _clean_report_text(value: Any, *, max_chars: int = 2400) -> str:
    """
    Chair 보고서용 텍스트 정리 함수.

    개선:
    - dict summary를 그대로 "{...}" 형태로 넣지 않고 문장형으로 렌더링
    - template / placeholder / missing-context 류 문구 제거
    - 너무 긴 내용은 max_chars 기준으로 축약
    """
    label_map = {
        "competitive_position": "경쟁 구도",
        "industry_stage": "산업 단계",
        "market_momentum": "시장 모멘텀",
        "oecd_interpretation": "거시·경기 신호",
        "value_chain_position": "밸류체인 포지션",
        "growth_driver": "성장 동인",
        "growth_drivers": "성장 동인",
        "risk": "리스크",
        "risks": "리스크",
        "key_risks": "주요 리스크",
        "key_thesis": "핵심 투자 포인트",
        "summary": "요약",
        "analysis": "분석",
    }

    banned_terms = (
        "template",
        "placeholder",
        "missing-context",
        "missing context",
        "프롬프트",
        "템플릿",
        "작성 요청",
        "요청문",
    )

    def clean_line(x: Any) -> str:
        s = str(x or "").strip()
        if not s:
            return ""

        lowered = s.lower()
        if any(term in lowered for term in banned_terms):
            return ""

        return " ".join(s.split())

    parts: list[str] = []

    if isinstance(value, dict):
        preferred_order = [
            "industry_stage",
            "value_chain_position",
            "oecd_interpretation",
            "market_momentum",
            "competitive_position",
            "summary",
            "analysis",
            "key_thesis",
            "key_risks",
            "risks",
        ]

        used = set()

        for key in preferred_order:
            if key in value:
                line = clean_line(value.get(key))
                if line:
                    label = label_map.get(key, key)
                    parts.append(f"{label}: {line}")
                    used.add(key)

        for key, val in value.items():
            if key in used:
                continue
            if isinstance(val, (dict, list)):
                line = _clean_report_text(val, max_chars=700)
            else:
                line = clean_line(val)

            if line:
                label = label_map.get(str(key), str(key))
                parts.append(f"{label}: {line}")

        text = " ".join(parts).strip()

    elif isinstance(value, list):
        for item in value[:8]:
            line = _clean_report_text(item, max_chars=500)
            if line:
                parts.append(line)
        text = " ".join(parts).strip()

    else:
        raw = str(value or "").strip()
        lines = []
        for line in raw.splitlines():
            cleaned = clean_line(line)
            if cleaned:
                lines.append(cleaned)
        text = " ".join(lines).strip()

    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."

    return text

'''

text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)

if count != 1:
    raise RuntimeError(f"_clean_report_text 교체 실패: count={count}")


# ---------------------------------------------------------------------
# 2) summary dict에서 thesis / risk 자동 생성 helper 추가
# ---------------------------------------------------------------------
helper_marker = "def _derive_report_items_from_summary_dict"
insert_before = "def _restore_original_history_report_fields"

helper_code = r'''
def _derive_report_items_from_summary_dict(
    source: dict,
    *,
    agent_name: str,
    kind: str,
) -> list[str]:
    """
    원본 history payload에 key_thesis/key_risks가 없더라도,
    summary dict의 구조적 항목을 보고 Chair 보고서용 thesis/risk를 자동 생성한다.

    특히 Market Agent의 아래 구조를 보고서용으로 분리한다.
    - industry_stage / value_chain_position / oecd_interpretation -> thesis
    - competitive_position / market_momentum 중 하락·변동성 문구 -> risk
    """
    if not isinstance(source, dict):
        return []

    summary_candidate_keys = {
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
        "analysis",
    }

    summary_dicts = []
    for value in _iter_report_field_values(source, summary_candidate_keys):
        if isinstance(value, dict):
            summary_dicts.append(value)

    if not summary_dicts:
        return []

    thesis_keys = {
        "industry_stage": "산업 성장성",
        "value_chain_position": "밸류체인 포지션",
        "oecd_interpretation": "거시·경기 신호",
        "growth_driver": "성장 동인",
        "growth_drivers": "성장 동인",
        "opportunity": "기회 요인",
        "opportunities": "기회 요인",
        "strength": "강점",
        "strengths": "강점",
        "commercialization": "사업화 연결성",
        "tech_to_value": "기술-가치 연결성",
    }

    risk_keys = {
        "competitive_position": "경쟁 리스크",
        "risk": "리스크",
        "risks": "리스크",
        "key_risks": "주요 리스크",
        "weakness": "약점",
        "weaknesses": "약점",
        "concern": "우려 요인",
        "concerns": "우려 요인",
        "drawdown": "낙폭 리스크",
        "volatility": "변동성 리스크",
        "liquidity": "유동성 리스크",
    }

    negative_terms = (
        "하락",
        "부진",
        "변동성",
        "고점 대비",
        "리스크",
        "경쟁",
        "압박",
        "둔화",
        "불확실",
        "약세",
        "낙폭",
    )

    items: list[str] = []

    def add_item(label: str, val: Any):
        text = _clean_report_text(val, max_chars=420)
        if not text:
            return
        item = f"{label}: {text}"
        if item not in items:
            items.append(item)

    for summary_dict in summary_dicts:
        for key, val in summary_dict.items():
            norm_key = str(key).strip().lower()

            if kind == "thesis":
                if norm_key in thesis_keys:
                    add_item(thesis_keys[norm_key], val)

                # market_momentum은 긍정 문맥이면 thesis로도 활용 가능
                elif norm_key == "market_momentum":
                    text = _clean_report_text(val, max_chars=420)
                    if text and not any(term in text for term in negative_terms):
                        add_item("시장 모멘텀", val)

            else:
                if norm_key in risk_keys:
                    add_item(risk_keys[norm_key], val)

                elif norm_key == "market_momentum":
                    text = _clean_report_text(val, max_chars=420)
                    if text and any(term in text for term in negative_terms):
                        add_item("주가·시장 모멘텀 리스크", val)

        if len(items) >= 5:
            break

    return items[:6]

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _restore_original_history_report_fields")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


# ---------------------------------------------------------------------
# 3) _restore_original_history_report_fields 안에 fallback thesis/risk 생성 로직 삽입
# ---------------------------------------------------------------------
restore_start = text.find("def _restore_original_history_report_fields(")
if restore_start < 0:
    raise RuntimeError("_restore_original_history_report_fields not found")

insert_pos = text.find("    if restored_summary:", restore_start)
if insert_pos < 0:
    raise RuntimeError("insert point not found: if restored_summary")

fallback_code = r'''
    if not restored_thesis:
        restored_thesis = _derive_report_items_from_summary_dict(
            source,
            agent_name=agent_name,
            kind="thesis",
        )

    if not restored_risks:
        restored_risks = _derive_report_items_from_summary_dict(
            source,
            agent_name=agent_name,
            kind="risks",
        )

'''

if fallback_code.strip() not in text[restore_start:insert_pos + 500]:
    text = text[:insert_pos] + fallback_code + text[insert_pos:]


path.write_text(text, encoding="utf-8")
print("[OK] report summary dict rendering + thesis/risk derivation patched.")

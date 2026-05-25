from pathlib import Path
import re

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------
# 1) helper 추가: 말줄임표 없이 문장 단위로 자르기
# ---------------------------------------------------------------------
helper_marker = "def _trim_to_complete_sentence"
insert_before = "def _clean_report_text"

helper_code = r'''
def _trim_to_complete_sentence(value: Any, *, max_chars: int = 900) -> str:
    """
    보고서 문장이 '고성능 WLP 패키지…'처럼 중간에서 끊기지 않도록
    가능한 문장 끝에서 자른다. 말줄임표는 붙이지 않는다.
    """
    text = str(value or "").strip()
    if not text:
        return ""

    text = " ".join(text.split())

    if len(text) <= max_chars:
        return text

    cut = text[:max_chars].rstrip()

    # 한국어 보고서에서 자연스럽게 끝나는 지점을 우선 탐색
    sentence_endings = ["다.", "니다.", "됩니다.", "입니다.", "합니다.", "있습니다.", "습니다.", "요.", "."]

    best = -1
    for ending in sentence_endings:
        idx = cut.rfind(ending)
        if idx > best:
            best = idx + len(ending)

    if best >= max(80, int(max_chars * 0.55)):
        return cut[:best].rstrip()

    # 문장 끝을 못 찾으면 마지막 공백 기준으로 자르되 말줄임표는 붙이지 않음
    space_idx = cut.rfind(" ")
    if space_idx >= max(80, int(max_chars * 0.55)):
        return cut[:space_idx].rstrip()

    return cut.rstrip()


def _summarize_market_dict_for_report(summary_dict: dict, *, max_chars: int = 760) -> str:
    """
    Market summary dict를 Chair 보고서용 완결 문단으로 변환한다.

    원칙:
    - summary는 너무 길게 만들지 않는다.
    - 경쟁 구도/주가 변동성 등은 risk bullet에 들어가므로 summary에서는 짧게만 반영한다.
    - 문장 중간 말줄임표가 생기지 않도록 각 항목을 문장 단위로 자른다.
    """
    if not isinstance(summary_dict, dict):
        return _trim_to_complete_sentence(summary_dict, max_chars=max_chars)

    ordered_keys = [
        ("industry_stage", "산업 단계"),
        ("value_chain_position", "밸류체인 포지션"),
        ("oecd_interpretation", "거시·경기 신호"),
        ("market_momentum", "시장 모멘텀"),
    ]

    parts = []

    for key, label in ordered_keys:
        value = summary_dict.get(key)
        if not value:
            continue

        # 각 항목이 너무 길면 해당 항목 내부에서 문장 단위로 정리
        cleaned = _trim_to_complete_sentence(value, max_chars=230)
        if cleaned:
            parts.append(f"{label}: {cleaned}")

    # competitive_position은 summary에 넣으면 길어지기 쉬우므로 짧게만 반영
    competitive = summary_dict.get("competitive_position")
    if competitive:
        cleaned = _trim_to_complete_sentence(competitive, max_chars=180)
        if cleaned:
            parts.append(f"경쟁 구도: {cleaned}")

    text = " ".join(parts).strip()
    return _trim_to_complete_sentence(text, max_chars=max_chars)


def _format_basis_opportunity_or_risk_dict(item: dict) -> str:
    """
    {'basis': ..., 'opportunity': ...} / {'basis': ..., '리스크': ..., 'severity': ...}
    형태가 보고서에 'basis: ... opportunity: ...'처럼 어색하게 나오지 않도록 정리한다.
    """
    if not isinstance(item, dict):
        return str(item or "").strip()

    basis = (
        item.get("basis")
        or item.get("근거")
        or item.get("evidence")
        or item.get("reason")
    )

    opportunity = (
        item.get("opportunity")
        or item.get("기회")
        or item.get("positive")
        or item.get("thesis")
    )

    risk = (
        item.get("risk")
        or item.get("리스크")
        or item.get("negative")
        or item.get("concern")
    )

    severity = item.get("severity") or item.get("중요도") or item.get("level")

    if opportunity:
        if basis:
            return f"{opportunity} 근거는 {basis}입니다."
        return str(opportunity).strip()

    if risk:
        if basis and severity:
            return f"{risk} 수준은 {severity}이며, 근거는 {basis}입니다."
        if basis:
            return f"{risk} 근거는 {basis}입니다."
        return str(risk).strip()

    # 일반 dict fallback
    parts = []
    for k, v in item.items():
        if v in (None, "", [], {}):
            continue
        parts.append(f"{k}: {v}")

    return " ".join(parts).strip()

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _clean_report_text")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


# ---------------------------------------------------------------------
# 2) _clean_report_text 내부의 말줄임표 하드컷 제거
#    기존: text = text[:max_chars].rstrip() + "..."
#    변경: _trim_to_complete_sentence 사용
# ---------------------------------------------------------------------
text = text.replace(
'''    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."

    return text
''',
'''    text = _trim_to_complete_sentence(text, max_chars=max_chars)

    return text
''',
)


# ---------------------------------------------------------------------
# 3) _pick_report_summary_from_source 교체:
#    dict summary는 market용 완결 문단으로 우선 렌더링
# ---------------------------------------------------------------------
pattern = r'''def _pick_report_summary_from_source\(source: dict, \*, fallback: str\) -> str:\n.*?\n\n(?=def _pick_report_items_from_source)'''

replacement = r'''def _pick_report_summary_from_source(source: dict, *, fallback: str) -> str:
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
        "analysis",
    }

    dict_candidates = []
    text_candidates = []

    for value in _iter_report_field_values(source, candidate_keys):
        if isinstance(value, dict):
            rendered = _summarize_market_dict_for_report(value, max_chars=760)
            if _is_report_text_usable(rendered):
                dict_candidates.append(rendered)
        elif _is_report_text_usable(value):
            cleaned = _clean_report_text(value, max_chars=1200)
            text_candidates.append(cleaned)

    # dict summary가 있으면, 문장형으로 안전하게 렌더링한 것을 우선 사용
    if dict_candidates:
        dict_candidates = sorted(dict_candidates, key=len, reverse=True)
        return _trim_to_complete_sentence(dict_candidates[0], max_chars=760)

    if text_candidates:
        text_candidates = sorted(text_candidates, key=len, reverse=True)
        return _trim_to_complete_sentence(text_candidates[0], max_chars=1000)

    return _trim_to_complete_sentence(fallback, max_chars=760)

'''

text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)

if count != 1:
    raise RuntimeError(f"_pick_report_summary_from_source 교체 실패: count={count}")


# ---------------------------------------------------------------------
# 4) _value_to_report_items 안에서 dict item이 어색하게 렌더링되는 문제 보정
# ---------------------------------------------------------------------
old = r'''        if isinstance(x, dict):
            for key in ("text", "summary", "title", "reason", "name", "description"):
                if x.get(key):
                    add_one(x.get(key))
                    return
            return
'''

new = r'''        if isinstance(x, dict):
            formatted = _format_basis_opportunity_or_risk_dict(x)
            if formatted:
                add_one(formatted)
            return
'''

if old in text:
    text = text.replace(old, new, 1)
else:
    print("[WARN] dict item rendering block not found. Skipped _value_to_report_items dict formatting patch.")


path.write_text(text, encoding="utf-8")
print("[OK] report ellipsis/truncation patch applied.")

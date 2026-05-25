from pathlib import Path
import re

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

helper_marker = "def _enrich_market_report_fields_from_summary_dict"
insert_before = "def _restore_original_history_report_fields"

helper_code = r'''
def _find_market_summary_dict(source: dict) -> dict:
    """
    Market Agent 원본 payload 안에서
    industry_stage / value_chain_position / market_momentum / competitive_position
    같은 구조화 summary dict를 찾는다.
    """
    if not isinstance(source, dict):
        return {}

    candidate_keys = {
        "summary",
        "market_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
        "analysis",
    }

    expected_keys = {
        "industry_stage",
        "value_chain_position",
        "oecd_interpretation",
        "market_momentum",
        "competitive_position",
    }

    for value in _iter_report_field_values(source, candidate_keys):
        if isinstance(value, dict):
            keys = {str(k).strip() for k in value.keys()}
            if keys & expected_keys:
                return value

    return {}


def _market_item(label: str, value: Any, *, max_chars: int = 360) -> str:
    text = _clean_report_text(value, max_chars=max_chars)
    text = _trim_to_complete_sentence(text, max_chars=max_chars)
    if not text:
        return ""
    return f"{label}: {text}"


def _append_unique_market_items(
    base_items: Any,
    extra_items: list[str],
    *,
    max_items: int = 5,
) -> list[str]:
    result: list[str] = []

    def add(value: Any):
        if value in (None, "", [], {}):
            return

        if isinstance(value, list):
            for x in value:
                add(x)
            return

        if isinstance(value, dict):
            formatted = _format_basis_opportunity_or_risk_dict(value)
            add(formatted)
            return

        text = _clean_report_text(value, max_chars=460)
        text = _trim_to_complete_sentence(text, max_chars=460)

        if not text:
            return

        if _is_compact_fallback_text(text):
            return

        if text not in result:
            result.append(text)

    add(base_items)

    for item in extra_items:
        add(item)

    return result[:max_items]


def _build_rich_market_summary(
    *,
    base_summary: str,
    summary_dict: dict,
    company: str,
) -> str:
    """
    너무 짧지도, 너무 길어서 끊기지도 않는 시장 요약을 만든다.
    """
    base = _clean_report_text(base_summary, max_chars=420)
    base = _trim_to_complete_sentence(base, max_chars=420)

    industry = summary_dict.get("industry_stage")
    value_chain = summary_dict.get("value_chain_position")
    momentum = summary_dict.get("market_momentum")
    competition = summary_dict.get("competitive_position")
    oecd = summary_dict.get("oecd_interpretation")

    parts = []

    if base:
        parts.append(base)

    detail_positive = []
    if industry:
        detail_positive.append(_trim_to_complete_sentence(industry, max_chars=180))
    if value_chain:
        detail_positive.append(_trim_to_complete_sentence(value_chain, max_chars=180))
    if oecd:
        detail_positive.append(_trim_to_complete_sentence(oecd, max_chars=160))

    detail_positive = [x for x in detail_positive if x]

    if detail_positive:
        parts.append("시장 측면에서는 " + " ".join(detail_positive))

    detail_risk = []
    if momentum:
        detail_risk.append(_trim_to_complete_sentence(momentum, max_chars=160))
    if competition:
        detail_risk.append(_trim_to_complete_sentence(competition, max_chars=180))

    detail_risk = [x for x in detail_risk if x]

    if detail_risk:
        parts.append("다만 " + " ".join(detail_risk))

    text = " ".join(parts).strip()

    # Chair 본문에서 또 잘리지 않도록 900자 안쪽으로 제한하되 문장 단위로 마감
    return _trim_to_complete_sentence(text, max_chars=900)


def _enrich_market_report_fields_from_summary_dict(
    *,
    compact: dict,
    source: dict,
    company: str,
) -> dict:
    """
    Auditor용 compact evidence는 유지하되,
    Chair 보고서의 market summary / thesis / risk를 너무 짧지 않게 보강한다.

    적용 결과:
    - summary: 2~3문장 수준으로 산업·밸류체인·시장모멘텀 포함
    - key_thesis: 원래 thesis + 산업 성장성 + 밸류체인 + 경기 신호
    - key_risks: 원래 risk + 주가 변동성 + 경쟁 구도
    """
    if not isinstance(compact, dict) or not isinstance(source, dict):
        return compact

    summary_dict = _find_market_summary_dict(source)
    if not summary_dict:
        return compact

    compact["summary"] = _build_rich_market_summary(
        base_summary=compact.get("summary") or "",
        summary_dict=summary_dict,
        company=company,
    )

    thesis_extras = []

    if summary_dict.get("industry_stage"):
        thesis_extras.append(
            _market_item("산업 성장성", summary_dict.get("industry_stage"))
        )

    if summary_dict.get("value_chain_position"):
        thesis_extras.append(
            _market_item("밸류체인 포지션", summary_dict.get("value_chain_position"))
        )

    if summary_dict.get("oecd_interpretation"):
        thesis_extras.append(
            _market_item("거시·경기 신호", summary_dict.get("oecd_interpretation"))
        )

    compact["key_thesis"] = _append_unique_market_items(
        compact.get("key_thesis") or compact.get("thesis") or [],
        [x for x in thesis_extras if x],
        max_items=5,
    )
    compact["thesis"] = compact["key_thesis"]

    risk_extras = []

    if summary_dict.get("market_momentum"):
        risk_extras.append(
            _market_item("주가·시장 모멘텀 리스크", summary_dict.get("market_momentum"))
        )

    if summary_dict.get("competitive_position"):
        risk_extras.append(
            _market_item("경쟁 구도 리스크", summary_dict.get("competitive_position"))
        )

    compact["key_risks"] = _append_unique_market_items(
        compact.get("key_risks") or compact.get("risks") or [],
        [x for x in risk_extras if x],
        max_items=5,
    )
    compact["risks"] = compact["key_risks"]

    restore_meta = compact.get("report_detail_restore")
    if not isinstance(restore_meta, dict):
        restore_meta = {}

    restore_meta.update(
        {
            "market_rich_restore_enabled": True,
            "summary_chars_after_market_enrich": len(str(compact.get("summary") or "")),
            "thesis_count_after_market_enrich": len(compact.get("key_thesis") or []),
            "risk_count_after_market_enrich": len(compact.get("key_risks") or []),
        }
    )

    compact["report_detail_restore"] = restore_meta

    return compact

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _restore_original_history_report_fields")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


old_call = '''    compact = _restore_original_history_report_fields(
        compact=compact,
        source=source,
        agent_name="market",
        company=company,
    )

'''

new_call = '''    compact = _restore_original_history_report_fields(
        compact=compact,
        source=source,
        agent_name="market",
        company=company,
    )

    compact = _enrich_market_report_fields_from_summary_dict(
        compact=compact,
        source=source,
        company=company,
    )

'''

if new_call.strip() not in text:
    if old_call not in text:
        raise RuntimeError("market restore call block not found")
    text = text.replace(old_call, new_call, 1)

path.write_text(text, encoding="utf-8")
print("[OK] market rich report restore patched.")

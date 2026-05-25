from __future__ import annotations

import copy
import json
import re
from collections import Counter
from typing import Any

# Support both execution styles used in this project.
# 1) PYTHONPATH=<project_root>      -> src.common.* works
# 2) PYTHONPATH=<project_root>/src  -> common.* works
# Chair/market evaluation scripts commonly use style (2), so importing only
# src.common.* can break with ModuleNotFoundError: No module named 'src'.
try:  # preferred when project root is on PYTHONPATH
    from src.common.evidence_contract import (
        enforce_evidence_contract,
        remove_unsupported_claims_from_packet,
        score_claim_evidence_packet,
    )
except ModuleNotFoundError:  # fallback when only project_root/src is on PYTHONPATH
    from common.evidence_contract import (
        enforce_evidence_contract,
        remove_unsupported_claims_from_packet,
        score_claim_evidence_packet,
    )


DEFAULT_PASS_THRESHOLD = 0.75


BAD_SOURCE_TYPES = {
    "agent_output_unverified",
    "llm_only",
    "self_generated",
    "unverified",
    "unknown",
    "",
}


NON_CLAIMABLE_SOURCE_TYPES = {
    "warning_stock",
    "status",
    "flag",
}


NON_CLAIMABLE_METRICS = {
    "warning_stock",
    "investment_warning",
    "warning_flag",
    "status",
    "flag",
    # Market Agent 메타데이터. 날짜/종목코드가 숫자로 변환되어
    # "20,260,430원" 같은 잘못된 claim이 되는 것을 막는다.
    "as_of",
    "date",
    "basdt",
    "ticker",
    "krx_code",
    "srtncd",
    "isincd",
    "currency",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace(",", "").strip()

    try:
        return float(text)
    except ValueError:
        return None


def _is_bad_source_type(source_type: Any) -> bool:
    return _clean_text(source_type).lower() in BAD_SOURCE_TYPES


def _is_status_or_flag_evidence(ev: dict[str, Any]) -> bool:
    if not isinstance(ev, dict):
        return False

    source_type = _clean_text(ev.get("source_type")).lower()
    metric = _clean_text(ev.get("metric")).lower()

    if source_type in NON_CLAIMABLE_SOURCE_TYPES:
        return True

    if metric in NON_CLAIMABLE_METRICS:
        return True

    if any(token in metric for token in ["as_of", "date", "basdt", "ticker", "krx_code", "srtncd", "isincd", "currency"]):
        return True

    if isinstance(ev.get("value"), bool):
        return True

    return False


def _is_non_claimable_evidence(ev: dict[str, Any]) -> bool:
    """
    자동 claim으로 만들면 안 되는 evidence를 걸러낸다.

    제외 대상:
    - source_type이 agent_output_unverified / llm_only / self_generated 등인 evidence
    - value가 None인 evidence
    - value가 bool인 evidence
    - snippet에 '확인 불가'가 들어간 evidence
    - warning_stock / status / flag 계열 evidence
    """
    if not isinstance(ev, dict):
        return True

    if _is_bad_source_type(ev.get("source_type")):
        return True

    if _is_status_or_flag_evidence(ev):
        return True

    if ev.get("value") is None:
        return True

    snippet = _clean_text(ev.get("snippet"))
    if "확인 불가" in snippet:
        return True

    return False


def _metric_to_korean(metric: Any) -> str:
    metric_text = _clean_text(metric).lower()

    mapping = {
        "sales": "매출",
        "sales growth": "매출 성장률",
        "sales_growth": "매출 성장률",
        "sales_growth_%": "매출 성장률",
        "operating income": "영업이익",
        "operating_income": "영업이익",
        "operating profit": "영업이익",
        "operating_profit": "영업이익",
        "operating margin": "영업이익률",
        "operating_margin": "영업이익률",
        "operating_margin_%": "영업이익률",
        "net income": "순이익",
        "net_income": "순이익",
        "debt ratio": "부채비율",
        "debt_ratio": "부채비율",
        "debt_ratio_%": "부채비율",
        "current ratio": "유동비율",
        "current_ratio": "유동비율",
        "current_ratio_%": "유동비율",
        "ocf": "영업활동현금흐름",
        "operating cash flow": "영업활동현금흐름",
        "operating_cash_flow": "영업활동현금흐름",
        "fcf": "자유현금흐름",
        "free cash flow": "자유현금흐름",
        "free_cash_flow": "자유현금흐름",
        "mdd": "최대낙폭",
        "max drawdown": "최대낙폭",
        "기간mdd_%": "기간 최대낙폭",
        "stock price trend": "주가",
        "current price": "현재가",
        "current_price": "현재가",
        "warning_stock": "투자경고 여부",
    }

    return mapping.get(metric_text, _clean_text(metric) or "지표")


def _format_number(num: float) -> str:
    if abs(num) >= 1000:
        return f"{num:,.0f}"
    return f"{num:.2f}".rstrip("0").rstrip(".")


def _format_value(value: Any, unit: Any) -> str:
    unit_text = _clean_text(unit)

    if value is None:
        return "확인 불가"

    if isinstance(value, bool):
        return "해당" if value else "해당 없음"

    num = _safe_float(value)

    if num is None:
        return str(value)

    number_text = _format_number(num)

    if unit_text == "%":
        return f"{number_text}%"

    if unit_text == "원":
        return f"{number_text}원"

    if unit_text:
        return f"{number_text}{unit_text}"

    return number_text


def _infer_unit_from_metric(metric: Any, value: Any, old_unit: Any, old_snippet: str) -> Any:
    metric_text = _clean_text(metric).lower()
    unit_text = _clean_text(old_unit)
    snippet = _clean_text(old_snippet)

    num = _safe_float(value)

    if num is None:
        if isinstance(value, bool):
            return None
        if unit_text == "%":
            return None
        return unit_text or None

    if unit_text == "%" and abs(num) > 1000:
        if any(k in metric_text for k in ["price", "현재가", "종가", "close", "stock"]):
            return "원"
        if "원" in snippet:
            return "원"

    if unit_text:
        return unit_text

    if any(k in metric_text for k in ["growth", "margin", "ratio", "mdd", "drawdown", "%"]):
        return "%"

    # stock_data.as_of처럼 "stock"이라는 단어가 들어가도 날짜/코드성 메타데이터는
    # 금액 단위가 아니다. 가격성 metric에만 원 단위를 추론한다.
    if any(k in metric_text for k in ["as_of", "date", "basdt", "ticker", "code", "srtncd", "isincd", "currency"]):
        return unit_text or None

    if any(k in metric_text for k in ["sales", "income", "profit", "cash", "fcf", "ocf", "price", "current_price", "close", "clpr", "stock_price"]):
        return "원"

    if "%" in snippet:
        return "%"
    if "원" in snippet:
        return "원"

    return None


def _extract_year_like_period(period: Any) -> int | None:
    text = _clean_text(period)

    if not text:
        return None

    match = re.search(r"(20\d{2}|19\d{2})", text)

    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def _infer_default_period_from_evidences(evidences: list[dict[str, Any]]) -> str | None:
    periods: list[str] = []

    for ev in evidences:
        if not isinstance(ev, dict):
            continue

        period = _clean_text(ev.get("period"))

        if period:
            periods.append(period)

    if not periods:
        return None

    years = [_extract_year_like_period(p) for p in periods]
    years = [y for y in years if y is not None]

    if years:
        return str(max(years))

    counter = Counter(periods)
    return counter.most_common(1)[0][0]


def _should_fill_finance_period(ev: dict[str, Any]) -> bool:
    if not isinstance(ev, dict):
        return False

    if _clean_text(ev.get("period")):
        return False

    source_type = _clean_text(ev.get("source_type")).lower()
    metric = _clean_text(ev.get("metric")).lower()

    if source_type in {"financial", "finance", "price"}:
        return True

    finance_keywords = [
        "sales",
        "income",
        "profit",
        "margin",
        "ratio",
        "debt",
        "current",
        "cash",
        "fcf",
        "ocf",
        "mdd",
        "price",
        "매출",
        "영업",
        "순이익",
        "부채",
        "유동",
        "현금",
        "주가",
    ]

    return any(keyword in metric for keyword in finance_keywords)


def _fill_missing_periods(
    evidences: list[dict[str, Any]],
    *,
    agent_name: str | None = None,
) -> list[dict[str, Any]]:
    evidences = copy.deepcopy(evidences)

    if agent_name != "finance":
        return evidences

    default_period = _infer_default_period_from_evidences(evidences)

    if not default_period:
        return evidences

    for ev in evidences:
        if not isinstance(ev, dict):
            continue

        if _should_fill_finance_period(ev):
            ev["period"] = default_period

    return evidences


def _normalize_evidence_snippet(ev: dict[str, Any]) -> dict[str, Any]:
    ev = copy.deepcopy(ev)

    source_type = ev.get("source_type")
    source = ev.get("source")
    metric = ev.get("metric")
    value = ev.get("value")
    period = ev.get("period")
    old_unit = ev.get("unit")
    old_snippet = _clean_text(ev.get("snippet"))

    unit = _infer_unit_from_metric(metric, value, old_unit, old_snippet)
    ev["unit"] = unit

    if _is_bad_source_type(source_type):
        ev["snippet"] = "검증 가능한 원천 evidence가 부족합니다."
        return ev

    source_text = _clean_text(source) or "원천 데이터"
    metric_text = _metric_to_korean(metric)
    value_text = _format_value(value, unit)
    period_text = f"{period} 기준 " if period not in (None, "") else ""

    ev["snippet"] = f"{source_text} | {period_text}{metric_text} | 값: {value_text}"

    return ev


def _sanitize_evidences(
    packet: dict[str, Any],
    *,
    agent_name: str | None = None,
) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    evidences = packet.get("evidences")
    if not isinstance(evidences, list):
        evidences = packet.get("evidence", [])

    if not isinstance(evidences, list):
        evidences = []

    raw_evidences: list[dict[str, Any]] = []

    for ev in evidences:
        if not isinstance(ev, dict):
            continue
        raw_evidences.append(copy.deepcopy(ev))

    raw_evidences = _fill_missing_periods(
        raw_evidences,
        agent_name=agent_name,
    )

    sanitized: list[dict[str, Any]] = []

    for ev in raw_evidences:
        sanitized.append(_normalize_evidence_snippet(ev))

    packet["evidences"] = sanitized
    packet["evidence"] = sanitized

    return packet


def _remove_bad_evidences(packet: dict[str, Any]) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    evidences = packet.get("evidences")
    if not isinstance(evidences, list):
        evidences = packet.get("evidence", [])

    if not isinstance(evidences, list):
        evidences = []

    kept: list[dict[str, Any]] = []
    removed_ids: list[str] = []

    for ev in evidences:
        if not isinstance(ev, dict):
            continue

        evidence_id = _clean_text(ev.get("evidence_id"))

        if _is_bad_source_type(ev.get("source_type")):
            if evidence_id:
                removed_ids.append(evidence_id)
            continue

        kept.append(ev)

    packet["evidences"] = kept
    packet["evidence"] = kept

    if removed_ids:
        raw_payload = packet.get("raw_payload")
        if not isinstance(raw_payload, dict):
            raw_payload = {}

        old_removed = raw_payload.get("removed_bad_evidence_ids", [])
        if not isinstance(old_removed, list):
            old_removed = []

        raw_payload["removed_bad_evidence_ids"] = old_removed + removed_ids
        packet["raw_payload"] = raw_payload

    return packet


def _claim_text(claim: Any) -> str:
    if isinstance(claim, dict):
        return _clean_text(
            claim.get("text")
            or claim.get("claim")
            or claim.get("summary")
            or claim.get("risk")
            or claim.get("opportunity")
        )
    return _clean_text(claim)


def _claim_evidence_ids(claim: Any) -> list[str]:
    if not isinstance(claim, dict):
        return []

    ids = claim.get("evidence_ids")
    if not isinstance(ids, list):
        return []

    return [_clean_text(x) for x in ids if _clean_text(x)]


def _used_evidence_ids(packet: dict[str, Any]) -> set[str]:
    claims = packet.get("claims")
    if not isinstance(claims, list):
        return set()

    used: set[str] = set()

    for claim in claims:
        for evidence_id in _claim_evidence_ids(claim):
            used.add(evidence_id)

    return used


def _supported_claim_texts(packet: dict[str, Any]) -> list[str]:
    claims = packet.get("claims")
    if not isinstance(claims, list):
        return []

    texts: list[str] = []

    for claim in claims:
        text = _claim_text(claim)
        if text:
            texts.append(text)

    return texts


def _classify_claim_type(ev: dict[str, Any]) -> str:
    metric = _clean_text(ev.get("metric")).lower()
    source_type = _clean_text(ev.get("source_type")).lower()
    value = ev.get("value")
    num = _safe_float(value)

    if any(k in metric for k in ["mdd", "drawdown"]):
        return "risk"

    if any(k in metric for k in ["debt ratio", "debt_ratio", "부채비율"]):
        if num is not None and num >= 150:
            return "risk"
        return "point"

    if any(k in metric for k in ["current ratio", "current_ratio", "유동비율"]):
        if num is not None and num < 100:
            return "risk"
        return "point"

    if any(k in metric for k in ["operating income", "operating_income", "operating profit", "영업이익"]):
        if num is not None and num < 0:
            return "risk"
        return "thesis"

    if any(k in metric for k in ["net income", "net_income", "순이익"]):
        if num is not None and num < 0:
            return "risk"
        return "thesis"

    if any(k in metric for k in ["sales growth", "sales_growth", "매출 성장률"]):
        if num is not None and num > 0:
            return "thesis"
        if num is not None and num < 0:
            return "risk"
        return "point"

    if any(k in metric for k in ["fcf", "free cash flow", "ocf", "operating cash flow"]):
        if num is not None and num > 0:
            return "thesis"
        if num is not None and num < 0:
            return "risk"
        return "point"

    if source_type == "price":
        return "risk"

    return "point"


def _make_atomic_claim_from_evidence(
    ev: dict[str, Any],
    *,
    agent_name: str,
    idx: int,
) -> dict[str, Any] | None:
    if not isinstance(ev, dict):
        return None

    if _is_non_claimable_evidence(ev):
        return None

    evidence_id = _clean_text(ev.get("evidence_id"))
    if not evidence_id:
        return None

    metric = ev.get("metric")
    period = ev.get("period")
    value = ev.get("value")
    unit = ev.get("unit")

    metric_text = _metric_to_korean(metric)
    value_text = _format_value(value, unit)
    period_text = f"{period} 기준 " if period not in (None, "") else ""

    source_metric = _clean_text(metric) or metric_text
    claim_text = f"{period_text}{source_metric} 값은 {value_text}입니다."

    return {
        "claim_id": f"{agent_name}.auto_cl.{idx:03d}",
        "text": claim_text,
        "evidence_ids": [evidence_id],
        "claim_type": _classify_claim_type(ev),
    }


def _is_status_or_flag_claim(
    claim: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> bool:
    text = _claim_text(claim).lower()

    if "warning_stock" in text:
        return True

    if "투자경고" in text:
        return True

    evidence_ids = _claim_evidence_ids(claim)

    if not evidence_ids:
        return False

    matched_evidences = [
        evidence_by_id[eid]
        for eid in evidence_ids
        if eid in evidence_by_id
    ]

    if not matched_evidences:
        return False

    return all(_is_status_or_flag_evidence(ev) for ev in matched_evidences)


def _evidence_metric_index(packet: dict[str, Any]) -> dict[str, list[str]]:
    evidences = packet.get("evidences")
    if not isinstance(evidences, list):
        evidences = packet.get("evidence", [])

    if not isinstance(evidences, list):
        evidences = []

    index: dict[str, list[str]] = {
        "sales_growth": [],
        "operating_loss": [],
        "net_loss": [],
        "debt_ratio": [],
        "current_ratio": [],
        "fcf": [],
        "ocf": [],
        "mdd": [],
        "price": [],
    }

    for ev in evidences:
        if not isinstance(ev, dict):
            continue

        evidence_id = _clean_text(ev.get("evidence_id"))
        if not evidence_id:
            continue

        if _is_bad_source_type(ev.get("source_type")):
            continue

        metric = _clean_text(ev.get("metric")).lower()
        value = ev.get("value")
        num = _safe_float(value)

        if any(k in metric for k in ["sales_growth", "sales growth", "매출 성장률"]):
            index["sales_growth"].append(evidence_id)

        if any(k in metric for k in ["operating_margin", "operating income", "operating_income", "영업이익", "영업이익률"]):
            if num is None or num < 0:
                index["operating_loss"].append(evidence_id)

        if any(k in metric for k in ["net_income", "net income", "순이익"]):
            if num is None or num < 0:
                index["net_loss"].append(evidence_id)

        if any(k in metric for k in ["debt_ratio", "debt ratio", "부채비율"]):
            index["debt_ratio"].append(evidence_id)

        if any(k in metric for k in ["current_ratio", "current ratio", "유동비율"]):
            index["current_ratio"].append(evidence_id)

        if any(k in metric for k in ["fcf", "free cash flow", "자유현금흐름"]):
            index["fcf"].append(evidence_id)

        if any(k in metric for k in ["ocf", "operating cash flow", "영업활동현금흐름"]):
            index["ocf"].append(evidence_id)

        if any(k in metric for k in ["mdd", "drawdown", "최대낙폭"]):
            index["mdd"].append(evidence_id)

        if any(k in metric for k in ["price", "stock", "주가", "현재가"]):
            index["price"].append(evidence_id)

    return index


def _append_unique_ids(base: list[str], extra: list[str]) -> list[str]:
    result = list(base)
    seen = set(result)

    for item in extra:
        if item and item not in seen:
            result.append(item)
            seen.add(item)

    return result


def _augment_claim_evidence_ids_by_text(
    packet: dict[str, Any],
    *,
    agent_name: str,
) -> dict[str, Any]:
    """
    Finance의 복합 claim에 대해 evidence_id를 보강한다.

    예:
    '적자 지속 및 높은 부채비율' claim이 부채비율 evidence만 가지고 있으면
    영업이익률/순이익 evidence도 함께 연결한다.
    """
    if agent_name != "finance":
        return packet

    packet = copy.deepcopy(packet)

    claims = packet.get("claims")
    if not isinstance(claims, list):
        return packet

    index = _evidence_metric_index(packet)

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        text = _claim_text(claim).lower()
        evidence_ids = _claim_evidence_ids(claim)

        extras: list[str] = []

        if any(k in text for k in ["적자", "영업손실", "손실", "수익성"]):
            extras = _append_unique_ids(extras, index["operating_loss"])
            extras = _append_unique_ids(extras, index["net_loss"])

        if any(k in text for k in ["부채비율", "부채", "재무 건전성", "재무적 리스크"]):
            extras = _append_unique_ids(extras, index["debt_ratio"])

        if any(k in text for k in ["유동비율", "유동성", "단기 유동성"]):
            extras = _append_unique_ids(extras, index["current_ratio"])

        if any(k in text for k in ["매출", "성장"]):
            extras = _append_unique_ids(extras, index["sales_growth"])

        if any(k in text for k in ["현금흐름", "fcf", "자유현금", "ocf", "영업활동현금"]):
            extras = _append_unique_ids(extras, index["fcf"])
            extras = _append_unique_ids(extras, index["ocf"])

        if any(k in text for k in ["mdd", "최대낙폭", "주가 변동성", "낙폭"]):
            extras = _append_unique_ids(extras, index["mdd"])

        if extras:
            claim["evidence_ids"] = _append_unique_ids(evidence_ids, extras)

    packet["claims"] = claims
    return packet


def _dedupe_claims(packet: dict[str, Any]) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    claims = packet.get("claims")
    if not isinstance(claims, list):
        packet["claims"] = []
        return packet

    evidences = packet.get("evidences")
    if not isinstance(evidences, list):
        evidences = packet.get("evidence", [])

    if not isinstance(evidences, list):
        evidences = []

    evidence_by_id = {
        _clean_text(ev.get("evidence_id")): ev
        for ev in evidences
        if isinstance(ev, dict) and _clean_text(ev.get("evidence_id"))
    }

    seen_texts: set[str] = set()
    seen_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        if _is_status_or_flag_claim(claim, evidence_by_id):
            continue

        text = _claim_text(claim)
        claim_id = _clean_text(claim.get("claim_id"))

        if not text:
            continue

        key = text.lower().replace(" ", "")

        if key in seen_texts:
            continue

        if claim_id and claim_id in seen_ids:
            continue

        seen_texts.add(key)

        if claim_id:
            seen_ids.add(claim_id)

        deduped.append(claim)

    packet["claims"] = deduped
    return packet


def _append_atomic_claims_for_orphan_evidences(
    packet: dict[str, Any],
    *,
    agent_name: str,
    max_new_claims: int = 8,
) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    claims = packet.get("claims")
    if not isinstance(claims, list):
        claims = []

    evidences = packet.get("evidences")
    if not isinstance(evidences, list):
        evidences = packet.get("evidence", [])

    if not isinstance(evidences, list):
        evidences = []

    used_ids = _used_evidence_ids({"claims": claims})
    added = 0

    for ev in evidences:
        if added >= max_new_claims:
            break

        if not isinstance(ev, dict):
            continue

        if _is_non_claimable_evidence(ev):
            continue

        evidence_id = _clean_text(ev.get("evidence_id"))

        if not evidence_id:
            continue

        if evidence_id in used_ids:
            continue

        claim = _make_atomic_claim_from_evidence(
            ev,
            agent_name=agent_name,
            idx=len(claims) + added + 1,
        )

        if claim is None:
            continue

        claims.append(claim)
        used_ids.add(evidence_id)
        added += 1

    packet["claims"] = claims
    packet = _dedupe_claims(packet)

    return packet


def _rewrite_summary_from_supported_claims(packet: dict[str, Any]) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    supported = _supported_claim_texts(packet)
    company = packet.get("company_name") or packet.get("company") or "해당 기업"

    if not supported:
        packet["summary"] = "검증 가능한 핵심 근거가 부족하여 보수적 판단이 필요합니다."
        return packet

    visible_claims = supported[:5]
    packet["summary"] = f"{company}에 대해 검증 가능한 핵심 근거는 다음과 같습니다. " + " ".join(visible_claims)

    return packet


def _rebuild_key_fields_from_claims(packet: dict[str, Any]) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    claims = packet.get("claims")
    if not isinstance(claims, list):
        return packet

    thesis: list[str] = []
    risks: list[str] = []
    points: list[str] = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        text = _claim_text(claim)

        if not text:
            continue

        claim_type = _clean_text(claim.get("claim_type"))

        if claim_type == "risk":
            risks.append(text)
        elif claim_type == "thesis":
            thesis.append(text)
        else:
            points.append(text)

    if isinstance(packet.get("key_thesis"), list):
        packet["key_thesis"] = thesis[:5]
    elif thesis:
        packet["key_thesis"] = thesis[:5]

    if isinstance(packet.get("key_risks"), list):
        packet["key_risks"] = risks[:5]
    elif risks:
        packet["key_risks"] = risks[:5]

    if isinstance(packet.get("risks"), list):
        packet["risks"] = risks[:5]

    if isinstance(packet.get("key_points"), list):
        packet["key_points"] = (thesis + points)[:5]
    elif thesis or points:
        packet["key_points"] = (thesis + points)[:5]

    return packet


def _append_warning(packet: dict[str, Any], message: str) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    old = _clean_text(packet.get("warning_note"))

    if not old:
        packet["warning_note"] = message
    elif message not in old:
        packet["warning_note"] = f"{old} {message}"

    return packet


def _score_and_remove_unsupported(
    packet: dict[str, Any],
    *,
    pass_threshold: float,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    check = score_claim_evidence_packet(
        packet,
        pass_threshold=pass_threshold,
    )

    if check.get("pass"):
        return packet, check, 0

    before_claim_count = len(packet.get("claims", [])) if isinstance(packet.get("claims"), list) else 0

    packet = remove_unsupported_claims_from_packet(packet, check)

    after_claim_count = len(packet.get("claims", [])) if isinstance(packet.get("claims"), list) else 0
    removed_count = max(0, before_claim_count - after_claim_count)

    return packet, check, removed_count


def finalize_agent_output(
    packet: dict[str, Any],
    *,
    agent_name: str,
    company_name: str | None = None,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    auto_remove_unsupported: bool = True,
) -> dict[str, Any]:
    """
    각 에이전트의 최종 JSON을 검증 가능한 grounded packet으로 정리한다.

    핵심 원칙:
    1. LLM이 만든 unsupported claim은 제거한다.
    2. 제거 후에도 검증 가능한 evidence가 남아 있으면 evidence 기반 단일 claim을 자동 생성한다.
    3. value=None 또는 '확인 불가' evidence는 claim으로 만들지 않는다.
    4. warning_stock/status/flag/bool evidence는 claim으로 만들지 않는다.
    5. finance evidence의 period가 비어 있으면 가능한 경우 최신 연도로 보정한다.
    6. finance 복합 claim은 관련 evidence_id를 자동 보강한다.
    7. summary/key_thesis/key_risks/key_points는 최종 통과 claim 기준으로 다시 작성한다.
    """

    if not isinstance(packet, dict):
        packet = {
            "agent": agent_name,
            "company_name": company_name or "",
            "company": company_name or "",
            "summary": _clean_text(packet),
        }

    packet = copy.deepcopy(packet)

    packet["agent"] = packet.get("agent") or agent_name
    packet["company_name"] = packet.get("company_name") or packet.get("company") or company_name or ""
    packet["company"] = packet.get("company") or packet.get("company_name") or company_name or ""

    packet = enforce_evidence_contract(
        packet,
        agent_name=agent_name,
        company=company_name or packet.get("company_name"),
    )

    packet = _sanitize_evidences(
        packet,
        agent_name=agent_name,
    )

    packet = enforce_evidence_contract(
        packet,
        agent_name=agent_name,
        company=company_name or packet.get("company_name"),
    )

    packet = _sanitize_evidences(
        packet,
        agent_name=agent_name,
    )

    packet = _augment_claim_evidence_ids_by_text(
        packet,
        agent_name=agent_name,
    )

    packet = _dedupe_claims(packet)

    pre_check = score_claim_evidence_packet(
        packet,
        pass_threshold=pass_threshold,
    )

    packet["pre_sanitize_grounding_check"] = pre_check

    if auto_remove_unsupported and not pre_check.get("pass"):
        packet, _, removed_count = _score_and_remove_unsupported(
            packet,
            pass_threshold=pass_threshold,
        )

        if removed_count > 0:
            packet = _append_warning(
                packet,
                f"검증 불가 claim {removed_count}개를 제거한 뒤 grounding 기준을 재검증했습니다.",
            )

    packet = _remove_bad_evidences(packet)

    packet = _augment_claim_evidence_ids_by_text(
        packet,
        agent_name=agent_name,
    )

    packet = _append_atomic_claims_for_orphan_evidences(
        packet,
        agent_name=agent_name,
        max_new_claims=8,
    )

    packet = _dedupe_claims(packet)

    second_check = score_claim_evidence_packet(
        packet,
        pass_threshold=pass_threshold,
    )

    packet["post_atomic_grounding_check"] = second_check

    if auto_remove_unsupported and not second_check.get("pass"):
        packet, _, removed_count = _score_and_remove_unsupported(
            packet,
            pass_threshold=pass_threshold,
        )

        if removed_count > 0:
            packet = _append_warning(
                packet,
                f"자동 생성 claim 중 검증 기준 미달 claim {removed_count}개를 추가 제거했습니다.",
            )

    packet = _dedupe_claims(packet)
    packet = _rebuild_key_fields_from_claims(packet)
    packet = _rewrite_summary_from_supported_claims(packet)

    final_check = score_claim_evidence_packet(
        packet,
        pass_threshold=pass_threshold,
    )

    packet["grounding_check"] = final_check

    if not final_check.get("pass"):
        packet = _append_warning(
            packet,
            f"최종 grounding score가 기준({pass_threshold:.2f})에 미달했습니다. "
            f"score={final_check.get('score')}",
        )

    packet["packet_version"] = "grounded_agent_v3"

    return packet


__all__ = ["finalize_agent_output"]
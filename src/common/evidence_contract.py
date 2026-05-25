from __future__ import annotations

import copy
import json
import re
from typing import Any


FORBIDDEN_SOURCE_TYPES = {
    "agent_output_unverified",
    "llm_only",
    "self_generated",
    "unverified",
    "unknown",
    "",
}


CONCEPT_RULES = {
    "sales_growth": {
        "claim_terms": ["매출", "매출 성장", "sales", "revenue"],
        "evidence_terms": ["매출", "매출 성장", "sales", "revenue", "sales growth"],
    },
    "operating_profit": {
        "claim_terms": ["영업이익", "영업손실", "영업이익률", "operating"],
        "evidence_terms": ["영업이익", "영업손실", "영업이익률", "operating", "operating margin"],
    },
    "fcf": {
        "claim_terms": ["FCF", "자유현금흐름", "free cash flow"],
        "evidence_terms": ["FCF", "자유현금흐름", "free cash flow"],
    },
    "ocf": {
        "claim_terms": ["OCF", "영업활동현금흐름", "operating cash flow"],
        "evidence_terms": ["OCF", "영업활동현금흐름", "operating cash flow"],
    },
    "debt_ratio": {
        "claim_terms": ["부채비율", "debt ratio"],
        "evidence_terms": ["부채비율", "debt ratio"],
    },
    "current_ratio": {
        "claim_terms": ["유동비율", "current ratio"],
        "evidence_terms": ["유동비율", "current ratio"],
    },
    "mdd": {
        "claim_terms": ["MDD", "최대 낙폭", "최대낙폭", "낙폭"],
        "evidence_terms": ["MDD", "최대 낙폭", "최대낙폭", "낙폭", "drawdown"],
    },
    "price": {
        "claim_terms": ["주가", "가격", "price"],
        "evidence_terms": ["주가", "가격", "price", "stock"],
    },
    "warning_stock": {
        "claim_terms": ["투자경고", "경고종목"],
        "evidence_terms": ["투자경고", "경고종목", "warning_stock"],
    },
    "technical_downtrend": {
        "claim_terms": ["기술적 하방", "하방 압력", "기술적 압력", "기술적 약세"],
        "evidence_terms": ["기술적", "하방", "이동평균", "추세", "차트", "technical"],
    },
}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _norm_agent(agent_name: str | None) -> str:
    return str(agent_name or "agent").strip().lower().replace("_agent", "") or "agent"


def _is_forbidden_source_type(source_type: Any) -> bool:
    return str(source_type or "").strip().lower() in FORBIDDEN_SOURCE_TYPES


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = _clean_text(text).lower()
    return any(term.lower() in lowered for term in terms)


def _years(text: str) -> set[str]:
    return set(re.findall(r"20\d{2}", _clean_text(text)))


def _numeric_values(text: str) -> list[float]:
    """
    연도는 별도 _years에서 처리하므로 숫자 매칭에서는 제외.
    """
    raw = re.findall(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", _clean_text(text))
    values: list[float] = []

    for token in raw:
        normalized = token.replace(",", "")
        if re.fullmatch(r"20\d{2}", normalized):
            continue

        try:
            values.append(float(normalized))
        except ValueError:
            continue

    return values


def _number_match_one(
    claim_value: float,
    evidence_value: float,
    *,
    claim_text: str,
    evidence_text: str,
) -> bool:
    """
    숫자 매칭을 보수적으로 수행.
    - 86.24가 -87.36과 잘못 매칭되는 문제를 방지.
    - -87% 이상과 -87.36%는 허용.
    """
    c = claim_value
    e = evidence_value

    joined = f"{claim_text} {evidence_text}".lower()
    sign_flip_allowed = any(
        key in joined
        for key in ["mdd", "낙폭", "하락", "손실", "적자", "drawdown"]
    )

    direct_diff = abs(c - e)

    if abs(c) <= 500 and abs(e) <= 500:
        # 퍼센트/비율/소형 수치는 엄격하게 본다.
        if direct_diff <= 0.10:
            return True

        # claim이 -87% 이상처럼 정수 근사 표현이면 0.5p까지 허용.
        if float(c).is_integer() and direct_diff <= 0.50:
            return True

        if sign_flip_allowed:
            abs_diff = abs(abs(c) - abs(e))
            if abs_diff <= 0.10:
                return True
            if float(c).is_integer() and abs_diff <= 0.50:
                return True

        return False

    # 큰 금액성 숫자는 2% 이내 상대 오차 허용
    tolerance = max(1.0, abs(c) * 0.02)
    if direct_diff <= tolerance:
        return True

    if sign_flip_allowed and abs(abs(c) - abs(e)) <= tolerance:
        return True

    return False


def _number_match_ratio(claim_text: str, evidence_text: str) -> float:
    claim_nums = _numeric_values(claim_text)
    evidence_nums = _numeric_values(evidence_text)

    if not claim_nums:
        return 1.0

    if not evidence_nums:
        return 0.0

    matched = 0

    for c in claim_nums:
        if any(
            _number_match_one(
                c,
                e,
                claim_text=claim_text,
                evidence_text=evidence_text,
            )
            for e in evidence_nums
        ):
            matched += 1

    return matched / max(1, len(claim_nums))


def _tokens(text: str) -> set[str]:
    raw = re.findall(
        r"[가-힣A-Za-z0-9%._,+\-]{2,}",
        _clean_text(text).lower(),
    )

    stopwords = {
        "입니다",
        "합니다",
        "그리고",
        "그러나",
        "대한",
        "으로",
        "에서",
        "있는",
        "없는",
        "기준",
        "확인",
        "필요",
        "상태",
        "가능성",
        "보유",
        "매수",
        "매도",
        "관망",
        "권고",
        "기업",
        "회사",
        "최근",
        "전년",
        "대비",
        "초기",
        "신호",
        "포착",
    }

    return {
        token.strip(".,()[]{}")
        for token in raw
        if len(token.strip(".,()[]{}")) >= 2 and token not in stopwords
    }


def _token_match_ratio(claim_text: str, evidence_text: str) -> float:
    claim_tokens = _tokens(claim_text)
    evidence_tokens = _tokens(evidence_text)

    if not claim_tokens:
        return 1.0

    if not evidence_tokens:
        return 0.0

    return len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))


def _metric_alias(metric: Any) -> str:
    metric = _clean_text(metric).lower()

    aliases = {
        "sales growth": "매출 매출성장 매출 성장 sales revenue",
        "sales_growth": "매출 매출성장 매출 성장 sales revenue",
        "sales_growth_%": "매출 매출성장 매출 성장 sales revenue",
        "operating margin": "영업이익률 영업손실 영업이익 operating margin",
        "operating_margin": "영업이익률 영업손실 영업이익 operating margin",
        "operating_margin_%": "영업이익률 영업손실 영업이익 operating margin",
        "operating income": "영업이익 영업손실 operating income",
        "free cash flow": "FCF 자유현금흐름 free cash flow",
        "fcf": "FCF 자유현금흐름 free cash flow",
        "operating cash flow": "OCF 영업활동현금흐름 operating cash flow",
        "ocf": "OCF 영업활동현금흐름 operating cash flow",
        "debt ratio": "부채비율 debt ratio",
        "debt_ratio": "부채비율 debt ratio",
        "debt_ratio_%": "부채비율 debt ratio",
        "current ratio": "유동비율 current ratio",
        "current_ratio": "유동비율 current ratio",
        "current_ratio_%": "유동비율 current ratio",
        "max drawdown": "MDD 최대낙폭 최대 낙폭 drawdown",
        "mdd": "MDD 최대낙폭 최대 낙폭 drawdown",
        "recent price trend": "주가 가격 price stock",
        "warning_stock": "투자경고 경고종목 warning_stock",
    }

    if metric in aliases:
        return aliases[metric]

    return ""


def _evidence_text(ev: dict[str, Any]) -> str:
    parts = [
        ev.get("evidence_id"),
        ev.get("source_type"),
        ev.get("source"),
        ev.get("metric"),
        _metric_alias(ev.get("metric")),
        ev.get("value"),
        ev.get("unit"),
        ev.get("period"),
        ev.get("snippet"),
        ev.get("rationale"),
        ev.get("text"),
    ]
    return " ".join(_clean_text(x) for x in parts if _clean_text(x))


def _infer_unit(metric: Any, value: Any, snippet: str) -> str | None:
    metric_text = _clean_text(metric).lower()
    snippet_text = _clean_text(snippet)

    if "%" in metric_text:
        return "%"
    if any(x in metric_text for x in ["ratio", "margin", "growth", "roe", "roa", "mdd", "return"]):
        return "%"
    if "%" in snippet_text:
        return "%"
    if "억원" in snippet_text:
        return "억원"
    if "원" in snippet_text:
        return "원"
    if "배" in snippet_text:
        return "배"
    if "건" in snippet_text:
        return "건"

    return None


def _infer_period(period: Any, snippet: str) -> str | None:
    if period not in (None, ""):
        return str(period)

    text = _clean_text(snippet)

    date_match = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if date_match:
        y, m, d = date_match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    ym_match = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월", text)
    if ym_match:
        y, m = ym_match.groups()
        return f"{y}-{int(m):02d}"

    year_match = re.search(r"(20\d{2})\s*년", text)
    if year_match:
        return year_match.group(1)

    return None


def _normalize_evidence(
    ev: Any,
    *,
    idx: int,
    agent_name: str,
    company: str,
) -> dict[str, Any]:
    agent = _norm_agent(agent_name)

    if not isinstance(ev, dict):
        ev = {
            "snippet": _clean_text(ev),
            "source_type": "agent_output_unverified",
            "source": f"{agent}_output",
        }

    source_type = (
        ev.get("source_type")
        or ev.get("category")
        or ev.get("type")
        or ev.get("data_type")
        or "agent_output_unverified"
    )

    source = (
        ev.get("source")
        or ev.get("file")
        or ev.get("filename")
        or ev.get("origin")
        or f"{agent}_source_context"
    )

    snippet = (
        ev.get("snippet")
        or ev.get("rationale")
        or ev.get("text")
        or ev.get("description")
        or ""
    )

    metric = ev.get("metric") or ev.get("name") or ev.get("key")
    value = ev.get("value")
    unit = ev.get("unit") or _infer_unit(metric, value, snippet)
    period = _infer_period(ev.get("period") or ev.get("date") or ev.get("year"), snippet)

    evidence_id = ev.get("evidence_id") or ev.get("id") or f"{agent}.ev.{idx:03d}"

    return {
        **ev,
        "evidence_id": str(evidence_id),
        "source_type": str(source_type),
        "source": str(source),
        "metric": metric,
        "value": value,
        "unit": unit,
        "period": period,
        "snippet": _clean_text(snippet),
    }


def _collect_evidences(packet: dict[str, Any]) -> list[Any]:
    evidences: list[Any] = []

    for key in ("evidences", "evidence"):
        value = packet.get(key)
        if isinstance(value, list):
            evidences.extend(value)
        elif isinstance(value, dict):
            evidences.append(value)

    metrics = packet.get("metrics")
    if isinstance(metrics, list):
        evidences.extend(metrics)

    seen: set[str] = set()
    unique: list[Any] = []

    for ev in evidences:
        ev_id = ""
        if isinstance(ev, dict):
            ev_id = str(ev.get("evidence_id") or ev.get("id") or "")

        if ev_id and ev_id in seen:
            continue

        if ev_id:
            seen.add(ev_id)

        unique.append(ev)

    return unique


def _unverified_evidence(agent_name: str) -> dict[str, Any]:
    agent = _norm_agent(agent_name)

    return {
        "evidence_id": f"{agent}.ev.unverified",
        "source_type": "agent_output_unverified",
        "source": f"{agent}_output",
        "metric": None,
        "value": None,
        "unit": None,
        "period": None,
        "snippet": "검증 가능한 원천 evidence가 부족합니다.",
    }


def _required_concepts(claim_text: str) -> list[str]:
    required: list[str] = []

    for concept, rule in CONCEPT_RULES.items():
        if _contains_any(claim_text, rule["claim_terms"]):
            required.append(concept)

    return required


def _concept_supported_by_evidence(
    concept: str,
    claim_years: set[str],
    evidence: dict[str, Any],
) -> bool:
    evidence_text = _evidence_text(evidence)
    rule = CONCEPT_RULES[concept]

    if not _contains_any(evidence_text, rule["evidence_terms"]):
        return False

    if claim_years:
        evidence_years = _years(evidence_text)
        if not evidence_years.intersection(claim_years):
            return False

    return True


def _concept_coverage(
    claim_text: str,
    valid_evidences: list[dict[str, Any]],
) -> tuple[float, list[str], dict[str, list[str]]]:
    concepts = _required_concepts(claim_text)

    if not concepts:
        return 1.0, [], {}

    claim_years = _years(claim_text)
    missing: list[str] = []
    concept_to_evidence_ids: dict[str, list[str]] = {}

    for concept in concepts:
        matched_ids: list[str] = []

        for ev in valid_evidences:
            if _concept_supported_by_evidence(concept, claim_years, ev):
                matched_ids.append(str(ev.get("evidence_id")))

        if matched_ids:
            concept_to_evidence_ids[concept] = matched_ids
        else:
            missing.append(concept)

    coverage = (len(concepts) - len(missing)) / max(1, len(concepts))
    return coverage, missing, concept_to_evidence_ids


def _best_evidence_ids(
    claim_text: str,
    evidences: list[dict[str, Any]],
    *,
    max_ids: int = 4,
) -> list[str]:
    concepts = _required_concepts(claim_text)
    claim_years = _years(claim_text)
    scored: list[tuple[float, str]] = []

    for ev in evidences:
        ev_id = str(ev.get("evidence_id", ""))
        if not ev_id:
            continue

        if _is_forbidden_source_type(ev.get("source_type")):
            continue

        evidence_text = _evidence_text(ev)

        concept_hit = False
        if concepts:
            for concept in concepts:
                if _concept_supported_by_evidence(concept, claim_years, ev):
                    concept_hit = True
                    break

            if not concept_hit:
                continue

        number_ratio = _number_match_ratio(claim_text, evidence_text)
        token_ratio = _token_match_ratio(claim_text, evidence_text)

        score = 0.65 * number_ratio + 0.35 * token_ratio

        if concepts:
            score += 0.25

        if score >= 0.20:
            scored.append((score, ev_id))

    scored.sort(reverse=True, key=lambda x: x[0])

    return [ev_id for _, ev_id in scored[:max_ids]]


def _claim_texts_from_packet(packet: dict[str, Any]) -> list[str]:
    """
    summary는 claim으로 자동 등록하지 않는다.
    summary는 여러 사실이 섞여 있어서 검증 단위로 부적합하다.
    """
    texts: list[str] = []

    for key in (
        "key_thesis",
        "key_points",
        "risks",
        "key_risks",
        "theses",
        "opportunities",
    ):
        value = packet.get(key)

        if not isinstance(value, list):
            continue

        for item in value:
            if isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("claim")
                    or item.get("risk")
                    or item.get("opportunity")
                    or item.get("summary")
                )
                if text:
                    texts.append(_clean_text(text))
            else:
                texts.append(_clean_text(item))

    cleaned: list[str] = []
    for text in texts:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        if len(text) > 350:
            text = text[:350].rstrip() + "..."

        cleaned.append(text)

    return cleaned[:12]


def _normalize_claim(
    claim: Any,
    *,
    idx: int,
    agent_name: str,
    evidences: list[dict[str, Any]],
    unverified_id: str,
) -> dict[str, Any]:
    agent = _norm_agent(agent_name)

    if isinstance(claim, dict):
        text = (
            claim.get("text")
            or claim.get("claim")
            or claim.get("summary")
            or claim.get("risk")
            or claim.get("opportunity")
            or ""
        )
        claim_id = claim.get("claim_id") or claim.get("id") or f"{agent}.cl.{idx:03d}"
        evidence_ids = claim.get("evidence_ids") or claim.get("evidence_id") or []
        evidence_ids = _as_list(evidence_ids)
        base = dict(claim)
    else:
        text = _clean_text(claim)
        claim_id = f"{agent}.cl.{idx:03d}"
        evidence_ids = []
        base = {}

    existing_ids = {str(ev.get("evidence_id")) for ev in evidences if ev.get("evidence_id")}
    evidence_ids = [str(x) for x in evidence_ids if str(x) in existing_ids]

    if not evidence_ids:
        evidence_ids = _best_evidence_ids(_clean_text(text), evidences)

    if not evidence_ids:
        evidence_ids = [unverified_id]

    base.update(
        {
            "claim_id": str(claim_id),
            "text": _clean_text(text),
            "evidence_ids": evidence_ids,
        }
    )

    return base


def enforce_evidence_contract(
    packet: dict[str, Any],
    *,
    agent_name: str,
    company: str | None = None,
) -> dict[str, Any]:
    agent = _norm_agent(agent_name)

    if not isinstance(packet, dict):
        packet = {
            "agent": agent,
            "company_name": company or "",
            "summary": _clean_text(packet),
        }

    packet = copy.deepcopy(packet)

    packet["agent"] = packet.get("agent") or agent
    packet["company_name"] = packet.get("company_name") or packet.get("company") or company or ""
    packet["company"] = packet.get("company") or packet.get("company_name") or company or ""

    raw_evidences = _collect_evidences(packet)

    normalized_evidences = [
        _normalize_evidence(
            ev,
            idx=i,
            agent_name=agent,
            company=packet["company_name"],
        )
        for i, ev in enumerate(raw_evidences, start=1)
    ]

    unverified = _unverified_evidence(agent)

    existing_ids = {ev.get("evidence_id") for ev in normalized_evidences}
    if unverified["evidence_id"] not in existing_ids:
        normalized_evidences.append(unverified)

    raw_claims = packet.get("claims")

    if isinstance(raw_claims, list) and raw_claims:
        claim_items = raw_claims
    else:
        claim_items = _claim_texts_from_packet(packet)

    normalized_claims = [
        _normalize_claim(
            claim,
            idx=i,
            agent_name=agent,
            evidences=normalized_evidences,
            unverified_id=unverified["evidence_id"],
        )
        for i, claim in enumerate(claim_items, start=1)
    ]

    normalized_claims = [
        cl for cl in normalized_claims
        if _clean_text(cl.get("text"))
    ]

    if not normalized_claims:
        normalized_claims = [
            {
                "claim_id": f"{agent}.cl.001",
                "text": "검증 가능한 핵심 주장이 부족합니다.",
                "evidence_ids": [unverified["evidence_id"]],
            }
        ]

    packet["claims"] = normalized_claims
    packet["evidences"] = normalized_evidences
    packet["evidence"] = normalized_evidences
    packet.setdefault("packet_version", "grounded_agent_v1")

    return packet


def _evaluate_claim(
    claim: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    claim_id = _clean_text(claim.get("claim_id"))
    claim_text = _clean_text(claim.get("text") or claim.get("claim"))
    evidence_ids = [str(x) for x in _as_list(claim.get("evidence_ids"))]

    if not claim_text:
        return {
            "claim_id": claim_id,
            "text": claim_text,
            "supported": False,
            "score": 0.0,
            "reason": "claim text가 비어 있습니다.",
        }

    if not evidence_ids:
        return {
            "claim_id": claim_id,
            "text": claim_text,
            "supported": False,
            "score": 0.0,
            "reason": "evidence_ids가 없습니다.",
        }

    missing_ids = [ev_id for ev_id in evidence_ids if ev_id not in evidence_by_id]
    if missing_ids:
        return {
            "claim_id": claim_id,
            "text": claim_text,
            "supported": False,
            "score": 0.0,
            "reason": f"존재하지 않는 evidence_id가 있습니다: {missing_ids}",
        }

    linked_evidences = [evidence_by_id[ev_id] for ev_id in evidence_ids]

    valid_evidences = [
        ev for ev in linked_evidences
        if not _is_forbidden_source_type(ev.get("source_type"))
    ]

    if not valid_evidences:
        return {
            "claim_id": claim_id,
            "text": claim_text,
            "supported": False,
            "score": 0.0,
            "reason": "검증 불가 source_type만 연결되어 있습니다.",
        }

    combined_evidence_text = " ".join(_evidence_text(ev) for ev in valid_evidences)

    number_ratio = _number_match_ratio(claim_text, combined_evidence_text)
    token_ratio = _token_match_ratio(claim_text, combined_evidence_text)
    concept_ratio, missing_concepts, concept_matches = _concept_coverage(
        claim_text,
        valid_evidences,
    )

    claim_has_number = bool(_numeric_values(claim_text))
    claim_years = _years(claim_text)

    year_ok = True
    if claim_years and not _required_concepts(claim_text):
        evidence_years = _years(combined_evidence_text)
        year_ok = bool(claim_years.intersection(evidence_years))

    if claim_has_number:
        score = 0.55 * number_ratio + 0.25 * concept_ratio + 0.20 * token_ratio
    else:
        score = 0.55 * concept_ratio + 0.45 * token_ratio

    score = round(score, 4)

    strict_flags: list[str] = []

    if claim_has_number and number_ratio < 1.0:
        strict_flags.append(f"숫자 불일치 또는 누락(number_ratio={number_ratio:.2f})")

    if missing_concepts:
        strict_flags.append(f"필수 근거 항목 누락: {missing_concepts}")

    if not year_ok:
        strict_flags.append(f"기간 불일치 또는 누락: claim_years={sorted(claim_years)}")

    if "지속적으로" in claim_text or "연속" in claim_text:
        if not _contains_any(combined_evidence_text, ["지속", "연속", "3개년", "2개년", "계속"]):
            strict_flags.append("지속성 표현을 뒷받침하는 기간 근거 부족")

    if _contains_any(claim_text, ["기술적 하방", "하방 압력", "기술적 약세"]):
        if not _contains_any(combined_evidence_text, ["기술적", "하방", "이동평균", "추세", "차트"]):
            strict_flags.append("기술적 하방 압력 표현을 뒷받침하는 기술적 지표 근거 부족")

    supported = not strict_flags

    if supported:
        if claim_has_number:
            supported = number_ratio >= 1.0 and concept_ratio >= 1.0 and token_ratio >= 0.05
        else:
            supported = concept_ratio >= 1.0 and token_ratio >= 0.12

    return {
        "claim_id": claim_id,
        "text": claim_text,
        "evidence_ids": evidence_ids,
        "supported": bool(supported),
        "score": score,
        "number_ratio": round(number_ratio, 4),
        "token_ratio": round(token_ratio, 4),
        "concept_ratio": round(concept_ratio, 4),
        "missing_concepts": missing_concepts,
        "concept_matches": concept_matches,
        "reason": "supported" if supported else " / ".join(strict_flags) or "evidence와 claim 연결이 약합니다.",
    }


def score_claim_evidence_packet(
    packet: dict[str, Any],
    *,
    pass_threshold: float = 0.75,
) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {
            "score": 0.0,
            "pass": False,
            "pass_threshold": pass_threshold,
            "supported_claims": [],
            "unsupported_claims": ["packet is not a JSON object"],
            "issues": ["packet is not a JSON object"],
            "claim_results": [],
        }

    claims = packet.get("claims") if isinstance(packet.get("claims"), list) else []

    evidences = packet.get("evidences")
    if not isinstance(evidences, list):
        evidences = packet.get("evidence", [])

    if not isinstance(evidences, list):
        evidences = []

    evidence_by_id = {
        str(ev.get("evidence_id")): ev
        for ev in evidences
        if isinstance(ev, dict) and ev.get("evidence_id")
    }

    if not claims:
        return {
            "score": 0.0,
            "pass": False,
            "pass_threshold": pass_threshold,
            "supported_claims": [],
            "unsupported_claims": ["claims[]가 비어 있습니다."],
            "issues": ["claims[]가 비어 있습니다."],
            "claim_count": 0,
            "supported_count": 0,
            "unsupported_count": 0,
            "claim_results": [],
        }

    claim_results: list[dict[str, Any]] = []

    for claim in claims:
        if not isinstance(claim, dict):
            claim_results.append(
                {
                    "claim_id": "",
                    "text": _clean_text(claim),
                    "supported": False,
                    "score": 0.0,
                    "reason": "claim이 dict 형식이 아닙니다.",
                }
            )
            continue

        claim_results.append(_evaluate_claim(claim, evidence_by_id))

    supported_results = [r for r in claim_results if r.get("supported")]
    unsupported_results = [r for r in claim_results if not r.get("supported")]

    total = len(claim_results)
    supported_count = len(supported_results)
    score = supported_count / max(1, total)

    return {
        "score": round(score, 4),
        "pass": score >= pass_threshold,
        "pass_threshold": pass_threshold,
        "claim_count": total,
        "supported_count": supported_count,
        "unsupported_count": len(unsupported_results),
        "supported_claims": [r.get("text", "") for r in supported_results],
        "unsupported_claims": [r.get("text", "") for r in unsupported_results],
        "issues": [
            f"{r.get('claim_id') or r.get('text', '')[:30]}: {r.get('reason')}"
            for r in unsupported_results
        ],
        "claim_results": claim_results,
    }


def remove_unsupported_claims_from_packet(
    packet: dict[str, Any],
    check: dict[str, Any],
) -> dict[str, Any]:
    packet = copy.deepcopy(packet)

    claim_results = check.get("claim_results", [])
    if not isinstance(claim_results, list):
        return packet

    supported_texts = {
        _clean_text(r.get("text"))
        for r in claim_results
        if isinstance(r, dict) and r.get("supported")
    }

    unsupported_texts = {
        _clean_text(r.get("text"))
        for r in claim_results
        if isinstance(r, dict) and not r.get("supported")
    }

    if not unsupported_texts:
        return packet

    original_claims = packet.get("claims")
    if isinstance(original_claims, list):
        packet["claims"] = [
            cl for cl in original_claims
            if isinstance(cl, dict) and _clean_text(cl.get("text")) in supported_texts
        ]

    for key in (
        "key_thesis",
        "key_points",
        "risks",
        "key_risks",
        "theses",
        "opportunities",
    ):
        value = packet.get(key)

        if not isinstance(value, list):
            continue

        filtered = []

        for item in value:
            if isinstance(item, dict):
                text = _clean_text(
                    item.get("text")
                    or item.get("claim")
                    or item.get("risk")
                    or item.get("opportunity")
                    or item.get("summary")
                )
            else:
                text = _clean_text(item)

            if text in unsupported_texts:
                continue

            filtered.append(item)

        packet[key] = filtered

    raw_payload = packet.get("raw_payload")
    if not isinstance(raw_payload, dict):
        raw_payload = {}

    removed = raw_payload.get("removed_ungrounded_claims")
    if not isinstance(removed, list):
        removed = []

    for text in sorted(unsupported_texts):
        if text and text not in removed:
            removed.append(text)

    raw_payload["removed_ungrounded_claims"] = removed
    packet["raw_payload"] = raw_payload

    return packet


__all__ = [
    "enforce_evidence_contract",
    "score_claim_evidence_packet",
    "remove_unsupported_claims_from_packet",
]
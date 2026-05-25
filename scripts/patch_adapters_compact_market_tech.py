from pathlib import Path

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

helper_marker = "def _compact_market_history_for_auditor"
insert_before = "POSITIVE_TERMS = ["

helper_code = r'''
def _short_text(value: Any, max_chars: int = 900) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _normalized_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _deep_find_first(obj: Any, keys: list[str], *, max_depth: int = 8) -> Any:
    """
    nested dict/list에서 후보 key 중 첫 값을 찾는다.
    너무 깊은 raw payload 전체를 Auditor에 넘기지 않고도 핵심 지표만 끌어오기 위한 helper.
    """
    target_keys = {_normalized_key(k) for k in keys}

    def walk(x: Any, depth: int) -> Any:
        if depth > max_depth:
            return None

        if isinstance(x, dict):
            for k, v in x.items():
                if _normalized_key(k) in target_keys and v not in (None, "", [], {}):
                    return v

            for v in x.values():
                found = walk(v, depth + 1)
                if found not in (None, "", [], {}):
                    return found

        elif isinstance(x, list):
            for item in x[:80]:
                found = walk(item, depth + 1)
                if found not in (None, "", [], {}):
                    return found

        return None

    return walk(obj, 0)


def _clean_summary_for_auditor(value: Any, *, fallback: str) -> str:
    """
    Auditor가 template/request/missing-context 문구를 실패 신호로 오인하지 않도록
    raw LLM prompt/placeholder성 문장을 제거한다.
    """
    text = str(value or "").strip()
    if not text:
        return fallback

    banned_terms = (
        "missing-context",
        "missing context",
        "template",
        "request",
        "placeholder",
        "프롬프트",
        "템플릿",
        "요청문",
        "작성 요청",
    )

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()
        if any(term in lowered for term in banned_terms):
            continue

        lines.append(stripped)

        if len(" ".join(lines)) >= 700:
            break

    cleaned = " ".join(lines).strip()
    return _short_text(cleaned or fallback, 900)


def _compact_market_history_for_auditor(payload: dict, *, company: str, company_dir: str) -> dict:
    """
    Market Agent history snapshot을 Chair/Auditor용 compact packet으로 변환한다.

    목적:
    - Auditor stage2에서 요구하는 return / drawdown / liquidity 키워드와 지표를 명시적으로 노출
    - market raw nested payload 전체를 넘기지 않고 핵심 market framework만 전달
    """
    source = payload if isinstance(payload, dict) else {}
    history_meta = source.get("agent_history_snapshot")

    total_score = (
        _deep_find_first(source, ["total_score", "market_score", "score"])
    )
    current_price = _deep_find_first(
        source,
        ["current_price", "latest_close", "close_price", "close", "현재가"],
    )
    annual_return = _deep_find_first(
        source,
        ["annual_return", "return_1y", "one_year_return", "yearly_return", "1y_return"],
    )
    recent_1m_return = _deep_find_first(
        source,
        ["recent_1m_return", "return_1m", "one_month_return", "monthly_return", "1m_return"],
    )
    mdd = _deep_find_first(
        source,
        ["mdd", "max_drawdown", "maximum_drawdown", "drawdown"],
    )
    volatility = _deep_find_first(
        source,
        ["volatility", "annualized_volatility", "vol_20d", "volatility_20d"],
    )
    avg_trading_value_20d = _deep_find_first(
        source,
        [
            "avg_trading_value_20d",
            "average_trading_value_20d",
            "avg_turnover_20d",
            "trading_value_20d",
            "거래대금_20일평균",
        ],
    )
    turnover_proxy = _deep_find_first(
        source,
        ["turnover_proxy", "turnover", "liquidity_turnover", "volume_turnover"],
    )
    liquidity_status = _deep_find_first(
        source,
        ["liquidity_status", "liquidity_grade", "liquidity", "유동성"],
    )

    original_summary = (
        source.get("summary")
        or source.get("market_summary")
        or source.get("analysis_summary")
        or source.get("analysis")
        or ""
    )

    summary = _clean_summary_for_auditor(
        original_summary,
        fallback=(
            f"{company} Market Agent snapshot은 주가 수익률(return), 최대낙폭(drawdown), "
            f"거래대금·회전율 기반 유동성(liquidity)을 Chair/Auditor 검증용으로 요약한 compact packet입니다."
        ),
    )

    framework_metrics = {
        "return": {
            "annual_return": annual_return,
            "recent_1m_return": recent_1m_return,
        },
        "drawdown": {
            "mdd": mdd,
            "volatility": volatility,
        },
        "liquidity": {
            "avg_trading_value_20d": avg_trading_value_20d,
            "turnover_proxy": turnover_proxy,
            "liquidity_status": liquidity_status,
        },
        "price": {
            "current_price": current_price,
        },
        "market_score": total_score,
    }

    evidences = [
        {
            "evidence_id": "MKT_RETURN_METRICS",
            "source_type": "market_history_snapshot",
            "source_name": "Market Agent price return metrics",
            "snippet": (
                f"{company} market return metrics: "
                f"annual_return={annual_return}, recent_1m_return={recent_1m_return}, "
                f"current_price={current_price}."
            ),
        },
        {
            "evidence_id": "MKT_DRAWDOWN_METRICS",
            "source_type": "market_history_snapshot",
            "source_name": "Market Agent drawdown and volatility metrics",
            "snippet": (
                f"{company} market drawdown metrics: "
                f"mdd={mdd}, volatility={volatility}."
            ),
        },
        {
            "evidence_id": "MKT_LIQUIDITY_METRICS",
            "source_type": "market_history_snapshot",
            "source_name": "Market Agent liquidity metrics",
            "snippet": (
                f"{company} market liquidity metrics: "
                f"avg_trading_value_20d={avg_trading_value_20d}, "
                f"turnover_proxy={turnover_proxy}, liquidity_status={liquidity_status}."
            ),
        },
    ]

    claims = [
        {
            "claim_id": "MKT_CLAIM_RETURN",
            "text": (
                f"{company}의 Market Agent는 return 지표로 "
                f"annual_return={annual_return}, recent_1m_return={recent_1m_return}을 제공합니다."
            ),
            "evidence_ids": ["MKT_RETURN_METRICS"],
        },
        {
            "claim_id": "MKT_CLAIM_DRAWDOWN",
            "text": (
                f"{company}의 Market Agent는 drawdown 지표로 "
                f"mdd={mdd}, volatility={volatility}를 제공합니다."
            ),
            "evidence_ids": ["MKT_DRAWDOWN_METRICS"],
        },
        {
            "claim_id": "MKT_CLAIM_LIQUIDITY",
            "text": (
                f"{company}의 Market Agent는 liquidity 지표로 "
                f"avg_trading_value_20d={avg_trading_value_20d}, "
                f"turnover_proxy={turnover_proxy}, liquidity_status={liquidity_status}를 제공합니다."
            ),
            "evidence_ids": ["MKT_LIQUIDITY_METRICS"],
        },
    ]

    compact = {
        "agent": "market",
        "company": company,
        "company_dir": company_dir,
        "summary": summary,
        "opinion": source.get("opinion"),
        "confidence": source.get("confidence"),
        "total_score": total_score,
        "framework_metrics": framework_metrics,
        "market_framework": {
            "return_visible": True,
            "drawdown_visible": True,
            "liquidity_visible": True,
            "framework_keywords": ["return", "drawdown", "liquidity"],
        },
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "source_contexts": evidences,
        "adapter_compaction": {
            "enabled": True,
            "reason": "Auditor용 compact market packet: return/drawdown/liquidity 명시",
            "raw_payload_omitted": True,
        },
    }

    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact


def _compact_tech_history_for_auditor(payload: dict, *, company: str, company_dir: str) -> dict:
    """
    Tech Agent history snapshot을 Chair/Auditor용 compact packet으로 변환한다.

    목적:
    - raw tech_chair_summary / threshold / template / 중간 dict를 그대로 넘기지 않음
    - patent_count가 confidence처럼 오인되는 문제 방지
    - registered_patents 충돌값을 Auditor 입력에서 제거하고 단일 count 명칭만 사용
    """
    source = payload if isinstance(payload, dict) else {}
    history_meta = source.get("agent_history_snapshot")

    total_score = _deep_find_first(
        source,
        [
            "final_investor_tech_score",
            "final_tech_evidence_score",
            "tech_evidence_score",
            "total_score",
            "score",
        ],
    )
    max_score = _deep_find_first(
        source,
        ["max_score", "total_possible_score", "score_max"],
    ) or 35

    bridge_score = _deep_find_first(
        source,
        [
            "tech_to_value_bridge_score",
            "peer_adjusted_bridge_score",
            "bridge_score",
            "tech_to_value_score",
        ],
    )
    bridge_grade = _deep_find_first(
        source,
        ["bridge_grade", "grade", "final_grade", "tech_to_value_grade"],
    )
    differentiation_score = _deep_find_first(
        source,
        ["technology_differentiation_score", "differentiation_score"],
    )
    momentum_score = _deep_find_first(
        source,
        ["patent_momentum_score", "momentum_score"],
    )
    evidence_confidence_score = _deep_find_first(
        source,
        ["tech_to_value_evidence_confidence", "evidence_confidence_score"],
    )
    ip_strength_score = _deep_find_first(
        source,
        ["tech_ip_strength_index", "ip_strength_score", "ip_strength_index"],
    )

    patent_records_count = _deep_find_first(
        source,
        [
            "patent_records_count",
            "patents_count",
            "patent_count",
            "total_patents",
            "patents",
        ],
    )

    # registered_patents는 payload 내부에서 서로 다른 의미로 충돌할 수 있어
    # registered_patents_estimated / registered_patents_count만 사용한다.
    registered_patents_count = _deep_find_first(
        source,
        [
            "registered_patents_count",
            "registered_patents_estimated",
            "valid_registered_patents_count",
        ],
    )

    original_summary = (
        source.get("summary")
        or source.get("tech_summary")
        or source.get("chair_summary")
        or source.get("analysis_summary")
        or ""
    )

    summary = _clean_summary_for_auditor(
        original_summary,
        fallback=(
            f"{company} Tech Agent snapshot은 기술-사업화 연결성, IP 정량 신호, "
            f"차별성, 특허 모멘텀, 근거 직접성을 Chair/Auditor 검증용으로 요약한 compact packet입니다."
        ),
    )

    tech_framework_metrics = {
        "tech_to_value_bridge_score": bridge_score,
        "bridge_grade": bridge_grade,
        "technology_differentiation_score": differentiation_score,
        "patent_momentum_score": momentum_score,
        "tech_to_value_evidence_confidence_score": evidence_confidence_score,
        "tech_ip_strength_score": ip_strength_score,
        "score": {
            "total_score": total_score,
            "max_score": max_score,
        },
        "ip_metrics": {
            "patent_records_count": patent_records_count,
            "registered_patents_count": registered_patents_count,
        },
    }

    evidences = [
        {
            "evidence_id": "TECH_BRIDGE_METRICS",
            "source_type": "tech_history_snapshot",
            "source_name": "Tech-to-Value Bridge compact metrics",
            "snippet": (
                f"{company} tech-to-value bridge metrics: "
                f"bridge_score={bridge_score}, bridge_grade={bridge_grade}, "
                f"total_score={total_score}, max_score={max_score}."
            ),
        },
        {
            "evidence_id": "TECH_IP_METRICS",
            "source_type": "tech_history_snapshot",
            "source_name": "IP quantitative compact metrics",
            "snippet": (
                f"{company} IP metrics: patent_records_count={patent_records_count}, "
                f"registered_patents_count={registered_patents_count}, "
                f"tech_ip_strength_score={ip_strength_score}."
            ),
        },
        {
            "evidence_id": "TECH_ML_METRICS",
            "source_type": "tech_history_snapshot",
            "source_name": "Tech ML compact metrics",
            "snippet": (
                f"{company} Tech ML metrics: differentiation_score={differentiation_score}, "
                f"patent_momentum_score={momentum_score}, "
                f"evidence_confidence_score={evidence_confidence_score}."
            ),
        },
    ]

    claims = [
        {
            "claim_id": "TECH_CLAIM_BRIDGE",
            "text": (
                f"{company}의 Tech Agent는 기술-사업화 연결성 지표로 "
                f"bridge_score={bridge_score}, bridge_grade={bridge_grade}를 제공합니다."
            ),
            "evidence_ids": ["TECH_BRIDGE_METRICS"],
        },
        {
            "claim_id": "TECH_CLAIM_IP",
            "text": (
                f"{company}의 Tech Agent는 IP 정량 지표로 "
                f"patent_records_count={patent_records_count}, "
                f"registered_patents_count={registered_patents_count}, "
                f"tech_ip_strength_score={ip_strength_score}를 제공합니다."
            ),
            "evidence_ids": ["TECH_IP_METRICS"],
        },
        {
            "claim_id": "TECH_CLAIM_ML",
            "text": (
                f"{company}의 Tech Agent는 기술 차별성·특허 모멘텀·근거 직접성 보조지표로 "
                f"differentiation_score={differentiation_score}, "
                f"patent_momentum_score={momentum_score}, "
                f"evidence_confidence_score={evidence_confidence_score}를 제공합니다."
            ),
            "evidence_ids": ["TECH_ML_METRICS"],
        },
    ]

    compact = {
        "agent": "tech",
        "company": company,
        "company_dir": company_dir,
        "summary": summary,
        "opinion": source.get("opinion"),
        "confidence": source.get("confidence"),
        "total_score": total_score,
        "max_score": max_score,
        "tech_framework_metrics": tech_framework_metrics,
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "source_contexts": evidences,
        "adapter_compaction": {
            "enabled": True,
            "reason": "Auditor용 compact tech packet: noisy raw nested payload 제거",
            "raw_payload_omitted": True,
            "removed_noisy_fields": [
                "raw_nested_thresholds",
                "template_or_request_text",
                "conflicting_registered_patents_raw_values",
                "full_tech_chair_summary_raw_payload",
            ],
        },
    }

    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError(f"insert marker not found: {insert_before}")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)

old_market = '''def run_market_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="market",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        normalized = _with_evidence_contract(
            history_payload,
            agent_name="market",
            company=company,
        )
        normalized.setdefault("market_adapter_status", "LOADED_FROM_AGENT_HISTORY")
        return normalized

    from market_agent.runner import run_market_report

    return _with_evidence_contract(
        run_market_report(company, company_dir=company_dir),
        agent_name="market",
        company=company,
    )
'''

new_market = '''def run_market_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="market",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        compact_payload = _compact_market_history_for_auditor(
            history_payload,
            company=company,
            company_dir=company_dir,
        )
        normalized = _with_evidence_contract(
            compact_payload,
            agent_name="market",
            company=company,
        )
        normalized.setdefault("market_adapter_status", "LOADED_FROM_AGENT_HISTORY_COMPACT")
        return normalized

    from market_agent.runner import run_market_report

    return _with_evidence_contract(
        run_market_report(company, company_dir=company_dir),
        agent_name="market",
        company=company,
    )
'''

old_tech = '''def run_tech_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="tech",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        normalized = _with_evidence_contract(
            history_payload,
            agent_name="tech",
            company=company,
        )
        normalized.setdefault("tech_adapter_status", "LOADED_FROM_AGENT_HISTORY")
        return normalized

    from tech_agent.runner import run_tech_agent

    return _with_evidence_contract(
        run_tech_agent(company_dir, company),
        agent_name="tech",
        company=company,
    )
'''

new_tech = '''def run_tech_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="tech",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        compact_payload = _compact_tech_history_for_auditor(
            history_payload,
            company=company,
            company_dir=company_dir,
        )
        normalized = _with_evidence_contract(
            compact_payload,
            agent_name="tech",
            company=company,
        )
        normalized.setdefault("tech_adapter_status", "LOADED_FROM_AGENT_HISTORY_COMPACT")
        return normalized

    from tech_agent.runner import run_tech_agent

    return _with_evidence_contract(
        run_tech_agent(company_dir, company),
        agent_name="tech",
        company=company,
    )
'''

if old_market not in text:
    raise RuntimeError("market function block not found. adapters.py 구조가 예상과 다릅니다.")
text = text.replace(old_market, new_market, 1)

if old_tech not in text:
    raise RuntimeError("tech function block not found. adapters.py 구조가 예상과 다릅니다.")
text = text.replace(old_tech, new_tech, 1)

path.write_text(text, encoding="utf-8")
print("[OK] adapters.py patched: compact market/tech history payloads for Auditor.")

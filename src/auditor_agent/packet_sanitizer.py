from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.data_paths import company_agent_dir, first_auditor_dir, read_json, rel_project_path

REMOVE_FOR_CHAIR = {
    "opinion",
    "final_opinion",
    "recommendation",
    "confidence",
    "evidence",
    "evidences",
    "source_contexts",
    "sources",
    "claims",
    "raw_payload",
    "web_verification",
    "chair_safe_claims",
    "chair_blocked_claims",
    "pre_sanitize_grounding_check",
    "post_atomic_grounding_check",
    "grounding_check",
}

COUNT_ONLY_RE = re.compile(r"(?:news_count|rss_count|related_keyword_count|count|_count)\s*값은", re.I)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "y"}


def _history_local_write_disabled() -> bool:
    backend = os.getenv("ALPHAPROVE_HISTORY_BACKEND", "").strip().lower()
    sheets_mode = backend in {"sheets", "google_sheets", "gsheets", "google"} or bool(os.getenv("ALPHAPROVE_HISTORY_SPREADSHEET_ID"))
    db_only = _env_bool("ALPHAPROVE_SHEETS_DB_ONLY", False)
    disabled = _env_bool("ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED", True)
    return sheets_mode and db_only and disabled


def _agent_name(packet: dict[str, Any]) -> str:
    for key in ("agent", "agent_name", "source_agent", "name"):
        value = packet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower().replace("_agent", "")
    raw = packet.get("raw_payload")
    if isinstance(raw, dict):
        for key in ("agent", "agent_name", "source_agent", "name"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower().replace("_agent", "")
    return "unknown"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _clip(value: Any, limit: int = 360) -> str:
    text = _text(value)
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    # Keep complete Korean/English sentences instead of leaving '...패키지…' fragments.
    boundaries = [cut.rfind(x) for x in (". ", "다. ", "요. ", "임. ", "음. ", "! ", "? ", "。")]
    boundary = max(boundaries)
    if boundary >= min(80, max(10, int(limit * 0.25))):
        cut = cut[: boundary + 1].rstrip()
    else:
        comma = max(cut.rfind(". "), cut.rfind("다."), cut.rfind("요."), cut.rfind("음."), cut.rfind(";"))
        if comma >= min(80, max(10, int(limit * 0.20))):
            cut = cut[: comma + 1].rstrip()
    return cut.rstrip(" ,;:/·-…")


def _as_list(value: Any, limit: int = 6) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value[:limit]
    if isinstance(value, tuple):
        return list(value)[:limit]
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _dedupe(items: list[str], *, limit: int = 4) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "")).strip(" -•\t\n")
        if not text:
            continue
        if text.lower().startswith(("opinion:", "confidence:")):
            continue
        key = re.sub(r"[\W_]+", "", text.lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(_clip(text, 420))
        if len(out) >= limit:
            break
    return out


def _nested_get(data: Any, path: list[str]) -> Any:
    cur = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _find_metric_in_evidence(packet: dict[str, Any], metric_names: list[str]) -> Any:
    names = {str(x).lower() for x in metric_names}
    for key in ("evidences", "evidence"):
        values = packet.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            metric = str(item.get("metric") or "").lower()
            if metric in names or any(metric.endswith("." + n) for n in names):
                return item.get("value")
    return None


def _format_number(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _strip_report_noise(text: str) -> str:
    lines: list[str] = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.lower().startswith(("opinion:", "confidence:")):
            continue
        if stripped.startswith("# ") and ("리포트" in stripped or "분석 결과" in stripped):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _markdown_section(text: str, title_keywords: list[str]) -> str:
    clean = _strip_report_noise(text)
    lines = clean.splitlines()
    start: int | None = None
    # Accept markdown headings and numbered bold issue-agent headings such as
    # '1. **핵심 이슈 요약**'. This prevents fallback clipping from cutting issue text.
    heading_re = re.compile(r"^\s{0,3}(?:#{2,5}\s*)?(?:\d+[.)]\s*)?(?:[-*•]\s*)?(?:\*\*)?(.+?)(?:\*\*)?\s*:?\s*$")

    def _is_heading(raw: str) -> bool:
        stripped = raw.strip()
        if stripped.startswith("##"):
            return True
        if re.match(r"^\d+[.)]\s+\*\*.+?\*\*", stripped):
            return True
        if re.match(r"^\*\*[^*]{2,40}\*\*\s*:?$", stripped):
            return True
        return False

    for idx, line in enumerate(lines):
        if not _is_heading(line):
            continue
        m = heading_re.match(line)
        if not m:
            continue
        heading = re.sub(r"^[0-9.\-\s]+", "", m.group(1)).strip(" *:")
        if any(keyword in heading for keyword in title_keywords):
            start = idx + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start, len(lines)):
        if _is_heading(lines[idx]):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _section_paragraph(text: str, title_keywords: list[str], *, limit: int = 520) -> str:
    section = _markdown_section(text, title_keywords)
    if not section:
        return ""
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
    for para in paragraphs:
        if para.startswith(("*", "-", "•")):
            continue
        return _clip(para, limit)
    return _clip(paragraphs[0], limit) if paragraphs else ""


def _section_bullets(text: str, title_keywords: list[str], *, limit: int = 4) -> list[str]:
    section = _markdown_section(text, title_keywords)
    if not section:
        return []
    items: list[str] = []
    for line in section.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith(("*", "-", "•")):
            raw = re.sub(r"^[\*\-•]\s+", "", raw).strip()
            raw = re.sub(r"^\*\*(.+?):\*\*\s*", r"\1: ", raw)
            raw = re.sub(r"^\*\*(.+?)\*\*\s*:?\s*", r"\1: ", raw)
            items.append(raw)
        elif len(items) < limit and not raw.startswith("#"):
            # Keep short standalone lines when the source did not use bullets.
            if len(raw) <= 240:
                items.append(raw)
    return _dedupe(items, limit=limit)


def _dict_item_text(item: Any, *keys: str) -> str:
    if isinstance(item, dict):
        for key in keys:
            if item.get(key) not in (None, ""):
                return _text(item.get(key))
        parts: list[str] = []
        for key in ("opportunity", "risk", "reason", "basis", "assessment", "value"):
            if item.get(key) not in (None, ""):
                parts.append(_text(item.get(key)))
        return " / ".join(parts)
    return _text(item)


def _market_analysis(packet: dict[str, Any]) -> dict[str, Any]:
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    analysis = raw.get("analysis") if isinstance(raw.get("analysis"), dict) else {}
    if not analysis:
        return {}

    market_summary = analysis.get("market_summary") if isinstance(analysis.get("market_summary"), dict) else {}
    summary = _clip(analysis.get("summary"), 560)
    if not summary and market_summary:
        pieces = [
            market_summary.get("industry_stage"),
            market_summary.get("value_chain_position"),
            market_summary.get("market_momentum"),
        ]
        summary = _clip(" ".join(_text(p) for p in pieces if p), 560)

    thesis: list[str] = []
    for item in _as_list(analysis.get("opportunities"), limit=4):
        text = _dict_item_text(item, "opportunity", "basis")
        if text:
            thesis.append(text)
    if market_summary.get("industry_stage"):
        thesis.append(market_summary["industry_stage"])
    if market_summary.get("value_chain_position"):
        thesis.append(market_summary["value_chain_position"])

    risks: list[str] = []
    for item in _as_list(analysis.get("risks"), limit=4):
        text = _dict_item_text(item, "risk", "basis")
        if text:
            risks.append(text)
    if market_summary.get("market_momentum"):
        risks.append(market_summary["market_momentum"])
    if market_summary.get("competitive_position"):
        risks.append(market_summary["competitive_position"])

    metrics: dict[str, Any] = {
        "market_total_score": analysis.get("total_score") or packet.get("total_score"),
        "current_price_krw": _find_metric_in_evidence(packet, ["stock_data.current_price", "current_price"]),
        "change_krw": _find_metric_in_evidence(packet, ["stock_data.change", "change", "stock_data.raw.vs"]),
        "change_rate_pct": _find_metric_in_evidence(packet, ["stock_data.change_rate", "change_rate", "stock_data.raw.fltrt"]),
        "scoring": analysis.get("scoring"),
        "qualitative_rubric": analysis.get("qualitative_rubric"),
    }
    metrics = {k: v for k, v in metrics.items() if v not in (None, "", [], {})}

    return {
        "summary": summary,
        "key_thesis": _dedupe(thesis, limit=4),
        "key_risks": _dedupe(risks, limit=4),
        "metrics": metrics,
        "watch_points": _dedupe([analysis.get("bwm_assessment", {}).get("judgment_effect")], limit=2),
    }


def _issue_analysis(packet: dict[str, Any]) -> dict[str, Any]:
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    text = raw.get("analysis_text") or raw.get("markdown_report") or ""
    if not text:
        return {}

    summary = _section_paragraph(text, ["핵심 이슈 요약", "요약"], limit=560)
    if not summary:
        summary = _clip(text, 560)

    thesis = []
    thesis.extend(_section_bullets(text, ["긍정 시그널", "긍정", "기회"], limit=4))
    impact = _section_paragraph(text, ["기업에 미치는 영향", "영향"], limit=260)
    if impact:
        thesis.append(impact)

    risks = _section_bullets(text, ["부정 시그널", "리스크", "위험"], limit=4)
    watch_points = _section_bullets(text, ["향후 체크포인트", "체크포인트", "모니터링"], limit=4)

    metrics = {
        "news_count": raw.get("news_count"),
        "rss_count": raw.get("rss_count"),
        "related_keyword_count": raw.get("related_keyword_count"),
        "df_news_rows": raw.get("df_news_rows"),
        "llm_error": raw.get("llm_error"),
    }
    metrics = {k: v for k, v in metrics.items() if v not in (None, "", [], {})}

    warning_note = packet.get("warning_note")
    if not warning_note and raw.get("llm_error"):
        warning_note = f"issue LLM 분석 오류: {raw.get('llm_error')}"

    return {
        "summary": summary,
        "key_thesis": _dedupe(thesis, limit=4),
        "key_risks": _dedupe(risks, limit=4),
        "watch_points": watch_points,
        "metrics": metrics,
        "warning_note": warning_note,
    }


def _macro_analysis(packet: dict[str, Any]) -> dict[str, Any]:
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    if not raw:
        return {}
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    llm = details.get("llm_analysis") if isinstance(details.get("llm_analysis"), dict) else {}

    summary = _clip(llm.get("llm_summary") or llm.get("macro_interpretation") or raw.get("summary"), 560)

    reasons = [_text(x) for x in _as_list(raw.get("reasons"), limit=9)]
    positive_keywords = ("완화", "우호", "개선", "상승 → 경기 기대", "규제 리스크 신호 약함")
    risk_keywords = ("부담", "약세", "위험", "인플레이션", "부정", "하락", "규제")

    thesis = [r for r in reasons if any(k in r for k in positive_keywords)]
    if not thesis:
        thesis = reasons[:3]

    risks = [_text(x) for x in _as_list(llm.get("key_risks"), limit=4)]
    if not risks:
        risks = [r for r in reasons if any(k in r for k in risk_keywords)]

    watch_points = [_text(x) for x in _as_list(llm.get("watch_points"), limit=4)]

    metrics = {
        "macro_score": raw.get("score"),
        "macro_signal": raw.get("signal"),
        "risk_level": raw.get("risk_level"),
        "ecos_daily": details.get("ecos_일별"),
        "external_daily": details.get("ext_일별"),
        "news_signal": details.get("뉴스"),
        "regulation_signal": details.get("규제"),
    }
    metrics = {k: v for k, v in metrics.items() if v not in (None, "", [], {})}

    return {
        "summary": summary,
        "key_thesis": _dedupe(thesis, limit=4),
        "key_risks": _dedupe(risks, limit=4),
        "watch_points": _dedupe(watch_points, limit=4),
        "metrics": metrics,
    }


def _canonical_company_key(packet: dict[str, Any], company: str | None = None, company_dir: str | None = None) -> str:
    for value in (
        company_dir,
        packet.get("company_dir"),
        packet.get("company_slug"),
        packet.get("company"),
        packet.get("company_name"),
        company,
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    for value in (raw.get("company_dir"), raw.get("company_slug"), raw.get("company"), raw.get("company_name")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return company or "unknown_company"


def _load_agent_json(company_key: str, agent: str, names: list[str]) -> dict[str, Any]:
    try:
        base = company_agent_dir(company_key, agent, create=False)
    except Exception:
        return {}
    for name in names:
        path = base / name
        if path.exists():
            data = read_json(path)
            if isinstance(data, dict):
                data.setdefault("_source_file", rel_project_path(path))
                return data
    return {}


def _deep_find(data: Any, keys: list[str]) -> Any:
    """Depth-first value lookup used only for compact packet generation."""
    if isinstance(data, dict):
        for key in keys:
            if key in data and data.get(key) not in (None, "", [], {}):
                return data.get(key)
        for value in data.values():
            found = _deep_find(value, keys)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(data, list):
        for value in data:
            found = _deep_find(value, keys)
            if found not in (None, "", [], {}):
                return found
    return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if text.lower() in {"", "none", "null", "nan", "확인 제한"}:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _fmt_score(value: Any, digits: int = 2) -> str:
    num = _to_float(value)
    return "확인 제한" if num is None else f"{num:.{digits}f}"


def _fmt_pct(value: Any, digits: int = 2) -> str:
    num = _to_float(value)
    if num is None:
        return "확인 제한"
    if -2.0 <= num <= 2.0:
        num *= 100.0
    return f"{num:.{digits}f}%"


def _fmt_krw(value: Any) -> str:
    num = _to_float(value)
    if num is None:
        return "확인 제한"
    if abs(num) >= 100_000_000:
        return f"{num / 100_000_000:,.1f}억원"
    return f"{num:,.0f}원"


def _agent_view_reference(packet: dict[str, Any]) -> str | None:
    """Return original specialist view for interpretation, without exposing an opinion field."""
    candidates = [
        packet.get("opinion"),
        packet.get("final_opinion"),
        packet.get("recommendation"),
        packet.get("investment_view"),
    ]
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    candidates.extend([raw.get("opinion"), raw.get("final_opinion"), raw.get("recommendation"), raw.get("investment_view")])
    for value in candidates:
        text = str(value or "").strip()
        for label in ("매수", "보유", "매도"):
            if label in text:
                return label
        upper = text.upper()
        if "BUY" in upper:
            return "매수"
        if "SELL" in upper:
            return "매도"
        if "HOLD" in upper:
            return "보유"
    return None


def _compact_peer_names(value: Any, limit: int = 5) -> str:
    names: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = item.get("company_name") or item.get("company") or item.get("name") or item.get("ticker")
            else:
                name = item
            if name and str(name) not in names:
                names.append(str(name))
            if len(names) >= limit:
                break
    return ", ".join(names)


def _tech_analysis(packet: dict[str, Any], company: str | None = None, company_dir: str | None = None) -> dict[str, Any]:
    company_key = _canonical_company_key(packet, company, company_dir)
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    base = raw if raw else packet

    chair_summary = base if str(base.get("agent") or "").lower() == "tech" and ("tech_to_value" in base or "selected_ml" in base) else {}
    if not chair_summary:
        chair_summary = _load_agent_json(company_key, "tech", [
            "tech_chair_summary.json",
            f"{company_key}_tech_chair_summary.json",
            "nepes_tech_chair_summary.json",
        ])
    investor = chair_summary.get("tech_investor_view") if isinstance(chair_summary.get("tech_investor_view"), dict) else {}
    if not investor:
        investor = _load_agent_json(company_key, "tech", [
            "tech_investor_scorecard.json",
            f"{company_key}_tech_investor_scorecard.json",
            "nepes_tech_investor_scorecard.json",
        ])
    peer_bridge = _load_agent_json(company_key, "tech", [
        "tech_peer_percentile_bridge.json",
        f"{company_key}_tech_peer_percentile_bridge.json",
        "nepes_tech_peer_percentile_bridge.json",
    ])
    peer_map = _load_agent_json(company_key, "tech", [
        "tech_peer_map.json",
        f"{company_key}_tech_peer_map.json",
        "nepes_tech_peer_map.json",
    ])

    ttv = chair_summary.get("tech_to_value") if isinstance(chair_summary.get("tech_to_value"), dict) else {}
    selected_ml = chair_summary.get("selected_ml") if isinstance(chair_summary.get("selected_ml"), dict) else {}
    ip_comp = chair_summary.get("ip_evidence_composite") if isinstance(chair_summary.get("ip_evidence_composite"), dict) else {}
    if not ip_comp:
        ip_comp = chair_summary.get("ip_evidence_composite_features") if isinstance(chair_summary.get("ip_evidence_composite_features"), dict) else {}

    original_view = _agent_view_reference(packet) or _agent_view_reference(chair_summary)
    final_score = (
        investor.get("final_tech_investor_score")
        or selected_ml.get("final_bridge_score_after_ip_evidence")
        or ttv.get("final_bridge_score_after_ip_evidence")
        or ttv.get("peer_adjusted_bridge_score")
        or ttv.get("base_bridge_score")
        or _deep_find(base, ["final_tech_investor_score", "peer_adjusted_bridge_score", "bridge_score"])
    )
    final_grade = investor.get("final_tech_investor_grade") or {}
    if isinstance(final_grade, dict):
        final_grade_text = final_grade.get("code") or final_grade.get("label")
    else:
        final_grade_text = final_grade

    base_bridge = ttv.get("base_bridge_score") or peer_bridge.get("base_bridge_score")
    peer_adjusted = ttv.get("peer_adjusted_bridge_score") or peer_bridge.get("peer_adjusted_bridge_score")
    final_after_ip = ttv.get("final_bridge_score_after_ip_evidence") or selected_ml.get("final_bridge_score_after_ip_evidence") or peer_adjusted
    peer_percentile = peer_bridge.get("peer_composite_percentile") or selected_ml.get("peer_composite_percentile")
    peer_band = peer_bridge.get("peer_percentile_band") or selected_ml.get("peer_percentile_band")
    peer_adj_points = peer_bridge.get("peer_adjustment_points") or ttv.get("peer_adjustment_points")
    peer_group = peer_bridge.get("peer_group") or _nested_get(peer_map, ["peer_group"])
    cluster_name = peer_bridge.get("cluster_name") or _nested_get(peer_map, ["cluster_name"])
    nearest_peers = _compact_peer_names(peer_bridge.get("nearest_peers") or _nested_get(peer_map, ["companies"]), limit=5)

    ip_score = (
        ttv.get("ip_evidence_composite_score")
        or selected_ml.get("ip_evidence_composite_score")
        or ip_comp.get("ip_evidence_composite_score")
        or ip_comp.get("score")
    )
    ip_signal = ttv.get("ip_evidence_bridge_signal") or ttv.get("ip_evidence_composite_bridge_signal") or ip_comp.get("bridge_signal")

    ip_legal = chair_summary.get("ip_legal_features") if isinstance(chair_summary.get("ip_legal_features"), dict) else {}
    if not ip_legal:
        ip_legal = selected_ml.get("ip_legal_stability") if isinstance(selected_ml.get("ip_legal_stability"), dict) else {}
    ip_quant = chair_summary.get("ip_quant_signals") if isinstance(chair_summary.get("ip_quant_signals"), dict) else {}
    patent_count = ip_legal.get("total_patents") or ip_quant.get("company_matched_patents") or _deep_find(chair_summary, ["company_matched_patent_count", "normalized_patent_count", "patent_count", "patents"])
    registered_count = ip_legal.get("registered_patents_estimated") or ip_quant.get("registered_patents") or _deep_find(chair_summary, ["registered_patent_count", "registered_patents", "등록특허"])
    recent_count = ip_quant.get("recent_5y_patents") or _deep_find(chair_summary, ["recent_5y_patent_count", "recent_patent_count", "최근 5년 특허"])
    grade = ttv.get("peer_adjusted_grade") or ttv.get("base_bridge_grade") or peer_bridge.get("peer_adjusted_grade") or final_grade_text

    summary_parts = []
    if original_view:
        summary_parts.append(f"기존 Tech Agent 내부 판단은 {original_view}였고, Auditor compact에서는 이를 참고 신호로만 사용합니다.")
    if final_after_ip or final_score:
        summary_parts.append(
            f"최종 Tech 점수는 {_fmt_score(final_after_ip or final_score)}/100 수준이며 판정은 {grade or '확인 제한'}입니다."
        )
    if peer_adjusted or peer_percentile:
        summary_parts.append(
            f"peer 기준으로는 {peer_group or cluster_name or '동종 기술군'} 내 {peer_band or '상대 위치 확인'}이며, base {_fmt_score(base_bridge)}점에서 peer 보정 후 {_fmt_score(peer_adjusted)}점으로 조정되었습니다."
        )
    if ip_score:
        summary_parts.append(f"IP Evidence Composite는 {_fmt_score(ip_score)}/100({ip_signal or '신호 확인 제한'})으로, 특허 수 자체보다 권리 안정성·청구항·인용·패밀리 품질을 보조 판단합니다.")
    summary = " ".join(summary_parts) or "기술 산출물을 peer-aware compact packet으로 정리했습니다."

    thesis = [
        f"Peer 대비 Tech-to-Value: {peer_group or cluster_name or '동종 기술군'} 기준 {peer_band or '상대 위치 확인'}, peer percentile {_fmt_score(peer_percentile)}%, 보정 { _fmt_score(peer_adj_points) }점.",
        f"Bridge 점수 흐름: base {_fmt_score(base_bridge)}/100 → peer-adjusted {_fmt_score(peer_adjusted)}/100 → IP 반영 후 {_fmt_score(final_after_ip)}/100.",
        f"개인투자자용 최종 Tech 점수: {_fmt_score(final_score)}/100, grade={final_grade_text or grade or '확인 제한'}.",
        f"IP 품질: IP Evidence Composite {_fmt_score(ip_score)}/100, signal={ip_signal or '확인 제한'}." if ip_score else "",
    ]
    if patent_count or registered_count or recent_count:
        thesis.append(f"특허 정량 신호: 회사 매칭/정규화 특허 {_format_number(patent_count) or '확인 제한'}건, 등록 {_format_number(registered_count) or '확인 제한'}건, 최근 5년 {_format_number(recent_count) or '확인 제한'}건.")
    if nearest_peers:
        thesis.append(f"동일/근접 peer 예시: {nearest_peers}.")

    risks = []
    watch_meaning = ttv.get("commercialization_watch_meaning")
    if watch_meaning or str(grade or "").upper() == "COMMERCIALIZATION_WATCH":
        risks.append(watch_meaning or "COMMERCIALIZATION_WATCH: 기술/IP 신호는 있으나 고객 채택·양산·매출·FCF 연결을 계속 확인해야 합니다.")
    risks.append("기술 점수는 peer 대비 우호적이어도 최종 가치평가 가산에는 고객 채택, 양산, 매출 전환, FCF 개선의 직접 근거가 필요합니다.")
    if str(ip_signal or "").upper().endswith("WEAK") or "WEAK" in str(ip_signal or "").upper():
        risks.append(f"IP 품질 신호가 {ip_signal}이므로 특허 방어력·글로벌 확장성은 보수적으로 해석해야 합니다.")
    family_signal = ttv.get("ip_family_bridge_signal") or selected_ml.get("ip_family_bridge_signal")
    if family_signal and "WEAK" in str(family_signal).upper():
        risks.append(f"글로벌 패밀리/해외 확장 신호가 {family_signal}로 약해 해외 방어력 확인이 필요합니다.")

    metrics = {
        "original_agent_view_reference": original_view,
        "final_tech_investor_score": final_score,
        "base_bridge_score": base_bridge,
        "peer_adjusted_bridge_score": peer_adjusted,
        "final_bridge_score_after_ip_evidence": final_after_ip,
        "peer_composite_percentile": peer_percentile,
        "peer_percentile_band": peer_band,
        "peer_adjustment_points": peer_adj_points,
        "peer_group": peer_group,
        "cluster_name": cluster_name,
        "ip_evidence_composite_score": ip_score,
        "ip_evidence_bridge_signal": ip_signal,
        "patent_count": patent_count,
        "registered_patent_count": registered_count,
        "recent_5y_patent_count": recent_count,
        "nearest_peers": nearest_peers,
    }
    metrics = {k: v for k, v in metrics.items() if v not in (None, "", [], {})}

    return {
        "summary": _clip(summary, 720),
        "key_thesis": _dedupe(thesis, limit=5),
        "key_risks": _dedupe(risks, limit=4),
        "metrics": metrics,
        "watch_points": _dedupe([
            "고객 채택·양산·매출 전환·FCF 개선 직접 근거",
            "IP Evidence 중 청구항·인용·패밀리 수집 상태",
            "동종 peer 대비 기술 점수와 재무성과의 괴리 여부",
        ], limit=4),
    }


def _valuation_analysis(packet: dict[str, Any], company: str | None = None, company_dir: str | None = None) -> dict[str, Any]:
    company_key = _canonical_company_key(packet, company, company_dir)
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    base = raw if raw else packet
    metrics_json = base if str(base.get("agent") or "").lower() == "valuation" and ("dcf" in base or "peer_comps" in base) else {}
    if not metrics_json:
        metrics_json = _load_agent_json(company_key, "valuation", [
            f"{company_key}_valuation_metrics.json",
            "nepes_valuation_metrics.json",
            "valuation_metrics.json",
        ])
    dashboard = _load_agent_json(company_key, "valuation", [
        f"{company_key}_dashboard_payload.json",
        "nepes_dashboard_payload.json",
        "dashboard_payload.json",
    ])
    validation = _load_agent_json(company_key, "valuation", [
        f"{company_key}_valuation_validation.json",
        "nepes_valuation_validation.json",
        "valuation_validation.json",
    ])

    data = metrics_json or dashboard or base
    original_view = _agent_view_reference(packet) or _agent_view_reference(data)
    dcf = data.get("dcf") if isinstance(data.get("dcf"), dict) else {}
    wacc = data.get("wacc") if isinstance(data.get("wacc"), dict) else {}
    scorecard = data.get("scorecard") if isinstance(data.get("scorecard"), dict) else data.get("valuation_scorecard") if isinstance(data.get("valuation_scorecard"), dict) else {}
    peer_comps = data.get("peer_comps") if isinstance(data.get("peer_comps"), dict) else {}
    ref_summary = data.get("reference_universe_summary") if isinstance(data.get("reference_universe_summary"), dict) else dashboard.get("reference_universe_summary") if isinstance(dashboard.get("reference_universe_summary"), dict) else {}
    target_ref = ref_summary.get("target_reference_row") if isinstance(ref_summary.get("target_reference_row"), dict) else {}
    summary_cards = dashboard.get("summary_cards") if isinstance(dashboard.get("summary_cards"), dict) else {}

    def card_value(name: str) -> Any:
        item = summary_cards.get(name)
        return item.get("value") if isinstance(item, dict) else None

    implied_price = dcf.get("implied_price") or dcf.get("implied_price_per_share") or card_value("implied_price")
    current_price = dcf.get("latest_close") or data.get("latest_close") or card_value("latest_close")
    upside = dcf.get("upside_downside_pct") or card_value("upside_downside_pct")
    enterprise_value = dcf.get("enterprise_value") or card_value("enterprise_value")
    equity_value = dcf.get("equity_value") or card_value("equity_value")
    wacc_value = wacc.get("wacc") or card_value("wacc") or _deep_find(data, ["wacc"])

    target_psr = card_value("target_psr") or _deep_find(peer_comps, ["target_psr", "psr"])
    median_psr = card_value("median_psr") or _deep_find(peer_comps, ["median_psr", "peer_median_psr"])
    psr_gap = card_value("psr_gap") or _deep_find(peer_comps, ["psr_gap"])
    valuation_score = scorecard.get("score") or _deep_find(data, ["valuation_score", "valuation_scorecard_score"])
    valuation_label = scorecard.get("label") or scorecard.get("label_kr") or _deep_find(data, ["valuation_label"])
    ref_score = target_ref.get("valuation_proxy_score")
    if ref_score is not None:
        try:
            ref_score_num = float(ref_score) * 100 if abs(float(ref_score)) <= 1.5 else float(ref_score)
        except Exception:
            ref_score_num = ref_score
    else:
        ref_score_num = None
    ref_label = target_ref.get("valuation_proxy_label") or target_ref.get("valuation_proxy_label_kr")
    peer_group = target_ref.get("peer_group") or ref_summary.get("target_peer_group") or card_value("reference_peer_group")
    peer_group_size = ref_summary.get("target_peer_group_size")
    ref_rows = ref_summary.get("reference_universe_rows") or card_value("reference_rows")
    credit_label = target_ref.get("credit_proxy_label") or target_ref.get("credit_proxy_label_kr")
    validation_status = data.get("validation_status") or validation.get("status") or dashboard.get("status")

    summary_parts = []
    if original_view:
        summary_parts.append(f"기존 Valuation Agent 내부 판단은 {original_view}였고, Auditor compact에서는 이를 참고 신호로만 사용합니다.")
    if implied_price or current_price or upside is not None:
        summary_parts.append(f"DCF 내재주가는 {_fmt_krw(implied_price)}이고 현재가 {_fmt_krw(current_price)} 대비 괴리율은 {_fmt_pct(upside)}입니다.")
    if target_psr or median_psr or psr_gap is not None:
        summary_parts.append(f"peer 대비 P/S는 {_fmt_score(target_psr)}배로 비교기업 중앙값 {_fmt_score(median_psr)}배 대비 {_fmt_pct(psr_gap)} 수준입니다.")
    if ref_score_num is not None or ref_label:
        summary_parts.append(f"208개 반도체 reference universe에서는 {peer_group or '동종군'} 기준 valuation proxy {_fmt_score(ref_score_num)}/100, label={ref_label or '확인 제한'}입니다.")
    summary = " ".join(summary_parts) or "가치평가 산출물을 peer-aware compact packet으로 정리했습니다."

    thesis = [
        f"DCF: 내재주가 {_fmt_krw(implied_price)}, 현재가 {_fmt_krw(current_price)}, 괴리율 {_fmt_pct(upside)}.",
        f"Peer P/S: 대상 {_fmt_score(target_psr)}배 vs 비교기업 중앙값 {_fmt_score(median_psr)}배, gap {_fmt_pct(psr_gap)}.",
        f"Reference Universe: {ref_rows or '확인 제한'}개 반도체 universe, {peer_group or '동종군'} peer group {peer_group_size or '확인 제한'}개, valuation proxy {_fmt_score(ref_score_num)}/100({ref_label or '확인 제한'}).",
        f"Valuation scorecard: {_fmt_score(valuation_score)}/100, label={valuation_label or '확인 제한'}, validation={validation_status or '확인 제한'}.",
    ]
    if wacc_value is not None:
        thesis.append(f"할인율/가치: WACC {_fmt_pct(wacc_value)}, DCF 기업가치 {_fmt_krw(enterprise_value)}, 지분가치 {_fmt_krw(equity_value)}.")

    risks = []
    up_num = _to_float(upside)
    up_pp = up_num * 100 if up_num is not None and -2 <= up_num <= 2 else up_num
    if up_pp is not None and abs(up_pp) < 10:
        risks.append("DCF 괴리율이 ±10% 이내라 안전마진이 크지 않아 매수/매도보다 보유 판단에 가깝습니다.")
    if wacc_value is not None and (_to_float(wacc_value) or 0) >= 0.10:
        risks.append(f"WACC가 {_fmt_pct(wacc_value)}로 높아 장기 현금흐름 가정 변화에 민감합니다.")
    if credit_label and "RISK" in str(credit_label).upper() and "LOW" not in str(credit_label).upper():
        risks.append(f"Reference universe의 credit proxy가 {credit_label}로 나타나 가치 매력과 재무/신용 리스크를 함께 봐야 합니다.")
    mdd = card_value("mdd") or _deep_find(data, ["mdd", "MDD"])
    vol = card_value("volatility") or _deep_find(data, ["volatility", "volatility_annualized"])
    if mdd is not None:
        risks.append(f"가격 리스크: MDD {_fmt_pct(mdd)}로 변동성/낙폭 리스크 확인이 필요합니다.")
    if vol is not None:
        risks.append(f"변동성: 연환산 변동성 {_fmt_pct(vol)} 수준입니다.")

    metrics = {
        "original_agent_view_reference": original_view,
        "implied_price_krw": implied_price,
        "current_price_krw": current_price,
        "upside_downside_pct": upside,
        "wacc": wacc_value,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "target_psr": target_psr,
        "peer_median_psr": median_psr,
        "psr_gap": psr_gap,
        "valuation_scorecard_score": valuation_score,
        "valuation_scorecard_label": valuation_label,
        "reference_universe_rows": ref_rows,
        "target_peer_group": peer_group,
        "target_peer_group_size": peer_group_size,
        "valuation_proxy_score": ref_score_num,
        "valuation_proxy_label": ref_label,
        "credit_proxy_label": credit_label,
        "validation_status": validation_status,
    }
    metrics = {k: v for k, v in metrics.items() if v not in (None, "", [], {})}

    return {
        "summary": _clip(summary, 720),
        "key_thesis": _dedupe(thesis, limit=5),
        "key_risks": _dedupe(risks, limit=4),
        "metrics": metrics,
        "watch_points": _dedupe([
            "DCF 괴리율이 안전마진으로 충분한지",
            "Peer P/S 저평가가 수익성·성장성 차이 때문인지",
            "Reference universe의 valuation proxy와 credit proxy 괴리",
        ], limit=4),
    }


def _agent_specific_compact(packet: dict[str, Any], agent: str, company: str | None = None, company_dir: str | None = None) -> dict[str, Any]:
    if agent == "market":
        return _market_analysis(packet)
    if agent == "issue":
        return _issue_analysis(packet)
    if agent == "macro":
        return _macro_analysis(packet)
    if agent == "tech":
        return _tech_analysis(packet, company=company, company_dir=company_dir)
    if agent == "valuation":
        return _valuation_analysis(packet, company=company, company_dir=company_dir)
    return {}


def _extract_summary(packet: dict[str, Any]) -> str:
    agent = _agent_name(packet)
    specific = _agent_specific_compact(packet, agent)
    if specific.get("summary"):
        return _clip(specific["summary"], 560)

    for key in ("summary", "investment_view", "analysis_summary", "reason", "rationale"):
        if packet.get(key):
            text = _clip(packet.get(key), 560)
            # Avoid Chair-facing summaries that only say counts when richer content is absent.
            if not COUNT_ONLY_RE.search(text) or agent not in {"issue", "market", "macro"}:
                return text
    claims = _as_list(packet.get("key_thesis") or packet.get("claims"), limit=2)
    if claims:
        item = claims[0]
        if isinstance(item, dict):
            item = item.get("text") or item.get("claim") or item.get("summary") or item
        return _clip(item, 560)
    return "수집된 에이전트 산출물을 Auditor가 compact packet으로 정리했습니다."


def _extract_key_items(packet: dict[str, Any], kind: str, limit: int = 4) -> list[str]:
    agent = _agent_name(packet)
    specific = _agent_specific_compact(packet, agent)
    if kind == "thesis" and specific.get("key_thesis"):
        return _dedupe(list(specific["key_thesis"]), limit=limit)
    if kind == "risk" and specific.get("key_risks"):
        return _dedupe(list(specific["key_risks"]), limit=limit)

    if kind == "thesis":
        keys = ("key_thesis", "theses", "findings", "key_points", "insights")
        # Claims are last resort only for non-count specialist packets.
        if agent not in {"issue", "market", "macro"}:
            keys = keys + ("claims",)
    else:
        keys = ("key_risks", "risks", "risk_factors", "watch_points", "warnings")

    out: list[str] = []
    for key in keys:
        for item in _as_list(packet.get(key), limit=limit):
            if isinstance(item, dict):
                text = item.get("text") or item.get("claim") or item.get("summary") or item.get("risk") or item.get("rationale") or item.get("snippet") or item
            else:
                text = item
            clipped = _clip(text, 420)
            if clipped and clipped not in out:
                out.append(clipped)
            if len(out) >= limit:
                return out
    return out


def _evidence_count(packet: dict[str, Any]) -> int:
    total = 0
    for key in ("evidence", "evidences", "source_contexts", "sources"):
        value = packet.get(key)
        if isinstance(value, list):
            total += len(value)
        elif isinstance(value, dict):
            total += 1
    return total


def _claim_count(packet: dict[str, Any]) -> int:
    value = packet.get("claims") or packet.get("key_thesis") or []
    if isinstance(value, list):
        return len(value)
    if value:
        return 1
    return 0


def _compact_metrics(packet: dict[str, Any]) -> Any:
    agent = _agent_name(packet)
    specific = _agent_specific_compact(packet, agent)
    if specific.get("metrics"):
        return specific["metrics"]

    metrics = packet.get("metrics")
    if isinstance(metrics, dict):
        # keep small metric dicts; compress very large nested metrics to top-level keys.
        if len(json.dumps(metrics, ensure_ascii=False, default=str)) <= 5000:
            return metrics
        out: dict[str, Any] = {}
        for key, value in metrics.items():
            if isinstance(value, (int, float, str)) or value is None:
                out[key] = value
            elif isinstance(value, dict):
                inner = {k: v for k, v in value.items() if isinstance(v, (int, float, str)) or v is None}
                if inner:
                    out[key] = inner
        return out
    if isinstance(metrics, list):
        return metrics[:12]
    return metrics


def build_compact_agent_packet(
    packet: dict[str, Any],
    *,
    company: str,
    company_dir: str | None = None,
    auditor_result: dict[str, Any] | None = None,
    stage_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    agent = _agent_name(packet)
    specific = _agent_specific_compact(packet, agent, company=company, company_dir=company_dir)
    summary = specific.get("summary") or _extract_summary(packet)
    key_thesis = specific.get("key_thesis") or _extract_key_items(packet, "thesis", limit=4)
    key_risks = specific.get("key_risks") or _extract_key_items(packet, "risk", limit=4)
    metrics = specific.get("metrics") or _compact_metrics(packet)
    compact: dict[str, Any] = {
        "agent": agent,
        "company_name": packet.get("company_name") or packet.get("company") or company,
        "industry_type": packet.get("industry_type") or packet.get("sector") or "deeptech_semiconductor",
        "summary": summary,
        "key_thesis": key_thesis,
        "key_risks": key_risks,
        "warning_note": specific.get("warning_note") if specific.get("warning_note") is not None else packet.get("warning_note"),
        "metrics": metrics,
        "audit_trace": {
            "original_claim_count": _claim_count(packet),
            "original_evidence_count": _evidence_count(packet),
            "removed_fields_for_chair": sorted(k for k in REMOVE_FOR_CHAIR if k in packet),
            "compact_source": "agent_specific_peer_aware_compact" if specific else "generic_packet_fields",
            "policy": "specialist agent files are not modified; this compact packet is generated by auditor_agent only",
        },
    }

    if specific.get("watch_points"):
        compact["watch_points"] = specific.get("watch_points")

    for key in ("output_files", "validation", "status", "data_quality", "risk_flags"):
        if key in packet and key not in compact:
            compact[key] = packet.get(key)

    if auditor_result:
        compact["auditor_status"] = auditor_result.get("status")
        compact["auditor_actual_match"] = auditor_result.get("actual_match")
        compact["auditor_stage_scores"] = auditor_result.get("stage_scores")
        compact["auditor_issues"] = auditor_result.get("issues")
    if stage_decision:
        compact["auditor_recommendation"] = stage_decision.get("recommendation")
        compact["auditor_signal"] = stage_decision.get("signal")
        compact["auditor_decision_basis"] = stage_decision.get("basis")
        compact["auditor_signal_components"] = stage_decision.get("components")

    # Remove empty values and make sure Chair-facing packets do not expose the noisy fields.
    clean = {k: v for k, v in compact.items() if v not in (None, "", [])}
    for forbidden in REMOVE_FOR_CHAIR:
        clean.pop(forbidden, None)
    return clean


def scrub_packet_for_chair(packet: dict[str, Any]) -> dict[str, Any]:
    """Remove user-requested noisy fields from a packet-like dict."""
    if not isinstance(packet, dict):
        return {}
    return {k: v for k, v in packet.items() if k not in REMOVE_FOR_CHAIR}


def persist_compact_packets(
    *,
    company_dir: str,
    company: str,
    compact_packets: list[dict[str, Any]],
    quantitative_decision: dict[str, Any],
) -> dict[str, Any]:
    if _history_local_write_disabled():
        return {
            "bundle_path": "google_sheets_only://auditor_chair_packet.json",
            "agent_packet_paths": {str(p.get("agent") or "unknown").lower(): "google_sheets_only://compact_packet" for p in compact_packets},
            "local_write_disabled": True,
            "storage": "google_sheets_run_results",
        }
    base = first_auditor_dir(company_dir) / "compact_agent_packets"
    base.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for packet in compact_packets:
        agent = str(packet.get("agent") or "unknown").lower()
        path = base / f"{agent}_compact_packet.json"
        path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[agent] = str(path)

    bundle = {
        "packet_version": "auditor_chair_compact_packets_v5_peer_aware",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "company_dir": company_dir,
        "company": company,
        "policy": "opinion/confidence/claims/evidence-heavy fields are removed from Chair-facing packets; Tech/Valuation include peer-aware summaries and original specialist view only as a reference signal, not as a Chair-facing opinion field.",
        "quantitative_decision": quantitative_decision,
        "packets": compact_packets,
    }
    bundle_path = base / "auditor_chair_packet.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"bundle_path": str(bundle_path), "agent_packet_paths": paths}

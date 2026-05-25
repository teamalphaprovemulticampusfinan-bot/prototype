from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .formatter import build_issue_markdown, build_issue_prompt
from .llm import call_issue_llm


def _clean_text(value: Any, limit: int = 500) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
    return text[:limit]


def _build_company_context(related_rows: list[dict]) -> str:
    if not related_rows:
        return "관련 내부 키워드 정보가 없습니다."

    lines = []
    for row in related_rows[:15]:
        keyword = row.get("키워드") or row.get("keyword") or ""
        category = row.get("카테고리") or row.get("category") or ""
        desc = row.get("설명") or row.get("description") or ""
        line = f"- 키워드: {keyword}"
        if category:
            line += f" / 카테고리: {category}"
        if desc:
            line += f" / 설명: {desc}"
        lines.append(line)

    return "\n".join(lines)


def _build_news_context(news_items: list[dict], rss_items: list[dict]) -> str:
    merged = []

    for item in news_items[:10]:
        title = item.get("title", "")
        summary = item.get("summary", "")
        merged.append(f"- 뉴스: {title} | {summary}")

    for item in rss_items[:10]:
        title = item.get("title", "")
        summary = item.get("summary", "")
        merged.append(f"- RSS: {title} | {summary}")

    if not merged:
        return "최근 수집된 뉴스/RSS 정보가 없습니다."

    return "\n".join(merged)


def _make_evidence(
    *,
    agent: str,
    idx: int,
    source_type: str,
    source: str,
    metric: str | None,
    value: Any,
    unit: str | None,
    period: str | None,
    snippet: str,
) -> dict[str, Any]:
    return {
        "evidence_id": f"{agent}.ev.{idx:03d}",
        "source_type": source_type,
        "source": source,
        "metric": metric,
        "value": value,
        "unit": unit,
        "period": period,
        "snippet": _clean_text(snippet, 1000),
    }


def _build_issue_evidences(
    company_name: str,
    related_rows: list[dict],
    news_items: list[dict],
    rss_items: list[dict],
    llm_error: str | None = None,
) -> list[dict[str, Any]]:
    evidences: list[dict[str, Any]] = []
    idx = 1

    for item in news_items[:8]:
        title = _clean_text(item.get("title"), 300)
        summary = _clean_text(item.get("summary") or item.get("description"), 700)
        url = _clean_text(item.get("url") or item.get("link") or "news", 300)
        if not title and not summary:
            continue
        evidences.append(
            _make_evidence(
                agent="issue",
                idx=idx,
                source_type="public_news",
                source=url,
                metric="news_item",
                value=None,
                unit=None,
                period=_clean_text(item.get("publishedAt") or item.get("published") or "", 100) or None,
                snippet=f"{title}. {summary}".strip(),
            )
        )
        idx += 1

    for item in rss_items[:8]:
        title = _clean_text(item.get("title"), 300)
        summary = _clean_text(item.get("summary") or item.get("description"), 700)
        link = _clean_text(item.get("link") or item.get("url") or "rss", 300)
        if not title and not summary:
            continue
        evidences.append(
            _make_evidence(
                agent="issue",
                idx=idx,
                source_type="rss",
                source=link,
                metric="rss_item",
                value=None,
                unit=None,
                period=_clean_text(item.get("published") or item.get("publishedAt") or "", 100) or None,
                snippet=f"{title}. {summary}".strip(),
            )
        )
        idx += 1

    for row in related_rows[:5]:
        keyword = _clean_text(row.get("키워드") or row.get("keyword"), 150)
        category = _clean_text(row.get("카테고리") or row.get("category"), 150)
        desc = _clean_text(row.get("설명") or row.get("description"), 500)
        if not keyword and not desc:
            continue
        evidences.append(
            _make_evidence(
                agent="issue",
                idx=idx,
                source_type="internal_keyword",
                source="Issue_Integration.xlsx",
                metric="related_keyword",
                value=None,
                unit=None,
                period=None,
                snippet=f"{company_name} 관련 내부 키워드: {keyword} / 카테고리: {category} / 설명: {desc}",
            )
        )
        idx += 1

    if not evidences:
        evidences.append(
            _make_evidence(
                agent="issue",
                idx=idx,
                source_type="system_status",
                source="issue_agent.collect_node",
                metric="collected_news_rss_count",
                value=0,
                unit="count",
                period=datetime.now(timezone.utc).date().isoformat(),
                snippet=f"{company_name}에 대해 issue_agent가 확인한 뉴스/RSS/내부 키워드 근거가 0건이므로 구체 이슈 판단을 보류합니다.",
            )
        )
        idx += 1

    if llm_error:
        evidences.append(
            _make_evidence(
                agent="issue",
                idx=idx,
                source_type="system_status",
                source="issue_agent.llm",
                metric="llm_error",
                value=None,
                unit=None,
                period=datetime.now(timezone.utc).isoformat(),
                snippet=f"issue_agent LLM 호출 실패: {_clean_text(llm_error, 700)}",
            )
        )

    return evidences


def _build_fallback_analysis(
    company_name: str,
    evidences: list[dict[str, Any]],
    *,
    llm_error: str | None,
) -> str:
    news_like = [
        ev for ev in evidences
        if ev.get("source_type") in {"public_news", "rss"}
    ]
    keyword_like = [
        ev for ev in evidences
        if ev.get("source_type") == "internal_keyword"
    ]

    lines: list[str] = []

    lines.append("1. 핵심 이슈 요약")
    if news_like:
        lines.append(
            f"- {company_name} 관련 수집 뉴스/RSS {len(news_like)}건을 기준으로 이슈를 확인했습니다."
        )
        for ev in news_like[:3]:
            lines.append(f"- 확인 근거: {ev.get('snippet', '')}")
    else:
        lines.append(
            f"- {company_name} 관련 최신 뉴스/RSS 원천 근거가 충분하지 않아 구체적인 신규 이슈 판단은 보류합니다."
        )

    lines.append("")
    lines.append("2. 기업에 미치는 영향")
    if keyword_like:
        lines.append(
            f"- 내부 키워드 {len(keyword_like)}건은 확인되지만, 뉴스/RSS 근거와 결합되지 않은 내용은 확정 이슈로 단정하지 않습니다."
        )
    else:
        lines.append("- 현재 수집 근거만으로 매출, 수익성, 수주, 고객사 변화 등 구체적 영향을 단정하지 않습니다.")

    lines.append("")
    lines.append("3. 긍정/부정 시그널")
    if news_like:
        lines.append("- 긍정/부정 판단은 위 수집 기사 원문 확인 후 확정해야 합니다.")
    else:
        lines.append("- 확인 가능한 외부 근거가 부족하므로 긍정/부정 시그널은 중립으로 처리합니다.")

    lines.append("")
    lines.append("4. 향후 체크포인트")
    lines.append("- 공식 공시, 회사 IR, 주요 고객사 발주 동향, 반도체 업황 뉴스 업데이트 여부를 재확인해야 합니다.")

    if llm_error:
        lines.append("")
        lines.append("[시스템 메모]")
        lines.append("- LLM 호출 장애가 발생하여 원천 근거 기반 fallback 분석을 사용했습니다.")

    return "\n".join(lines)


def _build_claims(
    company_name: str,
    analysis_text: str,
    evidences: list[dict[str, Any]],
    *,
    fallback_used: bool,
) -> list[dict[str, Any]]:
    evidence_ids = [ev["evidence_id"] for ev in evidences if ev.get("evidence_id")]
    news_ids = [
        ev["evidence_id"]
        for ev in evidences
        if ev.get("source_type") in {"public_news", "rss"}
    ]
    keyword_ids = [
        ev["evidence_id"]
        for ev in evidences
        if ev.get("source_type") == "internal_keyword"
    ]
    status_ids = [
        ev["evidence_id"]
        for ev in evidences
        if ev.get("source_type") == "system_status"
    ]

    claims: list[dict[str, Any]] = []

    if news_ids:
        claims.append(
            {
                "claim_id": "issue.cl.001",
                "claim_type": "summary",
                "text": f"{company_name} 관련 수집 뉴스/RSS {len(news_ids)}건을 기준으로 이슈를 확인했습니다.",
                "evidence_ids": news_ids[:5],
            }
        )
    else:
        claims.append(
            {
                "claim_id": "issue.cl.001",
                "claim_type": "summary",
                "text": f"{company_name} 관련 최신 뉴스/RSS 원천 근거가 충분하지 않아 구체적인 신규 이슈 판단은 보류합니다.",
                "evidence_ids": status_ids[:1] or evidence_ids[:1],
            }
        )

    if keyword_ids:
        claims.append(
            {
                "claim_id": "issue.cl.002",
                "claim_type": "context",
                "text": f"{company_name} 관련 내부 키워드 {len(keyword_ids)}건이 확인됩니다.",
                "evidence_ids": keyword_ids[:5],
            }
        )

    if fallback_used:
        claims.append(
            {
                "claim_id": "issue.cl.003",
                "claim_type": "system_status",
                "text": "LLM 호출 장애 또는 근거 부족으로 인해 원천 근거 기반 fallback 분석을 사용했습니다.",
                "evidence_ids": status_ids[-1:] or evidence_ids[:1],
            }
        )
    else:
        claims.append(
            {
                "claim_id": "issue.cl.003",
                "claim_type": "analysis",
                "text": _clean_text(analysis_text, 900),
                "evidence_ids": evidence_ids[:8],
            }
        )

    return claims


def run_collect_node(state: dict) -> dict:
    related_rows = state.get("related_rows", [])
    news_items = state.get("news_items", [])
    rss_items = state.get("rss_items", [])

    state["company_context"] = _build_company_context(related_rows)
    state["news_context"] = _build_news_context(news_items, rss_items)
    return state


def run_generate_node(state: dict) -> dict:
    company_name = state.get("company_name", "알 수 없는 기업")
    company_context = state.get("company_context", "")
    news_context = state.get("news_context", "")
    related_rows = state.get("related_rows", [])
    news_items = state.get("news_items", [])
    rss_items = state.get("rss_items", [])

    prompt = build_issue_prompt(
        company_name=company_name,
        company_context=company_context,
        news_context=news_context,
    )

    llm_error: str | None = None
    fallback_used = False

    try:
        analysis_text = call_issue_llm(prompt)
        if not str(analysis_text).strip():
            raise RuntimeError("issue_agent LLM returned empty response")
    except Exception as exc:
        llm_error = str(exc)
        fallback_used = True
        evidences_for_fallback = _build_issue_evidences(
            company_name=company_name,
            related_rows=related_rows,
            news_items=news_items,
            rss_items=rss_items,
            llm_error=llm_error,
        )
        analysis_text = _build_fallback_analysis(
            company_name=company_name,
            evidences=evidences_for_fallback,
            llm_error=llm_error,
        )

    evidences = _build_issue_evidences(
        company_name=company_name,
        related_rows=related_rows,
        news_items=news_items,
        rss_items=rss_items,
        llm_error=llm_error,
    )
    claims = _build_claims(
        company_name=company_name,
        analysis_text=analysis_text,
        evidences=evidences,
        fallback_used=fallback_used,
    )

    markdown_report = build_issue_markdown(
        company_name=company_name,
        analysis_text=analysis_text,
        related_rows=related_rows,
    )

    state["analysis_text"] = analysis_text
    state["markdown_report"] = markdown_report
    state["issue_evidences"] = evidences
    state["issue_claims"] = claims
    state["fallback_used"] = fallback_used
    state["llm_error"] = llm_error
    return state
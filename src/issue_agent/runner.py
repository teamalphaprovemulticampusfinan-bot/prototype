from __future__ import annotations

import argparse
import json
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

from common.grounded_output import finalize_agent_output
from common.output_paths import company_dir_from_name, agent_output_path
from common.data_paths import (
    canonical_company_name,
    company_config_path,
    rel_project_path,
    write_json,
    write_text,
)

from .config import SETTINGS
from .excel_loader import load_issue_data
from .graph import build_issue_graph
from .tools import fetch_news_for_company, filter_rss_for_company, fetch_rss_articles


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _display_name_from_company_dir(company_dir: str, fallback: str | None = None) -> str:
    if fallback and fallback.strip():
        return fallback.strip()
    cfg_path = company_config_path(company_dir)
    if yaml is not None and cfg_path.exists():
        try:
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except UnicodeDecodeError:
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig")) or {}
        except Exception:
            data = {}
        for key in ("display_name", "output_name", "corp_name", "name"):
            value = str(data.get(key) or "").strip()
            if value:
                return value
    return canonical_company_name(company_dir)


def _clean(value: Any, limit: int = 320) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())[:limit]


def _to_number(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).replace(",", "").replace("%", "").strip()
    try:
        num = float(text)
    except Exception:
        return None
    return int(num) if num.is_integer() else num


def _add_ev(
    rows: list[dict],
    *,
    source_type: str,
    source: str,
    metric: str,
    value: Any = None,
    unit: str | None = None,
    period: str | None = None,
    snippet: str = "",
) -> None:
    text = _clean(snippet)
    if not text:
        if value is None:
            return
        unit_text = unit or ""
        period_text = f"{period} " if period else ""
        text = f"{period_text}{metric} 값은 {value}{unit_text}입니다."
    rows.append(
        {
            "evidence_id": f"issue.ev.{len(rows) + 1:03d}",
            "source_type": source_type,
            "source": source,
            "metric": metric,
            "value": _to_number(value),
            "unit": unit,
            "period": period,
            "snippet": text,
        }
    )


def _title_from_item(item: Any) -> str:
    if isinstance(item, dict):
        return _clean(
            item.get("title")
            or item.get("headline")
            or item.get("summary")
            or item.get("description")
            or item.get("content"),
            260,
        )
    return _clean(item, 260)


def _period_from_item(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    return _clean(
        item.get("publishedAt")
        or item.get("pubDate")
        or item.get("date")
        or item.get("published")
        or item.get("time"),
        40,
    ) or None


def _source_from_item(item: Any, default: str) -> str:
    if not isinstance(item, dict):
        return default
    return _clean(item.get("source") or item.get("url") or item.get("link") or default, 180) or default


def _keyword_text(row: dict) -> str:
    preferred = ["키워드", "keyword", "이슈", "issue", "내용", "요약", "summary", "메모", "비고"]
    for key in preferred:
        if key in row and _clean(row.get(key)):
            return _clean(row.get(key), 260)
    parts = []
    for key, value in row.items():
        text = _clean(value, 80)
        if text and str(key) != "기업명":
            parts.append(f"{key}={text}")
    return _clean("; ".join(parts), 260)


def _build_issue_evidences(
    *,
    company_name: str,
    related_rows: list[dict],
    news_items: list,
    rss_items: list,
    graph_evidences: list,
) -> list[dict]:
    rows: list[dict] = []

    _add_ev(
        rows,
        source_type="issue",
        source="issue_data_collection",
        metric="news_count",
        value=len(news_items or []),
        unit="count",
        period=None,
        snippet=f"{company_name} 이슈 분석에서 수집된 공개 뉴스 항목 수는 {len(news_items or [])}건입니다.",
    )
    _add_ev(
        rows,
        source_type="issue",
        source="issue_data_collection",
        metric="rss_count",
        value=len(rss_items or []),
        unit="count",
        period=None,
        snippet=f"{company_name} 이슈 분석에서 수집된 RSS 항목 수는 {len(rss_items or [])}건입니다.",
    )
    _add_ev(
        rows,
        source_type="issue",
        source="issue_keywords_workbook",
        metric="related_keyword_count",
        value=len(related_rows or []),
        unit="count",
        period=None,
        snippet=f"{company_name} 이슈 키워드 엑셀에서 확인된 관련 행 수는 {len(related_rows or [])}건입니다.",
    )

    for item in (news_items or [])[:5]:
        title = _title_from_item(item)
        if not title:
            continue
        _add_ev(
            rows,
            source_type="issue_news",
            source=_source_from_item(item, "fetch_news_for_company"),
            metric="news_title",
            value=None,
            unit=None,
            period=_period_from_item(item),
            snippet=f"{company_name} 관련 공개 뉴스 제목: {title}",
        )

    for item in (rss_items or [])[:5]:
        title = _title_from_item(item)
        if not title:
            continue
        _add_ev(
            rows,
            source_type="issue_rss",
            source=_source_from_item(item, "rss_articles"),
            metric="rss_title",
            value=None,
            unit=None,
            period=_period_from_item(item),
            snippet=f"{company_name} 관련 RSS 제목: {title}",
        )

    for row in (related_rows or [])[:5]:
        text = _keyword_text(row)
        if not text:
            continue
        _add_ev(
            rows,
            source_type="issue_keyword",
            source="issue_keywords_workbook",
            metric="keyword_row",
            value=None,
            unit=None,
            period=None,
            snippet=f"{company_name} 이슈 키워드 엑셀 행: {text}",
        )

    # graph 내부에서 이미 evidence_id가 있는 근거만 제한적으로 보존한다.
    for item in graph_evidences[:5]:
        if not isinstance(item, dict):
            continue
        source_type = str(item.get("source_type") or item.get("category") or "issue_graph")
        if source_type.lower() in {"agent_output_unverified", "llm_only", "self_generated"}:
            continue
        snippet = _clean(item.get("snippet") or item.get("text") or item.get("rationale"), 260)
        if not snippet:
            continue
        _add_ev(
            rows,
            source_type=source_type,
            source=_clean(item.get("source") or "issue_graph", 160),
            metric=_clean(item.get("metric") or "graph_evidence", 80),
            value=item.get("value"),
            unit=item.get("unit"),
            period=item.get("period"),
            snippet=snippet,
        )

    return rows


def _claimable_evidence(ev: dict) -> bool:
    snippet = _clean(ev.get("snippet"), 320)
    if not snippet:
        return False
    if any(bad in snippet for bad in ["확인 불가", "입력해", "제공해", "요청", "예시"]):
        return False
    source_type = str(ev.get("source_type") or "").lower()
    if source_type in {"agent_output_unverified", "llm_only", "self_generated"}:
        return False
    return True


def _claims_from_evidences(evidences: list[dict], *, agent_name: str) -> list[dict]:
    claims: list[dict] = []
    for ev in evidences:
        if not _claimable_evidence(ev):
            continue
        snippet = _clean(ev.get("snippet"), 300)
        claims.append(
            {
                "claim_id": f"{agent_name}.cl.{len(claims) + 1:03d}",
                "text": snippet,
                "evidence_ids": [ev.get("evidence_id")],
            }
        )
        if len(claims) >= 6:
            break
    return claims


def run_company(company_name: str, company_dir: str | None = None) -> dict[str, Any]:
    company_dir = company_dir_from_name(company_dir or company_name)
    company_name = _display_name_from_company_dir(company_dir, company_name)

    try:
        df_keywords, df_news = load_issue_data()
    except Exception as exc:
        print(f"[issue] Issue workbook load failed; continue with empty data: {exc}")
        pandas = __import__("pandas")
        df_keywords, df_news = pandas.DataFrame(), pandas.DataFrame()

    related_rows: list[dict[str, Any]] = []
    if not df_keywords.empty and "기업명" in df_keywords.columns:
        related_rows = (
            df_keywords[df_keywords["기업명"] == company_name]
            .fillna("")
            .to_dict(orient="records")
        )

    news_items = fetch_news_for_company(company_name)
    rss_articles = fetch_rss_articles()
    rss_items = filter_rss_for_company(company_name, rss_articles)

    initial_state = {
        "company_name": company_name,
        "related_rows": related_rows,
        "news_items": news_items,
        "rss_items": rss_items,
    }

    graph = build_issue_graph()
    result = graph.invoke(initial_state)

    analysis_text = result.get("analysis_text", "")
    markdown_report = result.get("markdown_report", "")
    graph_evidences = _safe_list(result.get("issue_evidences"))
    fallback_used = bool(result.get("fallback_used", False))
    llm_error = result.get("llm_error")

    evidences = _build_issue_evidences(
        company_name=company_name,
        related_rows=related_rows,
        news_items=news_items,
        rss_items=rss_items,
        graph_evidences=graph_evidences,
    )
    claims = _claims_from_evidences(evidences, agent_name="issue")

    if claims:
        summary = " ".join(claim["text"] for claim in claims[:3])[:700]
    else:
        summary = f"{company_name} 이슈 분석에서 검증 가능한 원천 근거가 부족합니다."

    packet = {
        "agent": "issue",
        "company_name": company_name,
        "company": company_name,
        "company_dir": company_dir,
        "opinion": "보유",
        "confidence": 0.35 if fallback_used else 0.50,
        "summary": summary,
        "key_points": [claim["text"] for claim in claims[:3]],
        "risks": [],
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "fallback_used": fallback_used,
        "warning_note": (
            "LLM 호출 장애 또는 근거 부족으로 fallback 분석을 사용했습니다."
            if fallback_used
            else None
        ),
        "raw_payload": {
            "analysis_text": analysis_text,
            "markdown_report": markdown_report,
            "news_count": len(news_items or []),
            "rss_count": len(rss_items or []),
            "related_keyword_count": len(related_rows or []),
            "df_news_rows": 0 if df_news is None else len(df_news),
            "llm_error": llm_error,
            "graph_claims_original": _safe_list(result.get("issue_claims")),
        },
    }

    packet = finalize_agent_output(packet, agent_name="issue", company_name=company_name)
    try:
        saved = _save_issue_packet(company_name, packet, company_dir=company_dir)
        packet.setdefault("output_files", {}).update({k: v for k, v in saved.items() if v})
    except Exception as exc:
        print(f"[issue] output 저장 실패: {exc}")
    return packet




def _save_issue_packet(company_name: str, packet: dict[str, Any], company_dir: str | None = None) -> dict[str, str]:
    company_dir = company_dir_from_name(company_dir or company_name)
    primary = agent_output_path(company_dir, "issue", f"{company_dir}_issue.json")
    packet_path = agent_output_path(company_dir, "issue", f"{company_dir}_issue_agent_packet.json")
    md_path = agent_output_path(company_dir, "issue", f"{company_dir}_issue_report.md")
    write_json(primary, packet)
    write_json(packet_path, packet)
    markdown = ((packet.get("raw_payload") or {}).get("markdown_report") or "").strip()
    if markdown:
        write_text(md_path, markdown)
    return {
        "issue_json": rel_project_path(primary),
        "issue_agent_packet_json": rel_project_path(packet_path),
        "issue_report_md": rel_project_path(md_path) if markdown else "",
    }

def run_all_companies() -> list[dict[str, Any]]:
    from common.data_paths import KNOWN_COMPANY_DIRS, KNOWN_COMPANY_DIR_TO_NAME
    results = []
    for company_dir in KNOWN_COMPANY_DIRS:
        company_name = KNOWN_COMPANY_DIR_TO_NAME.get(company_dir, company_dir)
        print(f"[issue] 분석 중: {company_name} ({company_dir})")
        try:
            results.append(run_company(company_name, company_dir=company_dir))
        except Exception as exc:
            print(f"[issue] {company_name} 실패: {exc}")
    return results


# Markdown 저장 로직 - Chair 통합에서는 JSON 반환
# def _save_report(company_name: str, report: str) -> Path:
#     output_dir = Path("workspace") / "outputs"
#     output_dir.mkdir(parents=True, exist_ok=True)
#
#     safe_company_name = "".join(
#         ch for ch in company_name if ch not in '\\/:*?"<>|'
#     ).strip() or "issue_report"
#
#     output_path = output_dir / f"{safe_company_name}_issue_report.md"
#     output_path.write_text(report, encoding="utf-8")
#     return output_path


def run_issue_agent(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue Agent - 뉴스/RSS/이슈 키워드 분석")
    parser.add_argument(
        "--company-dir",
        type=str,
        required=False,
        help="회사 slug/폴더명 (예: nepes, hanmi, hansol, duksan, ltc)",
    )
    parser.add_argument(
        "--company",
        type=str,
        required=False,
        help="표시용 회사명 (예: 네패스). --company-dir 없이 쓰면 회사명으로 경로도 추론",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Issue_Integration.xlsx의 기업 전체 실행",
    )
    args = parser.parse_args(argv)

    if args.all:
        results = run_all_companies()
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if args.company_dir or args.company:
        company_dir = company_dir_from_name(args.company_dir or args.company)
        company_name = _display_name_from_company_dir(company_dir, args.company)
    else:
        company_name = SETTINGS.default_company
        company_dir = company_dir_from_name(company_name)

    result = run_company(company_name, company_dir=company_dir)
    try:
        saved = result.get("output_files", {})
        if saved.get("issue_json"):
            print(f"[issue] 저장 완료: {saved.get('issue_json')}")
    except Exception:
        pass

    print("\n[분석 결과]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_issue_agent(argv)


if __name__ == "__main__":
    raise SystemExit(main())

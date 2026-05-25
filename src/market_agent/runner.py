from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Any

import pandas as pd

try:
    import yaml
except Exception:
    yaml = None

from common.grounded_output import finalize_agent_output
from common.output_paths import agent_output_path, company_dir_from_name, write_json, rel_project_path
from common.data_paths import company_config_path, company_name as canonical_company_name

from .analyzer import build_llm
from .config import DEFAULT_COMPANIES, TICKERS
from .data_loader import load_workbook
from .formatter import to_markdown
from .graph import build_market_graph


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


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


TEXT_ONLY_MARKET_METRIC_TOKENS = (
    "as_of", "date", "basdt", "ticker", "krx_code",
    "srtncd", "isincd", "itmsnm", "mrktctg", "currency",
    "company_name", ".name",
)


def _is_text_only_market_metric(metric: str) -> bool:
    m = str(metric or "").lower()
    return any(token in m for token in TEXT_ONLY_MARKET_METRIC_TOKENS)


def _display_name_from_company_dir(company_dir: str, fallback: str | None = None) -> str:
    if fallback and fallback.strip():
        return fallback.strip()
    cfg_path = company_config_path(company_dir)
    if yaml is not None and cfg_path.exists():
        try:
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            for key in ("display_name", "output_name", "corp_name", "name"):
                value = str(data.get(key) or "").strip()
                if value:
                    return value
        except Exception:
            pass
    return canonical_company_name(company_dir)


def _add_ev(rows, *, source_type, source, metric, value=None, unit=None, period=None, snippet=""):
    text = _clean(snippet)
    if not text:
        if value is not None:
            text = f"{period + ' ' if period else ''}{metric} 값은 {value}{unit or ''}입니다."
        else:
            return
    rows.append({
        "evidence_id": f"market.ev.{len(rows) + 1:03d}",
        "source_type": source_type,
        "source":      source,
        "metric":      metric,
        "value":       _to_number(value),
        "unit":        unit,
        "period":      period,
        "snippet":     text,
    })


def _flatten(prefix, value):
    if isinstance(value, dict):
        items = []
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(_flatten(next_prefix, child))
        return items
    if isinstance(value, list):
        return [(prefix, value)]
    return [(prefix, value)]


def _build_market_evidences(result, analysis, company):
    rows = []
    score = analysis.get("total_score")
    if score is not None:
        _add_ev(rows, source_type="market", source="market_graph_analysis",
                metric="total_score", value=score, unit="score",
                snippet=f"{company} 마켓 분석 total_score 값은 {score}점입니다.")
    for field in ("stock_data", "oecd_data", "dart_data", "static_data"):
        data = result.get(field)
        if not isinstance(data, dict):
            continue
        for metric, value in _flatten("", data):
            if len(rows) >= 20:
                break
            full_metric = f"{field}.{metric}"
            if isinstance(value, list):
                _add_ev(rows, source_type="market", source=field,
                        metric=f"{full_metric}.count", value=len(value), unit="count",
                        snippet=f"{company} {full_metric} 항목 수는 {len(value)}건입니다.")
            elif _is_text_only_market_metric(full_metric):
                text = _clean(value)
                if text:
                    _add_ev(rows, source_type="market_metadata", source=field,
                            metric=full_metric, snippet=f"{company} {full_metric}: {text}")
            else:
                num = _to_number(value)
                if num is None:
                    text = _clean(value)
                    if text:
                        _add_ev(rows, source_type="market", source=field,
                                metric=full_metric, snippet=f"{company} {full_metric}: {text}")
                else:
                    unit = "%" if any(k in full_metric.lower() for k in ["rate","ratio","mdd","flt","%"]) else None
                    _add_ev(rows, source_type="market", source=field,
                            metric=full_metric, value=num, unit=unit,
                            snippet=f"{company} {full_metric} 값은 {num}{unit or ''}입니다.")
    if not rows:
        _add_ev(rows, source_type="market", source="market_runner",
                metric="data_collection_status", value=0, unit="count",
                snippet=f"{company} 마켓 에이전트에서 검증 가능한 수치형 원천 데이터 항목 수는 0건입니다.")
    return rows


def _claimable_evidence(ev):
    snippet = _clean(ev.get("snippet"), 320)
    if not snippet:
        return False
    if any(bad in snippet for bad in ["확인 불가","입력해","제공해","요청","예시"]):
        return False
    source_type = str(ev.get("source_type") or "").lower()
    metric      = str(ev.get("metric") or "").lower()
    if source_type in {"agent_output_unverified","llm_only","self_generated"}:
        return False
    if metric in {"warning_stock"}:
        return False
    if _is_text_only_market_metric(metric):
        return False
    if ev.get("value") is None:
        return False
    return True


def _claims_from_evidences(evidences, *, agent_name):
    claims = []
    for ev in evidences:
        if not _claimable_evidence(ev):
            continue
        claims.append({
            "claim_id":    f"{agent_name}.cl.{len(claims) + 1:03d}",
            "text":        _clean(ev.get("snippet"), 300),
            "evidence_ids": [ev.get("evidence_id")],
        })
        if len(claims) >= 6:
            break
    return claims


def run_market_report(company: str, company_dir: str | None = None) -> dict:
    # DB 초기화를 가장 먼저
    try:
        from .db_manager import init_db
        init_db()
    except Exception as e:
        print(f"[DB] 초기화 실패: {e}")

    if _env_bool("MARKET_AGENT_SKIP_LIVE_REFRESH", False):
        print("[Market Agent] live DART/NTIS refresh skipped; using prepared market intake/workbook/cache data")
    else:
        # DART 파싱
        try:
            from .dart_parser import get_corp_codes, run_dart_parser
            from .db_manager import get_conn
            import pandas as pd

            corp_code_map = get_corp_codes()
            features = run_dart_parser({company: TICKERS.get(company, "")}, corp_code_map)
            if features:
                conn = get_conn()
                pd.DataFrame(features).to_sql("value_chain", conn, if_exists="replace", index=False)
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[DART] 파싱 실패: {e}")

        # NTIS 정책 트렌드 수집
        try:
            from .ntis_fetcher import run_ntis_fetcher
            from .db_manager import get_conn
            all_trends = run_ntis_fetcher()
            policy_rows = []
            for t in all_trends:
                for year in ["2022","2023","2024","2025","2026"]:
                    policy_rows.append({
                        "segment":    t["segment"],
                        "keyword":    t["keyword"],
                        "year":       year,
                        "proj_count": t["year_counts"].get(year, 0),
                        "gov_fund":   t["year_funds"].get(year, 0),
                        "updated_at": datetime.now().isoformat(),
                    })
            if policy_rows:
                conn = get_conn()
                pd.DataFrame(policy_rows).to_sql("policy_trend", conn, if_exists="replace", index=False)
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[NTIS] 수집 실패: {e}")

    company_dir = company_dir_from_name(company_dir or company)
    company_dir = company_dir_from_name(company_dir or company)
    company     = _display_name_from_company_dir(company_dir, company)
    workbook    = load_workbook(company=company)
    llm         = build_llm()
    market_graph = build_market_graph(llm=llm, workbook=workbook)
    result = market_graph.invoke({
        "company": company, "stock_data": {}, "oecd_data": {},
        "dart_data": {}, "news_data": [], "static_data": {}, "analysis": {},
    })
    analysis  = result.get("analysis", {}) or {}
    evidences = _build_market_evidences(result, analysis, company)
    claims    = _claims_from_evidences(evidences, agent_name="market")
    summary   = " ".join(c["text"] for c in claims[:2])[:700] if claims else f"{company} 마켓 분석에서 검증 가능한 원천 근거가 부족합니다."
    packet = {
        "agent": "market", "company_name": company, "company": company,
        "opinion": "보유", "confidence": 0.45, "summary": summary,
        "key_points": [c["text"] for c in claims[:3]],
        "risks": [], "claims": claims, "evidences": evidences, "evidence": evidences,
        "raw_payload": {
            "analysis": analysis,
            "original_opportunities": analysis.get("opportunities", []),
            "original_risks": analysis.get("risks", []),
        },
    }
    # finalize 전에 점수 직접 저장
    packet["total_score"]  = analysis.get("total_score")
    packet["opinion"]      = analysis.get("opinion", "보유")
    packet["scoring"]      = analysis.get("scoring", {})
    
    packet = finalize_agent_output(packet, agent_name="market", company_name=company)
    # 수정 후
    try:
        saved = _save_market_packet(company, packet, company_dir=company_dir)
        packet.setdefault("output_files", {}).update(saved)
    except Exception as exc:
        print(f"[market] output 저장 실패: {exc}")

    # ← Excel 출력 추가
    try:
        from .excel_exporter import export_final_excel
        export_final_excel({company: packet})
    except Exception as exc:
        print(f"[Excel] 저장 실패: {exc}")

    return packet




def _save_market_packet(company, packet, company_dir=None):
    company_dir  = company_dir_from_name(company_dir or company)
    primary      = agent_output_path(company_dir, "market", f"{company_dir}_market.json")
    packet_path  = agent_output_path(company_dir, "market", f"{company_dir}_market_agent_packet.json")
    write_json(primary, packet)
    write_json(packet_path, packet)
    return {
        "market_json":               rel_project_path(primary),
        "market_agent_packet_json":  rel_project_path(packet_path),
    }


def run_market_reports(companies: list[str] | None = None) -> dict:
    """DART + NTIS 데이터 수집 + LLM 분석 + 파이널 Excel 출력"""
    from .dart_parser   import get_corp_codes, run_dart_parser
    from .ntis_fetcher  import run_ntis_fetcher
    from .db_manager    import init_db, get_conn
    from .excel_exporter import export_final_excel

    target_companies = companies or DEFAULT_COMPANIES
    target_tickers   = {k: v for k, v in TICKERS.items() if k in target_companies}

    # 1. DB 초기화
    init_db()

    # 2. DART 파싱
    print("\n[데이터 수집] DART 사업보고서 파싱 중...")
    corp_code_map = get_corp_codes()
    features      = run_dart_parser(target_tickers, corp_code_map)

    conn = get_conn()
    if features:
        pd.DataFrame(features).to_sql("value_chain", conn, if_exists="replace", index=False)
        pd.DataFrame([{
            "company_name":          f["company_name"],
            "peer_group":            f.get("vc_role", ""),
            "domestic_peers":        f.get("domestic_peers"),
            "global_peers":          f.get("global_peers"),
            "competition_intensity": f.get("competition_intensity"),
            "differentiation":       f.get("differentiation"),
            "updated_at":            f.get("updated_at"),
        } for f in features]).to_sql("competition", conn, if_exists="replace", index=False)

    # 3. NTIS
    print("\n[데이터 수집] NTIS 정책 트렌드 수집 중...")
    all_trends = run_ntis_fetcher()
    policy_rows = []
    for t in all_trends:
        for year in ["2022","2023","2024","2025","2026"]:
            policy_rows.append({
                "segment": t["segment"], "keyword": t["keyword"], "year": year,
                "proj_count": t["year_counts"].get(year, 0),
                "gov_fund":   t["year_funds"].get(year, 0),
                "updated_at": datetime.now().isoformat(),
            })
    pd.DataFrame(policy_rows).to_sql("policy_trend", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

    # 4. LLM 분석
    print("\n[LLM 분석] 시작...")
    reports = {}
    for company in target_companies:
        result  = run_market_report(company)
        reports[company] = result
        print(f"\n[{company}] 분석 완료: {result.get('summary', '')[:80]}")

    # 5. 파이널 Excel

    try:
        from .excel_exporter import export_final_excel
        export_final_excel({company: packet})
    except Exception as exc:
        print(f"[Excel] 저장 실패: {exc}")
    
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Market Agent")
    parser.add_argument("--company-dir", type=str, required=False)
    parser.add_argument("--company",     type=str, required=False)
    args = parser.parse_args(argv)

    if args.company_dir or args.company:
        company_dir  = company_dir_from_name(args.company_dir or args.company)
        company_name = _display_name_from_company_dir(company_dir, args.company)
        result = run_market_report(company_name, company_dir=company_dir)
        print(f"\n[{company_name}] 분석 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        run_market_reports()
    return 0

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from common.data_paths import company_agent_dir, rel_project_path
from data_intake.valuation_intake.runner import run_valuation_intake

from .advanced_valuation import build_advanced_valuation
from .dashboard_payload import build_dashboard_payload
from .data_loader import has_required_intake, intake_quality, load_context, valuation_dir
from .dcf import build_dcf, build_sensitivity
from .ml_overlay import build_ml_overlay
from .multiples import compute_peer_multiples
from .normalizer import latest_row, normalize_financials
from .reporter import build_report
from .scorecard import build_valuation_scorecard
from .schemas import ValuationResult
from .utils import read_json, write_json
from .validator import validate_valuation
from .wacc import compute_wacc


def _price_summary(price_rows: list[dict[str, Any]], shares_outstanding: Any = None) -> dict[str, Any]:
    # Avoid importing intake sources at valuation runtime except through runner.
    try:
        from data_intake.valuation_intake.sources import compute_price_summary
        return compute_price_summary(price_rows, shares_outstanding)
    except Exception:
        return {"price_rows": len(price_rows), "shares_outstanding": shares_outstanding}




def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _fmt_pct(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return "해당 없음"
    return f"{num * 100:.2f}%"


def _fmt_money(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return "해당 없음"
    return f"{num:,.0f}원"


def _valuation_opinion(validation_status: str, dcf: dict[str, Any]) -> str:
    if str(validation_status or "").upper() not in {"PASS", "OK"}:
        return "보유"
    upside = _safe_float(dcf.get("upside_downside_pct"))
    if upside is None:
        return "보유"
    if upside >= 0.20:
        return "매수"
    if upside <= -0.20:
        return "매도"
    return "보유"


def run_valuation(
    *,
    company_dir: str,
    company: str,
    field: str = "반도체",
    auto_intake: bool = True,
    skip_network: bool = False,
    years: int = 5,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    print(f"[Valuation Agent] 시작: {company} / {company_dir}")
    if auto_intake:
        quality = intake_quality(company_dir, as_of_date=as_of_date)
        needs_intake = (not has_required_intake(company_dir)) or quality.get("financial_rows", 0) == 0
        # 가격 CSV가 없거나 비어 있으면 valuation 자체 검증/대시보드 품질이 크게 떨어지므로
        # 기존 finance/market 산출물을 읽지 말고 valuation-intake를 한 번 더 실행해 자체 데이터를 복구합니다.
        if quality.get("price_rows_loaded", 0) == 0 and not skip_network:
            needs_intake = True
        if needs_intake:
            print(f"[Valuation Agent] intake 보강 필요 → valuation-intake 자동 실행: {quality}")
            run_valuation_intake(company_dir=company_dir, company=company, field=field, years=years, skip_network=skip_network)

    context = load_context(company_dir, company, as_of_date=as_of_date)
    # Keep DCF assumptions synchronized with valuation-intake price/share summary.
    if context.price_summary:
        for k in ("latest_close", "market_cap", "shares_outstanding"):
            if context.assumptions.get(k) in (None, "") and context.price_summary.get(k) is not None:
                context.assumptions[k] = context.price_summary.get(k)
    normalized = normalize_financials(context.financials)
    latest = latest_row(normalized)
    wacc = compute_wacc(latest, context.assumptions)
    dcf = build_dcf(normalized, context.assumptions, wacc)
    sensitivity = build_sensitivity(dcf)
    peer = compute_peer_multiples(context.peers)
    price_summary = _price_summary(context.price_history, context.assumptions.get("shares_outstanding"))
    # If the CSV could not be loaded but valuation-intake created a summary JSON, use it rather than
    # producing a false NO_PRICE_HISTORY warning.  Full price rows remain preferred for charts.
    if (not context.price_history or price_summary.get("price_rows", 0) == 0) and context.price_summary:
        price_summary = {**context.price_summary, **{k: v for k, v in price_summary.items() if v not in (None, 0)}}
    # Attach share/market-cap assumptions collected by valuation-intake.
    if context.assumptions.get("shares_outstanding") is not None:
        price_summary["shares_outstanding"] = context.assumptions.get("shares_outstanding")
    if context.assumptions.get("market_cap") is not None:
        price_summary["market_cap"] = context.assumptions.get("market_cap")
    ml = build_ml_overlay(
        normalized,
        peer.get("peer_rows") or context.peers,
        price_summary,
        peer_comps=peer,
        reference_universe=getattr(context, "reference_universe", []) or [],
        company_dir=company_dir,
        company=company,
    )
    advanced = build_advanced_valuation(
        normalized=normalized,
        dcf=dcf,
        peer=peer,
        price_summary=price_summary,
        wacc=wacc,
        reference_summary=getattr(context, "reference_summary", {}) or {},
        market_snapshot=getattr(context, "market_snapshot", {}) or {},
    )

    out_dir = valuation_dir(company_dir)
    workbook_path = out_dir / f"{company_dir}_valuation_workbook.xlsx"
    metrics_path = out_dir / f"{company_dir}_valuation_metrics.json"
    dashboard_path = out_dir / f"{company_dir}_dashboard_payload.json"
    validation_path = out_dir / f"{company_dir}_valuation_validation.json"
    report_path = out_dir / f"{company_dir}_valuation_report.md"
    source_map_path = out_dir / f"{company_dir}_source_map.json"

    validation_pre = validate_valuation(context, normalized, wacc, dcf)
    scorecard = build_valuation_scorecard(
        dcf=dcf,
        peer=peer,
        ml=ml,
        price_summary=price_summary,
        reference_summary=getattr(context, "reference_summary", {}) or {},
        validation=validation_pre,
        advanced=advanced,
    )
    dashboard = build_dashboard_payload(
        company_dir, company, normalized, wacc, dcf, peer, ml, validation_pre,
        price_history=context.price_history,
        price_summary=price_summary,
        reference_universe=getattr(context, "reference_universe", []) or [],
        reference_focus=getattr(context, "reference_focus", []) or [],
        reference_summary=getattr(context, "reference_summary", {}) or {},
        scorecard=scorecard,
        advanced=advanced,
    )
    workbook_existed_before = workbook_path.exists()
    workbook_policy = {
        "write_enabled": False,
        "status": "PRESERVED_EXISTING_WORKBOOK" if workbook_existed_before else "SKIPPED_WORKBOOK_WRITE",
        "note": "Valuation workbook xlsx files are never created, overwritten, or modified by the pipeline.",
    }
    print(
        "[Valuation Agent] workbook write skipped: "
        f"{workbook_policy['status']} ({workbook_path})"
    )
    validation_workbook_path = workbook_path if workbook_path.exists() else None
    validation = validate_valuation(context, normalized, wacc, dcf, workbook_path=validation_workbook_path)
    scorecard = build_valuation_scorecard(
        dcf=dcf,
        peer=peer,
        ml=ml,
        price_summary=price_summary,
        reference_summary=getattr(context, "reference_summary", {}) or {},
        validation=validation,
        advanced=advanced,
    )
    opinion = _valuation_opinion(str(validation.get("status") or validation_pre.get("status")), dcf)
    dashboard = build_dashboard_payload(
        company_dir, company, normalized, wacc, dcf, peer, ml, validation,
        price_history=context.price_history,
        price_summary=price_summary,
        reference_universe=getattr(context, "reference_universe", []) or [],
        reference_focus=getattr(context, "reference_focus", []) or [],
        reference_summary=getattr(context, "reference_summary", {}) or {},
        scorecard=scorecard,
        advanced=advanced,
    )
    metrics = {
        "agent": "valuation",
        "company_dir": company_dir,
        "company": company,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "data_cutoff_applied": ((context.source_map.get("loader_diagnostics") or {}).get("data_cutoff_applied") if isinstance(context.source_map, dict) else None),
        "data_principle": "valuation_agent independent intake only; finance_agent outputs are not read",
        "wacc": wacc,
        "dcf": dcf,
        "sensitivity": sensitivity,
        "peer_comps": peer,
        "price_summary": price_summary,
        "ml_overlay": ml,
        "reference_universe_summary": getattr(context, "reference_summary", {}) or {},
        "reference_universe_focus_rows": getattr(context, "reference_focus", []) or [],
        "workbook_write_policy": workbook_policy,
        "validation_status": validation.get("status"),
        "scorecard": scorecard,
        "advanced_valuation": advanced,
        "market_snapshot": getattr(context, "market_snapshot", {}) or {},
        "opinion": opinion,
    }
    price_summary_for_claim = price_summary or {}
    chair_json = {
        "agent": "valuation",
        "company_dir": company_dir,
        "company": company,
        "opinion": opinion,
        "summary": (
            f"{company} Valuation Agent는 독립 DART·주가·발행주식 수 intake 기반으로 "
            f"WACC {_fmt_pct(wacc.get('wacc'))}, DCF 내재주가 {_fmt_money(dcf.get('implied_price'))}, "
            f"현재가 대비 괴리율 {_fmt_pct(dcf.get('upside_downside_pct'))}, "
            f"P/S {peer.get('target_psr', '해당 없음')}배, "
            f"보조 가치평가 스코어 {scorecard.get('score', '해당 없음')}/100, "
            f"가치범위 중앙값 {((advanced.get('football_field') or {}).get('base_price') or '해당 없음')}원을 산출했습니다."
        ),
        "claims": [
            {
                "claim_id": "VAL_RUNNER_DCF",
                "text": (
                    f"{company}의 DCF 내재주가는 {_fmt_money(dcf.get('implied_price'))}이고 "
                    f"현재가 대비 괴리율은 {_fmt_pct(dcf.get('upside_downside_pct'))}입니다."
                ),
                "evidence_ids": ["VAL_RUNNER_METRICS"],
            },
            {
                "claim_id": "VAL_RUNNER_PRICE",
                "text": (
                    f"{company}의 valuation 전용 주가 데이터는 {price_summary_for_claim.get('price_rows', '해당 없음')}행이며 "
                    f"시가총액은 {_fmt_money(price_summary_for_claim.get('market_cap'))}입니다."
                ),
                "evidence_ids": ["VAL_RUNNER_PRICE"],
            },
            {
                "claim_id": "VAL_RUNNER_PSR_UNIVERSE",
                "text": (
                    f"{company}의 P/S는 {peer.get('target_psr', '해당 없음')}배이고, "
                    f"비교 피어 P/S 중앙값은 {peer.get('median_psr', '해당 없음')}배입니다. "
                    f"208개 reference universe 행 수는 {(getattr(context, 'reference_summary', {}) or {}).get('reference_universe_rows', '해당 없음')}개입니다."
                ),
                "evidence_ids": ["VAL_RUNNER_PSR", "VAL_RUNNER_REFERENCE_UNIVERSE"],
            },
            {
                "claim_id": "VAL_RUNNER_ADVANCED",
                "text": (
                    f"{company}의 다중 가치평가 교차검증은 가치범위표, 역산 DCF, 오너 이익/EPV를 포함하며 "
                    f"종합 가치평가 점수는 {advanced.get('advanced_valuation_score', '해당 없음')}/100입니다."
                ),
                "evidence_ids": ["VAL_RUNNER_ADVANCED"],
            },
            {
                "claim_id": "VAL_RUNNER_SCORECARD",
                "text": (
                    f"{company}의 Valuation 보조 스코어는 {scorecard.get('score', '해당 없음')}/100이며 "
                    f"라벨은 {scorecard.get('label_kr', '해당 없음')}입니다."
                ),
                "evidence_ids": ["VAL_RUNNER_SCORECARD"],
            },
        ],
        "evidences": [
            {
                "evidence_id": "VAL_RUNNER_METRICS",
                "source_type": "valuation_metrics_json",
                "source_name": f"{company_dir}_valuation_metrics.json",
                "snippet": (
                    f"WACC={_fmt_pct(wacc.get('wacc'))}, DCF 내재주가={_fmt_money(dcf.get('implied_price'))}, "
                    f"현재가 대비 괴리율={_fmt_pct(dcf.get('upside_downside_pct'))}, validation={validation.get('status')}."
                ),
            },
            {
                "evidence_id": "VAL_RUNNER_PRICE",
                "source_type": "valuation_price_history",
                "source_name": "valuation_price_history.csv / price_summary",
                "snippet": (
                    f"price_rows={price_summary_for_claim.get('price_rows', '해당 없음')}, "
                    f"market_cap={_fmt_money(price_summary_for_claim.get('market_cap'))}, "
                    f"shares_outstanding={price_summary_for_claim.get('shares_outstanding', '해당 없음')}."
                ),
            },
            {
                "evidence_id": "VAL_RUNNER_PSR",
                "source_type": "valuation_peer_input",
                "source_name": "valuation_peer_input.csv / peer_comps",
                "snippet": (
                    f"target_psr={peer.get('target_psr', '해당 없음')}, median_psr={peer.get('median_psr', '해당 없음')}, "
                    f"psr_signal={peer.get('psr_signal_kr', '해당 없음')}."
                ),
            },
            {
                "evidence_id": "VAL_RUNNER_REFERENCE_UNIVERSE",
                "source_type": "valuation_reference_universe",
                "source_name": "valuation_reference_universe_208.csv / valuation_reference_universe_summary.json",
                "snippet": (
                    f"reference_universe_rows={(getattr(context, 'reference_summary', {}) or {}).get('reference_universe_rows', '해당 없음')}, "
                    f"target_peer_group={(getattr(context, 'reference_summary', {}) or {}).get('target_peer_group', '해당 없음')}."
                ),
            },
            {
                "evidence_id": "VAL_RUNNER_ADVANCED",
                "source_type": "advanced_valuation",
                "source_name": f"{company_dir}_valuation_metrics.json / advanced_valuation",
                "snippet": (
                    f"advanced_score={advanced.get('advanced_valuation_score', '해당 없음')}, "
                    f"valuation_range={(advanced.get('football_field') or {})}, "
                    f"reverse_dcf={(advanced.get('reverse_dcf') or {})}"
                ),
            },
            {
                "evidence_id": "VAL_RUNNER_SCORECARD",
                "source_type": "valuation_scorecard",
                "source_name": f"{company_dir}_valuation_metrics.json / scorecard",
                "snippet": (
                    f"score={scorecard.get('score', '해당 없음')}, "
                    f"label={scorecard.get('label_kr', '해당 없음')}, "
                    f"method={scorecard.get('method_kr', 'DCF/PSR/품질/Universe/유동성/검증')}"
                ),
            },
        ],
    }

    source_map = {
        "company_dir": company_dir,
        "company": company,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "data_cutoff_applied": ((context.source_map.get("loader_diagnostics") or {}).get("data_cutoff_applied") if isinstance(context.source_map, dict) else None),
        "input_source_map": context.source_map,
        "workbook_write_policy": workbook_policy,
        "output_files": {
            "workbook_xlsx": rel_project_path(workbook_path),
            "metrics_json": rel_project_path(metrics_path),
            "dashboard_payload_json": rel_project_path(dashboard_path),
            "validation_json": rel_project_path(validation_path),
            "report_md": rel_project_path(report_path),
        },
    }
    report = build_report(company, company_dir, metrics, validation)
    write_json(metrics_path, metrics)
    write_json(dashboard_path, dashboard)
    write_json(validation_path, validation)
    write_json(source_map_path, source_map)
    report_path.write_text(report, encoding="utf-8")

    output_files = source_map["output_files"] | {"source_map_json": rel_project_path(source_map_path)}
    result = ValuationResult(
        company_dir=company_dir,
        company=company,
        status=str(validation.get("status")),
        metrics=metrics,
        dashboard_payload=dashboard,
        validation=validation,
        output_files=output_files,
    )
    print(f"[Valuation Agent] 완료: status={result.status}")
    print(f"[Valuation Agent] workbook={workbook_path} ({workbook_policy['status']})")
    return {
        "agent": "valuation",
        "company_dir": company_dir,
        "company": company,
        "status": result.status,
        "opinion": opinion,
        "chair_json": chair_json,
        "_audit_packet": chair_json,
        "metrics": metrics,
        "dashboard_payload": dashboard,
        "validation": validation,
        "output_files": output_files,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independent Valuation Agent")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--as-of-date", default=None, help="Use only valuation intake rows on or before this date/month/year, e.g. 2025-06-30 or 2025-06.")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--no-auto-intake", action="store_true", help="Do not auto-run valuation-intake when intake files are missing.")
    args = parser.parse_args(argv)
    run_valuation(
        company_dir=args.company_dir,
        company=args.company,
        field=args.field,
        years=args.years,
        as_of_date=args.as_of_date,
        skip_network=args.skip_network,
        auto_intake=not args.no_auto_intake,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

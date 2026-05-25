from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common.data_paths import company_agent_dir, rel_project_path


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _fmt_pct(v: Any) -> str:
    try:
        if v is None:
            return "해당 없음"
        return f"{float(v) * 100:.2f}%"
    except Exception:
        return "해당 없음"


def _fmt_money(v: Any) -> str:
    try:
        if v is None:
            return "해당 없음"
        return f"{float(v):,.0f}원"
    except Exception:
        return "해당 없음"


def _fmt_price(v: Any) -> str:
    try:
        if v is None:
            return "해당 없음"
        return f"{float(v):,.0f}원"
    except Exception:
        return "해당 없음"


def _ensure_valuation_outputs(company_dir: str, company: str) -> dict[str, Any] | None:
    out_dir = company_agent_dir(company_dir, "valuation", create=True)
    metrics_path = out_dir / f"{company_dir}_valuation_metrics.json"
    if not metrics_path.exists():
        try:
            from valuation_agent.runner import run_valuation

            run_valuation(company_dir=company_dir, company=company, auto_intake=True)
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc)}
    return _read_json(metrics_path)


def build_valuation_chair_section(*, company_dir: str, company: str) -> str:
    metrics = _ensure_valuation_outputs(company_dir, company)
    out_dir = company_agent_dir(company_dir, "valuation", create=True)
    workbook = out_dir / f"{company_dir}_valuation_workbook.xlsx"
    dashboard = out_dir / f"{company_dir}_dashboard_payload.json"
    report_md = out_dir / f"{company_dir}_valuation_report.md"

    if not isinstance(metrics, dict):
        return (
            "### 가치평가 분석\n"
            "- 의견: 보유\n"
            "- 핵심 근거: Valuation Agent 산출물을 확인하지 못했습니다.\n"
            "- WACC/DCF/Peer 비교/민감도: 해당 없음\n"
            "- 대시보드·워크북 산출물: 해당 없음\n"
            "- 한계: valuation-intake와 valuation 실행 로그 확인 필요\n"
        )

    if metrics.get("status") == "FAILED":
        return (
            "### 가치평가 분석\n"
            "- 의견: 보유\n"
            f"- 핵심 근거: Valuation Agent 실행 실패: {metrics.get('error')}\n"
            "- WACC/DCF/Peer 비교/민감도: 해당 없음\n"
            "- 대시보드·워크북 산출물: 해당 없음\n"
            "- 한계: valuation-intake 재실행 필요\n"
        )

    wacc = metrics.get("wacc") or {}
    dcf = metrics.get("dcf") or {}
    ml = metrics.get("ml_overlay") or {}
    peer = metrics.get("peer_comps") or {}
    ref = metrics.get("reference_universe_summary") or {}
    validation_status = metrics.get("validation_status") or "해당 없음"
    price = metrics.get("price_summary") or {}
    scorecard = metrics.get("scorecard") or {}
    advanced = metrics.get("advanced_valuation") or {}
    football = advanced.get("football_field") or {}
    reverse_dcf = advanced.get("reverse_dcf") or {}
    owner = advanced.get("owner_earnings") or {}
    opinion = metrics.get("opinion") or "보유"

    return (
        "### 가치평가 분석\n"
        f"- 의견: {opinion}\n"
        "- 핵심 근거: Valuation Agent는 기존 finance_agent 산출물을 읽지 않고 자체 `valuation/intake` 데이터로 "
        "DART 재무제표, 주가, 발행주식 수, 피어 데이터, 파이낸셜 모델링 가정을 수집해 DCF·WACC·Peer 비교·가치범위·역산 DCF·민감도를 계산합니다.\n"
        f"- WACC/DCF/Peer 비교/민감도: WACC **{_fmt_pct(wacc.get('wacc'))}**, "
        f"DCF 기업가치(EV) **{_fmt_money(dcf.get('enterprise_value'))}**, "
        f"DCF 지분가치 **{_fmt_money(dcf.get('equity_value'))}**, "
        f"DCF 내재주가 **{_fmt_price(dcf.get('implied_price'))}**, "
        f"현재가 대비 괴리율 **{_fmt_pct(dcf.get('upside_downside_pct'))}**입니다.\n"
        f"- 시장 데이터: 현재가 **{_fmt_price(price.get('latest_close') or dcf.get('latest_close'))}**, "
        f"주가 데이터 **{price.get('price_rows', '해당 없음')}행**, "
        f"1년 수익률 **{_fmt_pct(price.get('return_1y'))}**, MDD **{_fmt_pct(price.get('mdd'))}**, "
        f"시가총액 **{_fmt_money(price.get('market_cap'))}**입니다.\n"
        f"- ML 보조판단: **{ml.get('label_kr') or ml.get('label', '해당 없음')}** "
        f"(종합점수: {ml.get('composite_score', '해당 없음')}).\n"
        f"- 종합 가치평가 보강: 가치범위 중앙값 **{_fmt_price(football.get('base_price'))}**, "
        f"안전마진 **{_fmt_pct(football.get('margin_of_safety_pct'))}**, "
        f"역산 영구성장률 **{_fmt_pct(reverse_dcf.get('implied_terminal_growth_rate'))}**, "
        f"오너 이익 주당가치 **{_fmt_price(owner.get('owner_earnings_value_per_share'))}**입니다.\n"
        f"- 대시보드·워크북 산출물: Excel workbook `{rel_project_path(workbook)}`, "
        f"dashboard payload `{rel_project_path(dashboard)}`, valuation report `{rel_project_path(report_md)}`.\n"
        f"- 한계: 검증 상태 **{validation_status}**. DCF는 자동 수집 데이터와 기본 가정에 기반하므로 최종 투자판단 전 가정값 민감도와 원천 계정 매핑을 확인해야 합니다.\n"
    )


def inject_valuation_section(report: str, *, company_dir: str, company: str, **_: Any) -> str:
    section = build_valuation_chair_section(company_dir=company_dir, company=company).rstrip() + "\n"

    # Replace existing Valuation subsection inside the specialist summary.
    pattern = re.compile(
        r"### 가치평가 분석\n.*?(?=\n### |\n## 5\.|\Z)",
        re.DOTALL,
    )
    if pattern.search(report):
        return pattern.sub(lambda _m: section, report, count=1)

    # Insert before Issue if possible, otherwise before section 5.
    marker = "\n### 이슈 분석"
    if marker in report:
        return report.replace(marker, "\n" + section + marker, 1)

    marker2 = "\n## 5. 충돌 지점 및 해석"
    if marker2 in report:
        return report.replace(marker2, "\n" + section + marker2, 1)

    return report.rstrip() + "\n\n" + section

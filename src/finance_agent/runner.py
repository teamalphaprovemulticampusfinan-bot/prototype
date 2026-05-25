from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from .analyzer import analyze_finance
from .config import COMPANIES_DIR, WORKSPACE_DIR
from .data_loader import check_warning_stock, load_finance_data, load_stock_data, get_stock_data_range
from .prompts import build_prompt, build_extended_prompt

try:
    from common.data_paths import (
        company_name as _canonical_company_name,
        company_slug as _company_slug,
        decode_escaped_unicode as _decode_escaped_unicode,
        warning_csv_path as _canonical_warning_csv_path,
    )
except Exception:  # pragma: no cover - standalone fallback
    _canonical_company_name = None  # type: ignore[assignment]
    _company_slug = None  # type: ignore[assignment]
    _canonical_warning_csv_path = None  # type: ignore[assignment]

    def _decode_escaped_unicode(value: Any) -> str:  # type: ignore[no-redef]
        return str(value or "")


def _safe_company_slug(value: str, default: str | None = None) -> str:
    if callable(_company_slug):
        try:
            return str(_company_slug(value, default=default)).strip()
        except Exception:
            pass
    return (default or value or "").strip()


def _safe_company_display(value: str, fallback: str | None = None) -> str:
    if callable(_canonical_company_name):
        try:
            return str(_canonical_company_name(value)).strip()
        except Exception:
            pass
    return (fallback or value or "").strip()


def _first_existing_path(candidates: list[Path], default: Path) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return default


def resolve_company_files(company_name: str, display_name: str | None = None) -> tuple[Path, Path, str]:
    """Resolve the fixed finance-agent input files.

    Canonical input layout:
      data/반도체/<회사명>/finance/<회사명>_재무.csv
      data/반도체/<회사명>/finance/<회사명>_주식.csv
    """
    raw = _decode_escaped_unicode(str(company_name or "")).strip()
    display = _decode_escaped_unicode(str(display_name or "")).strip()
    slug = _safe_company_slug(raw or display, default=raw or display)
    canonical_display = _safe_company_display(slug, fallback=display or raw or slug)
    finance_dir = COMPANIES_DIR / canonical_display / "finance"
    finance_candidates = [
        finance_dir / f"{canonical_display}_재무.csv",
        finance_dir / f"{canonical_display}_재무데이터.csv",
        finance_dir / f"{canonical_display}_finance.csv",
        finance_dir / f"{slug}_finance.csv",
        finance_dir / f"{slug}_재무.csv",
    ]
    stock_candidates = [
        finance_dir / f"{canonical_display}_주식.csv",
        finance_dir / f"{canonical_display}_stock.csv",
        finance_dir / f"{canonical_display}_주가.csv",
        finance_dir / f"{slug}_stock.csv",
        finance_dir / f"{slug}_주식.csv",
        finance_dir / f"{slug}_주가.csv",
    ]
    finance_path = _first_existing_path(finance_candidates, finance_candidates[0])
    stock_path = _first_existing_path(stock_candidates, stock_candidates[0])

    return finance_path, stock_path, slug


def finance_output_paths(finance_path: Path, company_name: str) -> tuple[Path, Path]:
    output_dir = finance_path.parent
    return (
        output_dir / f"{company_name}_finance.json",
        output_dir / f"{company_name}_finance_agent_packet.json",
    )


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# -----------------------------------------------------------------------------
# Finance packet builder using prompts.py as the primary interpretation layer
# -----------------------------------------------------------------------------
# 목적
# - 팀원이 만든 prompts.py는 그대로 사용한다.
# - LLM이 prompts.py 규칙에 따라 만든 summary/key_thesis/key_risks를
#   최종 Chair 보고서에 최대한 반영한다.
# - 다만 First Auditor는 claim 단위로 숫자·기간·단위·evidence_id를 검증하므로,
#   pass/fail 대상 claims[]는 로컬 CSV에서 직접 확인 가능한 수치로 정규화한다.
#
# 구조
# 1) prompts.py → analyze_finance() → llm_data 생성
# 2) 로컬 CSV metric을 보고서용 report_core_points에 반영
# 3) LLM의 key_thesis/key_risks는 Chair View에 반영
# 4) Auditor용 claims[]는 evidence_id와 1:1 연결된 안전 claim만 생성
# 5) 검증 packet은 중복 alias 없이 evidence/claims와 최소 raw_payload만 보존
# -----------------------------------------------------------------------------


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text.lower() in {"nan", "none", "null", "확인 제한"}:
        return None
    try:
        value_f = float(text)
    except Exception:
        return None
    if math.isnan(value_f) or math.isinf(value_f):
        return None
    return value_f


def _fmt_metric_value(value: Any, unit: str | None = None, digits: int = 2) -> str:
    value_f = _num(value)
    if value_f is None:
        return "확인 제한"
    if unit == "원":
        return f"{value_f:,.0f}원"
    if unit:
        return f"{value_f:.{digits}f}{unit}"
    return f"{value_f:.{digits}f}"


def _latest_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean_rows = [r for r in rows if isinstance(r, dict) and _num(r.get("year")) is not None]
    if not clean_rows:
        return {}
    return max(clean_rows, key=lambda r: int(_num(r.get("year")) or 0))


def _latest_recent_stock(recent_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [r for r in recent_rows if isinstance(r, dict) and r.get("date")]
    if not rows:
        return {}
    rows = sorted(rows, key=lambda r: str(r.get("date")))
    return rows[-1]


def _clean_source_name(path: Path) -> str:
    try:
        return path.name
    except Exception:
        return str(path)


def _clean_text(text: Any, limit: int = 260) -> str:
    text = str(text or "").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _evidence(
    *,
    evidence_id: str,
    source_type: str,
    source: str,
    metric: str,
    value: Any,
    unit: str | None,
    period: str | int | None,
    snippet: str,
    label: str | None = None,
    prompt_rationale: str | None = None,
) -> dict[str, Any]:
    numeric_value = _num(value)
    return {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source": source,
        "metric": metric,
        "label": label or metric,
        "value": numeric_value if numeric_value is not None else value,
        "unit": unit,
        "period": str(period) if period not in (None, "") else None,
        "snippet": snippet,
        "prompt_rationale": prompt_rationale,
    }


def _claim(claim_id: str, text: str, evidence_ids: list[str], *, audit_safe: bool = True) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "text": text,
        "evidence_ids": evidence_ids,
        "audit_safe": audit_safe,
    }


METRIC_LABELS: dict[str, str] = {
    "sales_growth": "매출성장률",
    "operating_margin": "영업이익률",
    "roe": "ROE",
    "fcf": "FCF",
    "debt_ratio": "부채비율",
    "annual_return_%": "연수익률",
    "annual_mdd_%": "연간 MDD",
    "volume_mean": "거래량",
    "ma20_ratio_mean": "MA20 대비 비율",
    "vkospi_mean": "변동성지수",
    "latest_close": "최근 종가",
    "warning_stock": "투자경고 여부",
}


METRIC_DESCRIPTIONS: dict[str, str] = {
    "sales_growth": "성장성 방향을 보여주는 핵심 재무 지표입니다.",
    "operating_margin": "영업 단계 수익성 부담 여부를 판단하는 핵심 지표입니다.",
    "roe": "자기자본 대비 수익성 수준을 확인하는 지표입니다.",
    "fcf": "투자·운전자본 변동을 반영한 현금창출력을 확인하는 지표입니다.",
    "debt_ratio": "재무 레버리지와 안정성 부담을 확인하는 지표입니다.",
    "annual_return_%": "해당 연도 주가 성과를 보여주는 지표입니다.",
    "annual_mdd_%": "투자자가 경험할 수 있는 최대 낙폭 위험을 보여주는 지표입니다.",
    "volume_mean": "해당 연도 평균 거래량을 통해 시장 관심과 유동성을 확인하는 지표입니다.",
    "ma20_ratio_mean": "현재 가격이 20일 이동평균선(MA20) 대비 얼마나 떨어져/올라가 있는지 보여주는 지표입니다.",
    "vkospi_mean": "시장 변동성 환경을 함께 확인하기 위한 보조 지표입니다.",
}


def _build_report_points_from_metrics(
    *,
    company_name: str,
    evidence_by_metric: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    report_points: list[str] = []
    missing_metrics: list[str] = []
    mandatory_order = [
        "sales_growth",
        "operating_margin",
        "roe",
        "fcf",
        "debt_ratio",
        "annual_return_%",
        "annual_mdd_%",
        "volume_mean",
        "ma20_ratio_mean",
        "vkospi_mean",
    ]
    for metric in mandatory_order:
        label = METRIC_LABELS.get(metric, metric)
        if metric in evidence_by_metric:
            ev = evidence_by_metric[metric]
            value_text = _fmt_metric_value(ev.get("value"), ev.get("unit"))
            period = ev.get("period") or "최근"
            report_points.append(
                f"{label}: {company_name} {period} 기준 {label} 값은 {value_text}이며, {METRIC_DESCRIPTIONS.get(metric, '재무·주가 판단에 필요한 지표입니다')}"
            )
        else:
            missing_metrics.append(label)

    return report_points, missing_metrics


def build_auditor_safe_finance_packet(
    *,
    company_dir: str,
    company_name: str,
    finance_path: Path,
    stock_path: Path,
    warning_path: Path,
    finance_result: dict[str, Any],
    stock_result: dict[str, Any],
    warning_info: dict[str, Any],
    llm_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """prompts.py 분석 결과를 보고서에 살리고, audit claims는 CSV 기반으로 안정화한다."""
    llm_data = dict(llm_data or {})

    finance_rows = finance_result.get("finance_data") if isinstance(finance_result, dict) else []
    stock_metrics = stock_result.get("annual_metrics") if isinstance(stock_result, dict) else []
    yearly_summary = stock_result.get("yearly_summary") if isinstance(stock_result, dict) else []
    recent_1m = stock_result.get("recent_1m") if isinstance(stock_result, dict) else []

    latest_fin = _latest_row(finance_rows if isinstance(finance_rows, list) else [])
    latest_stock = _latest_row(stock_metrics if isinstance(stock_metrics, list) else [])
    latest_yearly = _latest_row(yearly_summary if isinstance(yearly_summary, list) else [])
    latest_recent = _latest_recent_stock(recent_1m if isinstance(recent_1m, list) else [])

    year = int(_num(latest_fin.get("year")) or _num(latest_stock.get("year")) or 0) or None
    stock_year = int(_num(latest_stock.get("year")) or year or 0) or None
    yearly_stock_year = int(_num(latest_yearly.get("year")) or stock_year or 0) or None
    latest_date = latest_recent.get("date")

    finance_source = _clean_source_name(finance_path)
    stock_source = _clean_source_name(stock_path)
    warning_source = _clean_source_name(warning_path)

    evidences: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    evidence_by_metric: dict[str, dict[str, Any]] = {}

    def add_metric(
        *,
        idx: int,
        source_type: str,
        source: str,
        row: dict[str, Any],
        metric: str,
        unit: str | None,
        period: str | int | None,
        digits: int = 2,
    ) -> None:
        value = row.get(metric)
        value_n = _num(value)
        if value_n is None or period in (None, ""):
            return
        label = METRIC_LABELS.get(metric, metric)
        value_text = _fmt_metric_value(value_n, unit, digits=digits)
        evidence_id = f"finance.ev.{idx:03d}"
        ev = _evidence(
            evidence_id=evidence_id,
            source_type=source_type,
            source=source,
            metric=metric,
            label=label,
            value=value_n,
            unit=unit,
            period=period,
            snippet=f"{company_name} {period} 기준 {label} 값은 {value_text}입니다.",
        )
        evidences.append(ev)
        evidence_by_metric[metric] = ev
        claims.append(
            _claim(
                f"finance.safe_cl.{idx:03d}",
                f"{company_name} {period} 기준 {label} 값은 {value_text}입니다.",
                [evidence_id],
            )
        )

    add_metric(idx=1, source_type="stock_csv", source=stock_source, row=latest_yearly, metric="sales_growth", unit="%", period=yearly_stock_year)
    add_metric(idx=2, source_type="financial_csv", source=finance_source, row=latest_fin, metric="operating_margin", unit="%", period=year)
    add_metric(idx=3, source_type="financial_csv", source=finance_source, row=latest_fin, metric="roe", unit="%", period=year)
    add_metric(idx=4, source_type="financial_csv", source=finance_source, row=latest_fin, metric="fcf", unit="원", period=year, digits=0)
    add_metric(idx=5, source_type="financial_csv", source=finance_source, row=latest_fin, metric="debt_ratio", unit="%", period=year)
    add_metric(idx=7, source_type="stock_csv", source=stock_source, row=latest_stock, metric="annual_return_%", unit="%", period=stock_year)
    add_metric(idx=8, source_type="stock_csv", source=stock_source, row=latest_stock, metric="annual_mdd_%", unit="%", period=stock_year)
    add_metric(idx=9, source_type="stock_csv", source=stock_source, row=latest_yearly, metric="volume_mean", unit="주", period=yearly_stock_year, digits=0)
    add_metric(idx=10, source_type="stock_csv", source=stock_source, row=latest_yearly, metric="ma20_ratio_mean", unit="배", period=yearly_stock_year, digits=4)
    add_metric(idx=11, source_type="stock_csv", source=stock_source, row=latest_yearly, metric="vkospi_mean", unit=None, period=yearly_stock_year)

    latest_close = latest_recent.get("close")
    if latest_date and _num(latest_close) is not None:
        evidence_id = "finance.ev.012"
        ev = _evidence(
            evidence_id=evidence_id,
            source_type="stock_csv",
            source=stock_source,
            metric="latest_close",
            label="최근 종가",
            value=_num(latest_close),
            unit="원",
            period=latest_date,
            snippet=f"{company_name} {latest_date} 최근 종가 값은 {_fmt_metric_value(latest_close, '원')}입니다.",
        )
        evidences.append(ev)
        evidence_by_metric["latest_close"] = ev

    if warning_info:
        warning_flag = bool(warning_info.get("warning"))
        evidence_id = "finance.ev.013"
        ev = _evidence(
            evidence_id=evidence_id,
            source_type="warning_stock_csv",
            source=warning_source,
            metric="warning_stock",
            label="투자경고 여부",
            value=1 if warning_flag else 0,
            unit=None,
            period=warning_info.get("date") or warning_info.get("source_date") or "최근",
            snippet=(
                warning_info.get("message")
                or f"{company_name} 투자경고종목 해당 여부 값은 {1 if warning_flag else 0}입니다."
            ),
        )
        evidences.append(ev)
        evidence_by_metric["warning_stock"] = ev

    if not claims and evidences:
        first = evidences[0]
        claims.append(
            _claim(
                "finance.safe_cl.001",
                f"{company_name} finance 데이터에서 {first.get('label') or first.get('metric')} 값은 {first.get('value')}입니다.",
                [str(first.get("evidence_id"))],
            )
        )

    report_core_points, missing_metrics = _build_report_points_from_metrics(
        company_name=company_name,
        evidence_by_metric=evidence_by_metric,
    )

    key_thesis: list[str] = []
    for value in llm_data.get("key_thesis") or []:
        text = _clean_text(value, 220)
        if text and text not in key_thesis:
            key_thesis.append(text)
    if not key_thesis:
        for point in report_core_points[:4]:
            clean_point = re.sub(r"\s*\(검증값:.*?\)$", "", point).strip()
            if clean_point and clean_point not in key_thesis:
                key_thesis.append(clean_point)


    key_risks: list[str] = []
    for value in llm_data.get("key_risks") or []:
        text = _clean_text(value, 220)
        if text and text not in key_risks:
            key_risks.append(text)
    operating_margin = latest_fin.get("operating_margin")
    debt_ratio = latest_fin.get("debt_ratio")
    if _num(operating_margin) is not None and (_num(operating_margin) or 0) < 0:
        key_risks.append(f"영업이익률 {_fmt_metric_value(operating_margin, '%')}로 수익성 부담을 확인해야 합니다.")
    if _num(debt_ratio) is not None and (_num(debt_ratio) or 0) >= 180:
        key_risks.append(f"부채비율 {_fmt_metric_value(debt_ratio, '%')}로 재무 레버리지 부담을 확인해야 합니다.")
    if _num(latest_stock.get("annual_mdd_%")) is not None and (_num(latest_stock.get("annual_mdd_%")) or 0) <= -25:
        key_risks.append(f"연간 MDD {_fmt_metric_value(latest_stock.get('annual_mdd_%'), '%')}로 주가 낙폭 리스크를 확인해야 합니다.")
    key_risks = list(dict.fromkeys([k for k in key_risks if k]))[:8]

    llm_summary = _clean_text(llm_data.get("summary"), 700)
    if llm_summary and "LLM 분석 실패" not in llm_summary and "validation errors" not in llm_summary:
        summary = llm_summary
    else:
        summary = "제공된 로컬 재무·주가 데이터 기준으로 핵심 지표를 점검했습니다."

    source_contexts = [
        f"financial_csv={finance_source}",
        f"stock_csv={stock_source}",
        f"warning_stock_csv={warning_source}",
        "prompts.py summary/key_thesis/key_risks are preserved in the Chair View where available.",
        "First Auditor claims are CSV-grounded one-to-one evidence claims for stable actual-information verification.",
    ]
    if missing_metrics:
        source_contexts.append("필수 지표 산출 한계: " + ", ".join(missing_metrics))

    packet = {
        "agent_name": "finance",
        "company_name": company_name,
        "company_dir": company_dir,
        "industry_type": llm_data.get("industry_type") or "deeptech_semiconductor",
        "summary": summary,
        "key_thesis": key_thesis[:8],
        "key_risks": key_risks[:8],
        "report_core_points": report_core_points[:12],
        "missing_prompt_metrics": missing_metrics,
        "evidence": evidences,
        "claims": claims,
        "warning_note": warning_info.get("message") if isinstance(warning_info, dict) else None,
        "source_contexts": source_contexts,
        "raw_payload": {
            "latest_financial_row": latest_fin,
            "latest_stock_metric": latest_stock,
            "latest_yearly_summary": latest_yearly,
            "latest_recent_stock_row": latest_recent,
            "audit_policy": "prompts_py_used_for_interpretation_claims_grounded_by_local_csv",
        },
        "packet_version": "finance_prompts_grounded_v4_compact",
    }

    return packet


def to_chair_view(packet: dict[str, Any]) -> dict[str, Any]:
    """Full audit packet에서 Chair Agent/terminal용 경량 뷰만 추출한다.

    claims, raw_payload, source_contexts 등
    auditor 전용 필드는 포함하지 않는다.
    """
    return {
        "agent": "finance",
        "company_name": packet.get("company_name") or packet.get("company") or "",
        "industry_type": packet.get("industry_type") or "deeptech_semiconductor",
        "summary": packet.get("summary") or "",
        "key_thesis": (packet.get("key_thesis") or [])[:8],
        "key_risks": (packet.get("key_risks") or [])[:8],
        "warning_note": packet.get("warning_note"),
    }


def run_finance_agent(company_name: str, display_name: str | None = None) -> dict:
    finance_path, stock_path, resolved_name = resolve_company_files(company_name, display_name)
    display_name = (display_name or _safe_company_display(resolved_name, fallback=resolved_name)).strip()

    print(f"[{company_name}] 재무 분석을 시작합니다...")

    try:
        warning_path = _canonical_warning_csv_path() if callable(_canonical_warning_csv_path) else WORKSPACE_DIR / "투자경고종목.csv"
    except Exception:
        warning_path = WORKSPACE_DIR / "투자경고종목.csv"

    if not finance_path.exists():
        raise FileNotFoundError(f"재무 데이터 파일을 찾을 수 없습니다: {finance_path}")

    if not stock_path.exists():
        raise FileNotFoundError(f"주식 데이터 파일을 찾을 수 없습니다: {stock_path}")

    if not warning_path.exists():
        print(f"[경고] 투자경고종목 데이터 파일을 찾을 수 없습니다: {warning_path}. 경고 검사를 생략합니다.")
        warning_info = {"warning": False, "message": None, "source_date": None}
    else:
        warning_info = check_warning_stock(str(warning_path), display_name)

    finance_result = load_finance_data(str(finance_path))
    stock_result = load_stock_data(str(stock_path))

    # 팀원이 작성한 prompts.py를 그대로 사용한다.
    prompt = build_prompt(
        company_name=display_name,
        finance_result=finance_result,
        stock_result=stock_result,
        warning_info=warning_info,
    )

    def get_extended_data(start_date: str, end_date: str) -> str:
        extended_data = get_stock_data_range(str(stock_path), start_date, end_date)
        return build_extended_prompt(prompt, extended_data, start_date, end_date)

    llm_data: dict[str, Any] = {}
    try:
        response = analyze_finance(prompt, get_extended_data=get_extended_data)
        llm_data = response.model_dump()
    except Exception as exc:
        # API 장애나 네트워크 실패 시에도 파이프라인은 유지한다.
        # 단, 사용자-facing summary에는 긴 validation/traceback 문구를 넣지 않는다.
        print(f"[finance] Gemini LLM 분석 실패 → NVIDIA 자동 fallback 없이 로컬 CSV 기반 검증 패킷으로 대체합니다: {exc}")
        llm_data = {
            "agent": "finance",
            "company_name": display_name,
            "industry_type": "deeptech_semiconductor",
            "summary": "제공된 로컬 재무·주가 데이터 기준으로 핵심 지표를 점검했습니다.",
            "key_thesis": [],
            "key_risks": [],
            "warning_note": None,
            "llm_error": str(exc),
        }

    # 1) Compact audit packet 생성 (auditor 검증용 구조 유지)
    audit_packet = build_auditor_safe_finance_packet(
        company_dir=company_name,
        company_name=display_name,
        finance_path=finance_path,
        stock_path=stock_path,
        warning_path=warning_path,
        finance_result=finance_result,
        stock_result=stock_result,
        warning_info=warning_info,
        llm_data=llm_data,
    )

    # 2) Chair JSON과 audit packet을 분리하고, 각각 별도 JSON으로 저장한다.
    chair_json = to_chair_view(audit_packet)
    finance_json_path, packet_json_path = finance_output_paths(finance_path, display_name)
    write_json(finance_json_path, chair_json)
    write_json(packet_json_path, audit_packet)

    return {
        "chair_json": chair_json,
        "_audit_packet": audit_packet,
        "output_files": {
            "finance_json": str(finance_json_path),
            "finance_agent_packet_json": str(packet_json_path),
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Finance Agent")
    parser.add_argument(
        "--company",
        type=str,
        required=True,
        help="표시용 회사명. 비우면 company.yaml의 corp_name 사용",
    )

    args = parser.parse_args(argv)
    result = run_finance_agent(args.company)

    # terminal 출력은 Chair Agent에 전달되는 경량 JSON만 사용한다.
    print("\n[분석 결과 (Chair View)]")
    print(json.dumps(result["chair_json"], ensure_ascii=False, indent=2))
    return 0

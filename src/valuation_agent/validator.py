from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import to_float


def _manifest_price_rows(context: Any) -> int:
    try:
        counts = getattr(context, "intake_manifest", {}).get("counts") or {}
        return int(counts.get("price_rows") or 0)
    except Exception:
        return 0


def validate_valuation(context: Any, normalized: list[dict[str, Any]], wacc: dict[str, Any], dcf: dict[str, Any], workbook_path: Path | None = None) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    audit_trail: list[dict[str, Any]] = []

    def add(severity: str, code: str, message: str) -> None:
        issues.append({"severity": severity, "code": code, "message": message})

    if not normalized:
        add("HIGH", "NO_NORMALIZED_FINANCIALS", "DART 기반 정규화 재무제표가 비어 있습니다. DART_API_KEY와 corp_code 매핑을 확인하세요.")
    else:
        audit_trail.append({"step": "normalized_financials", "status": "OK", "rows": len(normalized)})
        latest = normalized[-1]
        for key in ("revenue", "operating_profit", "assets", "liabilities", "equity"):
            if to_float(latest.get(key)) is None:
                add("MEDIUM", f"MISSING_{key.upper()}", f"최근 연도 {key} 값이 없습니다.")
        if len(normalized) < 3:
            add("MEDIUM", "SHORT_FINANCIAL_HISTORY", "재무제표 정규화 연도가 3년 미만이라 추세 기반 가정의 신뢰도가 낮습니다.")
        fcf_margin = to_float(latest.get("fcf_margin"))
        if fcf_margin is not None and fcf_margin < 0:
            add("MEDIUM", "NEGATIVE_FCF_MARGIN", "최근 연도 FCF margin이 음수입니다. DCF 결과 해석 시 보수적으로 봐야 합니다.")

    price_rows = getattr(context, "price_history", []) or []
    price_summary = getattr(context, "price_summary", {}) or {}
    manifest_price_rows = _manifest_price_rows(context)
    summary_price_rows = int(to_float(price_summary.get("price_rows")) or 0)
    if not price_rows:
        if summary_price_rows > 0 or manifest_price_rows > 0:
            add("LOW", "PRICE_HISTORY_SUMMARY_ONLY", "주가 원천 CSV 로딩은 제한되었지만 valuation_price_summary/manifest에 가격 수집 흔적이 있어 요약값으로 대체했습니다. valuation-intake 재실행 시 전체 차트 품질이 개선됩니다.")
            audit_trail.append({"step": "price_history_summary", "status": "WARN_SUMMARY_ONLY", "rows_in_manifest": manifest_price_rows, "rows_in_summary": summary_price_rows})
        else:
            add("MEDIUM", "NO_PRICE_HISTORY", "가격 데이터가 비어 있어 beta/volatility proxy와 dashboard 차트 품질이 제한됩니다.")
    else:
        audit_trail.append({"step": "price_history", "status": "OK", "rows": len(price_rows)})
        if len(price_rows) < 240:
            add("LOW", "SHORT_PRICE_HISTORY", "주가 데이터가 1년 미만입니다. 변동성·MDD 해석이 제한됩니다.")
        latest_close = to_float(price_rows[-1].get("close"))
        if latest_close is None:
            add("LOW", "LATEST_PRICE_MISSING", "최근 주가 행의 종가가 비어 있습니다. 현재가/괴리율 표시는 제한될 수 있습니다.")

    shares = to_float(context.assumptions.get("shares_outstanding")) if hasattr(context, "assumptions") else None
    if shares is None:
        add("LOW", "NO_SHARE_COUNT", "발행주식 수를 확인하지 못해 내재주가/시가총액 기반 지표 일부가 제한될 수 있습니다.")
    else:
        audit_trail.append({"step": "share_count", "status": "OK", "shares_outstanding": shares})
    audit_trail.append({"step": "reference_universe", "status": "OK" if getattr(context, "reference_universe", []) else "WARN", "rows": len(getattr(context, "reference_universe", []) or [])})

    market_cap = to_float(price_summary.get("market_cap"))
    if shares is not None and to_float(price_summary.get("latest_close")) is not None and market_cap is None:
        add("LOW", "MARKET_CAP_NOT_FILLED", "현재가와 발행주식 수는 있으나 시가총액 보조지표가 비어 있습니다. valuation-intake 재실행을 권장합니다.")
    else:
        audit_trail.append({"step": "market_cap", "status": "OK" if market_cap is not None else "INFO_NOT_AVAILABLE", "market_cap": market_cap})

    avg_value = to_float(price_summary.get("avg_trading_value_20d"))
    if price_rows and avg_value is None:
        add("LOW", "LIQUIDITY_PROXY_NOT_FILLED", "20일 평균 거래대금 proxy가 비어 있습니다. 가격 intake enrichment 로직을 확인하세요.")
    elif avg_value is not None:
        audit_trail.append({"step": "liquidity_proxy", "status": "OK", "avg_trading_value_20d": avg_value})

    wacc_v = to_float(wacc.get("wacc"))
    if wacc_v is None or not (0.03 <= wacc_v <= 0.25):
        add("MEDIUM", "WACC_OUT_OF_RANGE", f"WACC가 일반 범위를 벗어났습니다: {wacc_v}")
    if dcf.get("status") != "OK":
        add("HIGH", "DCF_NOT_OK", f"DCF 상태가 OK가 아닙니다: {dcf.get('status')}")
    ev = to_float(dcf.get("enterprise_value"))
    eq = to_float(dcf.get("equity_value"))
    if ev is not None and ev < 0:
        add("MEDIUM", "NEGATIVE_ENTERPRISE_VALUE", "DCF EV가 음수입니다. FCF margin/성장률/WACC 가정을 확인하세요.")
    if eq is not None and eq < 0:
        add("MEDIUM", "NEGATIVE_EQUITY_VALUE", "DCF 지분가치가 음수입니다. 부채 proxy와 현금흐름 가정을 확인하세요.")

    if workbook_path is not None:
        if workbook_path.exists():
            audit_trail.append({"step": "workbook_available", "status": "OK", "path": str(workbook_path)})
        else:
            add("HIGH", "WORKBOOK_MISSING", "valuation workbook 파일이 생성되지 않았습니다.")

    if not issues:
        issues.append({"severity": "INFO", "code": "NO_MAJOR_WARNINGS", "message": "주요 validation warning 없음"})

    high = [x for x in issues if x["severity"] == "HIGH"]
    med = [x for x in issues if x["severity"] == "MEDIUM"]
    status = "FAIL" if high else ("PASS_WITH_WARNINGS" if med else "PASS")
    return {
        "status": status,
        "issues": issues,
        "audit_trail": audit_trail,
        "principle": "valuation_agent 자체 데이터/모델 일관성 검증; 기존 web-auditor 의존 없음",
    }

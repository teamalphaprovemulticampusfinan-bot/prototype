from __future__ import annotations

from typing import Any

from .utils import safe_div, to_float


def _median(values: list[float | None]) -> float | None:
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return None
    n = len(clean)
    mid = n // 2
    return clean[mid] if n % 2 else (clean[mid - 1] + clean[mid]) / 2


def _percentile_rank(values: list[float | None], target: float | None, *, lower_is_better: bool = False) -> float | None:
    clean = sorted(float(v) for v in values if v is not None)
    if target is None or not clean:
        return None
    if lower_is_better:
        score = sum(1 for v in clean if v >= target) / len(clean) * 100.0
    else:
        score = sum(1 for v in clean if v <= target) / len(clean) * 100.0
    return round(score, 2)


def _signal_psr(psr: float | None, median_psr: float | None) -> str:
    if psr is None or median_psr is None or median_psr == 0:
        return "P/S 계산 제외"
    ratio = psr / median_psr
    if ratio <= 0.80:
        return "피어 대비 저PSR 구간: 상대 저평가 가능성"
    if ratio <= 1.20:
        return "피어 중앙값 부근: 상대가치 중립"
    return "피어 대비 고PSR 구간: 성장 프리미엄 또는 밸류 부담 확인 필요"


def _company_key(row: dict[str, Any]) -> str:
    return str(row.get("company_dir") or row.get("company") or row.get("stock_code") or "")


def compute_peer_multiples(peers: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute live peer multiples, including PSR.

    ``valuation_peer_input.csv`` is valuation-owned intake.  It may include only the
    five focal semiconductor firms because live DART/price collection for 208 firms
    would be too slow for a classroom demo.  The 208-firm universe is handled in the
    ML overlay separately, while this function focuses on multiples that require
    live market cap and normalized revenue.
    """

    rows: list[dict[str, Any]] = []
    for p in peers:
        revenue = to_float(p.get("revenue"))
        net_income = to_float(p.get("net_income"))
        operating_profit = to_float(p.get("operating_profit"))
        equity = to_float(p.get("equity"))
        liabilities = to_float(p.get("liabilities"))
        fcf = to_float(p.get("fcf"))
        latest_close = to_float(p.get("latest_close"))
        shares = to_float(p.get("shares_outstanding"))
        market_cap = to_float(p.get("market_cap"))
        if market_cap is None and latest_close is not None and shares is not None:
            market_cap = latest_close * shares
        enterprise_value = market_cap + (liabilities or 0.0) if market_cap is not None else None
        row = dict(p)
        row["is_target"] = str(row.get("is_target")).lower() in {"true", "1", "yes"} or row.get("is_target") is True
        row["market_cap"] = market_cap
        row["enterprise_value_proxy"] = enterprise_value
        row["psr"] = safe_div(market_cap, revenue)
        row["per"] = safe_div(market_cap, net_income)
        row["pbr"] = safe_div(market_cap, equity)
        row["ev_sales"] = safe_div(enterprise_value, revenue)
        row["ev_ebit"] = safe_div(enterprise_value, operating_profit)
        row["p_fcf"] = safe_div(market_cap, fcf)
        row["op_margin"] = safe_div(operating_profit, revenue)
        row["roe"] = safe_div(net_income, equity)
        row["debt_ratio"] = safe_div(liabilities, equity)
        row["psr_data_quality"] = "OK" if row.get("psr") is not None else "시가총액 또는 매출액 보강 필요"
        rows.append(row)

    median_psr = _median([r.get("psr") for r in rows])
    target = next((r for r in rows if r.get("is_target")), rows[0] if rows else {})
    target_psr = to_float(target.get("psr")) if target else None
    target_per = to_float(target.get("per")) if target else None
    target_pbr = to_float(target.get("pbr")) if target else None
    target_ev_sales = to_float(target.get("ev_sales")) if target else None
    psr_vs_median = safe_div(target_psr, median_psr)
    if psr_vs_median is not None:
        psr_vs_median -= 1.0

    return {
        "peer_rows": rows,
        "target_row": target,
        "target_company_key": _company_key(target) if target else "",
        "target_psr": target_psr,
        "target_per": target_per,
        "target_pbr": target_pbr,
        "target_ev_sales": target_ev_sales,
        "target_market_cap": to_float(target.get("market_cap")) if target else None,
        "target_revenue": to_float(target.get("revenue")) if target else None,
        "median_psr": median_psr,
        "median_per": _median([r.get("per") for r in rows]),
        "median_pbr": _median([r.get("pbr") for r in rows]),
        "median_ev_sales": _median([r.get("ev_sales") for r in rows]),
        "median_ev_ebit": _median([r.get("ev_ebit") for r in rows]),
        "median_p_fcf": _median([r.get("p_fcf") for r in rows]),
        "median_op_margin": _median([r.get("op_margin") for r in rows]),
        "median_roe": _median([r.get("roe") for r in rows]),
        "psr_vs_peer_median_pct": psr_vs_median,
        "psr_peer_percentile_lower_better": _percentile_rank([r.get("psr") for r in rows], target_psr, lower_is_better=True),
        "psr_signal_kr": _signal_psr(target_psr, median_psr),
        "peer_count": len(rows),
        "live_peer_count_with_psr": sum(1 for r in rows if r.get("psr") is not None),
        "method_note": "P/S=시가총액/매출액. Live peer multiples는 Valuation Agent 자체 DART/주가/발행주식 수 intake만 사용합니다.",
    }

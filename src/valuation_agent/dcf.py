from __future__ import annotations

from typing import Any

from .normalizer import historical_cagr, latest_row
from .utils import safe_div, to_float


def _avg(values: list[float | None], default: float) -> float:
    clean = [float(v) for v in values if v is not None]
    return sum(clean) / len(clean) if clean else default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_dcf(financials: list[dict[str, Any]], assumptions: dict[str, Any], wacc_result: dict[str, Any]) -> dict[str, Any]:
    latest = latest_row(financials)
    projection_years = int(to_float(assumptions.get("projection_years")) or 5)
    terminal_growth = to_float(assumptions.get("terminal_growth_rate")) or 0.015
    wacc = to_float(wacc_result.get("wacc")) or 0.095
    base_year = int(latest.get("year") or 0)
    base_revenue = to_float(latest.get("revenue"))
    if base_revenue is None:
        return {
            "status": "WARN_NO_REVENUE",
            "projection": [],
            "enterprise_value": None,
            "equity_value": None,
            "terminal_value": None,
            "wacc": wacc,
            "terminal_growth_rate": terminal_growth,
        }

    hist_growth = historical_cagr(financials, "revenue")
    recent_growth = _avg([r.get("revenue_growth") for r in financials[-3:]], hist_growth if hist_growth is not None else 0.03)
    explicit_growth = to_float(assumptions.get("forecast_revenue_growth"))
    growth = _clamp(explicit_growth if explicit_growth is not None else recent_growth, -0.10, 0.20)
    explicit_op_margin = to_float(assumptions.get("forecast_op_margin"))
    op_margin = _clamp(explicit_op_margin if explicit_op_margin is not None else _avg([r.get("op_margin") for r in financials[-3:]], 0.08), -0.20, 0.35)
    fcf_margin_hist = _avg([r.get("fcf_margin") for r in financials[-3:]], max(0.02, op_margin * 0.55))
    fcf_margin = _clamp(fcf_margin_hist, -0.20, 0.25)
    tax = to_float(assumptions.get("tax_rate")) or 0.24

    projection: list[dict[str, Any]] = []
    revenue = base_revenue
    pv_fcf = 0.0
    for i in range(1, projection_years + 1):
        fade = i / max(1, projection_years)
        g = growth * (1 - fade) + terminal_growth * fade
        revenue = revenue * (1 + g)
        ebit = revenue * op_margin
        nopat = ebit * (1 - tax)
        fcf = revenue * fcf_margin
        discount_factor = 1 / ((1 + wacc) ** i)
        pv = fcf * discount_factor
        pv_fcf += pv
        projection.append({
            "year": base_year + i if base_year else i,
            "revenue_growth": g,
            "revenue": revenue,
            "op_margin": op_margin,
            "ebit": ebit,
            "nopat": nopat,
            "fcf_margin": fcf_margin,
            "fcf": fcf,
            "discount_factor": discount_factor,
            "pv_fcf": pv,
        })

    last_fcf = projection[-1]["fcf"] if projection else 0.0
    terminal_value = None
    pv_terminal = None
    enterprise_value = None
    if wacc > terminal_growth:
        terminal_value = last_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        pv_terminal = terminal_value / ((1 + wacc) ** projection_years)
        enterprise_value = pv_fcf + pv_terminal

    cash = to_float(latest.get("cash")) or 0.0
    # Until detailed borrowings are collected, total liabilities are kept as a conservative debt proxy.
    liabilities = to_float(latest.get("liabilities")) or 0.0
    equity_value = enterprise_value + cash - liabilities if enterprise_value is not None else None
    shares_outstanding = to_float(assumptions.get("shares_outstanding"))
    latest_close = to_float(assumptions.get("latest_close"))
    implied_price = safe_div(equity_value, shares_outstanding)
    current_market_cap = latest_close * shares_outstanding if latest_close is not None and shares_outstanding is not None else None
    upside_downside = safe_div(implied_price, latest_close)
    if upside_downside is not None:
        upside_downside -= 1.0

    return {
        "status": "OK" if enterprise_value is not None else "WARN_INVALID_TERMINAL_MATH",
        "base_year": base_year,
        "base_revenue": base_revenue,
        "historical_revenue_cagr": hist_growth,
        "assumed_revenue_growth": growth,
        "assumed_op_margin": op_margin,
        "assumed_fcf_margin": fcf_margin,
        "wacc": wacc,
        "terminal_growth_rate": terminal_growth,
        "projection_years": projection_years,
        "projection": projection,
        "pv_fcf": pv_fcf,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "cash": cash,
        "debt_proxy_liabilities": liabilities,
        "equity_value": equity_value,
        "shares_outstanding": shares_outstanding,
        "latest_close": latest_close,
        "current_market_cap": current_market_cap,
        "implied_price": implied_price,
        "upside_downside_pct": upside_downside,
        "equity_value_note": "Equity value uses total liabilities as conservative debt proxy until detailed borrowings are available.",
    }


def build_sensitivity(dcf: dict[str, Any]) -> list[dict[str, Any]]:
    base_wacc = to_float(dcf.get("wacc")) or 0.095
    base_g = to_float(dcf.get("terminal_growth_rate")) or 0.015
    last_fcf = None
    projection = dcf.get("projection") or []
    if projection:
        last_fcf = to_float(projection[-1].get("fcf"))
    pv_fcf = to_float(dcf.get("pv_fcf")) or 0.0
    years = len(projection) or 5
    rows: list[dict[str, Any]] = []
    for w_delta in (-0.015, -0.005, 0.0, 0.005, 0.015):
        for g_delta in (-0.010, -0.005, 0.0, 0.005, 0.010):
            w = base_wacc + w_delta
            g = base_g + g_delta
            ev = None
            if last_fcf is not None and w > g:
                tv = last_fcf * (1 + g) / (w - g)
                ev = pv_fcf + tv / ((1 + w) ** years)
            rows.append({"wacc": w, "terminal_growth": g, "enterprise_value": ev})
    return rows

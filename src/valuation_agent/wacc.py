from __future__ import annotations

from typing import Any

from .utils import safe_div, to_float


def compute_wacc(latest: dict[str, Any], assumptions: dict[str, Any]) -> dict[str, Any]:
    rf = to_float(assumptions.get("risk_free_rate")) or 0.035
    mrp = to_float(assumptions.get("market_risk_premium")) or 0.060
    beta = to_float(assumptions.get("beta")) or 1.10
    cod = to_float(assumptions.get("pre_tax_cost_of_debt")) or 0.055
    tax = to_float(assumptions.get("tax_rate")) or 0.24

    liabilities = max(0.0, to_float(latest.get("liabilities")) or 0.0)
    book_equity = max(0.0, to_float(latest.get("equity")) or 0.0)
    market_cap = to_float(assumptions.get("market_cap"))
    equity_value_for_weight = market_cap if market_cap is not None and market_cap > 0 else book_equity

    debt_weight = safe_div(liabilities, liabilities + equity_value_for_weight)
    if debt_weight is None:
        debt_weight = 0.35
    debt_weight = min(0.90, max(0.0, debt_weight))
    equity_weight = 1.0 - debt_weight
    cost_of_equity = rf + beta * mrp
    after_tax_cod = cod * (1.0 - tax)
    wacc = equity_weight * cost_of_equity + debt_weight * after_tax_cod
    return {
        "risk_free_rate": rf,
        "market_risk_premium": mrp,
        "beta": beta,
        "cost_of_equity": cost_of_equity,
        "pre_tax_cost_of_debt": cod,
        "tax_rate": tax,
        "after_tax_cost_of_debt": after_tax_cod,
        "debt_weight": debt_weight,
        "equity_weight": equity_weight,
        "book_equity": book_equity,
        "market_cap_used_for_equity_weight": market_cap,
        "debt_proxy_liabilities": liabilities,
        "wacc": wacc,
        "weighting_note": "Uses market cap when share-count intake is available; otherwise uses book equity.",
    }

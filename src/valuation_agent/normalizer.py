from __future__ import annotations

from typing import Any

from .utils import safe_div, to_float


def _num(row: dict[str, Any], key: str) -> float | None:
    return to_float(row.get(key))


def normalize_financials(financials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Valuation Intake financials and add model-ready ratios.

    This function intentionally uses only valuation/intake artifacts. It does not
    read finance_agent outputs. The output is designed for WACC/DCF/Comps,
    dashboard cards and workbook tables.
    """
    rows: list[dict[str, Any]] = []
    for r in financials:
        try:
            year = int(float(str(r.get("year") or "0")))
        except Exception:
            continue
        row: dict[str, Any] = {"year": year}
        for key in [
            "revenue", "operating_profit", "net_income", "assets", "liabilities", "equity", "cash",
            "cfo", "capex", "fcf", "investing_cf", "source_account_count",
        ]:
            row[key] = to_float(r.get(key))
        # Preserve source-account labels for auditability.
        for key in [
            "revenue_source_account", "operating_profit_source_account", "net_income_source_account",
            "assets_source_account", "liabilities_source_account", "equity_source_account",
            "cfo_source_account", "capex_source_account", "cash_source_account",
        ]:
            if r.get(key):
                row[key] = r.get(key)
        if row.get("fcf") is None and row.get("cfo") is not None and row.get("capex") is not None:
            row["fcf"] = row["cfo"] - row["capex"]

        revenue = row.get("revenue")
        assets = row.get("assets")
        equity = row.get("equity")
        liabilities = row.get("liabilities")
        cash = row.get("cash")
        cfo = row.get("cfo")
        capex = row.get("capex")
        fcf = row.get("fcf")

        row["op_margin"] = safe_div(row.get("operating_profit"), revenue)
        row["net_margin"] = safe_div(row.get("net_income"), revenue)
        row["roe"] = safe_div(row.get("net_income"), equity)
        row["roa"] = safe_div(row.get("net_income"), assets)
        row["debt_ratio"] = safe_div(liabilities, equity)
        row["liability_to_assets"] = safe_div(liabilities, assets)
        row["equity_ratio"] = safe_div(equity, assets)
        row["cash_to_assets"] = safe_div(cash, assets)
        row["cfo_margin"] = safe_div(cfo, revenue)
        row["capex_to_sales"] = safe_div(capex, revenue)
        row["fcf_margin"] = safe_div(fcf, revenue)
        row["fcf_conversion"] = safe_div(fcf, row.get("operating_profit"))
        rows.append(row)

    rows.sort(key=lambda x: x["year"])
    for idx, row in enumerate(rows):
        if idx == 0:
            row["revenue_growth"] = None
            row["op_growth"] = None
            row["asset_growth"] = None
        else:
            prev = rows[idx - 1]
            for source_key, out_key in [
                ("revenue", "revenue_growth"),
                ("operating_profit", "op_growth"),
                ("assets", "asset_growth"),
            ]:
                cur_v = row.get(source_key)
                prev_v = prev.get(source_key)
                row[out_key] = (cur_v / prev_v - 1.0) if cur_v is not None and prev_v not in (None, 0) else None
    return rows


def historical_cagr(rows: list[dict[str, Any]], key: str = "revenue") -> float | None:
    values = [(r.get("year"), to_float(r.get(key))) for r in rows if to_float(r.get(key)) not in (None, 0)]
    if len(values) < 2:
        return None
    first_y, first_v = values[0]
    last_y, last_v = values[-1]
    if not first_v or not last_v or last_y == first_y:
        return None
    years = max(1, int(last_y) - int(first_y))
    try:
        return (last_v / first_v) ** (1 / years) - 1.0
    except Exception:
        return None


def latest_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[-1] if rows else {}


def latest_market_snapshot(price_history: list[dict[str, Any]], assumptions: dict[str, Any] | None = None) -> dict[str, Any]:
    clean = [r for r in price_history if to_float(r.get("close")) is not None]
    clean.sort(key=lambda r: str(r.get("date") or ""))
    if not clean:
        return {"latest_close": None, "market_cap": None, "price_rows": 0}
    latest = clean[-1]
    latest_close = to_float(latest.get("close"))
    shares = to_float((assumptions or {}).get("shares_outstanding"))
    market_cap = latest_close * shares if latest_close is not None and shares is not None else None
    closes = [to_float(r.get("close")) for r in clean if to_float(r.get("close")) is not None]
    high_52w = max(closes[-252:]) if len(closes) >= 1 else None
    low_52w = min(closes[-252:]) if len(closes) >= 1 else None
    return {
        "latest_date": latest.get("date"),
        "latest_close": latest_close,
        "shares_outstanding": shares,
        "market_cap": market_cap,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "price_rows": len(clean),
    }

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SECTOR_FILES = {
    "semiconductor_peer_multiples.csv": [
        "as_of_date", "peer_company", "ticker", "market", "vc_role", "revenue", "operating_profit",
        "net_income", "ebitda", "market_cap", "enterprise_value", "per", "pbr", "psr",
        "ev_ebitda", "ev_sales", "roe", "roa", "debt_ratio", "opm", "npm", "source",
    ],
    "deeptech_reference_universe.csv": [
        "as_of_date", "peer_company", "ticker", "market", "vc_role", "reference_group", "technology_theme",
        "revenue", "operating_profit", "net_income", "ebitda", "market_cap", "enterprise_value",
        "per", "pbr", "psr", "ev_ebitda", "ev_sales", "roe", "roa", "debt_ratio", "opm", "npm", "source",
    ],
    "wacc_assumptions.csv": [
        "as_of_date", "risk_free_rate", "market_risk_premium", "beta", "cost_of_equity", "cost_of_debt",
        "tax_rate", "debt_weight", "equity_weight", "wacc", "terminal_growth_rate",
        "forecast_revenue_growth", "forecast_op_margin", "forecast_capex_ratio", "forecast_wc_ratio",
        "discount_period", "source",
    ],
    "sector_growth_assumptions.csv": ["as_of_date", "sector", "vc_role", "revenue_growth", "op_margin", "capex_ratio", "source"],
}

COMPANY_FILES = {
    "financials_normalized.csv": [
        "as_of_date", "fiscal_year", "period_end", "revenue", "gross_profit", "operating_profit", "ebit", "ebitda",
        "net_income", "total_assets", "total_liabilities", "equity", "cash_and_equivalents", "total_debt",
        "operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "capex", "fcf", "working_capital", "source",
    ],
    "price_history.csv": ["date", "open", "high", "low", "close", "adj_close", "volume", "market_cap", "source"],
    "shares_outstanding.csv": [
        "date", "common_shares", "treasury_shares", "floating_shares", "diluted_shares", "cb_potential_shares",
        "bw_potential_shares", "stock_option_shares", "source",
    ],
    "dilution_events.csv": ["date", "event_type", "instrument", "dilutive_shares", "dilution_ratio", "status", "source", "note"],
    "valuation_assumptions.csv": SECTOR_FILES["wacc_assumptions.csv"],
    "peer_multiples.csv": SECTOR_FILES["semiconductor_peer_multiples.csv"],
}


def write_blank(path: Path, cols: list[str], force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return
    pd.DataFrame(columns=cols).to_csv(path, index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create src_eval valuation intake templates.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    sector_dir = root / "data" / args.field / "_sector_common" / "valuation"
    for name, cols in SECTOR_FILES.items():
        write_blank(sector_dir / name, cols, args.force)
    cfg = sector_dir / "valuation_methodology_config.yaml"
    if args.force or not cfg.exists():
        cfg.write_text(
            "methodology: src_eval valuation history evaluation\n"
            "note: final Buy/Hold/Sell decision is produced by DMA/probability tensor, not fixed thresholds.\n",
            encoding="utf-8",
        )
    if args.company:
        intake = root / "data" / args.field / args.company / "valuation" / "intake"
        for name, cols in COMPANY_FILES.items():
            write_blank(intake / name, cols, args.force)
    print(f"[OK] valuation templates checked: {sector_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Evaluation-only valuation intake enhancer.

This file is called from ``src_eval/data_intake/valuation_intake/runner.py``.
It creates a stable valuation intake folder without touching production ``src``.
All time-series tables are cut to ``VALUATION_AS_OF_DATE`` or
``ALPHAPROVE_DATA_CUTOFF_DATE`` when those environment variables exist.
"""

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


COMMON_VALUATION_COLUMNS = {
    "financials_normalized.csv": [
        "as_of_date", "fiscal_year", "period_end", "revenue", "gross_profit", "operating_profit",
        "ebit", "ebitda", "net_income", "total_assets", "total_liabilities", "equity",
        "cash_and_equivalents", "total_debt", "operating_cash_flow", "investing_cash_flow",
        "financing_cash_flow", "capex", "fcf", "working_capital", "source",
    ],
    "price_history.csv": ["date", "open", "high", "low", "close", "adj_close", "volume", "market_cap", "source"],
    "shares_outstanding.csv": [
        "date", "common_shares", "treasury_shares", "floating_shares", "diluted_shares",
        "cb_potential_shares", "bw_potential_shares", "stock_option_shares", "source",
    ],
    "dilution_events.csv": [
        "date", "event_type", "instrument", "dilutive_shares", "dilution_ratio", "status", "source", "note",
    ],
    "peer_multiples.csv": [
        "as_of_date", "peer_company", "ticker", "market", "vc_role", "revenue", "operating_profit",
        "net_income", "ebitda", "market_cap", "enterprise_value", "per", "pbr", "psr",
        "ev_ebitda", "ev_sales", "roe", "roa", "debt_ratio", "opm", "npm", "source",
    ],
    "valuation_assumptions.csv": [
        "as_of_date", "risk_free_rate", "market_risk_premium", "beta", "cost_of_equity",
        "cost_of_debt", "tax_rate", "debt_weight", "equity_weight", "wacc",
        "terminal_growth_rate", "forecast_revenue_growth", "forecast_op_margin",
        "forecast_capex_ratio", "forecast_wc_ratio", "discount_period", "source",
    ],
}


def _env_as_of() -> pd.Timestamp | None:
    for key in (
        "VALUATION_AS_OF_DATE",
        "ALPHAPROVE_DATA_CUTOFF_DATE",
        "EVAL_AS_OF_DATE",
        "AS_OF_DATE",
        "DATA_CUTOFF_DATE",
    ):
        raw = os.environ.get(key)
        if raw:
            ts = pd.to_datetime(raw, errors="coerce")
            if pd.notna(ts):
                return ts.normalize()
    return None


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()


def _write_csv(path: Path, df: pd.DataFrame, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df is None or df.empty:
        pd.DataFrame(columns=columns or []).to_csv(path, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(path, index=False, encoding="utf-8-sig")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        s = str(x).strip().replace(",", "")
        if s == "" or s.lower() in {"nan", "none", "null", "na", "n/a"}:
            return None
        return float(s)
    except Exception:
        return None


def _filter_asof(df: pd.DataFrame, as_of: pd.Timestamp | None) -> pd.DataFrame:
    if df.empty or as_of is None:
        return df.copy()
    for col in ("date", "as_of_date", "period_end", "fiscal_date", "기준일", "일자"):
        if col in df.columns:
            dates = pd.to_datetime(df[col], errors="coerce")
            if dates.notna().any():
                return df.loc[(dates.notna()) & (dates <= as_of)].copy()
    for col in ("fiscal_year", "year", "사업연도"):
        if col in df.columns:
            years = pd.to_numeric(df[col], errors="coerce")
            dates = pd.to_datetime(years.astype("Int64").astype(str) + "-12-31", errors="coerce")
            if dates.notna().any():
                return df.loc[(dates.notna()) & (dates <= as_of)].copy()
    return df.copy()


def _rename_soft(df: pd.DataFrame, mapping: dict[str, list[str]]) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    lower = {str(c).lower().strip(): c for c in out.columns}
    rename: dict[str, str] = {}
    for target, aliases in mapping.items():
        if target in out.columns:
            continue
        for a in aliases:
            key = a.lower().strip()
            if key in lower:
                rename[str(lower[key])] = target
                break
            for c in out.columns:
                if key and key in str(c).lower():
                    rename[str(c)] = target
                    break
            if target in rename.values():
                break
    if rename:
        out = out.rename(columns=rename)
    return out


def _normalize_financials(intake_dir: Path, as_of: pd.Timestamp | None) -> pd.DataFrame:
    df = pd.DataFrame()
    for name in ("valuation_normalized_financials.csv", "financials_normalized.csv", "valuation_raw_dart_accounts.csv", "financials_raw.csv"):
        df = _read_csv(intake_dir / name)
        if not df.empty:
            break
    df = _filter_asof(df, as_of)
    df = _rename_soft(df, {
        "as_of_date": ["as_of_date", "date", "기준일"],
        "fiscal_year": ["fiscal_year", "year", "사업연도"],
        "period_end": ["period_end", "fiscal_date", "결산일"],
        "revenue": ["revenue", "sales", "매출액"],
        "gross_profit": ["gross_profit", "매출총이익"],
        "operating_profit": ["operating_profit", "영업이익", "ebit"],
        "net_income": ["net_income", "당기순이익"],
        "total_assets": ["total_assets", "assets", "총자산"],
        "total_liabilities": ["total_liabilities", "liabilities", "총부채"],
        "equity": ["equity", "자본총계"],
        "cash_and_equivalents": ["cash_and_equivalents", "cash", "현금및현금성자산"],
        "total_debt": ["total_debt", "debt", "borrowings", "차입금"],
        "operating_cash_flow": ["operating_cash_flow", "cfo", "영업활동현금흐름"],
        "investing_cash_flow": ["investing_cash_flow", "cfi", "투자활동현금흐름"],
        "financing_cash_flow": ["financing_cash_flow", "cff", "재무활동현금흐름"],
        "capex": ["capex", "capital_expenditure"],
        "fcf": ["fcf", "free_cash_flow", "잉여현금흐름"],
        "working_capital": ["working_capital", "운전자본"],
    })
    # Derived fields when inputs exist.
    if "ebit" not in df.columns and "operating_profit" in df.columns:
        df["ebit"] = df["operating_profit"]
    if "ebitda" not in df.columns:
        df["ebitda"] = pd.NA
    if "fcf" not in df.columns and {"operating_cash_flow", "capex"}.issubset(df.columns):
        df["fcf"] = pd.to_numeric(df["operating_cash_flow"], errors="coerce") - pd.to_numeric(df["capex"], errors="coerce").abs()
    if "source" not in df.columns:
        df["source"] = "valuation_intake_normalized_or_dart"
    return df


def _normalize_prices(intake_dir: Path, as_of: pd.Timestamp | None) -> pd.DataFrame:
    df = pd.DataFrame()
    for name in ("valuation_price_history.csv", "eval_price_history_v45.csv", "price_history.csv", "valuation_stock_prices.csv"):
        df = _read_csv(intake_dir / name)
        if not df.empty:
            break
    df = _filter_asof(df, as_of)
    df = _rename_soft(df, {
        "date": ["date", "날짜", "일자"],
        "open": ["open", "시가"],
        "high": ["high", "고가"],
        "low": ["low", "저가"],
        "close": ["close", "adj_close", "종가"],
        "adj_close": ["adj_close", "adjusted_close", "수정종가"],
        "volume": ["volume", "거래량"],
        "market_cap": ["market_cap", "시가총액"],
    })
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]
    if "source" not in df.columns:
        df["source"] = "valuation_intake_price_history"
    return df


def _normalize_shares(intake_dir: Path, prices: pd.DataFrame, as_of: pd.Timestamp | None, share_summary: dict[str, Any] | None = None) -> pd.DataFrame:
    df = pd.DataFrame()
    for name in ("shares_outstanding.csv", "valuation_share_count.csv"):
        df = _read_csv(intake_dir / name)
        if not df.empty:
            break
    df = _filter_asof(df, as_of)
    df = _rename_soft(df, {
        "date": ["date", "as_of_date", "기준일"],
        "common_shares": ["common_shares", "shares_outstanding", "issued_shares", "상장주식수", "보통주"],
        "treasury_shares": ["treasury_shares", "자기주식"],
        "floating_shares": ["floating_shares", "유통주식수"],
        "diluted_shares": ["diluted_shares", "희석주식수"],
    })
    if df.empty:
        share_summary = share_summary or {}
        shares = share_summary.get("latest_shares") or share_summary.get("shares_outstanding")
        if shares is not None:
            df = pd.DataFrame([{
                "date": str(as_of.date()) if as_of is not None else "",
                "common_shares": shares,
                "treasury_shares": pd.NA,
                "floating_shares": pd.NA,
                "diluted_shares": shares,
                "source": "valuation_share_summary",
            }])
    if "diluted_shares" not in df.columns and "common_shares" in df.columns:
        df["diluted_shares"] = df["common_shares"]
    if "source" not in df.columns:
        df["source"] = "valuation_intake_share_count"
    return df


def _build_dilution_events(shares: pd.DataFrame, intake_dir: Path, as_of: pd.Timestamp | None) -> pd.DataFrame:
    explicit = _read_csv(intake_dir / "dilution_events.csv")
    explicit = _filter_asof(explicit, as_of)
    if not explicit.empty:
        return _rename_soft(explicit, {
            "date": ["date", "as_of_date", "기준일"],
            "event_type": ["event_type", "type", "종류"],
            "dilutive_shares": ["dilutive_shares", "potential_shares", "전환가능주식수"],
            "dilution_ratio": ["dilution_ratio", "희석률"],
            "status": ["status", "상태"],
        })
    rows: list[dict[str, Any]] = []
    if not shares.empty and "common_shares" in shares.columns:
        s = pd.to_numeric(shares["common_shares"], errors="coerce").dropna()
        if len(s) >= 2 and float(s.iloc[-2]) > 0:
            growth = float(s.iloc[-1]) / float(s.iloc[-2]) - 1.0
            if growth > 0:
                rows.append({
                    "date": str(as_of.date()) if as_of is not None else "",
                    "event_type": "share_count_increase_proxy",
                    "instrument": "common_shares",
                    "dilutive_shares": float(s.iloc[-1]) - float(s.iloc[-2]),
                    "dilution_ratio": growth,
                    "status": "proxy_from_shares_outstanding",
                    "source": "shares_outstanding.csv",
                    "note": "CB/BW/option detail not found; proxy uses as-of share count increase only.",
                })
    if not rows:
        rows.append({
            "date": str(as_of.date()) if as_of is not None else "",
            "event_type": "no_explicit_dilution_event_source_asof",
            "instrument": "",
            "dilutive_shares": pd.NA,
            "dilution_ratio": pd.NA,
            "status": "NO_EXPLICIT_DILUTION_EVENT_SOURCE_ASOF",
            "source": "valuation_intake_enhancer",
            "note": "No CB/BW/stock-option/paid-in capital increase source found before as_of_date.",
        })
    return pd.DataFrame(rows)


def _normalize_peers(intake_dir: Path, sector_dir: Path, as_of: pd.Timestamp | None) -> pd.DataFrame:
    df = pd.DataFrame()
    for p in [
        intake_dir / "peer_multiples.csv",
        intake_dir / "valuation_peer_input.csv",
        sector_dir / "semiconductor_peer_multiples.csv",
        sector_dir / "deeptech_reference_universe.csv",
    ]:
        df = _read_csv(p)
        if not df.empty:
            break
    df = _filter_asof(df, as_of)
    df = _rename_soft(df, {
        "as_of_date": ["as_of_date", "date", "기준일"],
        "peer_company": ["peer_company", "company", "company_name", "기업명"],
        "ticker": ["ticker", "stock_code", "종목코드"],
        "market": ["market", "시장"],
        "vc_role": ["vc_role", "value_chain_role", "role"],
        "revenue": ["revenue", "sales", "매출액"],
        "operating_profit": ["operating_profit", "영업이익"],
        "net_income": ["net_income", "당기순이익"],
        "ebitda": ["ebitda"],
        "market_cap": ["market_cap", "시가총액"],
        "enterprise_value": ["enterprise_value", "ev"],
        "per": ["per", "p/e"],
        "pbr": ["pbr", "p/b"],
        "psr": ["psr", "p/s"],
        "ev_ebitda": ["ev_ebitda", "ev/ebitda"],
        "ev_sales": ["ev_sales", "ev/sales"],
    })
    if "source" not in df.columns:
        df["source"] = "valuation_peer_input_or_sector_common"
    return df


def _build_assumptions(intake_dir: Path, sector_dir: Path, as_of: pd.Timestamp | None, assumptions: dict[str, Any] | None) -> pd.DataFrame:
    df = pd.DataFrame()
    for p in [intake_dir / "valuation_assumptions.csv", sector_dir / "wacc_assumptions.csv"]:
        df = _read_csv(p)
        if not df.empty:
            break
    df = _filter_asof(df, as_of)
    if df.empty:
        assumptions = assumptions or {}
        df = pd.DataFrame([{
            "as_of_date": str(as_of.date()) if as_of is not None else "",
            "risk_free_rate": assumptions.get("risk_free_rate", pd.NA),
            "market_risk_premium": assumptions.get("market_risk_premium", pd.NA),
            "beta": assumptions.get("beta", pd.NA),
            "cost_of_equity": assumptions.get("cost_of_equity", pd.NA),
            "cost_of_debt": assumptions.get("cost_of_debt", pd.NA),
            "tax_rate": assumptions.get("tax_rate", pd.NA),
            "debt_weight": assumptions.get("debt_weight", pd.NA),
            "equity_weight": assumptions.get("equity_weight", pd.NA),
            "wacc": assumptions.get("wacc", pd.NA),
            "terminal_growth_rate": assumptions.get("terminal_growth_rate", 0.01),
            "forecast_revenue_growth": assumptions.get("forecast_revenue_growth", pd.NA),
            "forecast_op_margin": assumptions.get("forecast_op_margin", pd.NA),
            "forecast_capex_ratio": assumptions.get("forecast_capex_ratio", pd.NA),
            "forecast_wc_ratio": assumptions.get("forecast_wc_ratio", pd.NA),
            "discount_period": assumptions.get("discount_period", 5),
            "source": "valuation_intake_enhancer_defaults_from_manifest",
        }])
    return df


def _latest_price(prices: pd.DataFrame) -> float | None:
    for col in ("close", "adj_close", "price"):
        if col in prices.columns:
            vals = pd.to_numeric(prices[col], errors="coerce").dropna()
            if len(vals):
                return float(vals.iloc[-1])
    return None


def _latest_num(df: pd.DataFrame, cols: list[str]) -> float | None:
    for col in cols:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(vals):
                return float(vals.iloc[-1])
    return None


def _build_dcf_inputs(fin: pd.DataFrame, prices: pd.DataFrame, shares: pd.DataFrame, ass: pd.DataFrame, as_of: pd.Timestamp | None) -> dict[str, Any]:
    current_price = _latest_price(prices)
    fcf = _latest_num(fin, ["fcf", "operating_cash_flow"])
    debt = _latest_num(fin, ["total_debt"])
    cash = _latest_num(fin, ["cash_and_equivalents"])
    shares_count = _latest_num(shares, ["diluted_shares", "common_shares"])
    wacc = _latest_num(ass, ["wacc"])
    tg = _latest_num(ass, ["terminal_growth_rate"])
    discount_period = _latest_num(ass, ["discount_period"])
    fair_price = None
    if fcf is not None and shares_count and shares_count > 0:
        w = wacc if wacc is not None and wacc > 0 else 0.10
        g = tg if tg is not None else 0.01
        n = int(discount_period or 5)
        # Simple conservative FCF perpetuity / finite DCF fallback.
        if w > g:
            terminal = fcf * (1 + g) / (w - g)
            pv_terminal = terminal / ((1 + w) ** max(n, 1))
            pv_fcf = sum((fcf / ((1 + w) ** i)) for i in range(1, max(n, 1) + 1))
            equity_value = pv_fcf + pv_terminal + (cash or 0.0) - (debt or 0.0)
            fair_price = max(equity_value, 0.0) / shares_count
    return {
        "as_of_date": str(as_of.date()) if as_of is not None else "",
        "current_price": current_price,
        "fair_price_base": fair_price,
        "fair_price_diluted": fair_price,
        "fcf_base": fcf,
        "net_debt": None if debt is None and cash is None else (debt or 0.0) - (cash or 0.0),
        "diluted_shares": shares_count,
        "wacc": wacc,
        "terminal_growth_rate": tg,
        "discount_period": discount_period,
        "source": "valuation_intake_enhancer_dcf_fallback",
    }


def _build_relative_inputs(peers: pd.DataFrame, prices: pd.DataFrame, fin: pd.DataFrame, as_of: pd.Timestamp | None) -> dict[str, Any]:
    def median(col: str) -> Any:
        if col not in peers.columns:
            return None
        vals = pd.to_numeric(peers[col], errors="coerce").dropna()
        vals = vals[vals > 0]
        return float(vals.median()) if len(vals) else None
    current = _latest_price(prices)
    market_cap = _latest_num(prices, ["market_cap"])
    revenue = _latest_num(fin, ["revenue"])
    equity = _latest_num(fin, ["equity"])
    ebitda = _latest_num(fin, ["ebitda"])
    debt = _latest_num(fin, ["total_debt"]) or 0.0
    cash = _latest_num(fin, ["cash_and_equivalents"]) or 0.0
    ev = market_cap + debt - cash if market_cap is not None else None
    return {
        "as_of_date": str(as_of.date()) if as_of is not None else "",
        "current_price": current,
        "company_psr": None if not market_cap or not revenue or revenue <= 0 else market_cap / revenue,
        "company_pbr": None if not market_cap or not equity or equity <= 0 else market_cap / equity,
        "company_ev_ebitda": None if not ev or not ebitda or ebitda <= 0 else ev / ebitda,
        "company_ev_sales": None if not ev or not revenue or revenue <= 0 else ev / revenue,
        "peer_median_psr": median("psr"),
        "peer_median_pbr": median("pbr"),
        "peer_median_ev_ebitda": median("ev_ebitda"),
        "peer_median_ev_sales": median("ev_sales"),
        "source": "valuation_intake_enhancer_relative_inputs",
    }


def _build_cross_agent_signals(company_root: Path, as_of: pd.Timestamp | None) -> dict[str, Any]:
    out: dict[str, Any] = {"as_of_date": str(as_of.date()) if as_of is not None else "", "source": "valuation_intake_enhancer_optional_cross_agent_summary"}
    # Only read compact numeric outputs if they already exist; never run other agents here.
    candidates = {
        "tech_signal": [company_root / "tech" / "tech_signal_history.json", company_root / "tech" / "tech_chair_summary.json"],
        "market_signal": [company_root / "market" / "market_signal_history.json", company_root / "market" / "market_result.json"],
        "issue_signal": [company_root / "issue" / "issue_signal_history.json", company_root / "issue" / "issue_result.json"],
        "macro_signal": [company_root / "macro" / "macro_signal_history.json", company_root / "macro" / "macro_result.json"],
    }
    for key, paths in candidates.items():
        for p in paths:
            if not p.exists():
                continue
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                for k in (key, key.replace("_signal", "_score"), "signal", "weighted_signal"):
                    if k in obj and _num(obj.get(k)) is not None:
                        out[key] = _num(obj.get(k))
                        break
                break
            except Exception:
                continue
    return out


def _ensure_sector_templates(sector_dir: Path) -> None:
    sector_dir.mkdir(parents=True, exist_ok=True)
    template_specs = {
        "semiconductor_peer_multiples.csv": COMMON_VALUATION_COLUMNS["peer_multiples.csv"],
        "deeptech_reference_universe.csv": COMMON_VALUATION_COLUMNS["peer_multiples.csv"] + ["reference_group", "technology_theme"],
        "wacc_assumptions.csv": COMMON_VALUATION_COLUMNS["valuation_assumptions.csv"],
        "sector_growth_assumptions.csv": ["as_of_date", "sector", "vc_role", "revenue_growth", "op_margin", "capex_ratio", "source"],
    }
    for name, cols in template_specs.items():
        path = sector_dir / name
        if not path.exists():
            _write_csv(path, pd.DataFrame(columns=cols), cols)
    cfg = sector_dir / "valuation_methodology_config.yaml"
    if not cfg.exists():
        cfg.write_text(
            "methodology: src_eval valuation history evaluation\n"
            "classification: vc_role based peer selection\n"
            "signal_blocks:\n"
            "  - intrinsic_value_signal\n"
            "  - relative_value_signal\n"
            "  - financial_quality_signal\n"
            "  - price_position_signal\n"
            "  - dilution_penalty\n"
            "  - discount_rate_pressure\n"
            "  - cross_agent_assumption_signal\n"
            "note: final Buy/Hold/Sell decision is produced by DMA/probability tensor, not fixed thresholds.\n",
            encoding="utf-8",
        )


def enhance_valuation_intake_outputs(
    *,
    intake_dir: Path,
    valuation_dir: Path,
    company: str,
    company_dir: str,
    field: str,
    target: Any,
    manifest: dict[str, Any],
    price_summary: dict[str, Any] | None = None,
    share_summary: dict[str, Any] | None = None,
    assumptions: dict[str, Any] | None = None,
    reference_summary: dict[str, Any] | None = None,
    diagnostics: list[str] | None = None,
) -> dict[str, Any]:
    as_of = _env_as_of()
    company_root = valuation_dir.parent
    sector_dir = valuation_dir.parents[1] / "_sector_common" / "valuation"
    _ensure_sector_templates(sector_dir)

    fin = _normalize_financials(intake_dir, as_of)
    prices = _normalize_prices(intake_dir, as_of)
    shares = _normalize_shares(intake_dir, prices, as_of, share_summary)
    dilution = _build_dilution_events(shares, intake_dir, as_of)
    peers = _normalize_peers(intake_dir, sector_dir, as_of)
    ass = _build_assumptions(intake_dir, sector_dir, as_of, assumptions)

    # Stable intake aliases requested by the evaluation pipeline.
    _write_csv(intake_dir / "financials_raw.csv", _read_csv(intake_dir / "valuation_raw_dart_accounts.csv"), COMMON_VALUATION_COLUMNS["financials_normalized.csv"])
    _write_csv(intake_dir / "financials_normalized.csv", fin, COMMON_VALUATION_COLUMNS["financials_normalized.csv"])
    _write_csv(intake_dir / "price_history.csv", prices, COMMON_VALUATION_COLUMNS["price_history.csv"])
    _write_csv(intake_dir / "shares_outstanding.csv", shares, COMMON_VALUATION_COLUMNS["shares_outstanding.csv"])
    _write_csv(intake_dir / "dilution_events.csv", dilution, COMMON_VALUATION_COLUMNS["dilution_events.csv"])
    _write_csv(intake_dir / "peer_multiples.csv", peers, COMMON_VALUATION_COLUMNS["peer_multiples.csv"])
    _write_csv(intake_dir / "valuation_assumptions.csv", ass, COMMON_VALUATION_COLUMNS["valuation_assumptions.csv"])

    profile = {
        "company_name": company,
        "slug": company_dir,
        "ticker": getattr(target, "ticker", "") or getattr(target, "stock_code", ""),
        "market": getattr(target, "market", ""),
        "field": field,
        "sector": "semiconductor" if field == "반도체" else field,
        "vc_role": getattr(target, "vc_role", ""),
        "currency": "KRW",
        "as_of_date": str(as_of.date()) if as_of is not None else "",
    }
    _json_dump(intake_dir / "company_profile.json", profile)
    _json_dump(intake_dir / "dcf_inputs.json", _build_dcf_inputs(fin, prices, shares, ass, as_of))
    _json_dump(intake_dir / "relative_valuation_inputs.json", _build_relative_inputs(peers, prices, fin, as_of))
    _json_dump(intake_dir / "cross_agent_signals_for_valuation.json", _build_cross_agent_signals(company_root, as_of))

    manifest = dict(manifest or {})
    manifest.setdefault("as_of_date", str(as_of.date()) if as_of is not None else "")
    manifest["eval_valuation_enhancer"] = {
        "version": "v35",
        "as_of_date": str(as_of.date()) if as_of is not None else "",
        "intake_files": [
            "company_profile.json", "financials_raw.csv", "financials_normalized.csv", "price_history.csv",
            "shares_outstanding.csv", "dilution_events.csv", "valuation_assumptions.csv", "peer_multiples.csv",
            "dcf_inputs.json", "relative_valuation_inputs.json", "cross_agent_signals_for_valuation.json",
        ],
        "row_counts": {
            "financials_normalized": int(len(fin)),
            "price_history": int(len(prices)),
            "shares_outstanding": int(len(shares)),
            "dilution_events": int(len(dilution)),
            "peer_multiples": int(len(peers)),
            "valuation_assumptions": int(len(ass)),
        },
        "sector_common_dir": str(sector_dir),
        "notes": [
            "All dated rows are filtered to VALUATION_AS_OF_DATE / ALPHAPROVE_DATA_CUTOFF_DATE when provided.",
            "No Buy/Hold/Sell thresholds are applied here; only continuous feature signals are prepared.",
        ],
    }
    if diagnostics is not None:
        diagnostics.append("[valuation-eval-v35] enhanced valuation intake aliases and signal input files generated")
    _json_dump(intake_dir / "valuation_intake_manifest.json", manifest)
    return manifest

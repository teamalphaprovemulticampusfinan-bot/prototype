from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def read_universe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str)


def choose_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lowered = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lowered:
            return lowered[n.lower()]
    for c in df.columns:
        lc = c.lower()
        if any(n.lower() in lc for n in names):
            return c
    return None


def role_prior(role: str) -> dict[str, float]:
    r = str(role or "").lower()
    out = {
        "fx_export_sensitivity": 0.20,
        "fx_cost_sensitivity": 0.20,
        "fx_debt_sensitivity": 0.10,
        "interest_debt_sensitivity": 0.45,
        "liquidity_funding_sensitivity": 0.45,
        "semiconductor_cycle_beta": 1.00,
        "commodity_cost_sensitivity": 0.25,
    }
    if any(k in r for k in ["장비", "후공정", "패키징", "테스트", "osat"]):
        out.update({"fx_export_sensitivity": 0.35, "fx_cost_sensitivity": 0.25, "semiconductor_cycle_beta": 1.15})
    if any(k in r for k in ["소재", "부품", "material", "chemical"]):
        out.update({"fx_export_sensitivity": 0.25, "fx_cost_sensitivity": 0.40, "commodity_cost_sensitivity": 0.45, "semiconductor_cycle_beta": 0.95})
    if any(k in r for k in ["파운드리", "제조", "foundry", "fab"]):
        out.update({"fx_export_sensitivity": 0.30, "fx_cost_sensitivity": 0.30, "semiconductor_cycle_beta": 1.05})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Create evaluation Macro Agent sensitivity/template files.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--universe-csv", default="")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    root = Path.cwd()
    macro_dir = root / "data" / "_global_common" / "macro"
    macro_dir.mkdir(parents=True, exist_ok=True)
    sector_macro_dir = root / "data" / args.field / "_sector_common" / "macro"
    sector_macro_dir.mkdir(parents=True, exist_ok=True)

    universe_path = Path(args.universe_csv) if args.universe_csv else root / "data" / args.field / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"
    uni = read_universe(universe_path)
    rows = []
    if not uni.empty:
        company_col = choose_col(uni, ["company", "company_name", "기업명", "name"])
        slug_col = choose_col(uni, ["company_dir", "slug"])
        ticker_col = choose_col(uni, ["ticker", "stock_code", "종목코드", "code"])
        role_col = choose_col(uni, ["vc_role", "role", "value_chain", "분류"])
        for _, r in uni.iterrows():
            company = str(r.get(company_col, "") if company_col else "")
            slug = str(r.get(slug_col, "") if slug_col else "")
            ticker = str(r.get(ticker_col, "") if ticker_col else "")
            vc_role = str(r.get(role_col, "") if role_col else "")
            prior = role_prior(vc_role)
            rows.append({
                "company_dir": slug,
                "company": company,
                "ticker": ticker,
                "stock_code": ticker,
                "field": args.field,
                "vc_role": vc_role,
                **prior,
                "source_note": "initial vc_role prior; replace with DART/IR/export/import/debt evidence when available",
            })
    if not rows:
        rows = [{
            "company_dir": "nepes",
            "company": "네패스",
            "ticker": "033640",
            "stock_code": "033640",
            "field": args.field,
            "vc_role": "후공정/패키징/테스트",
            **role_prior("후공정/패키징/테스트"),
            "source_note": "sample row; fill with company-level export/import/fx-debt evidence",
        }]

    df = pd.DataFrame(rows)
    for out in [macro_dir / "company_macro_sensitivity_template.csv", sector_macro_dir / "company_macro_sensitivity_template.csv"]:
        if out.exists() and not args.overwrite:
            print(f"[SKIP] exists: {out}")
            continue
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"[OK] wrote: {out} rows={len(df)}")

    config_path = macro_dir / "macro_signal_methodology_v36.json"
    if args.overwrite or not config_path.exists():
        config_path.write_text(
            '{\n'
            '  "macro_data_dir": "data/_global_common/macro",\n'
            '  "as_of_policy": "Use only rows with date <= MACRO_AS_OF_DATE / ALPHAPROVE_DATA_CUTOFF_DATE",\n'
            '  "core_factors": ["interest_rate", "yield_curve", "credit_liquidity", "fx_exposure", "inflation_commodity", "business_cycle", "market_risk", "semiconductor_cycle"],\n'
            '  "event_overlay_clip": [-0.20, 0.10],\n'
            '  "papers": ["Chen Roll Ross 1986", "Estrella Hardouvelis 1991", "Fama Schwert 1977", "Jorion 1990", "Han 2017", "Aubry Renou-Maissant 2014", "Liu Chung Chang 2013", "Baker Bloom Davis 2016", "Glasserman Lin 2023"]\n'
            '}\n',
            encoding="utf-8",
        )
        print(f"[OK] wrote: {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

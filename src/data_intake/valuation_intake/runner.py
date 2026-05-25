from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from common.data_paths import company_agent_dir, rel_project_path, write_json
from data_intake.valuation_intake.eval_enhancer import enhance_valuation_intake_outputs

from .blueprints import CANONICAL_WORKBOOK_TABS, archetype_catalog_records
from .reference_universe import export_reference_universe
from .sources import (
    COMPANY_REGISTRY,
    compute_price_summary,
    enrich_price_history,
    fetch_dart_financial_accounts,
    fetch_dart_share_counts,
    fetch_price_history,
    fetch_naver_market_snapshot,
    enrich_market_snapshot_with_derived_metrics,
    latest_share_count,
    load_local_financial_fallback,
    load_local_price_fallback,
    merge_financial_rows,
    merge_price_rows,
    normalize_dart_accounts,
    resolve_company,
    valuation_date_range,
    write_csv,
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_dump(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path



def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _has_price_rows(rows: list[dict[str, Any]]) -> bool:
    for r in rows:
        if str(r.get("date") or "").strip() and str(r.get("close") or "").strip() not in {"", "None", "nan"}:
            return True
    return False



def _augment_price_rows_with_share_metrics(rows: list[dict[str, Any]], shares_outstanding: Any) -> list[dict[str, Any]]:
    try:
        shares = float(shares_outstanding) if shares_outstanding not in (None, "") else None
    except Exception:
        shares = None
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        try:
            close = float(row.get("close")) if row.get("close") not in (None, "") else None
        except Exception:
            close = None
        try:
            volume = float(row.get("volume")) if row.get("volume") not in (None, "") else None
        except Exception:
            volume = None
        if shares is not None:
            row["shares_outstanding"] = shares
        if close is not None and shares is not None:
            row["market_cap"] = close * shares
        if close is not None and volume is not None:
            row["trading_value"] = close * volume
        if volume is not None and shares not in (None, 0):
            row["turnover_ratio"] = volume / shares
        out.append(row)
    return out

def _valuation_dirs(company_dir: str) -> tuple[Path, Path]:
    valuation_dir = company_agent_dir(company_dir, "valuation", create=True)
    intake_dir = valuation_dir / "intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    return valuation_dir, intake_dir


def _default_assumptions(company_dir: str, company: str, price_summary: dict[str, Any], share_summary: dict[str, Any]) -> dict[str, Any]:
    vol = price_summary.get("volatility_annualized")
    beta_proxy = None
    try:
        if vol is not None:
            beta_proxy = min(1.8, max(0.7, float(vol) / 0.25))
    except Exception:
        beta_proxy = None
    shares = share_summary.get("shares_outstanding") or price_summary.get("shares_outstanding")
    return {
        "company_dir": company_dir,
        "company": company,
        "created_at": _now(),
        "source": "valuation_intake_default_assumptions",
        "currency": "KRW",
        "units": "KRW actuals; workbook shows KRW mm / 억원 where noted",
        "risk_free_rate": float(os.getenv("VALUATION_RISK_FREE_RATE", "0.035")),
        "market_risk_premium": float(os.getenv("VALUATION_MARKET_RISK_PREMIUM", "0.060")),
        "beta": beta_proxy if beta_proxy is not None else float(os.getenv("VALUATION_DEFAULT_BETA", "1.10")),
        "pre_tax_cost_of_debt": float(os.getenv("VALUATION_PRETAX_COST_OF_DEBT", "0.055")),
        "tax_rate": float(os.getenv("VALUATION_TAX_RATE", "0.24")),
        "terminal_growth_rate": float(os.getenv("VALUATION_TERMINAL_GROWTH", "0.015")),
        "projection_years": int(os.getenv("VALUATION_PROJECTION_YEARS", "5")),
        "scenario_growth_delta": 0.02,
        "scenario_wacc_delta": 0.01,
        "latest_close": price_summary.get("latest_close"),
        "shares_outstanding": shares,
        "market_cap": price_summary.get("market_cap"),
        "share_count_year": share_summary.get("share_count_year"),
        "share_count_source": share_summary.get("share_count_source"),
        "notes": [
            "Valuation Agent는 finance_agent 산출물을 읽지 않고 자체 intake 데이터만 사용합니다.",
            "DART/가격/발행주식 수 데이터가 부족하면 validation에서 WARN을 표시합니다.",
            "기업별 *_valuation_workbook.xlsx 파일은 intake/agent 실행 중 생성·수정·덮어쓰기 하지 않습니다.",
            "업로드한 파이낸셜 모델링 파일은 런타임 데이터 소스가 아니라 workbook archetype 설계로 코드화되었습니다.",
        ],
    }


def _build_peer_rows(
    target: str,
    years: int,
    skip_network: bool,
    diagnostics: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    registry_items = list(COMPANY_REGISTRY.items())

    def build_one(slug: str, item: Any) -> tuple[str, dict[str, Any], list[str]]:
        peer_diag: list[str] = []
        raw: list[dict[str, Any]] = []
        normalized: list[dict[str, Any]] = []
        prices: list[dict[str, Any]] = []
        share_rows: list[dict[str, Any]] = []
        if not skip_network:
            raw = fetch_dart_financial_accounts(item, years=min(years, 3), diagnostics=peer_diag, start_date=start_date, end_date=end_date)
            normalized = normalize_dart_accounts(raw)
            fallback_financials = load_local_financial_fallback(item, start_date=start_date, end_date=end_date, diagnostics=peer_diag)
            normalized = merge_financial_rows(normalized, fallback_financials, diagnostics=peer_diag)
            prices_live = enrich_price_history(fetch_price_history(item, years=min(years, 3), diagnostics=peer_diag, start_date=start_date, end_date=end_date))
            prices = merge_price_rows(prices_live, load_local_price_fallback(item, start_date=start_date, end_date=end_date, diagnostics=peer_diag), diagnostics=peer_diag)
            share_rows = fetch_dart_share_counts(item, years=min(years, 3), diagnostics=peer_diag, start_date=start_date, end_date=end_date)
        share_summary = latest_share_count(share_rows)
        price_summary = compute_price_summary(prices, share_summary.get("shares_outstanding"))
        latest = normalized[-1] if normalized else {}
        latest_close = price_summary.get("latest_close")
        shares = share_summary.get("shares_outstanding")
        market_cap = price_summary.get("market_cap")
        revenue = latest.get("revenue")
        net_income = latest.get("net_income")
        equity = latest.get("equity")
        row = {
            "company_dir": slug,
            "company": item.name,
            "stock_code": item.stock_code,
            "market": item.market,
            "is_target": slug == target,
            "latest_year": latest.get("year"),
            "latest_close": latest_close,
            "shares_outstanding": shares,
            "market_cap": market_cap,
            "revenue": revenue,
            "operating_profit": latest.get("operating_profit"),
            "net_income": net_income,
            "assets": latest.get("assets"),
            "liabilities": latest.get("liabilities"),
            "equity": equity,
            "fcf": latest.get("fcf"),
            "fcf_margin": (latest.get("fcf") / revenue) if latest.get("fcf") is not None and revenue not in (None, 0) else None,
            "return_1y": price_summary.get("return_1y"),
            "volatility_annualized": price_summary.get("volatility_annualized"),
            "mdd": price_summary.get("mdd"),
            "high_52w": price_summary.get("high_52w"),
            "low_52w": price_summary.get("low_52w"),
            "data_status": "OK" if latest or latest_close is not None else "WARN_NO_LIVE_DATA",
            "diagnostics": " | ".join(peer_diag[-3:]),
        }
        return slug, row, peer_diag

    if not registry_items:
        return []

    try:
        worker_count = int(os.getenv("VALUATION_PEER_WORKERS", "4") or "4")
    except Exception:
        worker_count = 4
    worker_count = max(1, min(worker_count, len(registry_items)))

    if worker_count == 1 or len(registry_items) == 1:
        rows: list[dict[str, Any]] = []
        for slug, item in registry_items:
            peer_slug, row, peer_diag = build_one(slug, item)
            rows.append(row)
            if peer_diag:
                diagnostics.extend([f"peer:{peer_slug}: {x}" for x in peer_diag[-2:]])
        return rows

    print(f"[Valuation Intake] peer rows 병렬 수집: max_workers={worker_count}")
    ordered: list[dict[str, Any] | None] = [None] * len(registry_items)
    peer_logs: list[tuple[int, str, list[str]]] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(build_one, slug, item): (idx, slug)
            for idx, (slug, item) in enumerate(registry_items)
        }
        for future in as_completed(future_map):
            idx, fallback_slug = future_map[future]
            try:
                peer_slug, row, peer_diag = future.result()
            except Exception as exc:
                item = registry_items[idx][1]
                peer_slug = fallback_slug
                peer_diag = [f"peer collection exception: {exc}"]
                row = {
                    "company_dir": fallback_slug,
                    "company": item.name,
                    "stock_code": item.stock_code,
                    "market": item.market,
                    "is_target": fallback_slug == target,
                    "data_status": "WARN_PEER_COLLECTION_EXCEPTION",
                    "diagnostics": peer_diag[-1],
                }
            ordered[idx] = row
            peer_logs.append((idx, peer_slug or fallback_slug, peer_diag))

    for _, peer_slug, peer_diag in sorted(peer_logs, key=lambda x: x[0]):
        if peer_diag:
            diagnostics.extend([f"peer:{peer_slug}: {x}" for x in peer_diag[-2:]])

    rows = [row for row in ordered if isinstance(row, dict)]
    return rows


def run_valuation_intake(
    *,
    company_dir: str,
    company: str,
    field: str = "반도체",
    years: int = 5,
    skip_network: bool = False,
    force_fetch: bool = False,
    continue_on_error: bool = True,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    del force_fetch
    target = resolve_company(company_dir, company)
    valuation_dir, intake_dir = _valuation_dirs(target.slug)
    diagnostics: list[str] = []
    started_at = _now()

    print(f"[Valuation Intake] 시작: {target.name} / {target.slug}")
    print(f"[Valuation Intake] output_dir={valuation_dir}")
    range_start, range_end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
    start_date = range_start.isoformat()
    end_date = range_end.isoformat()
    print(f"[Valuation Intake] skip_network={skip_network}, years={years}")
    print(f"[Valuation Intake] collection_range={start_date} ~ {end_date}")

    template_records = archetype_catalog_records()
    template_csv = intake_dir / "valuation_modeling_template_catalog.csv"
    write_csv(template_csv, template_records)
    template_json = _json_dump(intake_dir / "valuation_modeling_template_catalog.json", template_records)

    reference_pack = export_reference_universe(
        intake_dir,
        company=target.name,
        company_dir=target.slug,
        stock_code=target.stock_code,
        field=field,
        max_focus_rows=int(os.getenv("VALUATION_REFERENCE_FOCUS_ROWS", "40")),
    )
    reference_summary = reference_pack.get("summary") or {}

    raw_accounts: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    prices: list[dict[str, Any]] = []
    share_rows: list[dict[str, Any]] = []
    peer_rows: list[dict[str, Any]] = []
    market_snapshot: dict[str, Any] = {}

    try:
        if not skip_network:
            raw_accounts = fetch_dart_financial_accounts(target, years=years, diagnostics=diagnostics, start_date=start_date, end_date=end_date)
            normalized = normalize_dart_accounts(raw_accounts)
            fallback_financials = load_local_financial_fallback(target, start_date=start_date, end_date=end_date, diagnostics=diagnostics)
            normalized = merge_financial_rows(normalized, fallback_financials, diagnostics=diagnostics)
            live_prices = enrich_price_history(fetch_price_history(target, years=years, diagnostics=diagnostics, start_date=start_date, end_date=end_date))
            local_prices = load_local_price_fallback(target, start_date=start_date, end_date=end_date, diagnostics=diagnostics)
            prices = merge_price_rows(live_prices, local_prices, diagnostics=diagnostics)
            share_rows = fetch_dart_share_counts(target, years=years, diagnostics=diagnostics, start_date=start_date, end_date=end_date)
            market_snapshot = fetch_naver_market_snapshot(target, diagnostics=diagnostics)
            peer_rows = _build_peer_rows(target.slug, years=years, skip_network=False, diagnostics=diagnostics, start_date=start_date, end_date=end_date)
        else:
            diagnostics.append("skip_network=True: live DART/price collection skipped by user option.")
            fallback_financials = load_local_financial_fallback(target, start_date=start_date, end_date=end_date, diagnostics=diagnostics)
            normalized = merge_financial_rows(normalized, fallback_financials, diagnostics=diagnostics)
            local_prices = load_local_price_fallback(target, start_date=start_date, end_date=end_date, diagnostics=diagnostics)
            prices = merge_price_rows(prices, local_prices, diagnostics=diagnostics)
            peer_rows = _build_peer_rows(target.slug, years=years, skip_network=True, diagnostics=diagnostics, start_date=start_date, end_date=end_date)
    except Exception as exc:
        diagnostics.append(f"valuation live intake exception: {exc}")
        if not continue_on_error:
            raise

    # 가격 데이터는 valuation workbook/dashboard 품질에 중요하므로,
    # 일시적인 Yahoo/Naver 장애로 0건이 반환되면 이전에 성공한 valuation 전용
    # intake CSV를 보존해 사용한다. finance/market agent 산출물은 읽지 않는다.
    if not _has_price_rows(prices):
        existing_price_rows = _read_csv_rows(intake_dir / "valuation_price_history.csv")
        if _has_price_rows(existing_price_rows):
            diagnostics.append(
                f"Live price providers returned 0 rows; reused existing valuation_price_history.csv rows={len(existing_price_rows)}."
            )
            prices = enrich_price_history(existing_price_rows)

    share_summary = latest_share_count(share_rows)
    prices = _augment_price_rows_with_share_metrics(prices, share_summary.get("shares_outstanding"))
    price_summary = compute_price_summary(prices, share_summary.get("shares_outstanding"))
    latest_financial = sorted(normalized, key=lambda r: str(r.get("year") or ""))[-1] if normalized else {}
    market_snapshot = enrich_market_snapshot_with_derived_metrics(
        target,
        latest_financial=latest_financial,
        price_summary=price_summary,
        market_snapshot=market_snapshot,
        diagnostics=diagnostics,
    )
    assumptions = _default_assumptions(target.slug, target.name, price_summary, share_summary)

    raw_path = write_csv(intake_dir / "valuation_raw_dart_accounts.csv", raw_accounts)
    normalized_path = write_csv(
        intake_dir / "valuation_normalized_financials.csv",
        normalized,
        fieldnames=[
            "year", "revenue", "operating_profit", "net_income", "assets", "liabilities", "equity", "cash",
            "cfo", "capex", "fcf", "investing_cf", "source_account_count",
            "revenue_source_account", "operating_profit_source_account", "net_income_source_account",
            "assets_source_account", "liabilities_source_account", "equity_source_account",
            "cfo_source_account", "capex_source_account", "cash_source_account",
        ],
    )
    price_path = write_csv(
        intake_dir / "valuation_price_history.csv",
        prices,
        fieldnames=[
            "date", "open", "high", "low", "close", "adj_close", "volume", "daily_return", "drawdown",
            "ma20", "ma60", "ma120", "rolling_vol_20", "rolling_vol_60", "return_20d", "return_60d",
            "return_120d", "distance_to_ma20", "distance_to_ma60", "distance_to_ma120",
            "rolling_high_52w", "rolling_low_52w", "price_to_52w_high", "price_to_52w_low",
            "shares_outstanding", "market_cap", "trading_value", "trading_value_ma20", "turnover_ratio", "source", "ticker",
        ],
    )
    shares_path = write_csv(intake_dir / "valuation_share_count.csv", share_rows)
    price_summary_path = _json_dump(intake_dir / "valuation_price_summary.json", price_summary)
    market_snapshot_path = _json_dump(intake_dir / "valuation_market_snapshot.json", market_snapshot)
    market_snapshot_csv = write_csv(intake_dir / "valuation_market_snapshot.csv", [market_snapshot] if market_snapshot else [{"status": "보조 투자지표 수집값 없음", "source": "naver_finance_item_main"}])
    peer_path = write_csv(intake_dir / "valuation_peer_input.csv", peer_rows)
    assumptions_path = _json_dump(intake_dir / "valuation_assumptions.json", assumptions)
    source_map = {
        "created_at": _now(),
        "company": target.name,
        "company_dir": target.slug,
        "stock_code": target.stock_code,
        "principle": "independent_valuation_agent_intake_only; does not read finance_agent outputs",
        "template_design_seed": "uploaded_financial_modeling_packs_distilled_to_blueprints",
        "canonical_workbook_tabs": CANONICAL_WORKBOOK_TABS,
        "files": {
            "template_catalog_csv": rel_project_path(template_csv),
            "template_catalog_json": rel_project_path(template_json),
            "eval_price_history_v45_csv": rel_project_path(intake_dir / "eval_price_history_v45.csv"),
            "raw_dart_accounts_csv": rel_project_path(raw_path),
            "normalized_financials_csv": rel_project_path(normalized_path),
            "price_history_csv": rel_project_path(price_path),
            "share_count_csv": rel_project_path(shares_path),
            "price_summary_json": rel_project_path(price_summary_path),
            "market_snapshot_json": rel_project_path(market_snapshot_path),
            "market_snapshot_csv": rel_project_path(market_snapshot_csv),
            "peer_input_csv": rel_project_path(peer_path),
            "assumptions_json": rel_project_path(assumptions_path),
            "reference_universe_208_csv": rel_project_path(reference_pack.get("all_path")),
            "reference_universe_focus_csv": rel_project_path(reference_pack.get("focus_path")),
            "reference_universe_summary_json": rel_project_path(reference_pack.get("summary_path")),
        },
        "recognized_input_policy": {
            "company_intake_files": [
                "valuation/intake/eval_price_history_v45.csv",
                "valuation/intake/valuation_market_snapshot.csv",
                "valuation/intake/valuation_price_history.csv",
                "valuation/intake/valuation_raw_dart_accounts.csv",
                "valuation/intake/valuation_share_count.csv",
            ],
            "sector_common_files": [
                "_sector_common/valuation/sector_growth_assumptions.csv",
                "_sector_common/valuation/semiconductor_peer_multiples.csv",
                "_sector_common/valuation/wacc_assumptions.csv",
            ],
            "workbook_xlsx_policy": "Do not create, overwrite, or modify *_valuation_workbook.xlsx during intake.",
        },
        "diagnostics": diagnostics,
    }
    source_map_path = _json_dump(intake_dir / "valuation_source_map.json", source_map)
    manifest = {
        "pipeline": "valuation_intake",
        "status": "OK" if normalized or prices else "WARN_NO_LIVE_DATA",
        "created_at": _now(),
        "started_at": started_at,
        "company": target.name,
        "company_dir": target.slug,
        "skip_network": skip_network,
        "years": years,
        "start_date": start_date,
        "end_date": end_date,
        "collection_range": {"start_date": start_date, "end_date": end_date},
        "outputs": {
            "intake_dir": rel_project_path(intake_dir),
            "valuation_source_map": rel_project_path(source_map_path),
            **source_map["files"],
        },
        "counts": {
            "raw_dart_accounts": len(raw_accounts),
            "normalized_financial_years": len(normalized),
            "price_rows": len(prices),
            "share_count_rows": len(share_rows),
            "market_snapshot_metric_count": int(market_snapshot.get("available_metric_count") or 0) if isinstance(market_snapshot, dict) else 0,
            "peer_rows": len(peer_rows),
            "reference_universe_rows": int(reference_summary.get("reference_universe_rows") or 0),
            "reference_focus_rows": int(reference_summary.get("focus_rows") or 0),
            "template_archetypes": len(template_records),
        },
        "price_summary": price_summary,
        "share_summary": share_summary,
        "reference_universe_summary": reference_summary,
        "diagnostics": diagnostics[-30:],
    }
    try:
        manifest = enhance_valuation_intake_outputs(
            intake_dir=intake_dir,
            valuation_dir=valuation_dir,
            company=target.name,
            company_dir=target.slug,
            field=field,
            target=target,
            manifest=manifest,
            price_summary=price_summary,
            share_summary=share_summary,
            assumptions=assumptions,
            reference_summary=reference_summary,
            diagnostics=diagnostics,
        )
    except Exception as exc:
        diagnostics.append(f"[valuation-eval-v35] enhancer skipped: {exc}")
        manifest["diagnostics"] = diagnostics[-30:]

    manifest_path = _json_dump(intake_dir / "valuation_intake_manifest.json", manifest)
    print(f"[Valuation Intake] manifest 저장: {manifest_path}")
    print(f"[Valuation Intake] status={manifest['status']}, counts={manifest['counts']}")
    if manifest["counts"].get("raw_dart_accounts", 0) == 0:
        print("[Valuation Intake] DART 재무제표 수집 0건: 최근 diagnostics를 확인하세요.")
        for msg in diagnostics[-8:]:
            print(f"  - {msg}")
    if manifest["counts"].get("price_rows", 0) == 0:
        print("[Valuation Intake] 주가 데이터 수집 0건: 가격 provider diagnostics를 확인하세요.")
        for msg in [m for m in diagnostics if "price" in m.lower() or "yfinance" in m.lower() or "naver" in m.lower() or "yahoo" in m.lower()][-12:]:
            print(f"  - {msg}")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run independent live intake for Valuation Agent.")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--start", dest="start_date", default=os.getenv("VALUATION_START_DATE", "2021-01-01"))
    parser.add_argument("--end", dest="end_date", default=os.getenv("VALUATION_END_DATE") or os.getenv("VALUATION_AS_OF_DATE") or os.getenv("ALPHAPROVE_DATA_CUTOFF_DATE"))
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args(argv)
    run_valuation_intake(
        company_dir=args.company_dir,
        company=args.company,
        field=args.field,
        years=args.years,
        skip_network=args.skip_network,
        force_fetch=args.force_fetch,
        continue_on_error=not args.stop_on_error,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

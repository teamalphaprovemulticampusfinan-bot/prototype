from __future__ import annotations

"""Export Google Sheets Chair/Auditor run results to a wide signal CSV.

Output columns start with the requested identity and agent signal fields:
date, field, company, ticker, stock_code, recommendation, weighted_signal,
as_of_date, signal_source, then for every agent:
agent_signal, agent_weighted_signal, agent_recommendation, agent_weight.

Additional realized-return columns are appended when local objective price data
exist.  These columns make the exported CSV usable as ALPHAPROVE_DMA_HISTORY_CSV
for the next run without writing any history result into data/<field>/<company>
agent folders.
"""

import argparse
import calendar
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.agent_history import list_agent_snapshots, list_run_results  # noqa: E402

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def _ensure_sheets_env() -> None:
    os.environ.setdefault("ALPHAPROVE_HISTORY_BACKEND", "sheets")


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            obj = json.loads(value)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _deep_find_qd(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        if isinstance(obj.get("quantitative_decision"), dict):
            return obj["quantitative_decision"]
        for key in ("auditor_result", "final_validation", "final_round", "result"):
            found = _deep_find_qd(obj.get(key))
            if found:
                return found
        for v in obj.values():
            found = _deep_find_qd(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _deep_find_qd(v)
            if found:
                return found
    return {}


def _payload_from_result(row: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(row.get("payload"))


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).replace(",", "").replace("%", "").strip()
        if not text or text.lower() in {"nan", "none", "null", "na", "n/a"}:
            return None
        return float(text)
    except Exception:
        return None


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt != "%Y%m%d" else text[:8], fmt)
        except Exception:
            pass
    return None


def _read_csv_rows(path: Path, limit: int = 200000) -> list[dict[str, Any]]:
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))[-limit:]
        except Exception:
            continue
    return []


def _norm_code(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    text = text.replace("'", "").replace('"', "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits and len(digits) <= 6:
        return digits.zfill(6)
    if len(text) == 6 and text.isdigit():
        return text
    return text


def _first(row: dict[str, Any], names: tuple[str, ...]) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _read_universe_identity(path: Path | None) -> dict[str, dict[str, str]]:
    if not path or not path.exists():
        return {}
    rows = _read_csv_rows(path)
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        company_dir = _first(row, ("company_dir", "slug", "company_slug", "폴더", "folder"))
        company = _first(row, ("company", "company_name", "name", "기업명", "회사명"))
        stock_code = _norm_code(_first(row, ("stock_code", "ticker6", "종목코드", "단축코드", "code", "ticker", "symbol")))
        market = _first(row, ("market", "시장", "거래소"))
        ticker = stock_code or _first(row, ("ticker", "symbol", "ticker6"))
        item = {"company_dir": company_dir, "company": company, "stock_code": stock_code, "ticker": ticker, "market": market}
        for key in (company_dir, company, stock_code):
            if key:
                out[str(key)] = item
    return out


def _signal_to_recommendation(value: Any) -> str:
    """Deprecated compatibility stub.

    History exports must not recreate 매수/보유/매도 from weighted_signal
    sign or magnitude.  The final recommendation must come from
    quantitative_decision.final_recommendation or its DMA label posterior model.
    """
    return ""


def _recommendation_from_quantitative_decision(qd: dict[str, Any]) -> str:
    """Extract recommendation without applying a numeric signal cutoff."""
    if not isinstance(qd, dict):
        return ""
    for key in ("final_recommendation", "base_recommendation", "recommendation"):
        label = str(qd.get(key) or "").strip()
        if label:
            return label

    model = qd.get("label_posterior_model")
    if isinstance(model, dict):
        for key in ("final_recommendation", "realized_calibrated_final_recommendation"):
            label = str(model.get(key) or "").strip()
            if label:
                return label
        posterior = model.get("label_posterior") or model.get("current_label_posterior")
        if isinstance(posterior, dict) and posterior:
            order = {"보유": 0, "매수": 1, "매도": 2}
            return sorted(
                [str(k) for k in posterior.keys()],
                key=lambda lab: (-(float(posterior.get(lab) or 0.0)), order.get(lab, 99)),
            )[0]

    return ""


def _company_identity(as_of_date: str, field: str, company_dir: str, fallback_company: str, universe: dict[str, dict[str, str]]) -> dict[str, str]:
    uni = universe.get(company_dir) or universe.get(fallback_company) or {}
    snaps = list_agent_snapshots(as_of_date=as_of_date, field=field, company_dir=company_dir)
    company = str(uni.get("company") or fallback_company or company_dir)
    stock_code = _norm_code(uni.get("stock_code"))
    ticker = _norm_code(uni.get("ticker")) or stock_code
    market = str(uni.get("market") or "")
    for snap in snaps:
        if snap.get("company_name") and not company:
            company = str(snap.get("company_name"))
        payload = _as_dict(snap.get("payload"))
        stock_code = stock_code or _norm_code(payload.get("stock_code") or payload.get("code") or payload.get("ticker6"))
        raw_ticker = payload.get("ticker") or payload.get("symbol")
        if raw_ticker and not ticker:
            ticker = str(raw_ticker).strip()
    if not ticker:
        ticker = stock_code
    return {"company": company, "ticker": ticker, "stock_code": stock_code, "market": market}


def _candidate_price_files(field: str, company: str, company_dir: str) -> list[Path]:
    base = PROJECT_ROOT / "data" / field
    candidates = [
        base / company / "valuation" / "intake" / "valuation_price_history.csv",
        base / company_dir / "valuation" / "intake" / "valuation_price_history.csv",
        base / company / "finance" / f"{company}_stock.csv",
        base / company_dir / "finance" / f"{company}_stock.csv",
    ]
    for root_name in (company, company_dir):
        root = base / root_name
        if root.exists():
            candidates.extend(root.glob("finance/*_stock.csv"))
            candidates.extend(root.glob("valuation/intake/*price*.csv"))
    return [p for p in candidates if p.exists() and p.stat().st_size > 0]


def _price_points(field: str, company: str, company_dir: str) -> list[tuple[datetime, float]]:
    points: list[tuple[datetime, float]] = []
    for path in _candidate_price_files(field, company, company_dir):
        for row in _read_csv_rows(path):
            date = _parse_date(row.get("date") or row.get("날짜") or row.get("일자"))
            price = None
            for col in ("adj_close", "close", "종가", "수정종가", "Adj Close", "Close"):
                price = _to_float(row.get(col))
                if price is not None and price > 0:
                    break
            if date is not None and price is not None and price > 0:
                points.append((date, float(price)))
        if points:
            break
    points = sorted(set(points), key=lambda x: x[0])
    return points


def _last_price_on_or_before(points: list[tuple[datetime, float]], target: datetime) -> tuple[datetime, float] | None:
    valid = [p for p in points if p[0] <= target]
    return valid[-1] if valid else None


def _first_price_on_or_after(points: list[tuple[datetime, float]], target: datetime, max_days: int = 10) -> tuple[datetime, float] | None:
    limit = target + timedelta(days=max_days)
    valid = [p for p in points if target <= p[0] <= limit]
    return valid[0] if valid else None


def _next_month_end(as_of: datetime) -> datetime:
    year = as_of.year + (1 if as_of.month == 12 else 0)
    month = 1 if as_of.month == 12 else as_of.month + 1
    day = calendar.monthrange(year, month)[1]
    return datetime(year, month, day)


def _add_realized_returns(out_rows: list[dict[str, Any]], *, field: str, as_of_date: str, frequency: str) -> None:
    asof_dt = _parse_date(as_of_date)
    if asof_dt is None:
        return
    end_dt = _next_month_end(asof_dt) if frequency == "monthly" else asof_dt + timedelta(days=30)
    returns: list[float] = []
    for row in out_rows:
        points = _price_points(field, str(row.get("company") or ""), str(row.get("company_dir") or ""))
        start = _last_price_on_or_before(points, asof_dt)
        end = _last_price_on_or_before(points, end_dt) or _first_price_on_or_after(points, end_dt)
        if not start or not end or start[1] <= 0:
            row["stock_return_1m"] = ""
            row["holding_start_date"] = ""
            row["holding_end_date"] = ""
            continue
        ret = end[1] / start[1] - 1.0
        row["stock_return_1m"] = round(ret, 8)
        row["holding_start_date"] = start[0].strftime("%Y-%m-%d")
        row["holding_end_date"] = end[0].strftime("%Y-%m-%d")
        returns.append(ret)
    benchmark = sum(returns) / len(returns) if returns else None
    for row in out_rows:
        stock_ret = _to_float(row.get("stock_return_1m"))
        if benchmark is None or stock_ret is None:
            row["benchmark_return_1m"] = ""
            row["excess_return_1m"] = ""
            row["target_label"] = ""
            continue
        excess = stock_ret - benchmark
        row["benchmark_return_1m"] = round(benchmark, 8)
        row["excess_return_1m"] = round(excess, 8)
        row["target_label"] = "매수" if excess > 0 else ("매도" if excess < 0 else "보유")


def export_signal_dataset(*, field: str, as_of_date: str, frequency: str, run_id: str | None, output_dir: Path | None = None, universe_csv: str | Path | None = None) -> Path:
    _ensure_sheets_env()
    universe = _read_universe_identity(Path(universe_csv) if universe_csv else None)
    rows = list_run_results(run_id=run_id, as_of_date=as_of_date, field=field, include_payload=True)
    by_company: dict[str, dict[str, Any]] = {}
    for r in rows:
        company_dir = str(r.get("company_dir") or "")
        if not company_dir:
            continue
        payload = _payload_from_result(r)
        qd = _deep_find_qd(payload)
        if qd:
            by_company.setdefault(company_dir, {})["qd"] = qd
            by_company[company_dir]["qd_source"] = f"google_sheets_run_results:{r.get('agent')}:{r.get('output_kind')}"
        if r.get("agent") == "chair":
            by_company.setdefault(company_dir, {})["chair"] = payload
            by_company[company_dir]["company_name"] = r.get("company_name") or payload.get("company") or ""

    out_rows: list[dict[str, Any]] = []
    date_value = as_of_date[:7] if frequency == "monthly" else as_of_date
    for company_dir, bundle in sorted(by_company.items()):
        qd = _as_dict(bundle.get("qd"))
        identity = _company_identity(as_of_date, field, company_dir, str(bundle.get("company_name") or company_dir), universe)
        weighted = qd.get("weighted_signal")
        recommendation = _recommendation_from_quantitative_decision(qd)
        row: dict[str, Any] = {
            "date": date_value,
            "field": field,
            "company": identity["company"],
            "company_dir": company_dir,
            "ticker": identity["ticker"] or identity["stock_code"],
            "stock_code": identity["stock_code"],
            "recommendation": recommendation,
            "weighted_signal": weighted if weighted is not None else "",
            "as_of_date": as_of_date,
            "signal_source": bundle.get("qd_source") or "google_sheets_history_run_results",
            "run_id": run_id or "",
        }
        decisions = qd.get("agent_decisions") if isinstance(qd.get("agent_decisions"), dict) else {}
        for agent in AGENTS:
            dec = decisions.get(agent) if isinstance(decisions.get(agent), dict) else {}
            signal = dec.get("signal", "")
            weight = dec.get("weight", dec.get("dma_weight", ""))
            row[f"{agent}_signal"] = signal
            row[f"{agent}_weighted_signal"] = dec.get("weighted_contribution", "")
            row[f"{agent}_recommendation"] = dec.get("recommendation") or dec.get("auditor_recommendation") or ""
            row[f"{agent}_weight"] = weight
        out_rows.append(row)

    _add_realized_returns(out_rows, field=field, as_of_date=as_of_date, frequency=frequency)

    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / field / "_sector_common" / "history_sheets_exports" / frequency
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = as_of_date[:7] if frequency == "monthly" else as_of_date
    safe_run = run_id or "all_runs"
    out_path = output_dir / f"signal_df_{frequency}_{suffix}_{safe_run}.csv"

    front = ["date", "field", "company", "ticker", "stock_code", "recommendation", "weighted_signal", "as_of_date", "signal_source"]
    for agent in AGENTS:
        front.extend([f"{agent}_signal", f"{agent}_weighted_signal", f"{agent}_recommendation", f"{agent}_weight"])
    extra = ["stock_return_1m", "benchmark_return_1m", "excess_return_1m", "target_label", "holding_start_date", "holding_end_date", "run_id", "company_dir"]
    fieldnames = front + extra
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)
    print(f"[DONE] signal dataset exported: {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Google Sheets history Chair/Auditor run results to signal_df CSV.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--frequency", choices=["daily", "monthly"], default="daily")
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir")
    parser.add_argument("--universe-csv")
    args = parser.parse_args(argv)
    export_signal_dataset(
        field=args.field,
        as_of_date=args.as_of_date,
        frequency=args.frequency,
        run_id=args.run_id,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        universe_csv=args.universe_csv,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

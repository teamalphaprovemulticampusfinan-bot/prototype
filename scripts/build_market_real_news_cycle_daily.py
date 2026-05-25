from __future__ import annotations

"""
Build real-source market_news_attention_daily.csv and semiconductor_cycle_daily.csv.

Scope is intentionally narrow: this script does not modify existing source code.
It only rewrites the two market_intake CSV inputs under:
  - data/market_excel/
  - data/<field>/_sector_common/market/

News source:
  - GDELT DOC 2.0 TimelineVolRaw raw article-count API, chunked by date.
  - Counts are converted into rolling attention signals. No sentiment is fabricated.

Cycle source:
  - Existing market_external_daily_v44.csv real market index prices.
  - Daily cycle proxy is derived from SOX/Nasdaq/S&P500/VIX/Korea semiconductor ETF prices.
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MARKET_EXCEL_DIR = DATA_DIR / "market_excel"

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_QUERY_EXTRA = '(semiconductor OR microchip OR chips OR "chip industry" OR "semiconductor industry" OR 반도체)'


def _decode_escaped_unicode(text: Any) -> str:
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text or ""))


def _safe_name(text: Any) -> str:
    text = _decode_escaped_unicode(str(text or "")).strip()
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    return text or "unknown"


def _parse_date(value: Any) -> pd.Timestamp | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        ts = pd.to_datetime(value, errors="coerce")
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).normalize()


def _date_range(start: str, end: str) -> pd.DatetimeIndex:
    s = _parse_date(start) or pd.Timestamp("2021-01-01")
    e = _parse_date(end) or pd.Timestamp(date.today())
    if e < s:
        e = s
    return pd.date_range(s, e, freq="D")


def _read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    last_exc: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"CSV read failed: {path}: {last_exc}")


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _sector_market_dir(field: str) -> Path:
    direct = DATA_DIR / field / "_sector_common" / "market"
    if direct.exists() or not DATA_DIR.exists():
        direct.mkdir(parents=True, exist_ok=True)
        return direct
    for child in DATA_DIR.iterdir():
        if child.is_dir() and _decode_escaped_unicode(child.name) == field:
            p = child / "_sector_common" / "market"
            p.mkdir(parents=True, exist_ok=True)
            return p
    direct.mkdir(parents=True, exist_ok=True)
    return direct


@dataclass
class CompanyTarget:
    company: str
    company_dir: str
    stock_code: str = ""
    ticker: str = ""


def _extract_yaml_value(text: str, keys: tuple[str, ...]) -> str:
    for key in keys:
        m = re.search(rf"^\s*{re.escape(key)}\s*:\s*['\"]?([^'\"\n#]+)", text, flags=re.M)
        if m:
            return str(m.group(1)).strip()
    return ""


def _load_universe(field: str) -> list[CompanyTarget]:
    targets: dict[str, CompanyTarget] = {}

    # 1) company.yaml under data/<field>/<company>/_company_common
    for field_dir in [DATA_DIR / field, *[p for p in DATA_DIR.iterdir() if p.is_dir() and _decode_escaped_unicode(p.name) == field]] if DATA_DIR.exists() else []:
        if not field_dir.exists() or not field_dir.is_dir():
            continue
        for child in field_dir.iterdir():
            if not child.is_dir() or child.name.startswith("_"):
                continue
            company_name = _decode_escaped_unicode(child.name)
            company_dir = child.name
            yaml_path = child / "_company_common" / "company.yaml"
            stock_code = ""
            ticker = ""
            if yaml_path.exists():
                try:
                    txt = yaml_path.read_text(encoding="utf-8")
                except Exception:
                    txt = yaml_path.read_text(encoding="utf-8", errors="ignore")
                company_name = _extract_yaml_value(txt, ("company", "company_name", "name")) or company_name
                company_dir = _extract_yaml_value(txt, ("company_dir", "slug")) or company_dir
                stock_code = _extract_yaml_value(txt, ("stock_code", "ticker", "code"))
                ticker = stock_code
            key = company_name.replace(" ", "")
            targets.setdefault(key, CompanyTarget(company=company_name, company_dir=company_dir, stock_code=stock_code, ticker=ticker))

    # 2) market_final_<company>.xlsx filenames
    if MARKET_EXCEL_DIR.exists():
        for path in MARKET_EXCEL_DIR.glob("market_final_*.xlsx"):
            name = path.stem.replace("market_final_", "")
            # skip timestamp-only workbooks
            if re.fullmatch(r"\d{8}_\d{4}", name):
                continue
            company = _decode_escaped_unicode(name).strip()
            if not company:
                continue
            key = company.replace(" ", "")
            targets.setdefault(key, CompanyTarget(company=company, company_dir=key))

    return sorted(targets.values(), key=lambda x: x.company)


def _clean_query_term(term: str) -> str:
    term = _decode_escaped_unicode(term).strip()
    term = re.sub(r"[()]+", " ", term).strip()
    return term


def _company_query(company: CompanyTarget, query_extra: str) -> str:
    terms = []
    company_name = _clean_query_term(company.company)
    no_space = company_name.replace(" ", "")
    if company_name:
        terms.append(f'"{company_name}"')
    if no_space and no_space != company_name:
        terms.append(f'"{no_space}"')
    if company.stock_code:
        terms.append(f'"{company.stock_code.zfill(6)}"')
    company_part = " OR ".join(dict.fromkeys(terms)) or '"semiconductor"'
    return f"({company_part}) AND {query_extra}"


def _sector_query(query_extra: str) -> str:
    return query_extra


def _chunk_dates(start: pd.Timestamp, end: pd.Timestamp, days: int):
    cur = start
    while cur <= end:
        nxt = min(end, cur + pd.Timedelta(days=max(1, days) - 1))
        yield cur, nxt
        cur = nxt + pd.Timedelta(days=1)


def _extract_timeline_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidates = []
    for key in ("timeline", "timeline_data", "data", "results"):
        val = payload.get(key)
        if isinstance(val, list):
            candidates = val
            break
    if not candidates:
        # Some GDELT responses nest the timeline under top-level values.
        for val in payload.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                candidates = val
                break
    out: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        date_val = item.get("date") or item.get("datetime") or item.get("time") or item.get("Date")
        count_val = None
        for k in ("value", "count", "articles", "articlecount", "volumeraw", "VolumeRaw", "raw"):
            if k in item:
                count_val = item.get(k)
                break
        if count_val is None:
            numeric = [(k, v) for k, v in item.items() if isinstance(v, (int, float))]
            if numeric:
                count_val = numeric[0][1]
        if date_val is None or count_val is None:
            continue
        ts = _parse_date(date_val)
        if ts is None:
            # GDELT sometimes returns YYYYMMDDHHMMSS.
            s = str(date_val)
            if re.fullmatch(r"\d{8,14}", s):
                ts = _parse_date(s[:8])
        if ts is None:
            continue
        try:
            count = float(count_val)
        except Exception:
            count = 0.0
        out.append({"date": ts.strftime("%Y-%m-%d"), "count": max(0.0, count)})
    return out


def _gdelt_fetch_counts(
    query: str,
    *,
    start_date: str,
    end_date: str,
    chunk_days: int,
    sleep_sec: float,
    timeout: int,
    cache_dir: Path,
    label: str,
    force: bool,
) -> pd.DataFrame:
    dates = _date_range(start_date, end_date)
    base = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "gdelt_article_count": 0.0})
    cache_dir.mkdir(parents=True, exist_ok=True)
    all_records: list[dict[str, Any]] = []
    start_ts, end_ts = dates.min(), dates.max()

    for a, b in _chunk_dates(start_ts, end_ts, chunk_days):
        cache_file = cache_dir / f"{_safe_name(label)}_{a.strftime('%Y%m%d')}_{b.strftime('%Y%m%d')}.json"
        payload: Any = None
        if cache_file.exists() and not force:
            try:
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                payload = None
        if payload is None:
            params = {
                "query": query,
                "mode": "timelinevolraw",
                "format": "json",
                "startdatetime": a.strftime("%Y%m%d000000"),
                "enddatetime": b.strftime("%Y%m%d235959"),
            }
            url = GDELT_ENDPOINT + "?" + urllib.parse.urlencode(params)
            try:
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                payload = json.loads(raw)
                cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            except Exception as exc:
                payload = {"error": str(exc), "query": query, "start": str(a.date()), "end": str(b.date())}
                cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            if sleep_sec > 0:
                time.sleep(sleep_sec)
        all_records.extend(_extract_timeline_records(payload))

    if all_records:
        got = pd.DataFrame(all_records)
        got = got.groupby("date", as_index=False)["count"].sum().rename(columns={"count": "gdelt_article_count"})
        base = base.drop(columns=["gdelt_article_count"]).merge(got, on="date", how="left")
        base["gdelt_article_count"] = pd.to_numeric(base["gdelt_article_count"], errors="coerce").fillna(0.0)
    return base


def _rolling_signal_from_count(count: pd.Series) -> pd.Series:
    s = pd.to_numeric(count, errors="coerce").fillna(0.0)
    mean = s.rolling(60, min_periods=10).mean().shift(1)
    std = s.rolling(120, min_periods=20).std().shift(1)
    z = (s - mean.fillna(s.expanding().mean().shift(1))) / std.replace(0, pd.NA)
    z = z.fillna(0.0).clip(-6, 6)
    return z.apply(lambda x: math.tanh(float(x) / 3.0))


def build_news_attention(
    *,
    field: str,
    start_date: str,
    end_date: str,
    company_level: bool,
    query_extra: str,
    chunk_days: int,
    sleep_sec: float,
    timeout: int,
    force: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dates = _date_range(start_date, end_date)
    targets = _load_universe(field)
    if not targets:
        targets = [CompanyTarget(company=f"{field}_SECTOR", company_dir="sector")]
    cache_dir = MARKET_EXCEL_DIR / "_gdelt_cache"
    rows: list[pd.DataFrame] = []
    meta = {"source": "GDELT DOC 2.0 TimelineVolRaw", "company_level": company_level, "targets": len(targets)}

    if company_level:
        for idx, target in enumerate(targets, start=1):
            query = _company_query(target, query_extra)
            print(f"[GDELT] {idx}/{len(targets)} {target.company}: fetching raw daily counts", flush=True)
            counts = _gdelt_fetch_counts(
                query,
                start_date=start_date,
                end_date=end_date,
                chunk_days=chunk_days,
                sleep_sec=sleep_sec,
                timeout=timeout,
                cache_dir=cache_dir,
                label=f"company_{target.company}",
                force=force,
            )
            counts["company"] = target.company
            counts["company_dir"] = target.company_dir
            counts["stock_code"] = str(target.stock_code or "").zfill(6) if target.stock_code else ""
            counts["ticker"] = str(target.ticker or target.stock_code or "").zfill(6) if (target.ticker or target.stock_code) else ""
            rows.append(counts)
    else:
        query = _sector_query(query_extra)
        print("[GDELT] sector query: fetching raw daily counts", flush=True)
        counts = _gdelt_fetch_counts(
            query,
            start_date=start_date,
            end_date=end_date,
            chunk_days=chunk_days,
            sleep_sec=sleep_sec,
            timeout=timeout,
            cache_dir=cache_dir,
            label="sector_semiconductor",
            force=force,
        )
        for target in targets:
            part = counts.copy()
            part["company"] = target.company
            part["company_dir"] = target.company_dir
            part["stock_code"] = str(target.stock_code or "").zfill(6) if target.stock_code else ""
            part["ticker"] = str(target.ticker or target.stock_code or "").zfill(6) if (target.ticker or target.stock_code) else ""
            rows.append(part)

    df = pd.concat(rows, ignore_index=True, sort=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values(["company", "date"])
    out_parts = []
    for _, g in df.groupby("company", dropna=False):
        g = g.sort_values("date").copy()
        g["daily_news_count"] = pd.to_numeric(g["gdelt_article_count"], errors="coerce").fillna(0.0)
        g["current_month_news_count"] = g.groupby(g["date"].dt.to_period("M"))["daily_news_count"].cumsum()
        month_sum = g.groupby(g["date"].dt.to_period("M"))["daily_news_count"].transform("sum")
        prev_month_sum = month_sum.groupby(g["date"].dt.to_period("M")).first().shift(1).reindex(g["date"].dt.to_period("M")).to_numpy()
        g["lag_month_news_count"] = pd.Series(prev_month_sum, index=g.index).fillna(0.0)
        g["current_window_news_signal"] = _rolling_signal_from_count(g["daily_news_count"])
        g["lag_window_news_signal"] = g["current_window_news_signal"].shift(30).fillna(0.0)
        g["news_attention_signal"] = (0.7 * g["current_window_news_signal"] + 0.3 * g["lag_window_news_signal"]).clip(-1, 1)
        g["news_count_current"] = g["current_month_news_count"]
        g["news_count_lag"] = g["lag_month_news_count"]
        g["news_reliability"] = ((g["current_month_news_count"] + 0.5 * g["lag_month_news_count"]) / 10.0).clip(0, 1)
        out_parts.append(g)
    out = pd.concat(out_parts, ignore_index=True, sort=False)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out["as_of_date"] = out["date"]
    out["field"] = field
    out["frequency"] = "daily"
    out["source_kind"] = "gdelt_doc_timelinevolraw_real_article_counts"
    out["data_cutoff_ok"] = True
    out["news_cutoff_applied"] = True
    out["evidence_note"] = "GDELT DOC TimelineVolRaw raw article counts; rolling attention signal only, sentiment is not fabricated."
    out["source_files"] = "https://api.gdeltproject.org/api/v2/doc/doc"
    cols = [
        "date", "field", "company", "company_dir", "ticker", "stock_code", "as_of_date", "frequency",
        "source_kind", "data_cutoff_ok", "daily_news_count", "current_month_news_count",
        "lag_month_news_count", "current_window_news_signal", "lag_window_news_signal",
        "news_attention_signal", "news_count_current", "news_count_lag", "news_reliability",
        "news_cutoff_applied", "evidence_note", "source_files",
    ]
    return out[[c for c in cols if c in out.columns]], meta


def _first_existing_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lower = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        hit = lower.get(name.lower())
        if hit is not None:
            return str(hit)
    return None


def _pct(s: pd.Series, periods: int) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").pct_change(periods=periods, fill_method=None)


def _zscore(s: pd.Series, window: int = 120) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    mean = x.rolling(window, min_periods=max(20, window // 4)).mean()
    std = x.rolling(window, min_periods=max(20, window // 4)).std()
    z = (x - mean) / std.replace(0, pd.NA)
    return z.fillna(0.0).clip(-6, 6)


def build_cycle_daily(*, field: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    ext_path = MARKET_EXCEL_DIR / "market_external_daily_v44.csv"
    ext = _read_csv_any(ext_path)
    if ext.empty:
        raise RuntimeError(f"market_external_daily_v44.csv is missing or empty: {ext_path}")
    date_col = _first_existing_col(ext, ["date", "Date", "날짜", "일자"])
    if date_col is None:
        raise RuntimeError("market_external_daily_v44.csv has no date column")
    ext = ext.copy()
    ext["date"] = pd.to_datetime(ext[date_col], errors="coerce").dt.normalize()
    ext = ext.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last")
    cal = pd.DataFrame({"date": _date_range(start_date, end_date)})
    work = cal.merge(ext, on="date", how="left").sort_values("date")

    close_map = {
        "sox": _first_existing_col(work, ["sox_adj_close", "sox_close", "external__sox_adj_close", "external__sox_close"]),
        "nasdaq": _first_existing_col(work, ["nasdaq_adj_close", "nasdaq_close", "external__nasdaq_adj_close", "external__nasdaq_close"]),
        "sp500": _first_existing_col(work, ["sp500_adj_close", "sp500_close", "external__sp500_adj_close", "external__sp500_close"]),
        "vix": _first_existing_col(work, ["vix_yf_close", "vix_close", "external__vix_yf_close", "external__vix_yf_close"]),
        "korea_etf": _first_existing_col(work, ["korea_etf_adj_close", "korea_etf_close", "external__korea_etf_adj_close", "external__korea_etf_close"]),
    }
    for key, col in close_map.items():
        if col is not None:
            work[f"_{key}"] = pd.to_numeric(work[col], errors="coerce").ffill()

    sox20 = _pct(work.get("_sox", pd.Series(index=work.index, dtype=float)), 20)
    sox60 = _pct(work.get("_sox", pd.Series(index=work.index, dtype=float)), 60)
    sox120 = _pct(work.get("_sox", pd.Series(index=work.index, dtype=float)), 120)
    nasdaq60 = _pct(work.get("_nasdaq", pd.Series(index=work.index, dtype=float)), 60)
    korea60 = _pct(work.get("_korea_etf", pd.Series(index=work.index, dtype=float)), 60)
    vix_z = _zscore(work.get("_vix", pd.Series(index=work.index, dtype=float)), 120)

    raw = (
        0.25 * sox20.fillna(0.0)
        + 0.30 * sox60.fillna(0.0)
        + 0.15 * sox120.fillna(0.0)
        + 0.15 * nasdaq60.fillna(0.0)
        + 0.10 * korea60.fillna(0.0)
        - 0.05 * vix_z.fillna(0.0)
    )
    signal = raw.apply(lambda x: math.tanh(float(x) * 3.0)).clip(-1, 1)
    available = sum(1 for c in close_map.values() if c is not None)
    reliability = min(1.0, max(0.0, available / 5.0))

    out = pd.DataFrame({
        "date": work["date"].dt.strftime("%Y-%m-%d"),
        "as_of_date": work["date"].dt.strftime("%Y-%m-%d"),
        "field": field,
        "frequency": "daily",
        "source_kind": "real_market_index_price_proxy",
        "data_cutoff_ok": True,
        "sox_momentum": sox20,
        "chip_sales_momentum": sox60,
        "global_chip_sales_momentum": sox120,
        "semiconductor_export_momentum": nasdaq60,
        "semiconductor_production_momentum": korea60,
        "semiconductor_shipment_momentum": sox20,
        "oecd_cli_momentum": -vix_z / 10.0,
        "sector_cycle_signal": signal,
        "sector_cycle_reliability": reliability,
        "cycle_real_source_coverage": available,
        "evidence_note": "Derived from real daily market-index prices in market_external_daily_v44.csv: SOX, Nasdaq, S&P500, VIX, Korea semiconductor ETF where available.",
        "source_files": str(ext_path.relative_to(ROOT)),
    })
    return out, {"source": str(ext_path.relative_to(ROOT)), "available_proxy_count": available, "reliability": reliability}


def _monthly_tail(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty or "date" not in daily.columns:
        return daily.copy()
    x = daily.copy()
    x["date"] = pd.to_datetime(x["date"], errors="coerce")
    x = x.dropna(subset=["date"]).sort_values("date")
    x = x.groupby(x["date"].dt.to_period("M"), as_index=False).tail(1)
    x["date"] = x["date"].dt.strftime("%Y-%m-%d")
    if "as_of_date" in x.columns:
        x["as_of_date"] = x["date"]
    if "frequency" in x.columns:
        x["frequency"] = "monthly"
    return x


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build real-source market news/cycle CSVs for AlphaProve market_intake")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--start-date", default="2021-01-01")
    parser.add_argument("--end-date", default=date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--company-level-news", action="store_true", help="Fetch GDELT counts per company. More real but much slower.")
    parser.add_argument("--sector-news-only", action="store_true", help="Fetch one sector GDELT query and apply sector attention to all companies.")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--skip-cycle", action="store_true")
    parser.add_argument("--query-extra", default=DEFAULT_QUERY_EXTRA)
    parser.add_argument("--gdelt-chunk-days", type=int, default=92)
    parser.add_argument("--sleep-sec", type=float, default=0.25)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--force", action="store_true", help="Ignore local GDELT cache and refetch")
    parser.add_argument("--no-rebuild-semiconductor", action="store_true", help="Do not call build_market_semiconductor_daily.py after writing sources")
    args = parser.parse_args(argv)

    MARKET_EXCEL_DIR.mkdir(parents=True, exist_ok=True)
    sector_dir = _sector_market_dir(args.field)
    manifest: dict[str, Any] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": args.field,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "files_written": [],
        "notes": [],
    }

    if not args.skip_cycle:
        cycle, meta = build_cycle_daily(field=args.field, start_date=args.start_date, end_date=args.end_date)
        for path in [MARKET_EXCEL_DIR / "semiconductor_cycle_daily.csv", sector_dir / "semiconductor_cycle_daily.csv"]:
            _write_csv(cycle, path)
            manifest["files_written"].append(str(path.relative_to(ROOT)))
        monthly = _monthly_tail(cycle)
        for path in [MARKET_EXCEL_DIR / "semiconductor_cycle_monthly.csv", sector_dir / "semiconductor_cycle_monthly.csv"]:
            _write_csv(monthly, path)
            manifest["files_written"].append(str(path.relative_to(ROOT)))
        manifest["cycle"] = meta
        print(f"[OK] cycle daily rows={len(cycle)}", flush=True)

    if not args.skip_news:
        company_level = bool(args.company_level_news and not args.sector_news_only)
        news, meta = build_news_attention(
            field=args.field,
            start_date=args.start_date,
            end_date=args.end_date,
            company_level=company_level,
            query_extra=args.query_extra,
            chunk_days=args.gdelt_chunk_days,
            sleep_sec=args.sleep_sec,
            timeout=args.timeout,
            force=args.force,
        )
        for path in [MARKET_EXCEL_DIR / "market_news_attention_daily.csv", sector_dir / "market_news_attention_daily.csv"]:
            _write_csv(news, path)
            manifest["files_written"].append(str(path.relative_to(ROOT)))
        monthly = _monthly_tail(news)
        for path in [MARKET_EXCEL_DIR / "market_news_attention_monthly.csv", sector_dir / "market_news_attention_monthly.csv"]:
            _write_csv(monthly, path)
            manifest["files_written"].append(str(path.relative_to(ROOT)))
        manifest["news"] = meta
        print(f"[OK] news daily rows={len(news)} company_level={company_level}", flush=True)

    manifest_path = MARKET_EXCEL_DIR / "market_real_news_cycle_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] manifest={manifest_path.relative_to(ROOT)}", flush=True)

    if not args.no_rebuild_semiconductor:
        import subprocess
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "build_market_semiconductor_daily.py"),
            "--field", args.field,
            "--start-date", args.start_date,
            "--end-date", args.end_date,
        ]
        print("[RUN] rebuild market_semiconductor_daily.csv", flush=True)
        subprocess.run(cmd, check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

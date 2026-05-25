from __future__ import annotations

"""Evaluation-only Market data intake builder.

This module is intentionally placed under ``src_eval`` and writes only the
CSV inputs consumed by ``src_eval.market_agent.history_market_features``.
It does not modify the operational ``src`` market agent.

Outputs:
  data/<field>/_sector_common/market/market_signals_daily.csv
  data/<field>/_sector_common/market/market_signals_monthly.csv
  data/<field>/_sector_common/market/semiconductor_cycle_daily.csv
  data/<field>/_sector_common/market/semiconductor_cycle_monthly.csv
  data/<field>/_sector_common/market/market_news_attention_daily.csv
  data/<field>/_sector_common/market/market_news_attention_monthly.csv
  data/<field>/_sector_common/market/company_market_sensitivity.csv
  data/<field>/_sector_common/market/market_feature_manifest.csv
"""

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import argparse
import json
import math
import os
import sqlite3
import sys
from typing import Any, Iterable

import numpy as np
import pandas as pd

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some envs
    requests = None  # type: ignore

from market_agent.history_market_features import (  # evaluation-only module in src_eval
    MARKET_COLUMNS,
    _combine_blocks,
    _ensure_columns,
    _firm_sensitivity_signal,
    _news_signal,
    _sector_cycle_signal,
    _softmax_recommendation,
    _technical_row,
    clip_signal,
    load_price_history,
    market_input_paths,
    project_root,
    sector_market_dir,
    tanh_scale,
)


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def _norm_col(name: Any) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        x = float(value)
        return x if math.isfinite(x) else default
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text or text.lower() in {"nan", "none", "null", "na"}:
        return default
    try:
        x = float(text)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists() or not path.is_file():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path)


def _to_date(value: Any) -> pd.Timestamp | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).normalize()


def _month_end(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(ts).to_period("M").to_timestamp("M").normalize()


def _month_start(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(ts).to_period("M").to_timestamp("D").normalize()


def _previous_month_window(ts: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    cur_start = _month_start(ts)
    prev_end = cur_start - pd.Timedelta(days=1)
    prev_start = _month_start(prev_end)
    return prev_start, prev_end


def _resolve_root(root: Path | None = None) -> Path:
    return Path(root or os.getenv("ALPHAPROVE_PROJECT_ROOT_OVERRIDE") or project_root()).resolve()


# -----------------------------------------------------------------------------
# Universe / workbook / DB loaders
# -----------------------------------------------------------------------------


def load_universe_for_eval(root: Path, field: str, universe_csv: str | Path | None = None) -> pd.DataFrame:
    candidates: list[Path] = []
    if universe_csv:
        candidates.append((root / universe_csv).resolve() if not Path(universe_csv).is_absolute() else Path(universe_csv))
    candidates.extend([
        root / "data" / field / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv",
        root / "data" / field / "_sector_common" / "universe" / "selected_25_companies.csv",
    ])
    for p in candidates:
        df = _read_csv_any(p)
        if df.empty:
            continue
        df.columns = [_norm_col(c) for c in df.columns]
        if "company" not in df.columns:
            for c in ("company_name", "name", "기업명", "회사명"):
                cn = _norm_col(c)
                if cn in df.columns:
                    df["company"] = df[cn]
                    break
        if "company_dir" not in df.columns:
            for c in ("slug", "company_slug"):
                if c in df.columns:
                    df["company_dir"] = df[c]
                    break
        if "stock_code" not in df.columns:
            for c in ("ticker", "종목코드"):
                cn = _norm_col(c)
                if cn in df.columns:
                    df["stock_code"] = df[cn]
                    break
        if "ticker" not in df.columns and "stock_code" in df.columns:
            df["ticker"] = df["stock_code"]
        if "peer_group" not in df.columns:
            df["peer_group"] = ""
        df["company"] = df["company"].astype(str).str.strip()
        df["company_dir"] = df.get("company_dir", "").astype(str).str.strip()
        df["stock_code"] = df.get("stock_code", "").astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
        df["ticker"] = df.get("ticker", df["stock_code"]).astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
        if "include_in_evaluation" in df.columns:
            inc = pd.to_numeric(df["include_in_evaluation"], errors="coerce").fillna(1)
            df = df[inc != 0]
        return df
    raise FileNotFoundError("universe CSV를 찾지 못했습니다. --universe-csv 또는 data/<field>/_sector_common/universe/*.csv를 확인하세요.")


def _workbook_candidates(root: Path, field: str) -> list[Path]:
    env_path = os.getenv("MARKET_WORKBOOK_PATH", "").strip().strip('"').strip("'")
    cands: list[Path] = []
    if env_path:
        p = Path(env_path)
        cands.append(p if p.is_absolute() else root / p)
    cands.extend([
        root / "data" / field / "_sector_common" / "data" / "Market_통합.xlsx",
        root / "data" / field / "_sector_common" / "source_data" / "Market_통합.xlsx",
        root / "data" / "Market_통합.xlsx",
        root / "Market_통합.xlsx",
    ])
    return cands


def load_market_workbook_tables(root: Path, field: str, allow_url: bool = True) -> tuple[dict[str, pd.DataFrame], str]:
    for p in _workbook_candidates(root, field):
        if p.exists() and p.is_file():
            xl = pd.ExcelFile(p)
            return {name: xl.parse(name) for name in xl.sheet_names}, str(p)

    url = os.getenv("MARKET_WORKBOOK_URL", "").strip().strip('"').strip("'")
    if allow_url and url and requests is not None:
        # 읽기 전용. 운영 market_agent의 원칙과 동일하게 파일을 로컬에 저장하지 않는다.
        resp = requests.get(url, timeout=45)
        resp.raise_for_status()
        content = resp.content
        if not content.startswith(b"PK"):
            raise ValueError("MARKET_WORKBOOK_URL 응답이 xlsx 형식이 아닙니다. GitHub blob URL이 아니라 raw URL인지 확인하세요.")
        xl = pd.ExcelFile(BytesIO(content))
        return {name: xl.parse(name) for name in xl.sheet_names}, "MARKET_WORKBOOK_URL(in_memory)"

    return {}, ""


def load_market_db_tables(root: Path) -> tuple[dict[str, pd.DataFrame], str]:
    raw_path = os.getenv("MARKET_ISSUES_DB_PATH", "").strip().strip('"').strip("'")
    db_path = Path(raw_path) if raw_path else root / "data" / "market_issues.db"
    if not db_path.is_absolute():
        db_path = root / db_path
    if not db_path.exists():
        return {}, ""
    tables: dict[str, pd.DataFrame] = {}
    conn = sqlite3.connect(str(db_path))
    try:
        names = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].astype(str).tolist()
        for name in names:
            try:
                tables[name] = pd.read_sql(f"SELECT * FROM {name}", conn)
            except Exception:
                tables[name] = pd.DataFrame()
    finally:
        conn.close()
    return tables, str(db_path)


# -----------------------------------------------------------------------------
# Static context -> sensitivity proxies
# -----------------------------------------------------------------------------


def _find_company_row(df: pd.DataFrame, company: str) -> dict[str, Any]:
    if df.empty:
        return {}
    d = df.copy()
    d.columns = [_norm_col(c) for c in d.columns]
    for c in ("company", "company_name", "기업명", "회사명"):
        cn = _norm_col(c)
        if cn in d.columns:
            sub = d[d[cn].astype(str).str.strip().eq(company)]
            if not sub.empty:
                return sub.iloc[0].to_dict()
    # 일부 엑셀은 첫 번째 열이 기업명인 경우가 많다.
    first = d.columns[0]
    sub = d[d[first].astype(str).str.strip().eq(company)]
    if not sub.empty:
        return sub.iloc[0].to_dict()
    return {}


def _workbook_role(company: str, workbook: dict[str, pd.DataFrame]) -> str:
    for sheet in ("벨류체인", "밸류체인", "value_chain", "기본"):
        df = workbook.get(sheet)
        if df is None or df.empty:
            continue
        row = _find_company_row(df, company)
        if not row:
            continue
        vals = [str(v) for v in row.values() if str(v).strip() and str(v).lower() != "nan"]
        # 역할 후보는 대체로 회사명 다음 열에 들어 있지만, 문자열 전체에서 키워드를 찾는 방식으로 방어한다.
        joined = " / ".join(vals)
        return joined[:500]
    return ""


def _db_company_context(company: str, db_tables: dict[str, pd.DataFrame], as_of: pd.Timestamp | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for table_name in ("value_chain", "competition"):
        df = db_tables.get(table_name, pd.DataFrame())
        if df.empty:
            continue
        d = df.copy()
        d.columns = [_norm_col(c) for c in d.columns]
        if "company_name" not in d.columns:
            continue
        sub = d[d["company_name"].astype(str).str.strip().eq(company)].copy()
        if sub.empty:
            continue
        if as_of is not None and "updated_at" in sub.columns:
            upd = pd.to_datetime(sub["updated_at"], errors="coerce")
            eligible = sub[upd.isna() | (upd <= as_of)]
            if not eligible.empty:
                sub = eligible
        row = sub.iloc[-1].to_dict()
        for k, v in row.items():
            ctx[f"{table_name}_{k}"] = v
    return ctx


def _role_based_sensitivity(role_text: str, peer_group: str = "") -> dict[str, float]:
    text = f"{role_text} {peer_group}".lower()
    # 기본값은 반도체 전반의 시장 민감도 proxy. 회귀계수가 아니라 분류 기반 초기값이며 manifest에 표시한다.
    vals = {
        "fx_beta": 0.20,
        "raw_material_beta": -0.15,
        "sox_beta": 0.55,
        "krx_sector_beta": 0.50,
        "export_sensitivity": 0.35,
        "import_cost_sensitivity": -0.20,
        "rate_sensitivity": -0.25,
        "supply_chain_sensitivity": -0.25,
    }
    if any(k in text for k in ("팹리스", "fabless", "설계", "design")):
        vals.update({"sox_beta": 0.85, "krx_sector_beta": 0.65, "export_sensitivity": 0.45, "rate_sensitivity": -0.35})
    if any(k in text for k in ("장비", "equipment", "본더", "tc bonder", "검사")):
        vals.update({"sox_beta": 0.75, "krx_sector_beta": 0.60, "export_sensitivity": 0.40, "supply_chain_sensitivity": -0.35, "rate_sensitivity": -0.30})
    if any(k in text for k in ("소재", "material", "케미칼", "chemical", "가스", "전구체")):
        vals.update({"raw_material_beta": -0.45, "import_cost_sensitivity": -0.35, "fx_beta": 0.30, "sox_beta": 0.50})
    if any(k in text for k in ("후공정", "패키징", "테스트", "osat", "package", "packaging")):
        vals.update({"sox_beta": 0.70, "krx_sector_beta": 0.65, "export_sensitivity": 0.40, "supply_chain_sensitivity": -0.30})
    if any(k in text for k in ("파운드리", "foundry", "idm")):
        vals.update({"sox_beta": 0.80, "krx_sector_beta": 0.70, "export_sensitivity": 0.50, "rate_sensitivity": -0.35})
    return vals


def build_company_sensitivity(
    root: Path,
    field: str,
    universe: pd.DataFrame,
    workbook: dict[str, pd.DataFrame],
    workbook_source: str,
    db_tables: dict[str, pd.DataFrame],
    db_source: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, r in universe.iterrows():
        company = str(r.get("company") or r.get("company_name") or "").strip()
        peer_group = str(r.get("peer_group") or "").strip()
        role_from_workbook = _workbook_role(company, workbook)
        db_ctx = _db_company_context(company, db_tables)
        role = str(db_ctx.get("value_chain_vc_role") or role_from_workbook or peer_group)
        sens = _role_based_sensitivity(role, peer_group)
        rows.append({
            "field": field,
            "company": company,
            "ticker": str(r.get("ticker") or r.get("stock_code") or "").replace(".0", "").zfill(6),
            "stock_code": str(r.get("stock_code") or r.get("ticker") or "").replace(".0", "").zfill(6),
            "company_dir": str(r.get("company_dir") or ""),
            "vc_role": role,
            "peer_group": peer_group,
            "source_kind": "market_db_workbook_role_proxy",
            **sens,
            "confidence": db_ctx.get("value_chain_confidence") or "proxy_review_required",
            "evidence_note": "market_issues.db/Market_통합.xlsx/Universe의 밸류체인 분류를 이용한 성능평가용 초기 민감도 proxy입니다. 실제 회귀계수가 있으면 이 CSV를 덮어쓰면 됩니다.",
            "source_files": ";".join([s for s in [db_source, workbook_source] if s]),
        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Date-aware sector cycle / news attention builders
# -----------------------------------------------------------------------------


def _date_grid(start: pd.Timestamp, end: pd.Timestamp, frequency: str) -> list[pd.Timestamp]:
    if frequency == "daily":
        return list(pd.date_range(start, end, freq="D"))
    if frequency == "monthly":
        return list(pd.date_range(_month_end(start), _month_end(end), freq="ME"))
    raise ValueError(f"unsupported frequency: {frequency}")


def _target_dict(row: pd.Series) -> dict[str, Any]:
    return {
        "company": row.get("company") or row.get("company_name") or row.get("name") or "",
        "company_dir": row.get("company_dir") or row.get("slug") or "",
        "ticker": str(row.get("ticker") or row.get("stock_code") or "").replace(".0", "").zfill(6),
        "stock_code": str(row.get("stock_code") or row.get("ticker") or "").replace(".0", "").zfill(6),
        "peer_group": row.get("peer_group") or "",
    }


def _load_all_price_histories(root: Path, field: str, universe: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, str, dict[str, Any]]]:
    out: dict[str, tuple[pd.DataFrame, str, dict[str, Any]]] = {}
    for _, r in universe.iterrows():
        t = _target_dict(r)
        key = str(t["company"] or t["company_dir"] or t["stock_code"])
        px, src = load_price_history(root, field, t)
        if not px.empty:
            px = px.copy()
            px["date"] = pd.to_datetime(px["date"], errors="coerce")
            px["close"] = pd.to_numeric(px["close"], errors="coerce")
            px["volume"] = pd.to_numeric(px.get("volume", np.nan), errors="coerce")
            px = px.dropna(subset=["date", "close"]).sort_values("date")
        out[key] = (px, src, t)
    return out


def _yfinance_suffixes(market: str) -> list[str]:
    m = str(market or "").upper()
    if "KOSPI" in m:
        return [".KS", ".KQ"]
    if "KOSDAQ" in m:
        return [".KQ", ".KS"]
    return [".KS", ".KQ"]


def _fetch_price_with_yfinance(code: str, market: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, str]:
    """Fetch a Korean stock price series through yfinance.

    This is intentionally best-effort.  The evaluation builder must never fail
    just because a provider is temporarily slow.  A timeout is applied so that
    ``--fetch-missing-price`` does not appear to hang forever.
    """
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return pd.DataFrame(), "yfinance_unavailable"

    fetch_start = (start - pd.Timedelta(days=220)).strftime("%Y-%m-%d")
    fetch_end = (end + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    timeout = int(os.getenv("MARKET_YFINANCE_TIMEOUT", "20") or "20")

    for suffix in _yfinance_suffixes(market):
        symbol = f"{str(code).zfill(6)}{suffix}"
        try:
            df = yf.download(
                symbol,
                start=fetch_start,
                end=fetch_end,
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=timeout,
            )
        except TypeError:
            # Older yfinance versions may not accept timeout=.
            try:
                df = yf.download(symbol, start=fetch_start, end=fetch_end, auto_adjust=False, progress=False, threads=False)
            except Exception:
                continue
        except Exception:
            continue
        if df is None or df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[0]).lower().replace(" ", "_") for c in df.columns]
        else:
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df = df.reset_index().rename(columns={"Date": "date", "date": "date", "adj_close": "adj_close"})
        if "date" not in df.columns:
            df = df.rename(columns={df.columns[0]: "date"})
        if "close" not in df.columns and "adj_close" in df.columns:
            df["close"] = df["adj_close"]
        if "volume" not in df.columns:
            df["volume"] = np.nan
        out = df[["date", "close", "volume"]].copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out["close"] = pd.to_numeric(out["close"], errors="coerce")
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
        out = out.dropna(subset=["date", "close"]).sort_values("date")
        if not out.empty:
            out["ticker"] = symbol
            out["source"] = "yfinance_eval_fetch"
            return out, f"yfinance:{symbol}"
    return pd.DataFrame(), "yfinance_no_data"


def _latest_price_date(px: pd.DataFrame) -> pd.Timestamp | None:
    if px is None or px.empty or "date" not in px.columns:
        return None
    dates = pd.to_datetime(px["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return pd.Timestamp(dates.max()).normalize()


def _merge_price_frames(existing: pd.DataFrame, fetched: pd.DataFrame) -> pd.DataFrame:
    frames = []
    if existing is not None and not existing.empty:
        frames.append(existing.copy())
    if fetched is not None and not fetched.empty:
        frames.append(fetched.copy())
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["close"] = pd.to_numeric(out.get("close"), errors="coerce")
    out["volume"] = pd.to_numeric(out.get("volume", np.nan), errors="coerce")
    out = out.dropna(subset=["date", "close"]).sort_values("date")
    out = out.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    keep = [c for c in ["date", "open", "high", "low", "close", "adj_close", "volume", "ticker", "source"] if c in out.columns]
    return out[keep].copy()


def _load_all_price_histories_with_optional_fetch(
    root: Path,
    field: str,
    universe: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    fetch_missing_price: bool = False,
    force_refresh_price_cache: bool = False,
    price_stale_days: int = 5,
    verbose: bool = True,
) -> dict[str, tuple[pd.DataFrame, str, dict[str, Any]]]:
    out = _load_all_price_histories(root, field, universe)
    if not fetch_missing_price and not force_refresh_price_cache:
        return out

    cache_dir = root / "data" / field / "_sector_common" / "market" / "source_price_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    stale_cutoff = (pd.Timestamp(end).normalize() - pd.Timedelta(days=max(0, int(price_stale_days or 0))))

    total = len(universe)
    fetched_count = 0
    cached_count = 0
    skipped_fresh_count = 0
    failed_count = 0

    for i, (_, r) in enumerate(universe.iterrows(), start=1):
        t = _target_dict(r)
        key = str(t["company"] or t["company_dir"] or t["stock_code"])
        company = str(t.get("company") or key)
        px, src, target = out.get(key, (pd.DataFrame(), "", t))
        code = str(t.get("stock_code") or t.get("ticker") or "").zfill(6)
        if not code or code == "000000":
            failed_count += 1
            if verbose:
                print(f"[price-fetch] {i}/{total} {company}: skip(no stock_code)", flush=True)
            continue

        cached = cache_dir / f"{code}.csv"
        cached_df = _read_csv_any(cached)
        if not cached_df.empty:
            cached_df.columns = [_norm_col(c) for c in cached_df.columns]
            if "date" in cached_df.columns and "close" in cached_df.columns:
                cached_df["date"] = pd.to_datetime(cached_df["date"], errors="coerce")
                cached_df["close"] = pd.to_numeric(cached_df["close"], errors="coerce")
                cached_df["volume"] = pd.to_numeric(cached_df.get("volume", np.nan), errors="coerce")
                cached_df = cached_df.dropna(subset=["date", "close"]).sort_values("date")
                cached_latest = _latest_price_date(cached_df)
                if cached_latest is not None and cached_latest >= stale_cutoff and not force_refresh_price_cache:
                    out[key] = (cached_df, str(cached), target)
                    cached_count += 1
                    if verbose:
                        print(f"[price-fetch] {i}/{total} {company}: use cache latest={cached_latest.date()}", flush=True)
                    continue

        latest = _latest_price_date(px)
        needs_fetch = force_refresh_price_cache or px.empty or latest is None or latest < stale_cutoff
        if not needs_fetch:
            skipped_fresh_count += 1
            if verbose:
                print(f"[price-fetch] {i}/{total} {company}: local fresh latest={latest.date() if latest is not None else 'NA'}", flush=True)
            continue

        if verbose:
            latest_text = latest.date() if latest is not None else "missing"
            print(f"[price-fetch] {i}/{total} {company}({code}): fetch start local_latest={latest_text} cutoff={stale_cutoff.date()}", flush=True)

        fetched, fetched_src = _fetch_price_with_yfinance(code, str(r.get("market") or ""), start, end)
        if fetched.empty:
            failed_count += 1
            if verbose:
                print(f"[price-fetch] {i}/{total} {company}({code}): fetch failed source={fetched_src}", flush=True)
            continue

        merged = _merge_price_frames(px, fetched)
        if merged.empty:
            failed_count += 1
            if verbose:
                print(f"[price-fetch] {i}/{total} {company}({code}): merge failed", flush=True)
            continue
        merged.to_csv(cached, index=False, encoding="utf-8-sig")
        out[key] = (merged, str(cached) + f" ({fetched_src})", target)
        fetched_count += 1
        if verbose:
            merged_latest = _latest_price_date(merged)
            print(f"[price-fetch] {i}/{total} {company}({code}): saved cache latest={merged_latest.date() if merged_latest is not None else 'NA'} rows={len(merged)}", flush=True)

    if verbose:
        print(
            f"[price-fetch] done fetched={fetched_count}, cache_used={cached_count}, "
            f"fresh_skipped={skipped_fresh_count}, failed_or_skipped={failed_count}, cache_dir={cache_dir}",
            flush=True,
        )
    return out


def _return_asof(px: pd.DataFrame, as_of: pd.Timestamp, lag: int) -> float | None:
    hist = px[px["date"] <= as_of].sort_values("date")
    if len(hist) <= lag:
        return None
    last = _safe_float(hist["close"].iloc[-1])
    prev = _safe_float(hist["close"].iloc[-lag - 1])
    if last is None or prev in (None, 0):
        return None
    return float(last / prev - 1.0)


def build_sector_cycle_tables(
    root: Path,
    field: str,
    universe: pd.DataFrame,
    price_map: dict[str, tuple[pd.DataFrame, str, dict[str, Any]]],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows_by_freq: dict[str, list[dict[str, Any]]] = {"daily": [], "monthly": []}
    for freq in ("daily", "monthly"):
        for dt in _date_grid(start, end, freq):
            r20s: list[float] = []
            r60s: list[float] = []
            volumes: list[float] = []
            used_sources: list[str] = []
            for px, src, _target in price_map.values():
                if px.empty:
                    continue
                r20 = _return_asof(px, dt, 20)
                r60 = _return_asof(px, dt, 60)
                if r20 is not None:
                    r20s.append(r20)
                if r60 is not None:
                    r60s.append(r60)
                hist = px[px["date"] <= dt]
                if not hist.empty and "volume" in hist:
                    v = _safe_float(hist["volume"].iloc[-1])
                    if v is not None:
                        volumes.append(v)
                if src:
                    used_sources.append(src)
            coverage = len(r20s) / max(1, len(price_map))
            ew20 = float(np.nanmean(r20s)) if r20s else np.nan
            ew60 = float(np.nanmean(r60s)) if r60s else np.nan
            # 기존 history_market_features의 sector-cycle 해석 함수가 읽는 컬럼에 맞춰 proxy를 채운다.
            base = {
                "date": str(dt.date()),
                "as_of_date": str(dt.date()),
                "field": field,
                "frequency": freq,
                "source_kind": "universe_equal_weight_price_proxy",
                "data_cutoff_ok": True,
                "sox_momentum": ew20,
                "chip_sales_momentum": ew60,
                "global_chip_sales_momentum": ew60,
                "semiconductor_export_momentum": ew20,
                "semiconductor_production_momentum": ew60,
                "semiconductor_shipment_momentum": ew20,
                "oecd_cli_momentum": ew60,
                "evidence_note": "30개 반도체 유니버스 가격 데이터만 이용한 날짜 컷오프 기반 시장 사이클 proxy입니다. SOX/수출/판매 실데이터가 있으면 같은 컬럼으로 덮어쓰면 됩니다.",
                "source_files": ";".join(sorted(set(used_sources))[:10]),
            }
            sig, rel, detail = _sector_cycle_signal(base)
            base["sector_cycle_signal"] = sig
            base["sector_cycle_reliability"] = float(min(1.0, max(rel, coverage)))
            base["news_cutoff_applied"] = True
            rows_by_freq[freq].append(base)
    return _ensure_columns(pd.DataFrame(rows_by_freq["daily"])), _ensure_columns(pd.DataFrame(rows_by_freq["monthly"]))


def _issue_source_candidates(root: Path, field: str) -> list[Path]:
    base = root / "data" / field / "_sector_common" / "issue"
    return [
        base / "issue_events_daily.csv",
        base / "issue_events_daily_v44.csv",
        base / "issue_events_common.csv",
        base / "company_issue_exposure.csv",
    ]


def _load_issue_events(root: Path, field: str) -> tuple[pd.DataFrame, str]:
    frames: list[pd.DataFrame] = []
    sources: list[str] = []
    for p in _issue_source_candidates(root, field):
        df = _read_csv_any(p)
        if df.empty:
            continue
        df.columns = [_norm_col(c) for c in df.columns]
        if "date" not in df.columns:
            for c in ("published_at", "pub_date", "일자", "날짜"):
                cn = _norm_col(c)
                if cn in df.columns:
                    df["date"] = df[cn]
                    break
        if "company" not in df.columns:
            for c in ("company_name", "기업명", "회사명"):
                cn = _norm_col(c)
                if cn in df.columns:
                    df["company"] = df[cn]
                    break
        if "stock_code" not in df.columns and "ticker" in df.columns:
            df["stock_code"] = df["ticker"]
        df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
        df = df.dropna(subset=["date"])
        if df.empty:
            continue
        frames.append(df)
        sources.append(str(p))
    if not frames:
        return pd.DataFrame(), ""
    out = pd.concat(frames, ignore_index=True, sort=False)
    if "sentiment_score" not in out.columns:
        out["sentiment_score"] = 0.5
    if "issue_count" not in out.columns:
        out["issue_count"] = 1
    if "materiality_weight" not in out.columns:
        out["materiality_weight"] = 1.0
    if "source_weight" not in out.columns:
        out["source_weight"] = 1.0
    out["company"] = out.get("company", "").astype(str).str.strip()
    out["stock_code"] = out.get("stock_code", out.get("ticker", "")).astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    out["ticker"] = out.get("ticker", out["stock_code"]).astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    return out, ";".join(sources)


def _weighted_news_signal(df: pd.DataFrame) -> tuple[float, int]:
    if df.empty:
        return 0.0, 0
    sent = pd.to_numeric(df.get("sentiment_score", 0.5), errors="coerce").fillna(0.5)
    # sentiment_score가 0~1이면 -1~1로 변환, 이미 -1~1이면 그대로 사용한다.
    if sent.min() >= 0 and sent.max() <= 1:
        sent = sent * 2.0 - 1.0
    materiality = pd.to_numeric(df.get("materiality_weight", 1.0), errors="coerce").fillna(1.0)
    source_w = pd.to_numeric(df.get("source_weight", 1.0), errors="coerce").fillna(1.0)
    issue_count = pd.to_numeric(df.get("issue_count", 1.0), errors="coerce").fillna(1.0)
    w = materiality * source_w * issue_count.clip(lower=1.0)
    denom = float(w.sum())
    if denom <= 0:
        return 0.0, int(len(df))
    return clip_signal(float((sent * w).sum() / denom)), int(issue_count.sum())


def build_news_attention_tables(
    root: Path,
    field: str,
    universe: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    events, event_sources = _load_issue_events(root, field)
    rows_by_freq: dict[str, list[dict[str, Any]]] = {"daily": [], "monthly": []}
    for freq in ("daily", "monthly"):
        for dt in _date_grid(start, end, freq):
            current_start = _month_start(dt)
            prev_start, prev_end = _previous_month_window(dt)
            for _, r in universe.iterrows():
                t = _target_dict(r)
                company = str(t["company"])
                code = str(t["stock_code"]).zfill(6)
                if events.empty:
                    cur = pd.DataFrame()
                    lag = pd.DataFrame()
                else:
                    base_mask = events["date"].notna() & (events["date"] <= dt)
                    company_mask = pd.Series([False] * len(events))
                    if "company" in events.columns:
                        company_mask |= events["company"].astype(str).str.strip().eq(company)
                    if "stock_code" in events.columns and code:
                        company_mask |= events["stock_code"].astype(str).str.zfill(6).eq(code)
                    cur = events[base_mask & company_mask & (events["date"] >= current_start) & (events["date"] <= dt)]
                    lag = events[base_mask & company_mask & (events["date"] >= prev_start) & (events["date"] <= prev_end)]
                cur_sig, cur_cnt = _weighted_news_signal(cur)
                lag_sig, lag_cnt = _weighted_news_signal(lag)
                row = {
                    "date": str(dt.date()),
                    "as_of_date": str(dt.date()),
                    "field": field,
                    "company": company,
                    "company_dir": t.get("company_dir", ""),
                    "ticker": str(t.get("ticker") or code).zfill(6),
                    "stock_code": code,
                    "frequency": freq,
                    "source_kind": "issue_events_current_month_70_lag_month_30",
                    "data_cutoff_ok": True,
                    "current_window_news_signal": cur_sig,
                    "lag_window_news_signal": lag_sig,
                    "news_attention_signal": clip_signal(0.7 * cur_sig + 0.3 * lag_sig),
                    "news_count_current": cur_cnt,
                    "news_count_lag": lag_cnt,
                    "news_cutoff_applied": True,
                    "news_reliability": min(1.0, (cur_cnt + 0.5 * lag_cnt) / 10.0) if (cur_cnt or lag_cnt) else 0.0,
                    "evidence_note": "Issue 이벤트를 as_of_date 이하로 자른 뒤 해당 월 70% + 전월 30%로 변환한 Market용 뉴스 주목도입니다.",
                    "source_files": event_sources,
                }
                rows_by_freq[freq].append(row)
    return _ensure_columns(pd.DataFrame(rows_by_freq["daily"])), _ensure_columns(pd.DataFrame(rows_by_freq["monthly"])), event_sources


# -----------------------------------------------------------------------------
# Integrated market signal rows
# -----------------------------------------------------------------------------


def _row_for_exact_date(df: pd.DataFrame, dt: pd.Timestamp, company: str = "", code: str = "") -> dict[str, Any]:
    if df.empty:
        return {}
    d = _ensure_columns(df)
    dates = pd.to_datetime(d["date"].fillna(d["as_of_date"]), errors="coerce")
    mask = dates.eq(dt)
    if company and d["company"].notna().any():
        cm = d["company"].astype(str).str.strip().eq(company)
        if cm.any():
            mask &= cm
    if code and d["stock_code"].notna().any():
        sm = d["stock_code"].astype(str).str.zfill(6).eq(str(code).zfill(6))
        if sm.any():
            mask &= sm
    sub = d[mask]
    if sub.empty:
        return {}
    return {k: (None if pd.isna(v) else v) for k, v in sub.iloc[0].to_dict().items()}


def _sensitivity_dict(sens_df: pd.DataFrame, company: str, code: str) -> dict[str, Any]:
    if sens_df.empty:
        return {}
    d = sens_df.copy()
    d.columns = [_norm_col(c) for c in d.columns]
    mask = pd.Series([True] * len(d))
    if "company" in d.columns and company:
        cm = d["company"].astype(str).str.strip().eq(company)
        if cm.any():
            mask &= cm
    if "stock_code" in d.columns and code:
        sm = d["stock_code"].astype(str).str.zfill(6).eq(str(code).zfill(6))
        if sm.any():
            mask &= sm
    sub = d[mask]
    if sub.empty:
        return {}
    return {k: (None if pd.isna(v) else v) for k, v in sub.iloc[0].to_dict().items()}


def build_integrated_market_tables(
    root: Path,
    field: str,
    universe: pd.DataFrame,
    price_map: dict[str, tuple[pd.DataFrame, str, dict[str, Any]]],
    cycle_daily: pd.DataFrame,
    cycle_monthly: pd.DataFrame,
    news_daily: pd.DataFrame,
    news_monthly: pd.DataFrame,
    sens_df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows_by_freq: dict[str, list[dict[str, Any]]] = {"daily": [], "monthly": []}
    for key, (px, px_src, target) in price_map.items():
        if px.empty:
            # 가격이 전혀 없으면 dense row를 만들 수 없으므로 manifest에서 coverage로 표시한다.
            continue
        company = str(target.get("company") or "")
        code = str(target.get("stock_code") or target.get("ticker") or "").zfill(6)
        ticker = str(target.get("ticker") or code).zfill(6)
        sens = _sensitivity_dict(sens_df, company, code)
        for freq in ("daily", "monthly"):
            if freq == "daily":
                dates = px[(px["date"] >= start) & (px["date"] <= end)]["date"].drop_duplicates().sort_values().tolist()
                cycle_df = cycle_daily
                news_df = news_daily
            else:
                month_dates = px[(px["date"] >= start) & (px["date"] <= end)].set_index("date").resample("ME").last().dropna(how="all").index.tolist()
                dates = [pd.Timestamp(d).normalize() for d in month_dates]
                cycle_df = cycle_monthly
                news_df = news_monthly
            for dt in dates:
                dt = pd.Timestamp(dt).normalize()
                tech = _technical_row(px, dt)
                row: dict[str, Any] = {
                    "date": str(dt.date()),
                    "as_of_date": str(dt.date()),
                    "field": field,
                    "company": company,
                    "ticker": ticker,
                    "stock_code": code,
                    "frequency": freq,
                    "source_kind": "src_eval_market_eval_intake_v51",
                    "data_cutoff_ok": True,
                    "source_files": px_src,
                }
                row.update(tech)
                cycle_row = _row_for_exact_date(cycle_df, dt)
                news_row = _row_for_exact_date(news_df, dt, company, code)
                for k, v in cycle_row.items():
                    if k not in {"company", "ticker", "stock_code"} and v is not None:
                        row[k] = v
                for k, v in news_row.items():
                    if k not in {"close", "volume"} and v is not None:
                        row[k] = v
                sector_sig, sector_rel, sector_detail = _sector_cycle_signal(row)
                sens_sig, sens_rel, sens_detail = _firm_sensitivity_signal(row, sens)
                tech_sig = clip_signal(row.get("technical_signal", 0.0))
                tech_rel = _safe_float(row.get("technical_reliability"), 0.0) or 0.0
                news_sig, news_rel, news_detail = _news_signal(row, freq)
                combined, reliability, block_weights = _combine_blocks([
                    ("sector_cycle", sector_sig, sector_rel),
                    ("firm_sensitivity", sens_sig, sens_rel),
                    ("technical", tech_sig, tech_rel),
                    ("news_attention", news_sig, news_rel),
                ])
                rec, probs = _softmax_recommendation(combined, reliability if reliability > 0 else 1.0)
                row.update({
                    "sector_cycle_signal": sector_sig,
                    "sector_cycle_reliability": sector_rel,
                    "firm_market_sensitivity_signal": sens_sig,
                    "firm_sensitivity_reliability": sens_rel,
                    "market_signal": clip_signal(combined),
                    "market_recommendation": rec,
                    "market_weighted_signal": clip_signal(combined * (reliability if reliability > 0 else 1.0)),
                    "signal_reliability": float(max(0.0, min(1.0, reliability))),
                    "prob_sell": probs.get("매도", np.nan),
                    "prob_hold": probs.get("보유", np.nan),
                    "prob_buy": probs.get("매수", np.nan),
                    "evidence_note": "price technical + sector-cycle proxy + issue news current/lag window + market DB/workbook sensitivity; all rows are generated at or before as_of_date.",
                    "source_files": ";".join(sorted(set(str(row.get("source_files", "")).split(";") + [str(sens.get("source_files", ""))]))).strip(";"),
                })
                rows_by_freq[freq].append(row)
    return _ensure_columns(pd.DataFrame(rows_by_freq["daily"])), _ensure_columns(pd.DataFrame(rows_by_freq["monthly"]))


# -----------------------------------------------------------------------------
# Public API / CLI
# -----------------------------------------------------------------------------


@dataclass
class MarketEvalIntakeResult:
    output_dir: str
    files: dict[str, str]
    row_counts: dict[str, int]
    sources: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {"output_dir": self.output_dir, "files": self.files, "row_counts": self.row_counts, "sources": self.sources}


def build_market_evaluation_inputs(
    *,
    root: Path | None = None,
    field: str = "반도체",
    start: str = "2025-01-01",
    end: str = "2026-01-31",
    universe_csv: str | Path | None = None,
    allow_workbook_url: bool = True,
    fetch_missing_price: bool = False,
    force_refresh_price_cache: bool = False,
    price_stale_days: int = 5,
    verbose: bool = True,
) -> MarketEvalIntakeResult:
    root = _resolve_root(root)
    start_ts = pd.to_datetime(start, errors="raise").normalize()
    end_ts = pd.to_datetime(end, errors="raise").normalize()
    out_dir = sector_market_dir(root, field)
    out_dir.mkdir(parents=True, exist_ok=True)

    universe = load_universe_for_eval(root, field, universe_csv)
    workbook, workbook_source = load_market_workbook_tables(root, field, allow_url=allow_workbook_url)
    db_tables, db_source = load_market_db_tables(root)
    price_map = _load_all_price_histories_with_optional_fetch(
        root,
        field,
        universe,
        start_ts,
        end_ts,
        fetch_missing_price=fetch_missing_price,
        force_refresh_price_cache=force_refresh_price_cache,
        price_stale_days=price_stale_days,
        verbose=verbose,
    )

    sens_df = build_company_sensitivity(root, field, universe, workbook, workbook_source, db_tables, db_source)
    cycle_daily, cycle_monthly = build_sector_cycle_tables(root, field, universe, price_map, start_ts, end_ts)
    news_daily, news_monthly, issue_sources = build_news_attention_tables(root, field, universe, start_ts, end_ts)
    market_daily, market_monthly = build_integrated_market_tables(
        root, field, universe, price_map, cycle_daily, cycle_monthly, news_daily, news_monthly, sens_df, start_ts, end_ts
    )

    paths = market_input_paths(root, field)
    output_map = {
        "daily": paths["daily"],
        "monthly": paths["monthly"],
        "company_sensitivity": paths["company_sensitivity"],
        "cycle_daily": paths["cycle_daily"],
        "cycle_monthly": paths["cycle_monthly"],
        "news_daily": paths["news_daily"],
        "news_monthly": paths["news_monthly"],
        "manifest": paths["manifest"],
    }

    market_daily.to_csv(output_map["daily"], index=False, encoding="utf-8-sig")
    market_monthly.to_csv(output_map["monthly"], index=False, encoding="utf-8-sig")
    sens_df.to_csv(output_map["company_sensitivity"], index=False, encoding="utf-8-sig")
    cycle_daily.to_csv(output_map["cycle_daily"], index=False, encoding="utf-8-sig")
    cycle_monthly.to_csv(output_map["cycle_monthly"], index=False, encoding="utf-8-sig")
    news_daily.to_csv(output_map["news_daily"], index=False, encoding="utf-8-sig")
    news_monthly.to_csv(output_map["news_monthly"], index=False, encoding="utf-8-sig")

    price_coverage = sum(1 for px, _src, _t in price_map.values() if not px.empty)
    manifest = pd.DataFrame([{
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "version": "v51_market_eval_intake",
        "field": field,
        "start": str(start_ts.date()),
        "end": str(end_ts.date()),
        "universe_rows": len(universe),
        "price_coverage_companies": price_coverage,
        "daily_rows": len(market_daily),
        "monthly_rows": len(market_monthly),
        "cycle_daily_rows": len(cycle_daily),
        "cycle_monthly_rows": len(cycle_monthly),
        "news_daily_rows": len(news_daily),
        "news_monthly_rows": len(news_monthly),
        "sensitivity_rows": len(sens_df),
        "workbook_source": workbook_source,
        "market_db_source": db_source,
        "issue_event_sources": issue_sources,
        "method": "src_eval-only market data_intake: price technicals, universe price proxy sector cycle, issue current/lag news windows, market DB/workbook sensitivity proxy",
        "cutoff_rule": "Every row uses only source dates <= as_of_date. current_window = month start ~ as_of_date; lag_window = previous month.",
    }])
    manifest.to_csv(output_map["manifest"], index=False, encoding="utf-8-sig")

    files = {k: str(v) for k, v in output_map.items()}
    row_counts = {
        "daily": len(market_daily),
        "monthly": len(market_monthly),
        "company_sensitivity": len(sens_df),
        "cycle_daily": len(cycle_daily),
        "cycle_monthly": len(cycle_monthly),
        "news_daily": len(news_daily),
        "news_monthly": len(news_monthly),
    }
    sources = {"workbook": workbook_source, "market_db": db_source, "issue_events": issue_sources}
    return MarketEvalIntakeResult(output_dir=str(out_dir), files=files, row_counts=row_counts, sources=sources)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build src_eval-only Market daily/monthly CSV inputs for evaluation/backtest")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2026-01-31")
    parser.add_argument("--universe-csv", default="")
    parser.add_argument("--no-workbook-url", action="store_true", help="Do not read MARKET_WORKBOOK_URL when local workbook is absent")
    parser.add_argument("--fetch-missing-price", action="store_true", help="If local price history is absent or stale, fetch KRX stocks through yfinance and cache under _sector_common/market/source_price_cache")
    parser.add_argument("--force-refresh-price-cache", action="store_true", help="Fetch and rewrite source_price_cache even when local price history already exists")
    parser.add_argument("--price-stale-days", type=int, default=int(os.getenv("MARKET_PRICE_STALE_DAYS", "5") or "5"), help="Treat local price history older than end-date minus this many days as stale")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-company price fetch progress logs")
    args = parser.parse_args(argv)
    result = build_market_evaluation_inputs(
        field=args.field,
        start=args.start,
        end=args.end,
        universe_csv=args.universe_csv or None,
        allow_workbook_url=not args.no_workbook_url,
        fetch_missing_price=args.fetch_missing_price,
        force_refresh_price_cache=args.force_refresh_price_cache,
        price_stale_days=args.price_stale_days,
        verbose=not args.quiet,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

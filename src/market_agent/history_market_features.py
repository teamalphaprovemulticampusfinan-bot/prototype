from __future__ import annotations

"""Shared market-history feature helpers for evaluation/data-intake flows.

The original evaluation builder imported these helpers from ``src_eval``.  In
Agent_6.9 the evaluation builder is now executed from the operational ``src``
tree, so this module provides the same lightweight contract directly under
``src/market_agent``.

Design goals:
- no LLM/API-key dependency;
- no import of the full Market Agent runtime;
- robust local price-history discovery across valuation, finance, market and
  sector cache folders;
- deterministic daily/monthly market-signal generation for evaluation inputs.
"""

from pathlib import Path
from typing import Any, Iterable
import math
import os

import numpy as np
import pandas as pd


MARKET_COLUMNS: list[str] = [
    "date",
    "as_of_date",
    "field",
    "company",
    "company_dir",
    "ticker",
    "stock_code",
    "frequency",
    "source_kind",
    "data_cutoff_ok",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "return_120d",
    "volatility_20d",
    "volatility_60d",
    "ma20",
    "ma60",
    "ma120",
    "ma20_gap",
    "ma60_gap",
    "ma120_gap",
    "rsi_14",
    "abnormal_volume",
    "volume_z",
    "relative_strength_vs_sector",
    "technical_signal",
    "technical_reliability",
    "sector_cycle_signal",
    "sector_cycle_reliability",
    "firm_market_sensitivity_signal",
    "firm_sensitivity_reliability",
    "current_window_news_signal",
    "lag_window_news_signal",
    "news_attention_signal",
    "news_count_current",
    "news_count_lag",
    "news_reliability",
    "news_cutoff_applied",
    "market_signal",
    "market_weighted_signal",
    "market_recommendation",
    "signal_reliability",
    "prob_sell",
    "prob_hold",
    "prob_buy",
    "evidence_note",
    "source_files",
]


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def project_root() -> Path:
    """Return the project root without depending on the process cwd."""
    env_root = os.getenv("ALPHAPROVE_PROJECT_ROOT_OVERRIDE", "").strip().strip('"').strip("'")
    if env_root:
        return Path(env_root).resolve()
    # .../src/market_agent/history_market_features.py -> project root
    return Path(__file__).resolve().parents[2]


def sector_market_dir(root: Path | str | None = None, field: str = "반도체") -> Path:
    root_path = Path(root).resolve() if root is not None else project_root()
    return root_path / "data" / field / "_sector_common" / "market"


def market_input_paths(root: Path | str | None = None, field: str = "반도체") -> dict[str, Path]:
    out_dir = sector_market_dir(root, field)
    return {
        "daily": out_dir / "market_signals_daily.csv",
        "monthly": out_dir / "market_signals_monthly.csv",
        "company_sensitivity": out_dir / "company_market_sensitivity.csv",
        "cycle_daily": out_dir / "semiconductor_cycle_daily.csv",
        "cycle_monthly": out_dir / "semiconductor_cycle_monthly.csv",
        "news_daily": out_dir / "market_news_attention_daily.csv",
        "news_monthly": out_dir / "market_news_attention_monthly.csv",
        "manifest": out_dir / "market_feature_manifest.csv",
    }


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _norm_col(name: Any) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float, np.integer, np.floating)):
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


def clip_signal(value: Any, lo: float = -1.0, hi: float = 1.0) -> float:
    x = _safe_float(value, 0.0) or 0.0
    return float(max(lo, min(hi, x)))


def tanh_scale(value: Any, scale: float = 1.0) -> float:
    x = _safe_float(value, 0.0) or 0.0
    s = abs(float(scale)) if scale else 1.0
    return clip_signal(float(math.tanh(x / s)))


def _read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists() or not path.is_file():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path)


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the common market columns while preserving extra columns."""
    out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    for col in MARKET_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    # Keep canonical columns first, then any extra source columns.
    extras = [c for c in out.columns if c not in MARKET_COLUMNS]
    return out[MARKET_COLUMNS + extras]


def _to_datetime_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.tz_localize(None)


def _normalize_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    work = df.copy()
    rename: dict[str, str] = {}
    for col in work.columns:
        n = _norm_col(col)
        if n in {"date", "datetime", "time", "일자", "날짜", "basdt", "trd_dd"}:
            rename[col] = "date"
        elif n in {"open", "open_price", "시가"}:
            rename[col] = "open"
        elif n in {"high", "high_price", "고가"}:
            rename[col] = "high"
        elif n in {"low", "low_price", "저가"}:
            rename[col] = "low"
        elif n in {"close", "adj_close", "close_price", "종가", "clpr", "price", "현재가"}:
            # Prefer an explicit close column over adj_close when both exist.
            if n == "adj_close" and "close" in [_norm_col(c) for c in work.columns]:
                rename[col] = "adj_close"
            else:
                rename[col] = "close" if "close" not in rename.values() else "adj_close"
        elif n in {"volume", "거래량", "trqu", "acc_trdvol"}:
            rename[col] = "volume"
        elif n in {"ticker", "stock_code", "symbol", "종목코드", "srtncd"}:
            rename[col] = "ticker"
    work = work.rename(columns=rename)
    if "date" not in work.columns or "close" not in work.columns:
        return pd.DataFrame()
    keep = [c for c in ["date", "open", "high", "low", "close", "adj_close", "volume", "ticker", "source"] if c in work.columns]
    out = work[keep].copy()
    out["date"] = _to_datetime_series(out["date"])
    for col in ["open", "high", "low", "close", "adj_close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if "adj_close" not in out.columns:
        out["adj_close"] = out["close"]
    if "volume" not in out.columns:
        out["volume"] = np.nan
    out = out.dropna(subset=["date", "close"]).sort_values("date")
    out = out.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return out


def _company_folder_candidates(root: Path, field: str, target: dict[str, Any]) -> list[Path]:
    names = []
    for k in ("company", "company_name", "company_dir", "slug"):
        v = str(target.get(k) or "").strip()
        if v and v.lower() not in {"nan", "none"}:
            names.append(v)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[Path] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        out.append(root / "data" / field / name)
    return out


def _price_file_candidates(root: Path, field: str, target: dict[str, Any]) -> list[Path]:
    code = str(target.get("stock_code") or target.get("ticker") or "").replace(".0", "").zfill(6)
    cands: list[Path] = []
    for company_dir in _company_folder_candidates(root, field, target):
        cands.extend([
            company_dir / "valuation" / "intake" / "valuation_price_history.csv",
            company_dir / "valuation" / "intake" / "price_history.csv",
            company_dir / "valuation" / "intake" / "raw" / f"naver_price_{code}.csv",
            company_dir / "valuation" / "source" / "valuation_manual_price_template.csv",
        ])
        cands.extend(sorted((company_dir / "finance").glob("*_stock.csv")))
        cands.extend(sorted((company_dir / "market").glob("*price*.csv")))
    if code and code != "000000":
        cands.extend([
            root / "data" / field / "_sector_common" / "market" / "source_price_cache" / f"{code}.csv",
            root / "data" / "market_excel" / "market_data" / f"{code}.csv",
        ])
    return cands


def load_price_history(root: Path | str | None, field: str, target: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    """Load local price history for a target company.

    Returns a normalized DataFrame with at least ``date``, ``close`` and
    ``volume`` when available.  It intentionally does not fetch the network;
    evaluation_builder controls optional yfinance fetch and cache creation.
    """
    root_path = Path(root).resolve() if root is not None else project_root()
    tried: list[str] = []
    for path in _price_file_candidates(root_path, field, target):
        tried.append(str(path))
        df = _normalize_price_frame(_read_csv_any(path))
        if not df.empty:
            return df, str(path)
    return pd.DataFrame(), ";".join(tried[:8])


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=max(3, window // 2)).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=max(3, window // 2)).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _technical_row(px: pd.DataFrame, dt: pd.Timestamp) -> dict[str, Any]:
    df = _normalize_price_frame(px)
    if df.empty:
        return {
            "technical_signal": 0.0,
            "technical_reliability": 0.0,
            "data_cutoff_ok": True,
        }
    dt = pd.Timestamp(dt).normalize()
    hist = df[df["date"] <= dt].copy()
    if hist.empty:
        return {"technical_signal": 0.0, "technical_reliability": 0.0, "data_cutoff_ok": True}
    hist = hist.sort_values("date").reset_index(drop=True)
    close = pd.to_numeric(hist["close"], errors="coerce")
    vol = pd.to_numeric(hist.get("volume", pd.Series(np.nan, index=hist.index)), errors="coerce")
    hist["return_1d"] = close.pct_change(1)
    hist["return_5d"] = close.pct_change(5)
    hist["return_20d"] = close.pct_change(20)
    hist["return_60d"] = close.pct_change(60)
    hist["return_120d"] = close.pct_change(120)
    hist["ma20"] = close.rolling(20, min_periods=5).mean()
    hist["ma60"] = close.rolling(60, min_periods=15).mean()
    hist["ma120"] = close.rolling(120, min_periods=30).mean()
    hist["ma20_gap"] = close / hist["ma20"] - 1.0
    hist["ma60_gap"] = close / hist["ma60"] - 1.0
    hist["ma120_gap"] = close / hist["ma120"] - 1.0
    hist["volatility_20d"] = hist["return_1d"].rolling(20, min_periods=5).std() * math.sqrt(252)
    hist["volatility_60d"] = hist["return_1d"].rolling(60, min_periods=15).std() * math.sqrt(252)
    hist["rsi_14"] = _rsi(close, 14)
    vol_ma20 = vol.rolling(20, min_periods=5).mean()
    vol_std20 = vol.rolling(20, min_periods=5).std()
    hist["volume_z"] = (vol - vol_ma20) / vol_std20.replace(0, np.nan)
    hist["abnormal_volume"] = vol / vol_ma20.replace(0, np.nan)
    row = hist.iloc[-1].to_dict()

    ret20 = _safe_float(row.get("return_20d"), 0.0) or 0.0
    ret60 = _safe_float(row.get("return_60d"), 0.0) or 0.0
    ma20_gap = _safe_float(row.get("ma20_gap"), 0.0) or 0.0
    ma60_gap = _safe_float(row.get("ma60_gap"), 0.0) or 0.0
    rsi14 = _safe_float(row.get("rsi_14"), 50.0) or 50.0
    # Momentum plus trend, with RSI extremes used as a small contrarian guard.
    momentum_sig = 0.45 * tanh_scale(ret20, 0.12) + 0.25 * tanh_scale(ret60, 0.20)
    trend_sig = 0.20 * tanh_scale(ma20_gap, 0.10) + 0.10 * tanh_scale(ma60_gap, 0.15)
    if rsi14 >= 75:
        rsi_adj = -0.10
    elif rsi14 <= 25:
        rsi_adj = 0.10
    else:
        rsi_adj = 0.0
    signal = clip_signal(momentum_sig + trend_sig + rsi_adj)
    reliability = min(1.0, max(0.15, len(hist) / 120.0))

    keep = {
        "open", "high", "low", "close", "adj_close", "volume", "return_1d", "return_5d", "return_20d", "return_60d",
        "return_120d", "volatility_20d", "volatility_60d", "ma20", "ma60", "ma120", "ma20_gap", "ma60_gap",
        "ma120_gap", "rsi_14", "abnormal_volume", "volume_z",
    }
    out = {k: row.get(k) for k in keep if k in row}
    out.update({
        "technical_signal": signal,
        "technical_reliability": float(reliability),
        "data_cutoff_ok": True,
    })
    return out


def _sector_cycle_signal(row: dict[str, Any] | pd.Series) -> tuple[float, float, str]:
    r = dict(row) if not isinstance(row, dict) else row
    candidates = [
        ("sector_cycle_signal", 1.00),
        ("sox_momentum", 0.35),
        ("chip_sales_momentum", 0.30),
        ("semiconductor_cycle_signal", 0.50),
        ("external__sox_return_20d", 0.25),
        ("external__nasdaq_return_20d", 0.15),
        ("external__sp500_return_20d", 0.10),
    ]
    vals: list[tuple[float, float, str]] = []
    for key, weight in candidates:
        if key in r:
            v = _safe_float(r.get(key))
            if v is not None:
                vals.append((clip_signal(v), weight, key))
    if not vals:
        return 0.0, 0.0, "NO_SECTOR_CYCLE_INPUT"
    wsum = sum(w for _v, w, _k in vals) or 1.0
    sig = clip_signal(sum(v * w for v, w, _k in vals) / wsum)
    rel = _safe_float(r.get("sector_cycle_reliability"), None)
    if rel is None:
        rel = min(1.0, 0.35 + 0.15 * len(vals))
    return sig, float(max(0.0, min(1.0, rel))), ",".join(k for _v, _w, k in vals)


def _firm_sensitivity_signal(row: dict[str, Any] | pd.Series, sens: dict[str, Any] | None = None) -> tuple[float, float, str]:
    r = dict(row) if not isinstance(row, dict) else row
    s = sens or {}
    sox = _safe_float(r.get("sox_momentum"), _safe_float(r.get("sector_cycle_signal"), 0.0)) or 0.0
    fx = _safe_float(r.get("fx_signal"), 0.0) or 0.0
    rate = _safe_float(r.get("rate_signal"), 0.0) or 0.0
    raw = _safe_float(r.get("raw_material_signal"), 0.0) or 0.0
    sox_beta = _safe_float(s.get("sox_beta"), 0.55) or 0.55
    fx_beta = _safe_float(s.get("fx_beta"), 0.20) or 0.20
    rate_beta = _safe_float(s.get("rate_sensitivity"), -0.25) or -0.25
    raw_beta = _safe_float(s.get("raw_material_beta"), -0.15) or -0.15
    # Negative beta means rising cost/rates are bad. The input signal sign is
    # preserved and beta sign reflects exposure direction.
    sig = clip_signal(sox * sox_beta + fx * fx_beta + rate * rate_beta + raw * raw_beta)
    available = sum(1 for x in [sox, fx, rate, raw] if x is not None)
    rel = min(1.0, 0.35 + 0.12 * available)
    if str(s.get("confidence", "")).lower() in {"high", "높음"}:
        rel = min(1.0, rel + 0.15)
    return sig, rel, "sox/fx/rate/raw sensitivity proxy"


def _news_signal(row: dict[str, Any] | pd.Series, frequency: str = "daily") -> tuple[float, float, str]:
    r = dict(row) if not isinstance(row, dict) else row
    sig = _safe_float(r.get("news_attention_signal"), None)
    if sig is None:
        cur = _safe_float(r.get("current_window_news_signal"), 0.0) or 0.0
        lag = _safe_float(r.get("lag_window_news_signal"), 0.0) or 0.0
        sig = 0.7 * cur + 0.3 * lag
    cnt = (_safe_float(r.get("news_count_current"), 0.0) or 0.0) + 0.5 * (_safe_float(r.get("news_count_lag"), 0.0) or 0.0)
    rel = _safe_float(r.get("news_reliability"), None)
    if rel is None:
        rel = min(1.0, cnt / (8.0 if frequency == "daily" else 15.0)) if cnt > 0 else 0.0
    return clip_signal(sig), float(max(0.0, min(1.0, rel))), "current_month_70_lag_month_30"


def _combine_blocks(blocks: Iterable[tuple[str, float, float]]) -> tuple[float, float, dict[str, float]]:
    clean: list[tuple[str, float, float]] = []
    for name, signal, reliability in blocks:
        sig = clip_signal(signal)
        rel = max(0.0, min(1.0, _safe_float(reliability, 0.0) or 0.0))
        if rel > 0:
            clean.append((name, sig, rel))
    if not clean:
        return 0.0, 0.0, {}
    total_rel = sum(rel for _name, _sig, rel in clean) or 1.0
    weights = {name: rel / total_rel for name, _sig, rel in clean}
    combined = clip_signal(sum(sig * weights[name] for name, sig, _rel in clean))
    reliability = min(1.0, total_rel / max(1.0, len(clean)))
    return combined, reliability, weights


def _softmax_recommendation(signal: Any, reliability: float = 1.0) -> tuple[str, dict[str, float]]:
    sig = clip_signal(signal)
    rel = max(0.05, min(1.0, _safe_float(reliability, 1.0) or 1.0))
    # Three-class probabilities without hard arbitrary thresholding.  Stronger
    # reliability sharpens Buy/Sell probabilities; lower reliability leaves Hold
    # dominant.
    sell_logit = -2.2 * sig * rel
    buy_logit = 2.2 * sig * rel
    hold_logit = 0.45 * (1.0 - abs(sig)) + 0.35 * (1.0 - rel)
    logits = np.array([sell_logit, hold_logit, buy_logit], dtype=float)
    logits = logits - np.nanmax(logits)
    exps = np.exp(logits)
    probs_arr = exps / exps.sum()
    labels = ["매도", "보유", "매수"]
    probs = {label: float(prob) for label, prob in zip(labels, probs_arr)}
    rec = labels[int(np.argmax(probs_arr))]
    return rec, probs

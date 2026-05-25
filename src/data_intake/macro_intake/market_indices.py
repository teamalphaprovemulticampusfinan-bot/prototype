from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

import pandas as pd

from .collector import fetch_fred_daily, fetch_yf, merge_dfs
from .normalizer import normalize


TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class MarketIndexSpec:
    label: str
    pykrx_ticker: str | None = None
    pykrx_market: str | None = None
    fred_series: str | None = None
    yahoo_ticker: str | None = None
    official_csv_env: str | None = None
    proxy_label: str | None = None
    proxy_yahoo_ticker: str | None = None


# Korean index values are collected from KRX-compatible index OHLCV when pykrx
# is installed.  US broad-market values are collected from FRED official series
# where available.  Yahoo is retained only as a non-sample market-data fallback.
MARKET_INDEX_SPECS: tuple[MarketIndexSpec, ...] = (
    MarketIndexSpec("KOSPI_지수", pykrx_ticker="1001", pykrx_market="KOSPI", yahoo_ticker="^KS11"),
    MarketIndexSpec("KOSDAQ_지수", pykrx_ticker="2001", pykrx_market="KOSDAQ", yahoo_ticker="^KQ11"),
    MarketIndexSpec("코스피200", pykrx_ticker="1028", pykrx_market="KOSPI", yahoo_ticker="^KS200"),
    MarketIndexSpec(
        "KRX_반도체_지수",
        pykrx_ticker="5044",
        pykrx_market="KRX",
        official_csv_env="MACRO_KRX_SEMICONDUCTOR_INDEX_CSV",
        proxy_label="KRX_반도체_프록시_KODEX반도체",
        proxy_yahoo_ticker="091160.KS",
    ),
    MarketIndexSpec("나스닥", fred_series="NASDAQCOM", yahoo_ticker="^IXIC"),
    MarketIndexSpec(
        "SOX_반도체_지수",
        official_csv_env="MACRO_SOX_INDEX_CSV",
        yahoo_ticker="^SOX",
    ),
    MarketIndexSpec("S&P500", fred_series="SP500", yahoo_ticker="^GSPC"),
)

KOREA_MARKET_LABELS = ("KOSPI_지수", "KOSDAQ_지수", "코스피200")
US_MARKET_LABELS = ("나스닥", "S&P500")
SEMICONDUCTOR_LABELS = ("KRX_반도체_지수", "KRX_반도체_프록시_KODEX반도체", "SOX_반도체_지수")
ALL_BENCHMARK_LABELS = (
    "KOSPI_지수",
    "KOSDAQ_지수",
    "코스피200",
    "KRX_반도체_지수",
    "KRX_반도체_프록시_KODEX반도체",
    "나스닥",
    "SOX_반도체_지수",
    "S&P500",
)


def _empty_index_frame(label: str) -> pd.DataFrame:
    return pd.DataFrame(columns=["date", label])


def _read_official_csv(env_name: str | None, label: str) -> pd.DataFrame | None:
    if not env_name:
        return None
    raw_path = os.getenv(env_name, "").strip().strip('"')
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.exists():
        print(f"  ⚠️ [{label}] 공식 CSV 경로 없음: {path}")
        return None

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949")
    except Exception as exc:
        print(f"  ⚠️ [{label}] 공식 CSV 로드 실패: {type(exc).__name__}: {exc}")
        return None

    if df.empty:
        return None

    date_col = next((c for c in df.columns if str(c).lower() in {"date", "날짜", "일자", "trd_dd", "bas_dd"}), df.columns[0])
    value_col = label if label in df.columns else None
    if value_col is None:
        candidates = [c for c in df.columns if c != date_col]
        value_col = candidates[-1] if candidates else None
    if value_col is None:
        return None

    out = df[[date_col, value_col]].copy()
    out.columns = ["date", label]
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out[label] = pd.to_numeric(out[label], errors="coerce")
    out = out.dropna(subset=["date", label]).sort_values("date")
    if out.empty:
        return None

    print(f"  ✅ [{label}] 사용자 제공 공식 CSV 사용: {path}")
    return out


def _fetch_pykrx_index(ticker: str, label: str, start: str, end: str) -> pd.DataFrame | None:
    try:
        from pykrx import stock  # type: ignore
    except Exception as exc:
        print(f"  ⚠️ pykrx import 실패 [{label}] → 다른 공식/시장 데이터 소스 시도: {type(exc).__name__}")
        return None

    try:
        df = stock.get_index_ohlcv_by_date(start.replace("-", ""), end.replace("-", ""), ticker, freq="d")
        if df is None or df.empty:
            print(f"  ⚠️ KRX index [{label}/{ticker}]: 빈 응답")
            return None

        out = df.reset_index()
        date_col = "날짜" if "날짜" in out.columns else out.columns[0]
        close_col = "종가" if "종가" in out.columns else None
        if close_col is None:
            numeric_cols = [c for c in out.columns if c != date_col and pd.api.types.is_numeric_dtype(out[c])]
            close_col = numeric_cols[-1] if numeric_cols else None
        if close_col is None:
            print(f"  ⚠️ KRX index [{label}/{ticker}]: 종가 컬럼 없음")
            return None

        out = out[[date_col, close_col]].copy()
        out.columns = ["date", label]
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out[label] = pd.to_numeric(out[label], errors="coerce")
        out = out.dropna(subset=["date", label]).sort_values("date")
        if out.empty:
            return None

        print(f"  ✅ [{label}] KRX index 수집 완료: rows={len(out)}")
        return out
    except Exception as exc:
        print(f"  ⚠️ KRX index [{label}/{ticker}] 오류: {type(exc).__name__}: {exc}")
        return None


def _fetch_fred_index(series_id: str, label: str, start: str, end: str) -> pd.DataFrame | None:
    try:
        df = fetch_fred_daily(series_id, label, start, end)
        if df is None or df.empty:
            return None
        df = df[["date", label]].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df[label] = pd.to_numeric(df[label], errors="coerce")
        df = df.dropna(subset=["date", label]).sort_values("date")
        if df.empty:
            return None
        print(f"  ✅ [{label}] FRED 공식 계열 수집 완료: {series_id}, rows={len(df)}")
        return df
    except Exception as exc:
        print(f"  ⚠️ FRED [{label}/{series_id}] 오류: {type(exc).__name__}: {exc}")
        return None


def _fetch_yahoo_index(ticker: str, label: str, start: str, end: str) -> pd.DataFrame | None:
    try:
        df = fetch_yf(ticker, label, start, end)
        if df is None or df.empty:
            return None
        df = df[["date", label]].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df[label] = pd.to_numeric(df[label], errors="coerce")
        df = df.dropna(subset=["date", label]).sort_values("date")
        if df.empty:
            return None
        print(f"  ⚠️ [{label}] 공식값 부재 → Yahoo market-data fallback 사용: {ticker}, rows={len(df)}")
        return df
    except Exception as exc:
        print(f"  ⚠️ Yahoo [{label}/{ticker}] 오류: {type(exc).__name__}: {exc}")
        return None


def _fetch_index(spec: MarketIndexSpec, start: str, end: str) -> pd.DataFrame | None:
    # 1) user-provided official CSV
    df = _read_official_csv(spec.official_csv_env, spec.label)
    if df is not None and not df.empty:
        return df

    # 2) KRX-compatible official index series
    if spec.pykrx_ticker:
        df = _fetch_pykrx_index(spec.pykrx_ticker, spec.label, start, end)
        if df is not None and not df.empty:
            return df

    # 3) FRED official series for US indices where available
    if spec.fred_series:
        df = _fetch_fred_index(spec.fred_series, spec.label, start, end)
        if df is not None and not df.empty:
            return df

    # 4) market-data fallback, never sample values
    if spec.yahoo_ticker:
        df = _fetch_yahoo_index(spec.yahoo_ticker, spec.label, start, end)
        if df is not None and not df.empty:
            return df

    # 5) explicit proxy for KRX semiconductor if direct index unavailable
    if spec.proxy_label and spec.proxy_yahoo_ticker:
        proxy = _fetch_yahoo_index(spec.proxy_yahoo_ticker, spec.proxy_label, start, end)
        if proxy is not None and not proxy.empty:
            print(f"  ⚠️ [{spec.label}] 직접 지수 없음 → ETF 추적 프록시 저장: {spec.proxy_label}")
            return proxy

    print(f"  ⚠️ [{spec.label}] 수집 실패 → 임의 sample 값 생성하지 않음")
    return None


def _safe_pct_change(series: pd.Series, periods: int) -> pd.Series:
    return series.pct_change(periods=periods, fill_method=None) * 100.0


def _available_columns(df: pd.DataFrame, labels: Iterable[str], suffix: str = "") -> list[str]:
    cols: list[str] = []
    for label in labels:
        col = f"{label}{suffix}"
        if col in df.columns:
            cols.append(col)
    return cols


def _mean_columns(df: pd.DataFrame, labels: Iterable[str], suffix: str) -> pd.Series | None:
    cols = _available_columns(df, labels, suffix)
    if not cols:
        return None
    return df[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1, skipna=True)


def _add_index_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    for label in ALL_BENCHMARK_LABELS:
        if label not in df.columns:
            continue
        values = pd.to_numeric(df[label], errors="coerce")
        # Remove impossible index values.  No sample replacement.
        values = values.mask(values <= 0)
        df[label] = values

        for period in (1, 5, 20, 60):
            df[f"{label}_수익률_{period}일"] = _safe_pct_change(values, period)

        ret_20 = df[f"{label}_수익률_20일"]
        df[f"{label}_변동성_20일"] = (
            values.pct_change(fill_method=None)
            .rolling(20, min_periods=10)
            .std()
            * (TRADING_DAYS_PER_YEAR ** 0.5)
            * 100.0
        )
        df[f"{label}_변동성_z_252일"] = (
            df[f"{label}_변동성_20일"]
            - df[f"{label}_변동성_20일"].rolling(252, min_periods=60).mean()
        ) / df[f"{label}_변동성_20일"].rolling(252, min_periods=60).std()
        df[f"{label}_모멘텀_20_60"] = ret_20 - df[f"{label}_수익률_60일"]

    base_market = ("KOSPI_지수", "KOSDAQ_지수", "나스닥", "S&P500")
    for period in (1, 5, 20, 60):
        mean_ret = _mean_columns(df, base_market, f"_수익률_{period}일")
        if mean_ret is not None:
            df[f"시장수익률_{period}일"] = mean_ret

    market_vol = _mean_columns(df, base_market, "_변동성_20일")
    if market_vol is not None:
        df["시장변동성_20일"] = market_vol

    market_vol_z = _mean_columns(df, base_market, "_변동성_z_252일")
    if market_vol_z is not None:
        df["시장변동성_z_252일"] = market_vol_z

    market_momentum = _mean_columns(df, base_market, "_모멘텀_20_60")
    if market_momentum is not None:
        df["시장모멘텀_20_60"] = market_momentum

    korea_ret = _mean_columns(df, KOREA_MARKET_LABELS, "_수익률_20일")
    if korea_ret is not None:
        df["한국시장수익률_20일"] = korea_ret

    us_ret = _mean_columns(df, US_MARKET_LABELS, "_수익률_20일")
    if us_ret is not None:
        df["미국시장수익률_20일"] = us_ret

    semi_ret = _mean_columns(df, SEMICONDUCTOR_LABELS, "_수익률_20일")
    if semi_ret is not None:
        df["반도체섹터수익률_20일"] = semi_ret

    semi_vol = _mean_columns(df, SEMICONDUCTOR_LABELS, "_변동성_20일")
    if semi_vol is not None:
        df["반도체섹터변동성_20일"] = semi_vol

    semi_momentum = _mean_columns(df, SEMICONDUCTOR_LABELS, "_모멘텀_20_60")
    if semi_momentum is not None:
        df["반도체섹터모멘텀_20_60"] = semi_momentum

    risk_cols = _available_columns(df, ALL_BENCHMARK_LABELS, "_수익률_20일")
    momentum_cols = _available_columns(df, ALL_BENCHMARK_LABELS, "_모멘텀_20_60")
    flags = []
    if risk_cols:
        flags.append(df[risk_cols].apply(pd.to_numeric, errors="coerce") < 0)
    if momentum_cols:
        flags.append(df[momentum_cols].apply(pd.to_numeric, errors="coerce") < 0)
    if flags:
        merged = pd.concat(flags, axis=1)
        df["시장_risk_off_비율"] = merged.mean(axis=1, skipna=True)

    return df


def collect_market_index_benchmarks(start: str, end: str) -> pd.DataFrame:
    """Collect market/sector index benchmarks.

    The function never creates sample values.  Missing official values remain
    missing and are later written as NA columns by schema_tools.
    """

    print("\n[시장 지수] KRX/FRED/Yahoo fallback 벤치마크 수집 시작")
    frames: list[pd.DataFrame] = []

    for spec in MARKET_INDEX_SPECS:
        frame = _fetch_index(spec, start, end)
        if frame is not None and not frame.empty:
            frames.append(frame)

    if not frames:
        print("⚠️ 시장 지수 수집 결과 없음")
        return pd.DataFrame(columns=["date", *ALL_BENCHMARK_LABELS])

    merged = merge_dfs(frames)
    if merged is None or merged.empty:
        return pd.DataFrame(columns=["date", *ALL_BENCHMARK_LABELS])

    merged = normalize(merged)
    merged = _add_index_features(merged)
    print(f"✅ 시장 지수 벤치마크 수집 완료: rows={len(merged)}, cols={len(merged.columns)}")
    return merged

from __future__ import annotations

"""
Macro 변화율/rolling 기준 유틸리티.

설계 원칙
---------
1. 전일/5/20/60영업일 변화율은 pandas pct_change(periods=n, fill_method=None)로 계산한다.
2. z-score는 현재값을 직전 rolling window의 평균/표준편차와 비교한다.
   - shift(1)을 적용해 현재값이 기준 평균/표준편차 계산에 섞이지 않도록 한다.
3. 급등/급락 cutoff는 고정 숫자가 아니라 직전 rolling window의 경험적 분위수로 계산한다.
   - watch: 5% / 95%
   - extreme: 1% / 99%
4. z-score 경계는 통계적 공정관리에서 널리 쓰이는 ±2σ watch, ±3σ extreme을 사용한다.
   - ±3σ는 NIST Engineering Statistics Handbook의 control chart 기준과 맞춘다.
5. 기본값은 최신 row 판정에 필요한 cutoff만 계산한다.
   - 전체 과거 행별 cutoff가 필요하면 MACRO_ROLLING_FULL_HISTORY=1 로 전환한다.
   - 기본값은 속도 우선이며, as-of-date별 파이프라인에서는 각 실행 시점의 latest row가 해당 기준일이므로
     미래 데이터 누수 없이 동작한다.
"""

import math
import os
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


DAILY_WINDOWS: Tuple[int, ...] = (1, 5, 20, 60)
MONTHLY_WINDOWS: Tuple[int, ...] = (1, 3, 6, 12)

DEFAULT_DAILY_Z_WINDOW = int(os.getenv("MACRO_ROLLING_Z_WINDOW_DAILY", "252"))
DEFAULT_MONTHLY_Z_WINDOW = int(os.getenv("MACRO_ROLLING_Z_WINDOW_MONTHLY", "60"))

DEFAULT_DAILY_MIN_OBS = int(os.getenv("MACRO_ROLLING_MIN_OBS_DAILY", "60"))
DEFAULT_MONTHLY_MIN_OBS = int(os.getenv("MACRO_ROLLING_MIN_OBS_MONTHLY", "24"))

WATCH_Z = float(os.getenv("MACRO_ROLLING_WATCH_Z", "2.0"))
EXTREME_Z = float(os.getenv("MACRO_ROLLING_EXTREME_Z", "3.0"))

WATCH_LOW_Q = float(os.getenv("MACRO_ROLLING_WATCH_LOW_Q", "0.05"))
WATCH_HIGH_Q = float(os.getenv("MACRO_ROLLING_WATCH_HIGH_Q", "0.95"))
EXTREME_LOW_Q = float(os.getenv("MACRO_ROLLING_EXTREME_LOW_Q", "0.01"))
EXTREME_HIGH_Q = float(os.getenv("MACRO_ROLLING_EXTREME_HIGH_Q", "0.99"))

FULL_HISTORY = os.getenv("MACRO_ROLLING_FULL_HISTORY", "0").strip() == "1"


_GENERATED_SUFFIX_MARKERS = (
    "_diff",
    "_pct_change",
    "_ma5",
    "_ma20",
    "_trend",
    "_chg_",
    "_delta_",
    "_bp_",
    "_zscore_",
    "_rolling_mean_",
    "_rolling_std_",
    "_mean_reversion_signal",
    "_z_alert",
    "_shock_flag",
    "_shock_cutoff_",
)


def is_generated_feature_column(col: str) -> bool:
    name = str(col)
    return any(marker in name for marker in _GENERATED_SUFFIX_MARKERS)


def numeric_source_columns(df: pd.DataFrame) -> List[str]:
    cols: List[str] = []
    for col in df.columns:
        if col == "date" or is_generated_feature_column(col):
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() >= 2:
            cols.append(str(col))
    return cols


def infer_frequency(dataset_name: str, df: pd.DataFrame) -> str:
    name = str(dataset_name or "").lower()
    if "월별" in name or "monthly" in name:
        return "monthly"
    if "분기" in name or "quarter" in name:
        return "quarterly"

    if "일별" in name or "daily" in name or "시장" in name or "benchmark" in name:
        return "daily"

    # 이름으로 판단이 안 되면 날짜 간격의 중앙값으로 추정한다.
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna().sort_values()
        if len(dates) >= 3:
            median_days = dates.diff().dt.days.dropna().median()
            if pd.notna(median_days):
                if median_days <= 10:
                    return "daily"
                if median_days <= 45:
                    return "monthly"
                return "quarterly"
    return "daily"


def _safe_pct_change(series: pd.Series, periods: int) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").pct_change(periods=periods, fill_method=None) * 100.0
    return out.replace([math.inf, -math.inf], pd.NA)


def _rolling_zscore(series: pd.Series, window: int, min_obs: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    s = pd.to_numeric(series, errors="coerce")
    # 현재값을 기준 평균/표준편차에 포함하지 않도록 shift(1)
    base = s.shift(1)
    mean = base.rolling(window=window, min_periods=min_obs).mean()
    std = base.rolling(window=window, min_periods=min_obs).std(ddof=0)
    std = std.where(std.abs() > 1e-12)
    z = (s - mean) / std
    return z.replace([math.inf, -math.inf], pd.NA), mean, std


def _alert_from_z(z: pd.Series) -> pd.Series:
    def _one(v: Any) -> int:
        try:
            x = float(v)
        except Exception:
            return 0
        if not math.isfinite(x):
            return 0
        if x >= EXTREME_Z:
            return 2
        if x >= WATCH_Z:
            return 1
        if x <= -EXTREME_Z:
            return -2
        if x <= -WATCH_Z:
            return -1
        return 0

    return z.map(_one).astype("int16")


def _latest_cutoffs_from_prior_window(
    change_series: pd.Series,
    window: int,
    min_obs: int,
) -> Dict[str, float | None]:
    s = pd.to_numeric(change_series, errors="coerce").replace([math.inf, -math.inf], pd.NA).dropna()
    # latest 변화율을 제외한 직전 window로 cutoff를 산정한다.
    if len(s) <= min_obs:
        return {"q01": None, "q05": None, "q95": None, "q99": None, "obs": int(len(s))}
    prior = s.iloc[-(window + 1):-1] if len(s) > window else s.iloc[:-1]
    if len(prior) < min_obs:
        return {"q01": None, "q05": None, "q95": None, "q99": None, "obs": int(len(prior))}
    return {
        "q01": float(prior.quantile(EXTREME_LOW_Q)),
        "q05": float(prior.quantile(WATCH_LOW_Q)),
        "q95": float(prior.quantile(WATCH_HIGH_Q)),
        "q99": float(prior.quantile(EXTREME_HIGH_Q)),
        "obs": int(len(prior)),
    }


def _shock_flag_from_cutoffs(latest_change: Any, cutoffs: Dict[str, float | None]) -> int:
    try:
        x = float(latest_change)
    except Exception:
        return 0
    if not math.isfinite(x):
        return 0
    q01, q05, q95, q99 = (cutoffs.get("q01"), cutoffs.get("q05"), cutoffs.get("q95"), cutoffs.get("q99"))
    if x > 0 and q99 is not None and x >= q99:
        return 2
    if x > 0 and q95 is not None and x >= q95:
        return 1
    if x < 0 and q01 is not None and x <= q01:
        return -2
    if x < 0 and q05 is not None and x <= q05:
        return -1
    return 0


def _rolling_shock_flags_full_history(change_series: pd.Series, window: int, min_obs: int) -> Tuple[pd.Series, pd.DataFrame]:
    s = pd.to_numeric(change_series, errors="coerce").replace([math.inf, -math.inf], pd.NA)
    base = s.shift(1)
    q01 = base.rolling(window=window, min_periods=min_obs).quantile(EXTREME_LOW_Q)
    q05 = base.rolling(window=window, min_periods=min_obs).quantile(WATCH_LOW_Q)
    q95 = base.rolling(window=window, min_periods=min_obs).quantile(WATCH_HIGH_Q)
    q99 = base.rolling(window=window, min_periods=min_obs).quantile(EXTREME_HIGH_Q)

    flag = pd.Series(0, index=s.index, dtype="int16")
    # 급등/급락은 변화율 방향도 함께 본다.
    # 예: 완만한 우상향 시계열에서 작은 양(+)의 변화가 하위 1%라는 이유만으로
    # "급락"으로 분류되는 것을 방지한다.
    flag = flag.mask((s > 0) & (s >= q95) & q95.notna(), 1)
    flag = flag.mask((s > 0) & (s >= q99) & q99.notna(), 2)
    flag = flag.mask((s < 0) & (s <= q05) & q05.notna(), -1)
    flag = flag.mask((s < 0) & (s <= q01) & q01.notna(), -2)

    cutoffs = pd.DataFrame({"q01": q01, "q05": q05, "q95": q95, "q99": q99}, index=s.index)
    return flag, cutoffs


def add_rolling_criteria_features(df: pd.DataFrame, dataset_name: str = "") -> pd.DataFrame:
    """전일/5/20/60 변화율, rolling z-score, 평균회귀, 급등/급락 cutoff 컬럼을 추가한다."""
    if df is None or df.empty or "date" not in df.columns:
        return df

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    freq = infer_frequency(dataset_name, out)
    if freq == "quarterly":
        # 분기 데이터는 변화율 기준의 실시간 민감도가 낮으므로 z-score만 최소 생성하지 않고 원본 유지.
        out.attrs["rolling_criteria"] = {"frequency": "quarterly", "applied": False}
        return out

    is_daily = freq == "daily"
    windows = DAILY_WINDOWS if is_daily else MONTHLY_WINDOWS
    unit = "bd" if is_daily else "m"
    z_window = DEFAULT_DAILY_Z_WINDOW if is_daily else DEFAULT_MONTHLY_Z_WINDOW
    min_obs = DEFAULT_DAILY_MIN_OBS if is_daily else DEFAULT_MONTHLY_MIN_OBS

    source_cols = numeric_source_columns(out)
    if not source_cols:
        out.attrs["rolling_criteria"] = {"frequency": freq, "applied": False, "reason": "numeric_source_columns 없음"}
        return out

    new_cols: Dict[str, Any] = {}

    for col in source_cols:
        s = pd.to_numeric(out[col], errors="coerce")

        # 수준 변화량: 금리/스프레드는 %p 단위 변화가 pct 변화보다 해석 안정적이라 함께 제공.
        new_cols[f"{col}_diff_1{unit}"] = s.diff(1)

        for w in windows:
            new_cols[f"{col}_chg_{w}{unit}_pct"] = _safe_pct_change(s, w)

            if any(token in col.lower() for token in ["금리", "스프레드", "yield", "rate", "spread"]):
                # 입력 금리가 보통 % 단위이므로 *100 = bp 변화.
                new_cols[f"{col}_bp_change_{w}{unit}"] = s.diff(w) * 100.0

        z, mean, std = _rolling_zscore(s, z_window, min_obs)
        new_cols[f"{col}_rolling_mean_{z_window}{unit}"] = mean
        new_cols[f"{col}_rolling_std_{z_window}{unit}"] = std
        new_cols[f"{col}_zscore_{z_window}{unit}"] = z
        new_cols[f"{col}_z_alert"] = _alert_from_z(z)
        # 평균회귀 관점: +1 = 과거 평균 대비 낮아 평균 쪽 반등 여지, -1 = 과거 평균 대비 높아 평균 쪽 하락 압력.
        new_cols[f"{col}_mean_reversion_signal"] = pd.Series(0, index=out.index, dtype="int16").mask(
            z <= -WATCH_Z, 1
        ).mask(z >= WATCH_Z, -1)

        one_period_change = new_cols[f"{col}_chg_1{unit}_pct"]
        if FULL_HISTORY:
            flag, cutoffs = _rolling_shock_flags_full_history(one_period_change, z_window, min_obs)
            new_cols[f"{col}_shock_flag"] = flag
            new_cols[f"{col}_shock_cutoff_lower_1pct"] = cutoffs["q01"]
            new_cols[f"{col}_shock_cutoff_lower_5pct"] = cutoffs["q05"]
            new_cols[f"{col}_shock_cutoff_upper_95pct"] = cutoffs["q95"]
            new_cols[f"{col}_shock_cutoff_upper_99pct"] = cutoffs["q99"]
        else:
            cutoffs = _latest_cutoffs_from_prior_window(one_period_change, z_window, min_obs)
            flag_series = pd.Series(0, index=out.index, dtype="int16")
            if len(out) > 0:
                flag_series.iloc[-1] = _shock_flag_from_cutoffs(one_period_change.iloc[-1], cutoffs)
            new_cols[f"{col}_shock_flag"] = flag_series

            for key, suffix in [
                ("q01", "lower_1pct"),
                ("q05", "lower_5pct"),
                ("q95", "upper_95pct"),
                ("q99", "upper_99pct"),
            ]:
                cutoff_series = pd.Series(pd.NA, index=out.index, dtype="Float64")
                if cutoffs.get(key) is not None and len(out) > 0:
                    cutoff_series.iloc[-1] = cutoffs[key]
                new_cols[f"{col}_shock_cutoff_{suffix}"] = cutoff_series

    feature_frame = pd.DataFrame(new_cols, index=out.index)
    result = pd.concat([out, feature_frame], axis=1)
    result.attrs["rolling_criteria"] = {
        "frequency": freq,
        "unit": unit,
        "windows": list(windows),
        "z_window": z_window,
        "min_obs": min_obs,
        "watch_z": WATCH_Z,
        "extreme_z": EXTREME_Z,
        "watch_quantiles": [WATCH_LOW_Q, WATCH_HIGH_Q],
        "extreme_quantiles": [EXTREME_LOW_Q, EXTREME_HIGH_Q],
        "full_history_cutoff": FULL_HISTORY,
        "source_column_count": len(source_cols),
    }
    return result


def _indicator_direction(col: str) -> str:
    """지표 방향성 해석.

    - risk_up: 값 상승이 성장주/위험자산에 부담으로 해석되는 지표
    - risk_down: 값 하락이 부담으로 해석되는 지표
    - market_up: 값 상승이 위험선호/시장 모멘텀에 우호적인 지표
    - neutral: 방향성보다 이상치 여부만 보는 지표
    """
    name = str(col).lower()

    if any(token in name for token in ["스프레드", "spread", "bbb", "aa-", "회사채"]):
        return "risk_up"
    if any(token in name for token in ["국고채", "국채", "금리", "콜금리", "cd금리", "dff", "sofr", "yield", "rate"]):
        return "risk_up"
    if any(token in name for token in ["원달러", "달러인덱스", "dxy", "환율"]):
        return "risk_up"
    if any(token in name for token in ["유가", "wti", "brent", "천연가스", "구리", "희토류", "헬륨"]):
        return "risk_up"
    if any(token in name for token in ["kospi", "kosdaq", "나스닥", "s&p", "sp500", "sox", "반도체_지수", "시장수익률", "섹터수익률", "지수"]):
        return "market_up"
    if "장단기" in name or "10y3m" in name or "10년_3" in name:
        return "risk_down"
    return "neutral"


def _impact_from_alert(col: str, z_alert: int, shock_flag: int) -> int:
    direction = _indicator_direction(col)
    # z와 shock 중 더 강한 것을 사용한다. sign: +는 상승/고평가, -는 하락/저평가.
    raw = shock_flag if abs(shock_flag) >= abs(z_alert) else z_alert

    if raw == 0:
        return 0
    sign = 1 if raw > 0 else -1
    strength = 2 if abs(raw) >= 2 else 1

    if direction == "risk_up":
        return -strength if sign > 0 else strength
    if direction == "risk_down":
        return strength if sign > 0 else -strength
    if direction == "market_up":
        return strength if sign > 0 else -strength
    return 0


def _discover_latest_feature(df: pd.DataFrame, col: str, marker: str) -> Any:
    candidates = [c for c in df.columns if str(c).startswith(f"{col}_") and marker in str(c)]
    if not candidates:
        return None
    return df.iloc[-1].get(candidates[0])


def score_rolling_criteria(df: pd.DataFrame, dataset_name: str = "") -> Tuple[int, List[str], Dict[str, Any]]:
    """Feature frame의 rolling 기준을 요약하고 제한적인 score impact를 반환한다.

    기준 자체는 통계/분포 기반이며, 점수 반영은 과도한 영향 방지를 위해 dataset별 ±2, 전체 scorer에서 추가 cap을 권장한다.
    """
    if df is None or df.empty or "date" not in df.columns:
        return 0, [], {"rolling_available": False, "reason": "empty_or_no_date"}

    source_cols = numeric_source_columns(df)
    if not source_cols:
        return 0, [], {"rolling_available": False, "reason": "no_numeric_source_columns"}

    latest = df.iloc[-1]
    triggered: List[Dict[str, Any]] = []
    raw_score = 0

    for col in source_cols:
        z_alert_val = _discover_latest_feature(df, col, "_z_alert")
        shock_val = _discover_latest_feature(df, col, "_shock_flag")
        chg1_val = _discover_latest_feature(df, col, "_chg_1")
        z_val = _discover_latest_feature(df, col, "_zscore_")

        try:
            z_alert = int(z_alert_val) if pd.notna(z_alert_val) else 0
        except Exception:
            z_alert = 0
        try:
            shock_flag = int(shock_val) if pd.notna(shock_val) else 0
        except Exception:
            shock_flag = 0

        if z_alert == 0 and shock_flag == 0:
            continue

        impact = _impact_from_alert(col, z_alert, shock_flag)
        raw_score += impact

        try:
            chg1 = float(chg1_val) if pd.notna(chg1_val) else None
        except Exception:
            chg1 = None
        try:
            zscore = float(z_val) if pd.notna(z_val) else None
        except Exception:
            zscore = None

        triggered.append({
            "indicator": col,
            "direction_rule": _indicator_direction(col),
            "z_alert": z_alert,
            "shock_flag": shock_flag,
            "latest_1_period_change_pct": None if chg1 is None else round(chg1, 4),
            "latest_zscore": None if zscore is None else round(zscore, 4),
            "score_impact": impact,
        })

    # 영향도가 과도하게 커지지 않도록 data frame 단위 cap.
    score = max(-2, min(2, raw_score))

    # 중요도: 절대 impact, shock/z 강도 기준 상위 정렬
    triggered = sorted(
        triggered,
        key=lambda x: (abs(x.get("score_impact", 0)), abs(x.get("shock_flag", 0)), abs(x.get("z_alert", 0))),
        reverse=True,
    )

    reasons: List[str] = []
    for item in triggered[:4]:
        ind = item["indicator"]
        shock = item.get("shock_flag", 0)
        zalert = item.get("z_alert", 0)
        chg = item.get("latest_1_period_change_pct")
        z = item.get("latest_zscore")
        pieces = []
        if shock:
            label = "급등" if shock > 0 else "급락"
            level = "극단" if abs(shock) >= 2 else "주의"
            pieces.append(f"1기간 변화율 {label} {level} 구간")
        if zalert:
            label = "상단" if zalert > 0 else "하단"
            level = "3σ 이상" if abs(zalert) >= 2 else "2σ 이상"
            pieces.append(f"rolling z-score {label} {level}")
        metric = ", ".join(pieces) if pieces else "rolling 이상 신호"
        tail = []
        if chg is not None:
            tail.append(f"변화율 {chg:.2f}%")
        if z is not None:
            tail.append(f"z={z:.2f}")
        tail_text = f" ({', '.join(tail)})" if tail else ""
        reasons.append(f"{dataset_name}/{ind}: {metric}{tail_text}")

    details = {
        "rolling_available": True,
        "method": "backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff",
        "basis": {
            "daily_horizons": ["1영업일", "5영업일", "20영업일", "60영업일"],
            "monthly_horizons": ["1개월", "3개월", "6개월", "12개월"],
            "zscore_watch": f"|z| >= {WATCH_Z}",
            "zscore_extreme": f"|z| >= {EXTREME_Z}",
            "shock_watch_quantile": f"{int(WATCH_LOW_Q * 100)}% / {int(WATCH_HIGH_Q * 100)}%",
            "shock_extreme_quantile": f"{int(EXTREME_LOW_Q * 100)}% / {int(EXTREME_HIGH_Q * 100)}%",
            "no_lookahead": "현재값은 rolling 평균/표준편차/cutoff 산정에서 제외",
        },
        "dataset_score_raw": raw_score,
        "dataset_score_capped": score,
        "triggered_count": len(triggered),
        "triggered_items": triggered[:12],
    }
    return score, reasons, details

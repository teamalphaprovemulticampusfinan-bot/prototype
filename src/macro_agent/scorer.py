from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml

from .rolling_criteria import score_rolling_criteria
from .company_sensitivity import score_company_macro_sensitivity


# ============================================================
# config.yaml 로드
# scorer.py 기준으로 같은 디렉토리(macro_agent/)의 config.yaml을 읽는다.
# 파일이 없으면 하드코딩 fallback 값을 사용한다.
# ============================================================

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_config() -> dict:
    """config.yaml을 읽어 반환한다. 파일이 없으면 빈 dict를 반환한다."""
    if not _CONFIG_PATH.exists():
        print(f"  ⚠️ config.yaml 없음 ({_CONFIG_PATH}) → 하드코딩 기본값 사용")
        return {}
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_CONFIG = _load_config()


# ============================================================
# 수준 기반 임계값 (Level Thresholds)
# config.yaml의 thresholds 섹션에서 로드한다.
# yaml에 없는 항목은 _THRESHOLDS_DEFAULT로 fallback된다.
#
# 예: 국고채 10년물이 4.8% → 5.0%로 오르면 고금리 구간 상승 → -2점
#     국고채 10년물이 1.5% → 1.6%로 오르면 저금리 구간 소폭 상승 → -1점
# ============================================================

_THRESHOLDS_DEFAULT: Dict[str, Dict[str, float]] = {
    # 국내 금리
    "국고채_10년":       {"high": 4.0, "low": 2.0},
    "국고채_3년":        {"high": 3.5, "low": 1.5},
    "콜금리":            {"high": 3.5, "low": 1.5},
    "cd금리_91일":       {"high": 3.5, "low": 1.5},
    # 신용스프레드 (절댓값 수준)
    "신용스프레드_bbb-": {"high": 4.0, "low": 2.0},
    "신용스프레드_aa-":  {"high": 2.0, "low": 0.8},
    # 환율
    "원달러":            {"high": 1400, "low": 1200},
    # 미국 금리
    "미국_국채_10년":    {"high": 4.5, "low": 2.5},
    "미국_국채_13주":    {"high": 5.0, "low": 2.0},
    # 달러인덱스
    "달러인덱스_dxy":    {"high": 105, "low": 95},
    # OECD CLI: 100 기준선 위아래로 판단
    "oecd_cli_한국":     {"high": 101.0, "low": 99.0},
    "oecd_cli_미국":     {"high": 101.0, "low": 99.0},
    "g20_cli":           {"high": 101.0, "low": 99.0},
    # CPI
    "cpi_전년비":        {"high": 3.0, "low": 1.0},
    # 미국 실업률
    "미국_실업률":       {"high": 5.0, "low": 3.5},
    # BSI: 100 기준선
    "bsi_전산업_전망":   {"high": 102, "low": 98},
}

# config.yaml thresholds로 덮어쓰기 (없는 항목은 default 유지)
_yaml_thresholds: Dict[str, Any] = _CONFIG.get("thresholds") or {}
THRESHOLDS: Dict[str, Dict[str, float]] = {
    **_THRESHOLDS_DEFAULT,
    **{
        k: {"high": float(v["high"]), "low": float(v["low"])}
        for k, v in _yaml_thresholds.items()
    },
}


# ============================================================
# 섹터 가중치 로드 헬퍼
# config.yaml의 sector_weights 섹션에서 지표별 가중치를 읽는다.
# sector가 없거나 지표가 없으면 default 섹터 → 없으면 인수 기본값 사용.
# ============================================================

_SECTOR_WEIGHTS: Dict[str, Any] = _CONFIG.get("sector_weights") or {}


def _get_weight(col: str, key: str, default: int, sector: str = "default") -> int:
    """sector → col → key 순서로 가중치를 조회한다.

    조회 우선순위:
    1. sector_weights[sector][col][key]
    2. sector_weights["default"][col][key]
    3. 인수 default 값
    """
    for s in (sector, "default"):
        w = _SECTOR_WEIGHTS.get(s, {}).get(col, {}).get(key)
        if w is not None:
            return int(w)
    return default


def _canonical_col(col: str) -> str:
    return str(col or "").strip().lower()


def _series_thresholds(df: pd.DataFrame | None, col: str, *, high_q: float = 0.80, low_q: float = 0.20) -> dict[str, Any]:
    """Return objective level thresholds from the available historical distribution.

    Primary rule: rolling empirical percentiles from the input history, not hand-picked cutoffs.
    Fallback rule: config/default thresholds only when there are too few numeric observations.
    """
    key = _canonical_col(col)
    if df is not None and key in df.columns:
        series = pd.to_numeric(df[key], errors="coerce").dropna()
        if len(series) >= 30:
            return {
                "method": "empirical_percentile",
                "lookback_observations": int(len(series)),
                "high": float(series.quantile(high_q)),
                "low": float(series.quantile(low_q)),
                "high_q": high_q,
                "low_q": low_q,
            }
    t = THRESHOLDS.get(key) or THRESHOLDS.get(col)
    if t is not None:
        return {"method": "fallback_static_when_history_insufficient", "high": float(t["high"]), "low": float(t["low"])}
    return {"method": "unavailable", "high": None, "low": None}


def _level(value: float, col: str, df: pd.DataFrame | None = None) -> str:
    """해당 컬럼의 현재 수준이 고수준/중립/저수준 중 어디인지 반환한다."""
    t = _series_thresholds(df, col)
    if t.get("high") is None or t.get("low") is None:
        return "neutral"
    if value >= float(t["high"]):
        return "high"
    if value <= float(t["low"]):
        return "low"
    return "neutral"


def _macro_criteria_snapshot(df: pd.DataFrame | None, columns: list[str]) -> dict[str, Any]:
    if df is None or df.empty:
        return {}
    out: dict[str, Any] = {}
    for col in columns:
        key = _canonical_col(col)
        if key not in df.columns:
            continue
        latest = pd.to_numeric(df[key], errors="coerce").dropna()
        if latest.empty:
            continue
        th = _series_thresholds(df, key)
        out[key] = {
            **th,
            "latest": float(latest.iloc[-1]),
            "zone": _level(float(latest.iloc[-1]), key, df),
        }
    return out




def _join_recent_text(df: pd.DataFrame, text_cols: list[str], *, tail_rows: int = 30) -> str:
    """Return robust recent text from news/regulation frames.

    Some pandas versions return a DataFrame rather than a Series from
    DataFrame.agg(..., axis=1) when the input has duplicate text columns or an
    empty/irregular shape.  Calling .tolist() on that DataFrame raised
    'DataFrame' object has no attribute 'tolist' and caused the macro news and
    regulation sub-scores to be skipped.
    """
    if df is None or df.empty or not text_cols:
        return ""

    existing_cols: list[str] = []
    seen: set[str] = set()
    for col in text_cols:
        if col in df.columns and col not in seen:
            existing_cols.append(col)
            seen.add(col)

    if not existing_cols:
        return ""

    try:
        frame = df.tail(tail_rows).loc[:, existing_cols].copy()
        # Duplicate column names can still appear in externally prepared CSVs.
        # Keep the first physical occurrence so row-wise joining stays stable.
        if getattr(frame.columns, "duplicated", None) is not None:
            frame = frame.loc[:, ~frame.columns.duplicated()]
        frame = frame.fillna("").astype(str)
        row_text = frame.apply(lambda row: " ".join(x for x in row.tolist() if x), axis=1)
        return " ".join(row_text.tolist()).lower()
    except Exception:
        # Last-resort fallback: iterate row dictionaries without assuming pandas
        # return types from agg/apply.  This keeps macro scoring fail-open.
        pieces: list[str] = []
        try:
            for _, row in df.tail(tail_rows).iterrows():
                for col in existing_cols:
                    value = row.get(col, "")
                    if pd.notna(value):
                        pieces.append(str(value))
        except Exception:
            return ""
        return " ".join(pieces).lower()

def _finite_float(value: Any) -> float | None:
    """NaN/inf를 제외한 실수만 반환한다."""
    try:
        out = float(value)
    except Exception:
        return None
    if pd.isna(out) or not math.isfinite(out):
        return None
    return out


def _score_rate(
    col: str,
    level_val: float,
    diff_val: float,
    up_msg: str,
    down_msg: str,
    up_high_msg: str,
    down_high_msg: str,
    up_weight: int = -1,
    down_weight: int = 1,
    sector: str = "default",
    df: pd.DataFrame | None = None,
) -> Tuple[int, str, dict]:
    """금리/환율처럼 '상승=부정, 하락=긍정'인 지표의 점수를 계산한다.

    가중치 우선순위:
    1. config.yaml sector_weights[sector][col]
    2. config.yaml sector_weights["default"][col]
    3. 인수 up_weight / down_weight 기본값

    고수준 구간에서는 config의 high_multiplier(기본 2)를 적용한다.
    """
    # 가중치를 config에서 읽되, 없으면 인수 기본값 사용
    uw = _get_weight(col, "up_weight",   default=up_weight,   sector=sector)
    dw = _get_weight(col, "down_weight", default=down_weight, sector=sector)
    hm = _get_weight(col, "high_multiplier", default=2,       sector=sector)

    lv = _level(level_val, col, df)
    th = _series_thresholds(df, col)
    detail = {
        f"{col}_level": round(float(level_val), 4),
        f"{col}_diff":  round(float(diff_val), 4),
        f"{col}_zone":  lv,
        f"{col}_criteria": th,
    }

    if diff_val > 0:
        if lv == "high":
            return uw * hm, up_high_msg, detail
        return uw, up_msg, detail
    elif diff_val < 0:
        if lv == "high":
            return dw * hm, down_high_msg, detail
        return dw, down_msg, detail

    return 0, "", detail


# ============================================================
# 메인 점수 계산
# ============================================================

def calculate_macro_score(
    feature_data: Dict[str, pd.DataFrame],
    sector: str = "default",
    company_dir: str | None = None,
    company: str | None = None,
) -> Dict[str, Any]:
    """feature_builder.py에서 만든 feature_data를 바탕으로 매크로 환경 점수를 계산한다.

    Args:
        feature_data: feature_builder가 반환한 dict
        sector: config.yaml sector_weights에서 사용할 섹터 키
                (예: "반도체", "바이오", "이차전지", "default")

    점수 의미:
    + 점수 = 위험자산에 우호적
    - 점수 = 위험자산에 비우호적

    커버리지:
    - ecos_일별:   국내 금리, 환율, 신용스프레드
    - ext_일별:    미국 금리, 달러인덱스, 유가, 구리
    - ecos_월별:   한국 기준금리, CPI, BSI, 실업률
    - ecos_분기별: GDP 성장률
    - ext_월별:    미국 기준금리, 실업률, OECD CLI
    - 뉴스:        키워드 기반 투자심리
    - 규제:        수출규제/관세 리스크
    - 기업별 민감도: 수출/원자재/장비규제/HBM·메모리/금리/신용스프레드 노출도
    """
    total_score = 0
    reasons: List[str] = []
    details: Dict[str, Any] = {}

    # 데이터 커버리지 추적 (coverage_ratio 계산용)
    available: List[str] = []
    all_keys = [
        "ecos_일별", "ext_일별", "시장벤치마크",
        "ecos_월별", "ecos_분기별", "ext_월별",
        "뉴스", "규제",
    ]

    def _run(key: str, fn, df: pd.DataFrame):
        nonlocal total_score
        try:
            s, r, d = fn(df)
            total_score += s
            reasons.extend(r)
            details[key] = d
            available.append(key)
        except Exception as e:
            print(f"  ⚠️ {key} 점수 계산 실패: {e}")

    # 1. ECOS 일별
    if (df := feature_data.get("ecos_일별")) is not None:
        _run("ecos_일별", lambda d: score_ecos_daily(d, sector=sector), df)

    # 2. 외부 일별
    if (df := feature_data.get("ext_일별")) is not None:
        _run("ext_일별", lambda d: score_ext_daily(d, sector=sector), df)
        try:
            s, r, d = score_market_benchmarks(df, sector=sector)
            if d.get("market_benchmark_available"):
                total_score += s
                reasons.extend(r)
                details["시장벤치마크"] = d
                available.append("시장벤치마크")
        except Exception as e:
            print(f"  ⚠️ 시장벤치마크 점수 계산 실패: {e}")

    # 3. ECOS 월별 (신규)
    if (df := feature_data.get("ecos_월별")) is not None:
        _run("ecos_월별", lambda d: score_ecos_monthly(d, sector=sector), df)

    # 4. ECOS 분기별 (신규)
    if (df := feature_data.get("ecos_분기별")) is not None:
        _run("ecos_분기별", score_ecos_quarterly, df)

    # 5. 외부 월별 (신규)
    if (df := feature_data.get("ext_월별")) is not None:
        _run("ext_월별", lambda d: score_ext_monthly(d, sector=sector), df)

    # 6. 뉴스
    if (df := feature_data.get("뉴스")) is not None:
        _run("뉴스", score_news, df)

    # 7. 규제
    if (df := feature_data.get("규제")) is not None:
        _run("규제", score_regulation, df)


    # B. 변화율/rolling 기준
    # - 기준 산정은 feature_builder의 rolling_criteria.py에서 생성한 backward-looking feature를 사용한다.
    # - z-score/급등급락은 객관적 통계 기준을 쓰되, macro 총점 왜곡 방지를 위해 전체 영향은 ±4로 cap.
    rolling_raw_score = 0
    rolling_reasons: List[str] = []
    rolling_details: Dict[str, Any] = {}

    for rolling_key in ("ecos_일별", "ext_일별", "ecos_월별", "ext_월별"):
        rolling_df = feature_data.get(rolling_key)
        if rolling_df is None:
            continue
        try:
            rs, rr, rd = score_rolling_criteria(rolling_df, dataset_name=rolling_key)
            rolling_raw_score += rs
            rolling_reasons.extend(rr)
            rolling_details[rolling_key] = rd
        except Exception as e:
            rolling_details[rolling_key] = {
                "rolling_available": False,
                "reason": f"rolling 기준 계산 실패: {e}",
            }

    if rolling_details:
        rolling_capped_score = max(-4, min(4, rolling_raw_score))
        total_score += rolling_capped_score
        reasons.extend(rolling_reasons[:8])
        details["변화율_rolling_기준"] = {
            "score_raw": rolling_raw_score,
            "score_capped": rolling_capped_score,
            "details": rolling_details,
        }

    # F. 기업별 민감도 기준
    # - 기업 exposure는 로컬 company.yaml/finance CSV/선택 외부 CSV만 읽는다.
    # - macro shock은 A/B에서 만든 공식 시계열 기반 rolling 기준을 그대로 사용한다.
    # - 전체 macro 점수 왜곡 방지를 위해 company sensitivity 총 영향은 company_sensitivity.py 내부에서 ±4로 cap한다.
    company_sensitivity_result: Dict[str, Any] | None = None
    if company_dir or company:
        try:
            cs, cr, cd = score_company_macro_sensitivity(
                feature_data,
                company_dir=company_dir,
                company=company,
                sector=sector,
            )
            total_score += cs
            if cr:
                reasons.extend(cr[:8])
            company_sensitivity_result = {
                "score": cs,
                "reasons": cr,
                "details": cd,
            }
            details["기업별_macro_민감도"] = company_sensitivity_result
        except Exception as e:
            company_sensitivity_result = {
                "score": 0,
                "reasons": [],
                "details": {
                    "available": False,
                    "reason": f"기업별 macro 민감도 계산 실패: {e}",
                },
            }
            details["기업별_macro_민감도"] = company_sensitivity_result

    # 커버리지 비율 계산
    coverage_ratio = round(len(available) / len(all_keys), 2)
    print(f"  📊 데이터 커버리지: {len(available)}/{len(all_keys)} ({coverage_ratio * 100:.0f}%)")
    print(f"  ⚙️  적용 섹터 가중치: {sector}")

    macro_numeric_criteria = {}
    for _k, _cols in {
        "ecos_일별": ["국고채_10년", "국고채_3년", "콜금리", "cd금리_91일", "국고채_10년_3년_스프레드", "회사채_aa-", "회사채_bbb-", "신용스프레드_aa-", "신용스프레드_bbb-", "원달러"],
        "ext_일별": ["달러인덱스_dxy", "미국_국채_10년", "미국_국채_13주", "미국_국채_10년_13주_스프레드", "미국_국채_10년_2년_스프레드", "유가_wti", "유가_brent", "유가_평균", "천연가스", "구리"],
    }.items():
        if isinstance(feature_data.get(_k), pd.DataFrame):
            snap = _macro_criteria_snapshot(feature_data.get(_k), _cols)
            if snap:
                macro_numeric_criteria[_k] = snap

    return {
        "score": total_score,
        "interpretation": _interpret_score(total_score),
        "reasons": reasons,
        "details": details,
        "macro_numeric_criteria": macro_numeric_criteria,
        "company_macro_sensitivity": company_sensitivity_result,
        "data_coverage": {
            "available": available,
            "missing": [k for k in all_keys if k not in available],
            "coverage_ratio": coverage_ratio,
        },
    
    }


# ============================================================
# 기존 scoring 함수 (일별) — sector 파라미터 추가
# ============================================================

def score_ecos_daily(df: pd.DataFrame, sector: str = "default") -> Tuple[int, List[str], Dict]:
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    if df.empty:
        return 0, ["ecos_일별 데이터 없음"], detail

    latest = df.iloc[-1]

    # 국내 금리: 방향 + 수준
    for col in ["국고채_10년", "국고채_3년", "콜금리", "cd금리_91일"]:
        if f"{col}_diff" not in df.columns or col not in df.columns:
            continue
        s, msg, d = _score_rate(
            col=col,
            level_val=latest[col],
            diff_val=latest[f"{col}_diff"],
            up_msg=f"{col} 상승 → 금리 부담 증가",
            down_msg=f"{col} 하락 → 유동성 환경 개선",
            up_high_msg=f"{col} 고수준 구간 추가 상승 → 금리 부담 심화",
            down_high_msg=f"{col} 고수준 구간 하락 → 유동성 환경 개선 (고금리 완화)",
            sector=sector,
            df=df,
        )
        score += s
        detail.update(d)
        if msg:
            reasons.append(msg)

    # 국내 장단기 금리차: 역전/축소는 경기 둔화 신호, 확대는 정상화 신호
    if "국고채_10년_3년_스프레드" in df.columns:
        spread = _finite_float(latest.get("국고채_10년_3년_스프레드"))
        spread_diff = _finite_float(latest.get("국고채_10년_3년_스프레드_diff")) or 0.0
        if spread is not None:
            detail["국고채_10년_3년_스프레드"] = round(spread, 4)
            detail["국고채_10년_3년_스프레드_criteria"] = _series_thresholds(df, "국고채_10년_3년_스프레드")
            if spread < 0:
                score -= 2
                reasons.append("국내 장단기 금리차 역전 → 경기 둔화·자금조달 부담 신호")
            elif spread_diff < 0:
                score -= 1
                reasons.append("국내 장단기 금리차 축소 → 경기 기대 약화 신호")
            elif spread_diff > 0:
                score += 1
                reasons.append("국내 장단기 금리차 확대 → 경기 정상화 신호")

    # 원달러: 방향 + 수준
    if "원달러_diff" in df.columns and "원달러" in df.columns:
        s, msg, d = _score_rate(
            col="원달러",
            level_val=latest["원달러"],
            diff_val=latest["원달러_diff"],
            up_msg="원달러 상승 → 원화 약세/위험 회피",
            down_msg="원달러 하락 → 원화 강세/위험 선호",
            up_high_msg="원달러 고수준 구간 추가 상승 → 환율 리스크 심화",
            down_high_msg="원달러 고수준 구간 하락 → 환율 부담 완화",
            sector=sector,
            df=df,
        )
        score += s
        detail.update(d)
        if msg:
            reasons.append(msg)

    # 신용스프레드: 절댓값 수준 + 변화량
    for spread_col in ["신용스프레드_bbb-", "신용스프레드_aa-"]:
        if spread_col not in df.columns or f"{spread_col}_diff" not in df.columns:
            continue
        lv = _level(latest[spread_col], spread_col, df)
        diff_val = latest[f"{spread_col}_diff"]
        detail[f"{spread_col}_level"] = round(float(latest[spread_col]), 4)
        detail[f"{spread_col}_diff"]  = round(float(diff_val), 4)
        detail[f"{spread_col}_zone"]  = lv

        if diff_val > 0:
            penalty = -3 if lv == "high" else -2
            score += penalty
            reasons.append(
                f"{spread_col} 고수준 구간 확대 → 신용 리스크 심화"
                if lv == "high"
                else f"{spread_col} 확대 → 신용 리스크 증가"
            )
        elif diff_val < 0:
            bonus = 2 if lv == "high" else 1
            score += bonus
            reasons.append(
                f"{spread_col} 고수준에서 축소 → 신용 리스크 완화 신호"
                if lv == "high"
                else f"{spread_col} 축소 → 신용 리스크 완화"
            )

    # 신용스프레드 fallback (BBB-/AA- 원본 컬럼)
    if (
        "신용스프레드_bbb-" not in df.columns
        and "회사채_bbb-_diff" in df.columns
        and "회사채_aa-_diff" in df.columns
    ):
        bbb_diff = latest["회사채_bbb-_diff"]
        aa_diff  = latest["회사채_aa-_diff"]
        spread_change = bbb_diff - aa_diff
        detail["credit_spread_change"] = round(float(spread_change), 4)

        if spread_change > 0:
            score -= 2
            reasons.append("회사채 BBB-/AA- 스프레드 확대 → 신용 리스크 증가")
        elif spread_change < 0:
            score += 1
            reasons.append("회사채 스프레드 축소 → 신용 리스크 완화")

    return score, reasons, detail


def score_ext_daily(df: pd.DataFrame, sector: str = "default") -> Tuple[int, List[str], Dict]:
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    if df.empty:
        return 0, ["ext_일별 데이터 없음"], detail

    latest = df.iloc[-1]

    # 미국 금리: 10Y-2Y 장단기 금리차 우선, 없으면 10Y-13W 스프레드를 사용
    if "미국_국채_10년_2년_스프레드_diff" in df.columns:
        spread = latest["미국_국채_10년_2년_스프레드"]
        spread_diff = latest["미국_국채_10년_2년_스프레드_diff"]
        detail["미국_국채_10년_2년_스프레드"] = round(float(spread), 4)
        detail["미국_국채_10년_2년_스프레드_diff"] = round(float(spread_diff), 4)
        detail["미국_국채_10년_2년_스프레드_criteria"] = _series_thresholds(df, "미국_국채_10년_2년_스프레드")
        if spread < 0:
            score -= 2
            reasons.append("미국 10년-2년 장단기 금리차 역전 → 경기 둔화 리스크 신호")
        elif spread_diff > 0:
            score += 1
            reasons.append("10년-2년 스프레드 확대 → 경기 정상화/수요 개선 신호")
        elif spread_diff < 0:
            score -= 1
            reasons.append("10년-2년 스프레드 축소 → 성장 둔화·경기 약화 우려")
    elif "미국_국채_10년_13주_스프레드_diff" in df.columns:
        spread = latest["미국_국채_10년_13주_스프레드"]
        spread_diff = latest["미국_국채_10년_13주_스프레드_diff"]
        detail["미국_국채_10년_13주_스프레드"] = round(float(spread), 4)
        detail["미국_국채_10년_13주_스프레드_diff"] = round(float(spread_diff), 4)
        detail["미국_국채_10년_13주_스프레드_criteria"] = _series_thresholds(df, "미국_국채_10년_13주_스프레드")
        if spread < 0:
            score -= 2
            reasons.append("미국 10년-13주 장단기 금리차 역전 → 경기 둔화 리스크 신호")
        elif spread_diff > 0:
            score += 1
            reasons.append("10년-13주 스프레드 확대 → 경기 정상화/수요 개선 신호")
        elif spread_diff < 0:
            score -= 1
            reasons.append("10년-13주 스프레드 축소 → 성장 둔화·경기 약화 우려")

    for col in ["미국_국채_10년", "미국_국채_13주"]:
        if f"{col}_diff" not in df.columns or col not in df.columns:
            continue
        s, msg, d = _score_rate(
            col=col,
            level_val=latest[col],
            diff_val=latest[f"{col}_diff"],
            up_msg=f"{col} 상승 → 글로벌 금리 부담",
            down_msg=f"{col} 하락 → 글로벌 유동성 부담 완화",
            up_high_msg=f"{col} 고수준 구간 추가 상승 → 글로벌 긴축 압력 심화",
            down_high_msg=f"{col} 고수준 구간 하락 → 글로벌 긴축 완화 기대",
            sector=sector,
            df=df,
        )
        score += s
        detail.update(d)
        if msg:
            reasons.append(msg)

    # 달러인덱스: 방향 + 수준
    col = "달러인덱스_dxy"
    if f"{col}_diff" in df.columns and col in df.columns:
        s, msg, d = _score_rate(
            col=col,
            level_val=latest[col],
            diff_val=latest[f"{col}_diff"],
            up_msg="달러인덱스 상승 → 달러 강세/위험자산 부담",
            down_msg="달러인덱스 하락 → 위험자산에 우호적",
            up_high_msg="달러인덱스 고수준 구간 추가 상승 → 신흥국/위험자산 압박 심화",
            down_high_msg="달러인덱스 고수준에서 하락 → 달러 강세 완화",
            sector=sector,
            df=df,
        )
        score += s
        detail.update(d)
        if msg:
            reasons.append(msg)

    # 유가: 방향 (인플레이션/원가 부담 관점)
    if "유가_평균_diff" in df.columns:
        diff_val = latest["유가_평균_diff"]
        detail["유가_평균_diff"] = round(float(diff_val), 4)
        if diff_val > 0:
            score -= 1
            reasons.append("평균 유가 상승 → 원가 부담·인플레이션 압력")
        elif diff_val < 0:
            score += 1
            reasons.append("평균 유가 하락 → 원가 부담 완화")

    for col in ["유가_wti", "유가_brent"]:
        if f"{col}_diff" not in df.columns:
            continue
        diff_val = latest[f"{col}_diff"]
        detail[f"{col}_diff"] = round(float(diff_val), 4)
        if diff_val > 0:
            score -= 1
            reasons.append(f"{col} 상승 → 유가 상승은 경기 회복과 비용 부담을 동시에 반영")
        elif diff_val < 0:
            score += 1
            reasons.append(f"{col} 하락 → 유가 하락은 원가 부담 완화와 성장 둔화 신호")

    if "유가_브렌트_wti_스프레드_diff" in df.columns:
        spread_diff = latest["유가_브렌트_wti_스프레드_diff"]
        if isinstance(spread_diff, (int, float)):
            if spread_diff > 0:
                reasons.append("브렌트-위티 스프레드 확대 → 글로벌 공급 우려가 상대적으로 커지는 신호")
            elif spread_diff < 0:
                reasons.append("브렌트-위티 스프레드 축소 → 수요 회복이 더 강한 신호")

    # 구리: 경기 선행 신호 — config 가중치 적용
    col = "구리"
    if f"{col}_diff" in df.columns:
        diff_val = latest[f"{col}_diff"]
        detail[f"{col}_diff"] = round(float(diff_val), 4)
        uw = _get_weight(col, "up_weight",   default=1,  sector=sector)
        dw = _get_weight(col, "down_weight", default=-1, sector=sector)
        if diff_val > 0:
            score += uw
            reasons.append("구리 가격 상승 → 경기 기대 개선")
        elif diff_val < 0:
            score += dw
            reasons.append("구리 가격 하락 → 경기 둔화 우려")

    # 미국 하이일드 스프레드 (ext_일별에 포함된 경우)
    col = "미국_하이일드_스프레드"
    if col in df.columns and f"{col}_diff" in df.columns:
        lv = _level(latest[col], col, df)
        diff_val = latest[f"{col}_diff"]
        detail[f"{col}_level"] = round(float(latest[col]), 4)
        detail[f"{col}_diff"]  = round(float(diff_val), 4)
        if diff_val > 0:
            penalty = -2 if lv == "high" else -1
            score += penalty
            reasons.append(
                "미국 하이일드 스프레드 고수준 확대 → 글로벌 신용 리스크 심화"
                if lv == "high"
                else "미국 하이일드 스프레드 확대 → 글로벌 신용 리스크 증가"
            )
        elif diff_val < 0:
            score += 1
            reasons.append("미국 하이일드 스프레드 축소 → 글로벌 신용 리스크 완화")

    return score, reasons, detail


def score_market_benchmarks(df: pd.DataFrame, sector: str = "default") -> Tuple[int, List[str], Dict]:
    """시장 공통 벤치마크의 수익률/변동성/모멘텀을 별도 레이어로 점수화한다.

    기준은 방향성(0 초과/미만), 252거래일 기준 변동성 z-score, 과반 risk-off 여부처럼
    데이터에서 바로 재현 가능한 규칙만 사용한다.
    """
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {"market_benchmark_available": False}

    if df.empty:
        return 0, ["시장 벤치마크 데이터 없음"], detail

    latest = df.iloc[-1]

    index_cols = [
        "kospi_지수",
        "kosdaq_지수",
        "krx_반도체_지수",
        "krx_반도체_프록시_kodex반도체",
        "코스피200",
        "나스닥",
        "sox_반도체_지수",
        "s&p500",
    ]
    metric_cols = [
        "시장수익률_20일",
        "시장수익률_60일",
        "시장변동성_20일",
        "시장변동성_z_252일",
        "시장모멘텀_20_60",
        "시장_risk_off_비율",
        "한국시장수익률_20일",
        "미국시장수익률_20일",
        "반도체섹터수익률_20일",
        "반도체섹터변동성_20일",
        "반도체섹터모멘텀_20_60",
    ]

    available = []
    for col in index_cols + metric_cols:
        if col not in df.columns:
            continue
        value = _finite_float(latest.get(col))
        if value is None:
            continue
        available.append(col)
        detail[col] = round(value, 4)

    if not available:
        detail["missing_reason"] = "시장 지수/수익률/변동성/모멘텀 컬럼 없음"
        return 0, ["시장 벤치마크 데이터 없음"], detail

    detail["market_benchmark_available"] = True
    detail["available_market_benchmark_columns"] = available

    if "krx_반도체_지수" not in available and "krx_반도체_프록시_kodex반도체" in available:
        detail["semiconductor_benchmark_note"] = "KRX 반도체 지수 원천값이 없어서 KODEX 반도체 ETF 프록시만 사용 가능"

    def get(col: str) -> float | None:
        if col not in df.columns:
            return None
        return _finite_float(latest.get(col))

    def add_signed_return(col: str, label: str) -> None:
        nonlocal score
        value = get(col)
        if value is None:
            return
        if value > 0:
            score += 1
            reasons.append(f"{label} 20일 수익률 양수 → 시장/섹터 방향성 우호")
        elif value < 0:
            score -= 1
            reasons.append(f"{label} 20일 수익률 음수 → 시장/섹터 방향성 약화")

    def add_signed_momentum(col: str, label: str) -> None:
        nonlocal score
        value = get(col)
        if value is None:
            return
        if value > 0:
            score += 1
            reasons.append(f"{label} 20/60일 모멘텀 양수 → 추세 우호")
        elif value < 0:
            score -= 1
            reasons.append(f"{label} 20/60일 모멘텀 음수 → 추세 약화")

    add_signed_return("시장수익률_20일", "전체 시장")
    add_signed_return("한국시장수익률_20일", "한국 시장")
    add_signed_return("미국시장수익률_20일", "미국 시장")
    add_signed_return("반도체섹터수익률_20일", "반도체 섹터")
    add_signed_momentum("시장모멘텀_20_60", "전체 시장")
    add_signed_momentum("반도체섹터모멘텀_20_60", "반도체 섹터")

    vol_z = get("시장변동성_z_252일")
    if vol_z is not None:
        if vol_z > 1.0:
            score -= 1
            reasons.append("시장 변동성 z-score가 +1 초과 → 최근 변동성이 1년 기준보다 높음")
        elif vol_z < -1.0:
            score += 1
            reasons.append("시장 변동성 z-score가 -1 미만 → 최근 변동성이 1년 기준보다 낮음")

    risk_off = get("시장_risk_off_비율")
    if risk_off is not None:
        if risk_off >= 0.5:
            score -= 1
            reasons.append("시장 risk-off 비율 50% 이상 → 벤치마크 과반이 약세")
        elif risk_off <= 0.25:
            score += 1
            reasons.append("시장 risk-off 비율 25% 이하 → 벤치마크 약세 비중 낮음")

    if not reasons:
        reasons.append("시장 벤치마크 원천값은 있으나 방향성/변동성 신호는 중립")

    return score, reasons, detail


# ============================================================
# 신규: ECOS 월별 scoring
# ============================================================

def score_ecos_monthly(df: pd.DataFrame, sector: str = "default") -> Tuple[int, List[str], Dict]:
    """한국 기준금리, CPI, BSI, 실업률 기반 월별 점수 계산."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    if df.empty:
        return 0, ["ecos_월별 데이터 없음"], detail

    latest = df.iloc[-1]

    # 한국 기준금리: 방향 + 수준
    col = "한국_기준금리"
    if col in df.columns and f"{col}_diff" in df.columns:
        s, msg, d = _score_rate(
            col=col,
            level_val=latest[col],
            diff_val=latest[f"{col}_diff"],
            up_msg="한국 기준금리 인상 → 국내 유동성 긴축",
            down_msg="한국 기준금리 인하 → 국내 유동성 완화",
            up_high_msg="한국 기준금리 고수준 추가 인상 → 긴축 압력 심화",
            down_high_msg="한국 기준금리 고수준에서 인하 → 피벗 기대 강화",
            sector=sector,
            df=df,
        )
        score += s
        detail.update(d)
        if msg:
            reasons.append(msg)

    # CPI 전년비: 수준 판단 (방향이 아니라 수준이 더 중요)
    col = "cpi_전년비"
    if col in df.columns:
        cpi = latest[col]
        lv = _level(cpi, col)
        detail[f"{col}_level"] = round(float(cpi), 4)
        detail[f"{col}_zone"]  = lv

        if lv == "high":
            score -= 2
            reasons.append(f"CPI 전년비 {cpi:.1f}% — 고물가 구간 → 금리 인하 기대 약화")
        elif lv == "low":
            score += 1
            reasons.append(f"CPI 전년비 {cpi:.1f}% — 저물가 구간 → 완화적 통화정책 여지")
        else:
            reasons.append(f"CPI 전년비 {cpi:.1f}% — 물가 중립 구간")

    # BSI 전산업 전망: 100 기준선
    col = "bsi_전산업_전망"
    if col in df.columns:
        bsi = latest[col]
        lv = _level(bsi, col)
        detail[f"{col}_level"] = round(float(bsi), 4)
        detail[f"{col}_zone"]  = lv

        if lv == "high":
            score += 1
            reasons.append(f"BSI 전망 {bsi:.1f} — 기업 경기 낙관 우위")
        elif lv == "low":
            score -= 1
            reasons.append(f"BSI 전망 {bsi:.1f} — 기업 경기 비관 우위")
        else:
            reasons.append(f"BSI 전망 {bsi:.1f} — 기업 경기 중립")

    # 실업률: 수준 판단 (한국 기준)
    col = "실업률"
    if col in df.columns:
        unemp = latest[col]
        detail[f"{col}_level"] = round(float(unemp), 4)
        if unemp >= 4.0:
            score -= 1
            reasons.append(f"실업률 {unemp:.1f}% — 고용 악화 신호")
        elif unemp <= 2.8:
            score += 1
            reasons.append(f"실업률 {unemp:.1f}% — 고용 양호")

    return score, reasons, detail


# ============================================================
# 신규: ECOS 분기별 scoring
# ============================================================

def score_ecos_quarterly(df: pd.DataFrame) -> Tuple[int, List[str], Dict]:
    """GDP 성장률 기반 분기별 점수 계산."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    if df.empty:
        return 0, ["ecos_분기별 데이터 없음"], detail

    latest = df.iloc[-1]

    # GDP 성장률 전년비
    col = "gdp성장률_전년비"
    if col in df.columns:
        gdp = latest[col]
        detail[f"{col}_level"] = round(float(gdp), 4)

        if gdp >= 3.0:
            score += 2
            reasons.append(f"GDP 전년비 {gdp:.1f}% — 고성장 구간 → 경기 우호적")
        elif gdp >= 1.5:
            score += 1
            reasons.append(f"GDP 전년비 {gdp:.1f}% — 완만한 성장 → 중립적")
        elif gdp >= 0:
            score -= 1
            reasons.append(f"GDP 전년비 {gdp:.1f}% — 저성장 구간 → 경기 부담")
        else:
            score -= 2
            reasons.append(f"GDP 전년비 {gdp:.1f}% — 역성장 → 경기 위축 신호")

    # GDP 성장률 전기비 (모멘텀)
    col = "gdp성장률_전기비"
    if col in df.columns:
        gdp_qoq = latest[col]
        detail[f"{col}_level"] = round(float(gdp_qoq), 4)

        if gdp_qoq < 0:
            score -= 1
            reasons.append(f"GDP 전기비 {gdp_qoq:.1f}% — 전분기 대비 역성장 → 모멘텀 약화")
        elif gdp_qoq >= 1.0:
            score += 1
            reasons.append(f"GDP 전기비 {gdp_qoq:.1f}% — 전분기 대비 가속 성장")

    return score, reasons, detail


# ============================================================
# 신규: 외부 월별 scoring
# ============================================================

def score_ext_monthly(df: pd.DataFrame, sector: str = "default") -> Tuple[int, List[str], Dict]:
    """미국 기준금리, 실업률, OECD CLI 기반 월별 점수 계산."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    if df.empty:
        return 0, ["ext_월별 데이터 없음"], detail

    latest = df.iloc[-1]

    # 미국 기준금리 FFR: 방향 + 수준
    # down_weight 기본값 2 (Fed 금리인하는 시장에 강한 긍정 신호) — config로 덮어쓸 수 있음
    col = "미국_기준금리_ffr"
    if col in df.columns and f"{col}_diff" in df.columns:
        s, msg, d = _score_rate(
            col=col,
            level_val=latest[col],
            diff_val=latest[f"{col}_diff"],
            up_msg="미국 기준금리 인상 → 글로벌 긴축 압력",
            down_msg="미국 기준금리 인하 → 글로벌 유동성 완화",
            up_high_msg="미국 기준금리 고수준 추가 인상 → 긴축 압력 극대화",
            down_high_msg="미국 기준금리 고수준에서 인하 → Fed 피벗 확인 → 강한 완화 신호",
            up_weight=-1,
            down_weight=2,  # config에 등록돼 있으면 config 값 우선
            sector=sector,
            df=df,
        )
        score += s
        detail.update(d)
        if msg:
            reasons.append(msg)

    # 미국 실업률: 수준 판단
    col = "미국_실업률"
    if col in df.columns:
        unemp = latest[col]
        lv = _level(unemp, col)
        detail[f"{col}_level"] = round(float(unemp), 4)
        detail[f"{col}_zone"]  = lv

        if lv == "high":
            score -= 1
            reasons.append(f"미국 실업률 {unemp:.1f}% — 고용 악화 → 경기 침체 우려")
        elif lv == "low":
            score += 1
            reasons.append(f"미국 실업률 {unemp:.1f}% — 고용 탄탄 → 경기 견조")

    # OECD CLI: 방향 + 100 기준선 수준
    for col in ["oecd_cli_한국", "oecd_cli_미국", "g20_cli"]:
        if col not in df.columns or f"{col}_diff" not in df.columns:
            continue

        cli_val  = latest[col]
        diff_val = latest[f"{col}_diff"]
        lv = _level(cli_val, col)

        detail[f"{col}_level"] = round(float(cli_val), 4)
        detail[f"{col}_diff"]  = round(float(diff_val), 4)
        detail[f"{col}_zone"]  = lv

        # CLI는 방향(개선/악화)이 수준보다 더 중요
        if diff_val > 0:
            bonus = 2 if lv == "high" else 1
            score += bonus
            reasons.append(
                f"{col} {cli_val:.2f} 상승 (기준선 위) → 경기 회복 모멘텀 강화"
                if lv == "high"
                else f"{col} {cli_val:.2f} 상승 → 경기 개선 신호"
            )
        elif diff_val < 0:
            penalty = -2 if lv == "low" else -1
            score += penalty
            reasons.append(
                f"{col} {cli_val:.2f} 하락 (기준선 아래) → 경기 침체 우려 심화"
                if lv == "low"
                else f"{col} {cli_val:.2f} 하락 → 경기 둔화 신호"
            )

    return score, reasons, detail


# ============================================================
# 기존 scoring 함수 (뉴스 / 규제) — 변경 없음
# ============================================================

def score_news(df: pd.DataFrame) -> Tuple[int, List[str], Dict]:
    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    text_cols = [col for col in df.columns if col in ["title", "summary", "description", "content"]]

    if not text_cols:
        return 0, ["뉴스 텍스트 컬럼이 없어 뉴스 점수 계산 생략"], detail

    recent_text = _join_recent_text(df, text_cols, tail_rows=30)
    if not recent_text:
        return 0, ["뉴스 텍스트가 비어 있어 뉴스 점수 계산 생략"], detail

    negative_keywords = [
        "tariff", "ban", "sanction", "export control",
        "war", "risk", "shortage", "inflation",
        "rate hike", "recession",
    ]
    positive_keywords = [
        "growth", "recovery", "deal", "agreement",
        "rate cut", "stimulus", "expansion",
        "supply improves",
    ]

    neg_count = sum(recent_text.count(k) for k in negative_keywords)
    pos_count = sum(recent_text.count(k) for k in positive_keywords)

    detail["positive_keyword_count"] = pos_count
    detail["negative_keyword_count"] = neg_count

    if neg_count > pos_count:
        score -= 1
        reasons.append("부정 뉴스 키워드 우세 → 투자심리 부담")
    elif pos_count > neg_count:
        score += 1
        reasons.append("긍정 뉴스 키워드 우세 → 투자심리 개선")
    else:
        reasons.append("뉴스 긍정/부정 신호 중립")

    return score, reasons, detail


def score_regulation(df: pd.DataFrame) -> Tuple[int, List[str], Dict]:
    score = 0
    reasons: List[str] = []
    detail: Dict[str, Any] = {}

    text_cols = [col for col in df.columns if col in ["title", "summary", "description", "content"]]

    if not text_cols:
        return 0, ["규제 텍스트 컬럼이 없어 규제 점수 계산 생략"], detail

    recent_text = _join_recent_text(df, text_cols, tail_rows=30)
    if not recent_text:
        return 0, ["규제 텍스트가 비어 있어 규제 점수 계산 생략"], detail

    risk_keywords = [
        "export control", "restriction", "sanction",
        "tariff", "ban", "regulation", "penalty",
        "investigation", "emission", "carbon border",
    ]

    risk_count = sum(recent_text.count(k) for k in risk_keywords)
    detail["regulation_risk_keyword_count"] = risk_count

    if risk_count >= 5:
        score -= 2
        reasons.append("규제 리스크 키워드 다수 발견 → 매도/관망 요인")
    elif risk_count > 0:
        score -= 1
        reasons.append("규제 리스크 키워드 일부 발견 → 투자심리 부담")
    else:
        reasons.append("규제 리스크 신호 약함")

    return score, reasons, detail

def _interpret_score(score: int) -> dict:
    if score >= 10:
        return {"condition": "우호적",     "risk_level": "low"}
    elif score >= 3:
        return {"condition": "중립 우호",  "risk_level": "medium"}
    elif score >= -3:
        return {"condition": "중립",       "risk_level": "medium"}
    elif score >= -10:
        return {"condition": "중립 비우호","risk_level": "high"}
    else:
        return {"condition": "비우호적",   "risk_level": "high"}

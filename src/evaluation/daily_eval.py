from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from evaluation.monthly_eval import (
    AGENTS,
    CompanyTarget,
    build_all_snapshots,
    project_root,
    read_universe,
    run_chair_from_history,
    save_snapshots_to_history,
)


_DATE_COL_CANDIDATES = [
    "date", "Date", "날짜", "일자", "기준일", "base_date", "공시일",
    "게시일", "작성일", "published_at", "pubDate", "rcept_dt", "stlm_dt",
]


@dataclass(frozen=True)
class DailyWindow:
    """Daily evaluation window with the same interface expected by monthly_eval.py."""
    month: str
    start_date: str
    end_date: str
    as_of_date: str
    year: int
    month_num: int

    @classmethod
    def parse(cls, day: str) -> "DailyWindow":
        d = datetime.strptime(str(day).strip(), "%Y-%m-%d").date()
        return cls(
            month=d.isoformat(),
            start_date=d.isoformat(),
            end_date=d.isoformat(),
            as_of_date=d.isoformat(),
            year=d.year,
            month_num=d.month,
        )

    @property
    def start_s(self) -> str:
        return self.start_date

    @property
    def end_s(self) -> str:
        return self.end_date

    @property
    def start(self) -> date:
        return date.fromisoformat(self.start_date)

    @property
    def end(self) -> date:
        return date.fromisoformat(self.end_date)

    @property
    def yyyy_mm(self) -> str:
        return self.as_of_date[:7]


def iter_days(start_date: str, end_date: str) -> list[DailyWindow]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if start > end:
        raise ValueError("--start-date는 --end-date보다 늦을 수 없습니다.")

    out: list[DailyWindow] = []
    cur = start
    while cur <= end:
        out.append(DailyWindow.parse(cur.isoformat()))
        cur += timedelta(days=1)
    return out


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        num = float(value)
        return None if math.isnan(num) or math.isinf(num) else num
    text = str(value).replace(",", "").replace("%", "").replace("원", "").strip()
    if not text or text.lower() in {"nan", "none", "null", "확인 제한", "na", "n/a"}:
        return None
    try:
        num = float(text)
        return None if math.isnan(num) or math.isinf(num) else num
    except Exception:
        return None


def _safe_round(value: Any, digits: int = 4) -> float | None:
    num = _to_float(value)
    return None if num is None else round(num, digits)


def _jsonable(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            converted = _jsonable(v)
            if converted is not None:
                out[str(k)] = converted
        return out
    if isinstance(obj, (list, tuple)):
        out = []
        for v in obj:
            converted = _jsonable(v)
            if converted is not None:
                out.append(converted)
        return out
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return str(obj)


def _date_column(df: pd.DataFrame) -> str | None:
    for c in _DATE_COL_CANDIDATES:
        if c in df.columns:
            return c
    for c in df.columns:
        col_text = str(c).lower()
        raw = str(c)
        if "date" in col_text or "일자" in raw or "날짜" in raw or "기준일" in raw:
            return c
    return None


def _parse_date_series(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    parsed = pd.to_datetime(s, errors="coerce")
    compact = s.str.fullmatch(r"\d{8}")
    if compact.any():
        parsed.loc[compact] = pd.to_datetime(s.loc[compact], format="%Y%m%d", errors="coerce")
    return parsed


def _normalize_date_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    df = df.copy()
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    date_col = _date_column(df)
    if date_col:
        df["__date"] = _parse_date_series(df[date_col]).dt.date
        return df, date_col

    year_cols = [c for c in df.columns if str(c).lower() in {"year", "yyyy", "연도", "년도"}]
    month_cols = [c for c in df.columns if str(c).lower() in {"month", "mm", "월"}]
    day_cols = [c for c in df.columns if str(c).lower() in {"day", "dd", "일"}]
    if year_cols and month_cols and day_cols:
        y = pd.to_numeric(df[year_cols[0]], errors="coerce")
        m = pd.to_numeric(df[month_cols[0]], errors="coerce")
        d = pd.to_numeric(df[day_cols[0]], errors="coerce")
        dates: list[Any] = []
        for yy, mm, dd in zip(y, m, d):
            try:
                dates.append(date(int(yy), int(mm), int(dd)))
            except Exception:
                dates.append(pd.NaT)
        df["__date"] = dates
        return df, f"{year_cols[0]}-{month_cols[0]}-{day_cols[0]}"
    return df, None


def _filter_exact_day(df: pd.DataFrame, window: DailyWindow) -> tuple[pd.DataFrame, str | None]:
    normalized, date_col = _normalize_date_columns(df)
    if "__date" not in normalized.columns:
        return normalized.iloc[0:0].copy(), date_col
    return normalized[normalized["__date"] == window.start].drop(columns=["__date"], errors="ignore"), date_col


def _compact_preview(df: pd.DataFrame, max_cols: int = 16) -> dict[str, Any]:
    if df.empty:
        return {}
    row = df.iloc[-1].to_dict()
    out: dict[str, Any] = {}
    for k, v in row.items():
        if len(out) >= max_cols:
            break
        try:
            if pd.isna(v):
                continue
        except Exception:
            pass
        if isinstance(v, (int, float)):
            out[str(k)] = float(v)
        else:
            text = str(v).strip()
            if text:
                out[str(k)] = text[:200]
    return out


def _numeric_summary(df: pd.DataFrame, max_cols: int = 20) -> dict[str, Any]:
    if df.empty:
        return {}
    out: dict[str, Any] = {}
    priority_cols = [
        "시장수익률_20일",
        "한국시장수익률_20일",
        "미국시장수익률_20일",
        "반도체섹터수익률_20일",
        "시장변동성_20일",
        "시장변동성_z_252일",
        "시장모멘텀_20_60",
        "시장_risk_off_비율",
        "KOSPI_지수",
        "KOSDAQ_지수",
        "KRX_반도체_지수",
        "SOX_반도체_지수",
        "S&P500",
    ]
    cols = [c for c in priority_cols if c in df.columns]
    cols.extend(c for c in df.columns if c not in priority_cols)
    for col in cols:
        if len(out) >= max_cols:
            break
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        if not vals.empty:
            out[str(col)] = _safe_round(vals.iloc[-1], 6)
    return out




def _json_dump_compact(value: Any, max_chars: int = 800) -> str:
    try:
        text = json.dumps(_jsonable(value), ensure_ascii=False, separators=(",", ":"))
    except Exception:
        text = str(value)
    return text[:max_chars]


def _date_tokens(window: DailyWindow) -> set[str]:
    d = window.start
    return {
        d.isoformat(),
        d.strftime("%Y%m%d"),
        d.strftime("%Y.%m.%d"),
        d.strftime("%Y/%m/%d"),
        d.strftime("%Y-%m-%d 00:00:00"),
        f"{d.month}/{d.day}/{d.year}",
        f"{d.year}.{d.month}.{d.day}",
        f"{d.year}/{d.month}/{d.day}",
    }


def _parse_any_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\.0$", "", text)
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10] if fmt in {"%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"} else text, fmt).date()
        except Exception:
            pass
    try:
        parsed = pd.to_datetime([text], errors="coerce")[0]
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _read_excel_all_sheets_header_none(path: Path) -> dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(path, sheet_name=None, header=None)
    except Exception:
        return {}


def _file_matches_target(path: Path, target: CompanyTarget) -> bool:
    name = path.stem.lower().replace(" ", "")
    checks = [
        target.company_name.lower().replace(" ", ""),
        target.company_dir.lower().replace(" ", ""),
        str(target.stock_code).zfill(6) if target.stock_code else "",
    ]
    return any(c and c in name for c in checks)


def _company_text_tokens(target: CompanyTarget) -> list[str]:
    toks = [target.company_name, target.company_dir, str(target.stock_code).zfill(6) if target.stock_code else ""]
    return [t for t in toks if t]


def _rows_containing_day(df: pd.DataFrame, window: DailyWindow) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    tokens = _date_tokens(window)
    mask = pd.Series(False, index=df.index)
    for col in df.columns:
        s = df[col].astype(str)
        col_mask = pd.Series(False, index=df.index)
        for token in tokens:
            col_mask = col_mask | s.str.contains(re.escape(token), na=False)
        mask = mask | col_mask
    return df.loc[mask].copy()


def _date_header_columns(df: pd.DataFrame, window: DailyWindow) -> list[Any]:
    out = []
    for col in df.columns:
        d = _parse_any_date(col)
        if d == window.start:
            out.append(col)
    return out


def _wide_date_metrics(df: pd.DataFrame, window: DailyWindow, max_rows: int = 200) -> dict[str, Any]:
    """Extract values from wide sheets where date is a column header and metric names are in rows."""
    if df is None or df.empty:
        return {}
    date_cols = _date_header_columns(df, window)
    if not date_cols:
        return {}
    date_col = date_cols[0]
    out: dict[str, Any] = {}
    # Use the first few non-date columns as metric-name candidates.
    non_date_cols = [c for c in df.columns if c not in date_cols]
    for _, row in df.head(max_rows).iterrows():
        metric_name = ""
        for c in non_date_cols[:4]:
            val = row.get(c)
            if val is None:
                continue
            try:
                if pd.isna(val):
                    continue
            except Exception:
                pass
            text = str(val).strip()
            # Avoid using long narrative cells as metric names.
            if text and not re.fullmatch(r"[-+]?\d+(\.\d+)?", text) and len(text) <= 80:
                metric_name = text
                break
        if not metric_name:
            continue
        value = row.get(date_col)
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        out[metric_name] = value
    return _jsonable(out) if out else {}


def _extract_alias_metrics(values: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "valuation_implied_price": ["implied", "intrinsic", "fair value", "fair_price", "내재", "적정", "공정", "본질", "진정한", "목표주가", "target"],
        "valuation_current_price": ["current price", "market price", "close", "종가", "현재가", "주가", "평가일주가"],
        "valuation_gap_pct": ["gap", "upside", "괴리", "상승여력", "저평가", "고평가", "할인율"],
        "valuation_wacc": ["wacc", "할인율", "가중평균자본비용"],
        "valuation_dcf_value": ["dcf", "현금흐름할인", "fcf value"],
        "valuation_psr": ["psr", "p/s", "price sales", "매출액배수"],
        "valuation_per": ["per", "p/e", "주가수익"],
        "valuation_pbr": ["pbr", "p/b", "주가순자산"],
        "valuation_ev_ebitda": ["ev/ebitda", "ev_ebitda"],
        "valuation_score": ["valuation score", "가치평가점수", "밸류에이션점수", "종합가치평가", "투자점수"],
    }
    out: dict[str, Any] = {}
    for key, value in values.items():
        lk = str(key).lower().replace("_", " ")
        for out_key, keys in aliases.items():
            if out_key in out:
                continue
            if any(k.lower() in lk for k in keys):
                num = _to_float(value)
                out[out_key] = num if num is not None else str(value)[:200]
    # Objective formula only when both source-side price and fair/implied price are present.
    if "valuation_gap_pct" not in out:
        fair = _to_float(out.get("valuation_implied_price"))
        current = _to_float(out.get("valuation_current_price"))
        if fair is not None and current not in (None, 0):
            out["valuation_gap_pct"] = round((fair / current - 1.0) * 100.0, 4)
            out["valuation_gap_pct_formula"] = "(valuation_implied_price / valuation_current_price - 1) * 100"
    return out



def _workbook_key_value_metrics(raw_sheets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Extract label→adjacent value pairs from formatted valuation workbook sheets.

    The valuation workbook is not always a rectangular date table. Key sheets such as
    30_발표용_원페이지, 00_대시보드, 22_종합가치평가, 23_가치범위표, 26_투자판단_요약
    often store values as label/value pairs in adjacent cells. This extractor keeps
    those values objective by taking only cells physically adjacent to labels.
    """
    important_sheets = [
        "30_발표용_원페이지", "00_대시보드", "07_WACC", "09_DCF_가치평가",
        "17_투자자요약", "19_가치평가_브릿지", "22_종합가치평가", "23_가치범위표",
        "24_역산DCF", "26_투자판단_요약", "28_대시보드_연동키",
    ]
    label_keywords = [
        "현재가", "종가", "시장가", "주가", "DCF 내재주가", "내재주가", "적정가",
        "공정가치", "가치범위 중앙값", "중앙값", "하단값", "상단값", "안전마진",
        "괴리율", "상승여력", "DCF 괴리율", "WACC", "DCF 기업가치", "DCF 지분가치",
        "종합 가치평가 점수", "종합 점수", "가치평가 점수", "PSR", "P/S", "PER", "PBR",
    ]
    out: dict[str, Any] = {}

    def _is_blank(v: Any) -> bool:
        if v is None:
            return True
        try:
            if pd.isna(v):
                return True
        except Exception:
            pass
        return str(v).strip() == ""

    def _clean_label(v: Any) -> str:
        return re.sub(r"\s+", " ", str(v).strip())

    for sheet_name, df in raw_sheets.items():
        if df is None or df.empty:
            continue
        # Prefer valuation summary sheets, but still allow all sheets as fallback.
        sheet_priority = 0 if sheet_name in important_sheets else 1
        arr = df.values
        rows, cols = arr.shape
        for r in range(rows):
            for c in range(cols):
                cell = arr[r][c]
                if _is_blank(cell):
                    continue
                label = _clean_label(cell)
                if not any(k.lower() in label.lower() for k in label_keywords):
                    continue
                # Search right cells first, then below cells. This matches the workbook layout.
                candidates: list[Any] = []
                for dc in range(1, 5):
                    if c + dc < cols and not _is_blank(arr[r][c + dc]):
                        candidates.append(arr[r][c + dc])
                for dr in range(1, 4):
                    if r + dr < rows and not _is_blank(arr[r + dr][c]):
                        candidates.append(arr[r + dr][c])
                for value in candidates:
                    key = f"{sheet_name}:{label}"
                    # Do not let low priority sheets overwrite high priority values.
                    if key not in out:
                        out[key] = value
                    # Also store a plain label if it is not already set.
                    plain_key = label
                    if plain_key not in out or sheet_priority == 0:
                        out.setdefault(plain_key, value)
                    break
    return out


def _clip_signal(value: Any, low: float = -1.0, high: float = 1.0) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    return round(max(low, min(high, num)), 4)


def _recommendation_from_signal_value(signal: Any) -> str:
    num = _to_float(signal)
    if num is None:
        return ""
    if num < 0.0:
        return "매도"
    if num < 1.0:
        return "보유"
    return "매수"


def _objective_valuation_signal(metrics: dict[str, Any]) -> tuple[float | None, str]:
    """Valuation signal from source-side valuation gap only.

    Formula is explicit and auditable:
      valuation_signal = clip(valuation_gap_pct / 50, -1, 1)
    where valuation_gap_pct is either workbook-provided or computed from
    valuation_implied_price and the exact-day current/close price.
    """
    gap = _to_float(metrics.get("valuation_gap_pct"))
    if gap is None:
        fair = _to_float(metrics.get("valuation_implied_price"))
        current = _to_float(metrics.get("valuation_current_price"))
        if fair is not None and current not in (None, 0):
            gap = (fair / current - 1.0) * 100.0
            metrics["valuation_gap_pct"] = round(gap, 4)
            metrics["valuation_gap_pct_formula"] = "(valuation_implied_price / valuation_current_price - 1) * 100"
    if gap is None:
        score = _to_float(metrics.get("valuation_score"))
        if score is not None:
            # Score-based fallback only if the workbook explicitly provides a valuation score.
            return _clip_signal((score - 50.0) / 50.0), "valuation_score_formula:(score-50)/50"
        return None, "NO_VALUATION_GAP_OR_SCORE"
    return _clip_signal(gap / 50.0), "valuation_gap_formula:clip(gap_pct/50,-1,1)"


def _objective_macro_signal_from_indicators(indicators: dict[str, Any]) -> tuple[float | None, str]:
    """Macro signal from daily macro stress indicators.

    Negative means macro pressure is high for equity/deep-tech valuation.
    This is not an LLM judgment; it is a transparent deterministic pressure formula.
    """
    vals = {str(k): _to_float(v) for k, v in (indicators or {}).items()}
    vals = {k: v for k, v in vals.items() if v is not None}
    if not vals:
        return None, "NO_NUMERIC_MACRO_INDICATORS"

    components: list[float] = []

    def add_pressure(key_contains: str, neutral: float, scale: float, positive_is_good: bool = False) -> None:
        for k, v in vals.items():
            if key_contains in k:
                pressure = (v - neutral) / scale
                if positive_is_good:
                    pressure = -pressure
                components.append(max(-2.0, min(2.0, pressure)))
                return

    def add_direction_pressure(key_contains: str, positive_is_good: bool = True) -> None:
        for k, v in vals.items():
            if key_contains in k:
                if v > 0:
                    components.append(-1.0 if positive_is_good else 1.0)
                elif v < 0:
                    components.append(1.0 if positive_is_good else -1.0)
                else:
                    components.append(0.0)
                return

    add_pressure("원달러", 1300.0, 250.0)
    add_pressure("달러인덱스", 100.0, 10.0)
    add_pressure("국고채_3년", 3.0, 1.0)
    add_pressure("국고채_10년", 3.2, 1.0)
    add_pressure("미국_국채_10년", 4.0, 1.0)
    add_pressure("신용스프레드_AA", 0.7, 0.5)
    add_pressure("미국_하이일드_스프레드", 3.5, 2.0)
    add_pressure("유가_WTI", 75.0, 25.0)
    add_direction_pressure("시장수익률_20일", positive_is_good=True)
    add_direction_pressure("한국시장수익률_20일", positive_is_good=True)
    add_direction_pressure("미국시장수익률_20일", positive_is_good=True)
    add_direction_pressure("반도체섹터수익률_20일", positive_is_good=True)
    add_direction_pressure("시장모멘텀_20_60", positive_is_good=True)
    add_direction_pressure("반도체섹터모멘텀_20_60", positive_is_good=True)
    add_pressure("시장변동성_z_252일", 0.0, 1.0)
    add_pressure("시장_risk_off_비율", 0.5, 0.5)

    if not components:
        return None, "NO_SUPPORTED_MACRO_INDICATOR_KEYS"
    avg_pressure = sum(components) / len(components)
    # Higher pressure is bad, so signal is negative pressure.
    signal = _clip_signal(-avg_pressure / 2.0)
    return signal, "macro_pressure_formula:negative_avg_standardized_fx_rate_credit_oil_market_benchmark_pressure"


def _num_is_zero(value: Any) -> bool:
    num = _to_float(value)
    return num is not None and abs(num) < 1e-12


def _apply_objective_zero_signal_backfill(row: dict[str, Any]) -> dict[str, Any]:
    """Fill zero signals only when objective source data exists but Auditor returned 0.

    This prevents a valid daily source snapshot from being lost in the final CSV.
    It never invents Issue signal when the day has no issue rows.
    """
    row = dict(row)
    changed = False

    # Valuation: workbook data + valuation gap/score formula.
    if _num_is_zero(row.get("valuation_signal")) and str(row.get("valuation_workbook_status") or "").startswith("FOUND"):
        metrics = dict(row)
        sig, formula = _objective_valuation_signal(metrics)
        if sig is not None and not _num_is_zero(sig):
            row.update({k: v for k, v in metrics.items() if k.startswith("valuation_")})
            row["valuation_signal"] = sig
            row["valuation_recommendation"] = _recommendation_from_signal_value(sig)
            weight = _to_float(row.get("valuation_weight"))
            if weight is not None:
                row["valuation_weight"] = weight
                row["valuation_weighted_signal"] = round(sig * weight, 6)
            row["valuation_signal_source"] = f"objective_daily_valuation_source_backfill:{formula}"
            changed = True

    # Macro: exact/as-of daily macro indicators + deterministic pressure formula.
    if _num_is_zero(row.get("macro_signal")) and str(row.get("macro_daily_status") or "").startswith("FOUND"):
        preview = row.get("macro_daily_indicator_preview")
        indicators: dict[str, Any] = {}
        if isinstance(preview, str) and preview.strip():
            try:
                indicators = json.loads(preview)
            except Exception:
                indicators = {}
        elif isinstance(preview, dict):
            indicators = preview
        sig, formula = _objective_macro_signal_from_indicators(indicators)
        if sig is not None and not _num_is_zero(sig):
            row["macro_signal"] = sig
            row["macro_recommendation"] = _recommendation_from_signal_value(sig)
            weight = _to_float(row.get("macro_weight"))
            if weight is not None:
                row["macro_weight"] = weight
                row["macro_weighted_signal"] = round(sig * weight, 6)
            row["macro_signal_source"] = f"objective_daily_macro_source_backfill:{formula}"
            changed = True

    # Issue: 0 is allowed only when there were no issue rows that day.
    if _num_is_zero(row.get("issue_signal")):
        issue_count = _to_float(row.get("issue_daily_count") or row.get("issue_news_count"))
        if not issue_count:
            row["issue_signal_source"] = "NO_DAILY_ISSUE_ROWS_NEUTRAL_ZERO"

    if changed:
        total = 0.0
        has_any = False
        for agent in AGENTS:
            val = _to_float(row.get(f"{agent}_weighted_signal"))
            if val is not None:
                total += val
                has_any = True
        if has_any:
            row["weighted_signal"] = round(total, 6)
            row["recommendation"] = _recommendation_from_signal_value(total)
            row["weighted_signal_source"] = "recomputed_after_objective_zero_signal_backfill"
    return row


def _add_daily_evidence(payload: dict[str, Any], *, evidence_id: str, source_type: str, source_name: str, snippet: str, value: Any = None, source_file: str = "") -> None:
    payload.setdefault("evidences", []).append({
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_name": source_name,
        "source": source_name,
        "metric": source_type,
        "value": _jsonable(value),
        "period": payload.get("evaluation_context", {}).get("date") or payload.get("evaluation_window", {}).get("as_of_date") or "",
        "source_file": source_file,
        "snippet": snippet[:1000],
    })


def _add_daily_claim(payload: dict[str, Any], *, claim_id: str, text: str, evidence_ids: list[str]) -> None:
    payload.setdefault("claims", []).append({
        "claim_id": claim_id,
        "text": text,
        "evidence_ids": evidence_ids,
        "claim_type": "factual_daily_evidence",
    })


def _company_root(target: CompanyTarget) -> Path:
    root = project_root()
    candidates = [
        root / "data" / target.field / target.company_name,
        root / "data" / target.field / target.company_dir,
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return candidates[0]


def _read_excel_all_sheets(path: Path) -> dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(path, sheet_name=None)
    except Exception:
        return {}


def _find_valuation_workbook(target: CompanyTarget) -> Path | None:
    base = _company_root(target) / "valuation"
    files: list[Path] = []
    if base.exists():
        files.extend(base.glob(f"{target.company_dir}_valuation_workbook.xlsx"))
        files.extend(base.glob("*valuation_workbook*.xlsx"))
        files.extend(base.glob("*.xlsx"))
    seen: set[str] = set()
    unique: list[Path] = []
    for p in files:
        key = str(p).replace("\\", "/").lower()
        if key not in seen and p.exists() and p.is_file():
            seen.add(key)
            unique.append(p)
    for p in unique:
        name = p.name.lower()
        if "valuation" in name and "workbook" in name:
            return p
    return unique[0] if unique else None



def _enhance_valuation_with_workbook(target: CompanyTarget, window: DailyWindow, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Attach exact-day valuation workbook evidence without inventing opinions.

    The extractor checks all sheets in data/<field>/<company>/valuation/*valuation_workbook*.xlsx.
    It supports three workbook shapes:
      1) normal table with a date column,
      2) wide table where 2025-01-02 etc. are column headers,
      3) raw sheets where the date appears inside cells.
    """
    wb = _find_valuation_workbook(target)
    snapshot = dict(snapshot or {})
    metrics = dict(snapshot.get("metrics") or {})
    raw_payload = dict(snapshot.get("raw_payload") or {})

    base_status = {
        "valuation_workbook_status": "NO_VALUATION_WORKBOOK",
        "valuation_workbook_source_file": str(wb) if wb else "",
        "valuation_workbook_daily_rows": 0,
        "valuation_workbook_sheets": "",
        "valuation_workbook_date_column": "",
        "valuation_workbook_exact_table_rows": 0,
        "valuation_workbook_raw_date_rows": 0,
        "valuation_workbook_wide_date_metrics": 0,
    }
    metrics.update(base_status)
    if wb is None:
        snapshot["metrics"] = metrics
        snapshot["raw_payload"] = raw_payload
        return _jsonable(snapshot)

    header_sheets = _read_excel_all_sheets(wb)
    raw_sheets = _read_excel_all_sheets_header_none(wb)
    matched_tables: list[pd.DataFrame] = []
    raw_date_rows: list[pd.DataFrame] = []
    wide_values: dict[str, Any] = {}
    date_cols: list[str] = []
    sheet_hits: list[str] = []

    for sheet_name, df in header_sheets.items():
        if df is None or df.empty:
            continue
        day_rows, date_col = _filter_exact_day(df, window)
        if date_col:
            date_cols.append(f"{sheet_name}:{date_col}")
        if not day_rows.empty:
            tmp = day_rows.copy()
            tmp["_sheet"] = sheet_name
            matched_tables.append(tmp)
            sheet_hits.append(sheet_name)
        wvals = _wide_date_metrics(df, window)
        if wvals:
            wide_values.update({f"{sheet_name}:{k}": v for k, v in wvals.items()})
            if sheet_name not in sheet_hits:
                sheet_hits.append(sheet_name)

    for sheet_name, df in raw_sheets.items():
        if df is None or df.empty:
            continue
        raw_hit = _rows_containing_day(df, window)
        if not raw_hit.empty:
            tmp = raw_hit.copy()
            tmp["_sheet"] = sheet_name
            raw_date_rows.append(tmp)
            if sheet_name not in sheet_hits:
                sheet_hits.append(sheet_name)

    combined_values: dict[str, Any] = {}
    table_preview: dict[str, Any] = {}
    raw_preview: dict[str, Any] = {}
    exact_rows_count = 0
    raw_rows_count = 0

    if matched_tables:
        combined = pd.concat(matched_tables, ignore_index=True)
        exact_rows_count = int(len(combined))
        table_preview = _compact_preview(combined, max_cols=40)
        combined_values.update(table_preview)
        combined_values.update(_numeric_summary(combined, max_cols=40))
    if raw_date_rows:
        raw_combined = pd.concat(raw_date_rows, ignore_index=True)
        raw_rows_count = int(len(raw_combined))
        raw_preview = _compact_preview(raw_combined, max_cols=40)
        combined_values.update({f"raw:{k}": v for k, v in raw_preview.items()})
    if wide_values:
        combined_values.update(wide_values)

    alias_metrics = _extract_alias_metrics(combined_values)
    found = bool(exact_rows_count or raw_rows_count or wide_values)

    metrics.update({
        "valuation_workbook_status": "FOUND_EXACT_DAILY_WORKBOOK_DATA" if found else "NO_EXACT_DAILY_ROW_IN_WORKBOOK",
        "valuation_workbook_source_file": str(wb),
        "valuation_workbook_daily_rows": int(exact_rows_count + raw_rows_count + (1 if wide_values else 0)),
        "valuation_workbook_sheets": "; ".join(sheet_hits[:20]),
        "valuation_workbook_date_column": "; ".join(date_cols[:20]),
        "valuation_workbook_exact_table_rows": exact_rows_count,
        "valuation_workbook_raw_date_rows": raw_rows_count,
        "valuation_workbook_wide_date_metrics": len(wide_values),
        **alias_metrics,
    })

    raw_payload["valuation_workbook_daily_preview"] = table_preview
    raw_payload["valuation_workbook_raw_date_preview"] = raw_preview
    raw_payload["valuation_workbook_wide_date_values"] = wide_values
    raw_payload["valuation_workbook_alias_metrics"] = alias_metrics

    if found:
        _add_daily_evidence(
            snapshot,
            evidence_id="VALUATION_DAILY_WORKBOOK",
            source_type="valuation_workbook_exact_day",
            source_name="company valuation workbook",
            source_file=str(wb),
            value={"metrics": alias_metrics, "sheets": sheet_hits[:20], "rows": metrics["valuation_workbook_daily_rows"]},
            snippet=f"{target.company_name} {window.as_of_date} valuation workbook exact-day data found: rows={metrics['valuation_workbook_daily_rows']}, sheets={'; '.join(sheet_hits[:10])}",
        )
        _add_daily_claim(
            snapshot,
            claim_id="VALUATION_DAILY_FACT_001",
            text=f"{target.company_name} valuation snapshot uses only {window.as_of_date} rows/columns found in the company valuation workbook.",
            evidence_ids=["VALUATION_DAILY_WORKBOOK"],
        )
        snapshot["summary"] = (snapshot.get("summary") or "") + f"\n[Daily valuation workbook] {window.as_of_date} exact workbook evidence rows={metrics['valuation_workbook_daily_rows']}."

    snapshot["metrics"] = metrics
    snapshot["raw_payload"] = raw_payload
    return _jsonable(snapshot)


def _find_market_excel_files() -> list[Path]:
    root = project_root()
    patterns = [
        "data/market_excel/market_final_*.xlsx",
        "data/market-excel/market_final_*.xlsx",
        "data/market_excel/*.xlsx",
        "data/market-excel/*.xlsx",
        "data/*/_sector_common/data/Market_*.xlsx",
        "data/*/_sector_common/data/*Market*.xlsx",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(root.glob(pat))
    seen: set[str] = set()
    unique: list[Path] = []
    for p in files:
        key = str(p).replace("\\", "/").lower()
        if key not in seen and p.exists() and p.is_file():
            seen.add(key)
            unique.append(p)
    unique.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return unique


def _match_company_rows(df: pd.DataFrame, target: CompanyTarget) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    text = df.astype(str).agg(" ".join, axis=1)
    mask = text.str.contains(re.escape(target.company_name), case=False, na=False)
    if target.company_dir:
        mask = mask | text.str.contains(re.escape(target.company_dir), case=False, na=False)
    if target.stock_code:
        mask = mask | text.str.contains(re.escape(str(target.stock_code).zfill(6)), case=False, na=False)
    return df.loc[mask].copy()



def _targeted_market_excel_files(target: CompanyTarget) -> list[Path]:
    files = _find_market_excel_files()
    if not files:
        return []
    targeted = [p for p in files if _file_matches_target(p, target)]
    generic = [p for p in files if p not in targeted]
    return targeted + generic


def _market_excel_snapshot(target: CompanyTarget, window: DailyWindow) -> dict[str, Any]:
    files = _targeted_market_excel_files(target)
    out: dict[str, Any] = {
        "market_excel_status": "NO_MARKET_EXCEL_FILE",
        "market_excel_source_file": "",
        "market_excel_daily_rows": 0,
        "market_excel_total_score_raw": "",
        "market_excel_recommendation_raw": "",
        "market_excel_vc_role_raw": "",
        "market_excel_metric_preview": {},
    }
    if not files:
        return out

    checked: list[str] = []
    for path in files:
        file_is_targeted = _file_matches_target(path, target)
        checked.append(str(path))
        sheets = _read_excel_all_sheets(path)
        for sheet_name, df in sheets.items():
            if df is None or df.empty:
                continue
            matched = _match_company_rows(df, target)
            # Only allow one-row fallback for company-specific workbook/file.
            if matched.empty and file_is_targeted and len(df) == 1:
                matched = df.copy()
            if matched.empty:
                continue
            exact, _date_col = _filter_exact_day(matched, window)
            chosen = exact if not exact.empty else matched.tail(1)
            preview = _compact_preview(chosen, max_cols=40)
            total_score = ""
            recommendation = ""
            vc_role = ""
            for k, v in preview.items():
                lk = str(k).lower()
                sk = str(k)
                if not total_score and ("총점" in sk or "score" in lk):
                    total_score = v
                if not recommendation and ("투자의견" in sk or "recommend" in lk or "opinion" in lk):
                    recommendation = v
                if not vc_role and ("vc_role" in lk or "밸류체인" in sk or "value_chain" in lk):
                    vc_role = v
            out.update({
                "market_excel_status": "FOUND_EXACT_DAILY_ROWS" if not exact.empty else "FOUND_COMPANY_ROW_NO_DAILY_DATE",
                "market_excel_source_file": str(path),
                "market_excel_daily_rows": int(len(exact)),
                "market_excel_sheet": sheet_name,
                "market_excel_total_score_raw": total_score,
                "market_excel_recommendation_raw": recommendation,
                "market_excel_vc_role_raw": vc_role,
                "market_excel_metric_preview": preview,
                "market_excel_checked_files": checked[:10],
            })
            return out
    out["market_excel_status"] = "NO_COMPANY_ROW_IN_MARKET_EXCEL"
    out["market_excel_source_file"] = str(files[0])
    out["market_excel_checked_files"] = checked[:10]
    return out


def _enhance_market_daily(target: CompanyTarget, window: DailyWindow, snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(snapshot or {})
    metrics = dict(snapshot.get("metrics") or {})
    raw_payload = dict(snapshot.get("raw_payload") or {})
    dq = dict(snapshot.get("data_quality") or {})
    price_quality = dq.get("price_quality") if isinstance(dq.get("price_quality"), dict) else {}

    price_rows = (
        metrics.get("price_monthly_rows")
        or metrics.get("price_rows_month")
        or metrics.get("price_rows_daily")
        or price_quality.get("monthly_rows")
        or dq.get("monthly_rows")
        or 0
    )
    price_source = (
        metrics.get("price_source_file")
        or metrics.get("market_price_source_file")
        or price_quality.get("source_file")
        or dq.get("source_file")
        or ""
    )
    metrics["market_price_status"] = "FOUND_EXACT_DAILY_PRICE_ROW" if (_to_float(price_rows) or 0) > 0 else "NO_EXACT_DAILY_PRICE_ROW"
    metrics["market_price_daily_rows"] = price_rows
    metrics["market_price_monthly_rows"] = price_rows
    metrics["market_price_source_file"] = price_source

    excel_info = _market_excel_snapshot(target, window)
    for k, v in excel_info.items():
        if k != "market_excel_metric_preview":
            metrics[k] = v
    raw_payload["market_excel_metric_preview"] = excel_info.get("market_excel_metric_preview", {})

    if excel_info.get("market_excel_source_file"):
        _add_daily_evidence(
            snapshot,
            evidence_id="MARKET_DAILY_EXCEL_DB",
            source_type="market_excel_db",
            source_name="data/market_excel market_final workbook",
            source_file=str(excel_info.get("market_excel_source_file") or ""),
            value={k: v for k, v in excel_info.items() if k != "market_excel_metric_preview"},
            snippet=f"Market Excel DB source={excel_info.get('market_excel_source_file')} status={excel_info.get('market_excel_status')}",
        )
    snapshot["metrics"] = metrics
    snapshot["raw_payload"] = raw_payload
    return _jsonable(snapshot)




def _candidate_company_data_files(target: CompanyTarget, agent: str, exts: tuple[str, ...] = ("*.csv", "*.xlsx", "*.json")) -> list[Path]:
    root = _company_root(target)
    roots = [root / agent, root / "valuation", root / "valuation" / "intake", root / "_company_common"]
    files: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        for ext in exts:
            files.extend(r.glob(ext))
    seen = set()
    out = []
    for p in files:
        key = str(p).replace("\\", "/").lower()
        if key not in seen and p.exists() and p.is_file():
            seen.add(key)
            out.append(p)
    return out


def _read_table_file(path: Path) -> list[tuple[str, pd.DataFrame]]:
    try:
        if path.suffix.lower() in {".csv", ".txt"}:
            return [(path.stem, pd.read_csv(path, encoding="utf-8-sig"))]
        if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            return list(_read_excel_all_sheets(path).items())
    except Exception:
        return []
    return []


def _enhance_finance_daily(target: CompanyTarget, window: DailyWindow, snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(snapshot or {})
    metrics = dict(snapshot.get("metrics") or {})
    raw_payload = dict(snapshot.get("raw_payload") or {})
    hits: list[pd.DataFrame] = []
    source_files: list[str] = []

    for p in _candidate_company_data_files(target, "finance", ("*.csv", "*.xlsx", "*.xlsm")):
        for sheet, df in _read_table_file(p):
            if df is None or df.empty:
                continue
            exact, dcol = _filter_exact_day(df, window)
            if not exact.empty:
                tmp = exact.copy()
                tmp["_source_file"] = str(p)
                tmp["_sheet"] = sheet
                hits.append(tmp)
                source_files.append(str(p))

    if hits:
        combined = pd.concat(hits, ignore_index=True)
        metrics.update({
            "finance_daily_status": "FOUND_EXACT_DAILY_ROWS",
            "finance_daily_rows": int(len(combined)),
            "finance_daily_source_files": "; ".join(sorted(set(source_files))[:10]),
            **{f"finance_daily_{k}": v for k, v in _numeric_summary(combined, max_cols=20).items()},
        })
        raw_payload["finance_daily_preview"] = _compact_preview(combined, max_cols=30)
        _add_daily_evidence(snapshot, evidence_id="FINANCE_DAILY_ROWS", source_type="finance_exact_day_rows", source_name="local finance/valuation files", source_file="; ".join(sorted(set(source_files))[:10]), value=raw_payload["finance_daily_preview"], snippet=f"{target.company_name} finance exact-day rows found for {window.as_of_date}: {len(combined)}")
    else:
        metrics.setdefault("finance_daily_status", "NO_EXACT_DAILY_FINANCE_ROW")
        metrics.setdefault("finance_daily_rows", 0)
    snapshot["metrics"] = metrics
    snapshot["raw_payload"] = raw_payload
    return _jsonable(snapshot)


def _decode_escaped_unicode(text: str) -> str:
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text))


def _split_name_and_date(stem: str) -> tuple[str, str]:
    decoded = _decode_escaped_unicode(stem)
    m = re.match(r"^(?P<base>.+?)_(?P<date>20\d{6})$", decoded)
    if not m:
        return decoded, "00000000"
    return m.group("base"), m.group("date")


def _select_latest_files_by_key(files: list[Path]) -> list[Path]:
    latest_by_key: dict[str, tuple[str, Path]] = {}
    for path in sorted(files, key=lambda p: p.name):
        key, d = _split_name_and_date(path.stem)
        old = latest_by_key.get(key)
        if old is None or d > old[0]:
            latest_by_key[key] = (d, path)
    return [item[1] for item in sorted(latest_by_key.values(), key=lambda x: x[1].name)]


def _macro_candidate_files(field: str) -> list[Path]:
    root = project_root()
    patterns = [
        "data/_global_common/macro/**/*.csv",
        "data/_global_common/macro/**/*.xlsx",
        f"data/{field}/_sector_common/macro/**/*.csv",
        f"data/{field}/_sector_common/macro/**/*.xlsx",
        f"data/{field}/_sector_common/data/*macro*.csv",
        f"data/{field}/_sector_common/data/*macro*.xlsx",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(root.glob(pat))
    exclude_keys = ["macro_run_summary", "run_summary", "summary"]
    files = [
        p for p in files
        if p.exists()
        and p.is_file()
        and not any(ex in p.name.lower() for ex in exclude_keys)
        and "debug" not in [part.lower() for part in p.parts]
    ]
    # Additional filename keyword scan, limited to obvious macro names.
    keywords = ["macro", "ecos", "fred", "oecd", "exchange", "fx", "rate", "interest", "환율", "금리", "cpi", "물가"]
    for p in (root / "data" / "_global_common").rglob("*") if (root / "data" / "_global_common").exists() else []:
        if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".xlsm"}:
            lower_name = p.name.lower()
            lower_parts = [part.lower() for part in p.parts]
            if any(ex in lower_name for ex in exclude_keys):
                continue
            if "debug" in lower_parts:
                continue
            if any(k in lower_name for k in keywords):
                files.append(p)
    return _select_latest_files_by_key(files)


def _latest_before_day(df: pd.DataFrame, window: DailyWindow) -> pd.DataFrame:
    norm, dcol = _normalize_date_columns(df)
    if "__date" not in norm.columns:
        return pd.DataFrame()
    before = norm[norm["__date"] <= window.start].copy()
    before = before.dropna(subset=["__date"])
    if before.empty:
        return before
    max_d = before["__date"].max()
    return before[before["__date"] == max_d].drop(columns=["__date"], errors="ignore")


def _enhance_macro_daily(target: CompanyTarget, window: DailyWindow, snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(snapshot or {})
    metrics = dict(snapshot.get("metrics") or {})
    raw_payload = dict(snapshot.get("raw_payload") or {})
    exact_hits: list[pd.DataFrame] = []
    asof_hits: list[pd.DataFrame] = []
    exact_files: list[str] = []
    asof_files: list[str] = []

    for p in _macro_candidate_files(target.field):
        for sheet, df in _read_table_file(p):
            if df is None or df.empty:
                continue
            exact, dcol = _filter_exact_day(df, window)
            if not exact.empty:
                tmp = exact.copy()
                tmp["_source_file"] = str(p)
                tmp["_sheet"] = sheet
                exact_hits.append(tmp)
                exact_files.append(str(p))
            else:
                latest = _latest_before_day(df, window)
                if not latest.empty:
                    tmp = latest.copy()
                    tmp["_source_file"] = str(p)
                    tmp["_sheet"] = sheet
                    asof_hits.append(tmp)
                    asof_files.append(str(p))

    chosen = pd.concat(exact_hits, ignore_index=True) if exact_hits else (pd.concat(asof_hits, ignore_index=True) if asof_hits else pd.DataFrame())
    source_files = exact_files if exact_hits else asof_files
    if not chosen.empty:
        nums = _numeric_summary(chosen, max_cols=60)
        status = "FOUND_EXACT_DAILY_MACRO_ROWS" if exact_hits else "NO_EXACT_DAILY_MACRO_ROW_USED_LATEST_BEFORE_DATE"
        metrics.update({
            "macro_daily_status": status,
            "macro_daily_rows": int(len(chosen)),
            "macro_daily_exact_rows": int(sum(len(x) for x in exact_hits)) if exact_hits else 0,
            "macro_daily_source_files": "; ".join(sorted(set(source_files))[:10]),
            "macro_daily_indicator_preview": nums,
        })
        # Override/add macro_indicators with daily/as-of numbers so Chair sees date-specific macro values.
        old_ind = metrics.get("macro_indicators") if isinstance(metrics.get("macro_indicators"), dict) else {}
        metrics["macro_indicators"] = {**old_ind, **nums}
        raw_payload["macro_daily_preview"] = _compact_preview(chosen, max_cols=40)
        _add_daily_evidence(snapshot, evidence_id="MACRO_DAILY_ROWS", source_type="macro_exact_or_asof_rows", source_name="local macro csv/xlsx", source_file=metrics["macro_daily_source_files"], value=nums, snippet=f"{target.company_name} macro data for {window.as_of_date}: {status}, rows={len(chosen)}")
    else:
        metrics.setdefault("macro_daily_status", "NO_MACRO_ROWS_ON_OR_BEFORE_DATE")
        metrics.setdefault("macro_daily_rows", 0)
    snapshot["metrics"] = metrics
    snapshot["raw_payload"] = raw_payload
    return _jsonable(snapshot)


def _enhance_issue_daily(target: CompanyTarget, window: DailyWindow, snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(snapshot or {})
    metrics = dict(snapshot.get("metrics") or {})
    dq = dict(snapshot.get("data_quality") or {})
    count = metrics.get("daily_issue_count")
    if count in (None, ""):
        count = metrics.get("monthly_issue_count") or metrics.get("news_count") or dq.get("monthly_rows") or 0
    metrics["issue_daily_count"] = count
    metrics["issue_daily_status"] = "FOUND_EXACT_DAILY_ISSUES" if (_to_float(count) or 0) > 0 else "NO_ISSUE_ROWS_ON_DATE"
    snapshot["metrics"] = metrics
    return _jsonable(snapshot)



def _enhance_snapshots_for_daily(target: CompanyTarget, window: DailyWindow, snapshots: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = dict(snapshots)
    # Set daily evaluation context first so evidence period/date is correct.
    for agent, payload in out.items():
        payload = dict(payload or {})
        payload["evaluation_context"] = {
            "mode": "daily_cutoff",
            "date": window.as_of_date,
            "start_date": window.start_s,
            "end_date": window.end_s,
            "no_future_data": True,
            "rule": "Only rows exactly dated on the evaluation day are used; if a macro series has no row for a non-business day, latest row on/before the date is marked explicitly.",
        }
        if isinstance(payload.get("evaluation_window"), dict):
            payload["evaluation_window"].update({
                "mode": "daily_asof_replay",
                "month": window.month,
                "start_date": window.start_s,
                "end_date": window.end_s,
                "as_of_date": window.as_of_date,
                "strict_no_future_data": True,
            })
        out[agent] = payload

    out["finance"] = _enhance_finance_daily(target, window, out.get("finance", {}))
    out["market"] = _enhance_market_daily(target, window, out.get("market", {}))
    out["valuation"] = _enhance_valuation_with_workbook(target, window, out.get("valuation", {}))
    out["issue"] = _enhance_issue_daily(target, window, out.get("issue", {}))
    out["macro"] = _enhance_macro_daily(target, window, out.get("macro", {}))
    return out


def _payload_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            obj = json.loads(value)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _deep_find_qd(data: Any, max_depth: int = 8) -> dict[str, Any] | None:
    if max_depth < 0:
        return None
    if isinstance(data, dict):
        qd = data.get("quantitative_decision")
        if isinstance(qd, dict) and isinstance(qd.get("agent_decisions"), dict):
            return qd
        for value in data.values():
            found = _deep_find_qd(value, max_depth - 1)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _deep_find_qd(value, max_depth - 1)
            if found:
                return found
    return None


def _recommendation_from_qd(qd: dict[str, Any]) -> str:
    for key in ("final_recommendation", "recommendation", "opinion"):
        value = qd.get(key)
        if value not in (None, "", [], {}):
            return str(value)
    return ""


def _weighted_signal_from_qd(qd: dict[str, Any]) -> Any:
    for key in ("weighted_signal", "final_weighted_signal", "total_weighted_signal"):
        value = qd.get(key)
        if value not in (None, "", [], {}):
            return value
    return ""


def _load_run_results(*, run_id: str, field: str) -> list[dict[str, Any]]:
    from common.agent_history import list_run_results
    return list_run_results(run_id=run_id, field=field, include_payload=True)



def _base_row_from_snapshots(*, target: CompanyTarget, window: DailyWindow, snapshots: dict[str, dict[str, Any]], run_id: str) -> dict[str, Any]:
    market_metrics = snapshots.get("market", {}).get("metrics", {}) or {}
    valuation_metrics = snapshots.get("valuation", {}).get("metrics", {}) or {}
    issue_metrics = snapshots.get("issue", {}).get("metrics", {}) or {}
    macro_metrics = snapshots.get("macro", {}).get("metrics", {}) or {}
    tech_metrics = snapshots.get("tech", {}).get("metrics", {}) or {}
    finance_metrics = snapshots.get("finance", {}).get("metrics", {}) or {}

    macro_source_files = macro_metrics.get("macro_source_files", [])
    if isinstance(macro_source_files, list):
        macro_source_files_text = "; ".join(str(x) for x in macro_source_files[:5])
    else:
        macro_source_files_text = str(macro_source_files or "")

    return {
        "date": window.as_of_date,
        "ticker": target.company_name,
        "recommendation": "",
        "weighted_signal": "",
        "stock_code": target.stock_code,
        "company_dir": target.company_dir,
        "field": target.field,
        "as_of_date": window.as_of_date,
        "run_id": run_id,

        "finance_daily_status": finance_metrics.get("finance_daily_status", ""),
        "finance_daily_rows": finance_metrics.get("finance_daily_rows", ""),
        "finance_daily_source_files": finance_metrics.get("finance_daily_source_files", ""),
        "finance_fiscal_year_used": finance_metrics.get("fiscal_year_used", ""),
        "finance_source_file": finance_metrics.get("finance_source_file", ""),
        "finance_sales_growth_pct": finance_metrics.get("sales_growth_%", ""),
        "finance_operating_margin_pct": finance_metrics.get("operating_margin_%", ""),
        "finance_debt_ratio_pct": finance_metrics.get("debt_ratio_%", ""),

        "market_price_status": market_metrics.get("market_price_status", ""),
        "market_price_daily_rows": market_metrics.get("market_price_daily_rows", ""),
        "market_price_source_file": market_metrics.get("market_price_source_file", ""),
        "market_excel_status": market_metrics.get("market_excel_status", ""),
        "market_excel_source_file": market_metrics.get("market_excel_source_file", ""),
        "market_excel_total_score_raw": market_metrics.get("market_excel_total_score_raw", ""),
        "market_excel_recommendation_raw": market_metrics.get("market_excel_recommendation_raw", ""),
        "market_excel_vc_role_raw": market_metrics.get("market_excel_vc_role_raw", ""),

        "valuation_workbook_status": valuation_metrics.get("valuation_workbook_status", ""),
        "valuation_workbook_source_file": valuation_metrics.get("valuation_workbook_source_file", ""),
        "valuation_workbook_daily_rows": valuation_metrics.get("valuation_workbook_daily_rows", ""),
        "valuation_workbook_exact_table_rows": valuation_metrics.get("valuation_workbook_exact_table_rows", ""),
        "valuation_workbook_raw_date_rows": valuation_metrics.get("valuation_workbook_raw_date_rows", ""),
        "valuation_workbook_wide_date_metrics": valuation_metrics.get("valuation_workbook_wide_date_metrics", ""),
        "valuation_workbook_sheets": valuation_metrics.get("valuation_workbook_sheets", ""),
        "valuation_workbook_date_column": valuation_metrics.get("valuation_workbook_date_column", ""),
        "valuation_implied_price": valuation_metrics.get("valuation_implied_price", ""),
        "valuation_current_price": valuation_metrics.get("valuation_current_price", ""),
        "valuation_gap_pct": valuation_metrics.get("valuation_gap_pct", ""),
        "valuation_wacc": valuation_metrics.get("valuation_wacc", ""),
        "valuation_dcf_value": valuation_metrics.get("valuation_dcf_value", ""),
        "valuation_psr": valuation_metrics.get("valuation_psr", ""),
        "valuation_per": valuation_metrics.get("valuation_per", ""),
        "valuation_pbr": valuation_metrics.get("valuation_pbr", ""),
        "valuation_score": valuation_metrics.get("valuation_score", ""),

        "issue_status": issue_metrics.get("issue_daily_status", ""),
        "issue_daily_count": issue_metrics.get("issue_daily_count", ""),
        "issue_news_count": issue_metrics.get("monthly_issue_count", issue_metrics.get("news_count", "")),
        "issue_source_file": issue_metrics.get("issue_source_file", ""),

        "macro_daily_status": macro_metrics.get("macro_daily_status", ""),
        "macro_daily_rows": macro_metrics.get("macro_daily_rows", ""),
        "macro_daily_exact_rows": macro_metrics.get("macro_daily_exact_rows", ""),
        "macro_daily_source_files": macro_metrics.get("macro_daily_source_files", ""),
        "macro_daily_indicator_preview": _json_dump_compact(macro_metrics.get("macro_daily_indicator_preview", {})),
        "macro_score": macro_metrics.get("macro_score", ""),
        "macro_source_files": macro_source_files_text,

        "tech_source_file": tech_metrics.get("tech_source_file", ""),
        "tech_final_score": tech_metrics.get("final_tech_investor_score", ""),
        "tech_ip_evidence_score": tech_metrics.get("ip_evidence_composite_score", ""),
    }




# ---------------------------------------------------------------------
# Valuation workbook backed signal patch
# ---------------------------------------------------------------------

def _clip_signal(value: Any) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    return max(-1.0, min(1.0, num))


def _find_numeric_by_keywords_from_preview(preview: dict[str, Any], keywords: list[str]) -> float | None:
    if not isinstance(preview, dict):
        return None

    for k, v in preview.items():
        key = str(k).lower()
        raw_key = str(k)

        if any(kw.lower() in key or kw in raw_key for kw in keywords):
            num = _to_float(v)
            if num is not None:
                return num

    return None


def _valuation_gap_from_snapshot(row: dict[str, Any]) -> tuple[float | None, str]:
    """
    valuation workbook?? ?? ???/???/???? ??? valuation gap? ???.
    ????:
    1) ?? valuation_gap_pct ??? ??? ??? ??
    2) valuation_implied_price / valuation_current_price
    3) valuation_workbook preview? ????/????/DCF value? ???/??
    """

    direct_gap = _to_float(
        row.get("valuation_gap_pct")
        or row.get("valuation_upside_downside_pct")
        or row.get("upside_downside_pct")
    )
    if direct_gap is not None:
        return direct_gap, "valuation_gap_pct_existing"

    implied = _to_float(
        row.get("valuation_implied_price")
        or row.get("valuation_target_price")
        or row.get("valuation_fair_price")
        or row.get("dcf_implied_price")
    )
    current = _to_float(
        row.get("valuation_current_price")
        or row.get("valuation_close")
        or row.get("market_end_close")
        or row.get("end_close")
    )

    if implied is not None and current not in (None, 0):
        return (implied / current - 1.0) * 100.0, "valuation_price_columns"

    # daily_eval.py ???? base row? preview dict? ???/JSON?? ??? ???? ??
    preview = row.get("valuation_workbook_metric_preview") or row.get("valuation_workbook_daily_preview") or {}
    if isinstance(preview, str):
        try:
            preview = json.loads(preview)
        except Exception:
            preview = {}

    numeric_summary = row.get("valuation_workbook_numeric_summary") or {}
    if isinstance(numeric_summary, str):
        try:
            numeric_summary = json.loads(numeric_summary)
        except Exception:
            numeric_summary = {}

    merged = {}
    if isinstance(preview, dict):
        merged.update(preview)
    if isinstance(numeric_summary, dict):
        merged.update(numeric_summary)

    current = _find_numeric_by_keywords_from_preview(
        merged,
        [
            "???", "??", "close", "current price", "market price",
            "??", "price",
        ],
    )
    implied = _find_numeric_by_keywords_from_preview(
        merged,
        [
            "????", "????", "????", "implied price", "fair price",
            "target price", "dcf value", "dcf", "intrinsic",
        ],
    )

    # ????/???? ?? ?? ? ?? ?? ??? ? ??
    if current is not None and implied is not None:
        if current > 0 and 10 <= current <= 2_000_000 and 10 <= implied <= 2_000_000:
            return (implied / current - 1.0) * 100.0, "valuation_workbook_preview_price_pair"

    return None, "valuation_gap_not_found"


def _apply_valuation_signal_from_excel_formula(row: dict[str, Any]) -> dict[str, Any]:
    """
    Auditor? valuation_signal? 0?? ?????,
    valuation workbook? ??? ?? ???? ??? ? ????? valuation_signal? ???.

    valuation_signal = valuation_gap_pct / 100
    ?: ??? ?? ???? +18.5% -> 0.185
        ??? ?? ???? -12.3% -> -0.123
    """

    status = str(row.get("valuation_workbook_status") or "")
    signal = _to_float(row.get("valuation_signal"))

    # workbook? ??? ???? ???.
    if "FOUND" not in status:
        return row

    # ?? signal? ?? 0? ?? ??? ?? Auditor ?? ????.
    if signal is not None and abs(signal) > 1e-12:
        return row

    gap_pct, source = _valuation_gap_from_snapshot(row)

    if gap_pct is None:
        row["valuation_signal_source"] = "VALUATION_WORKBOOK_FOUND_BUT_GAP_NOT_EXTRACTED"
        row["valuation_gap_pct"] = row.get("valuation_gap_pct", "")
        return row

    valuation_signal = _clip_signal(gap_pct / 100.0)

    if valuation_signal is None:
        return row

    row["valuation_gap_pct"] = round(float(gap_pct), 6)
    row["valuation_signal"] = round(float(valuation_signal), 6)
    row["valuation_signal_source"] = f"excel_formula:{source}:signal=gap_pct/100"

    weight = _to_float(row.get("valuation_weight"))
    if weight is not None:
        row["valuation_weighted_signal"] = round(float(valuation_signal) * weight, 6)
        row["valuation_weighted_signal_source"] = "excel_formula:valuation_signal*valuation_weight"

    # recommendation? signal ??? ????? ??
    if not row.get("valuation_recommendation"):
        if valuation_signal > 0:
            row["valuation_recommendation"] = "BUY_DIRECTION"
        elif valuation_signal < 0:
            row["valuation_recommendation"] = "SELL_DIRECTION"
        else:
            row["valuation_recommendation"] = "HOLD_DIRECTION"

    return row



def export_daily_signal_csv(*, targets: list[CompanyTarget], windows: list[DailyWindow], run_id: str, field: str, base_rows: list[dict[str, Any]], output_dir: str | Path | None = None) -> Path:
    rows = _load_run_results(run_id=run_id, field=field)
    qd_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    qd_source_by_key: dict[tuple[str, str], str] = {}

    for result in rows:
        payload = _payload_dict(result.get("payload"))
        qd = _deep_find_qd(payload)
        if not qd:
            continue
        company_dir = str(result.get("company_dir") or "")
        as_of_date = str(result.get("as_of_date") or "")
        key = (as_of_date, company_dir)
        qd_by_key[key] = qd
        qd_source_by_key[key] = f"google_sheets_run_results:{result.get('agent')}:{result.get('output_kind')}"

    out_rows: list[dict[str, Any]] = []
    for base in base_rows:
        row = dict(base)
        key = (str(row.get("as_of_date") or ""), str(row.get("company_dir") or ""))
        qd = qd_by_key.get(key)
        if qd:
            row["auditor_qd_status"] = "FOUND"
            row["auditor_qd_source"] = qd_source_by_key.get(key, "")
            row["recommendation"] = _recommendation_from_qd(qd)
            row["weighted_signal"] = _weighted_signal_from_qd(qd)
            decisions = qd.get("agent_decisions") if isinstance(qd.get("agent_decisions"), dict) else {}
            for agent in AGENTS:
                dec = decisions.get(agent) if isinstance(decisions.get(agent), dict) else {}
                row[f"{agent}_signal"] = dec.get("signal", "")
                row[f"{agent}_weighted_signal"] = dec.get("weighted_contribution", "")
                row[f"{agent}_recommendation"] = dec.get("recommendation", "")
                row[f"{agent}_weight"] = dec.get("weight", "")
                row[f"{agent}_signal_source"] = "auditor_quantitative_decision" if dec else "AUDITOR_AGENT_DECISION_NOT_FOUND"
        else:
            row["auditor_qd_status"] = "NOT_FOUND"
            row["auditor_qd_source"] = ""
            for agent in AGENTS:
                row.setdefault(f"{agent}_signal", "")
                row.setdefault(f"{agent}_weighted_signal", "")
                row.setdefault(f"{agent}_recommendation", "")
                row.setdefault(f"{agent}_weight", "")
                row.setdefault(f"{agent}_signal_source", "AUDITOR_QD_NOT_FOUND")
        row = _apply_objective_zero_signal_backfill(row)
        row = _apply_valuation_signal_from_excel_formula(row)
        out_rows.append(row)

    if output_dir is None:
        output_dir = project_root() / "data" / field / "_sector_common" / "history_sheets_exports" / "daily" / windows[0].yyyy_mm / run_id
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"signal_df_daily_{windows[0].yyyy_mm}.csv"

    df = pd.DataFrame(out_rows)
    # signal 컬럼을 CSV 맨 앞쪽에 배치한다.
    # 기존에는 signal 컬럼이 뒤쪽으로 밀려 Excel에서 "없는 것처럼" 보였기 때문에
    # date/ticker/recommendation 바로 뒤에서 확인 가능하게 정렬한다.
    signal_front = [
        "date",
        "ticker",
        "recommendation",
        "weighted_signal",
        "auditor_qd_status",
        "auditor_qd_source",
    ]

    for agent in AGENTS:
        signal_front.extend(
            [
                f"{agent}_signal",
                f"{agent}_weighted_signal",
                f"{agent}_recommendation",
                f"{agent}_weight",
                f"{agent}_signal_source",
            ]
        )

    evidence_front = [
        "stock_code",
        "company_dir",
        "field",
        "as_of_date",
        "run_id",
        "market_price_status",
        "market_price_daily_rows",
        "market_price_source_file",
        "market_excel_status",
        "market_excel_source_file",
        "market_excel_total_score_raw",
        "market_excel_recommendation_raw",
        "market_excel_vc_role_raw",
        "valuation_workbook_status",
        "valuation_workbook_source_file",
        "valuation_workbook_daily_rows",
        "valuation_workbook_sheets",
        "valuation_workbook_date_column",
        "issue_status",
        "issue_news_count",
        "issue_source_file",
        "macro_score",
        "macro_source_files",
        "finance_fiscal_year_used",
        "finance_source_file",
        "finance_sales_growth_pct",
        "finance_operating_margin_pct",
        "finance_debt_ratio_pct",
        "tech_source_file",
        "tech_final_score",
        "tech_ip_evidence_score",
    ]

    front = [c for c in signal_front + evidence_front if c in df.columns]
    cols = front + [c for c in df.columns if c not in front]
    df = df[cols]
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[DONE] daily signal_df 저장 완료: {out_path}")
    return out_path


def run_daily_evaluation(*, start_date: str, end_date: str, universe_csv: str | Path, field: str = "반도체", limit: int | None = None, run_id: str | None = None, output_dir: str | Path | None = None, fail_open: bool = True, skip_chair: bool = False, date_limit: int | None = None) -> Path:
    windows = iter_days(start_date, end_date)
    if date_limit:
        windows = windows[:date_limit]

    targets = read_universe(universe_csv, field=field)
    if limit:
        targets = targets[:limit]
    if not targets:
        raise RuntimeError(f"universe CSV에서 실행 대상을 찾지 못했습니다: {universe_csv}")

    run_id = run_id or f"eval_daily_{windows[0].yyyy_mm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"[start/daily] dates={windows[0].as_of_date}~{windows[-1].as_of_date}, companies={len(targets)}, run_id={run_id}")
    print("[mode] objective daily snapshots -> Google Sheets history -> existing Chair/Auditor replay -> one daily CSV")

    base_rows: list[dict[str, Any]] = []
    total = len(windows) * len(targets)
    step = 0

    for window in windows:
        for target in targets:
            step += 1
            print(f"[{step}/{total}] {window.as_of_date} {target.company_name}/{target.company_dir} daily snapshots 저장 중...")
            snapshots = build_all_snapshots(target, window)  # DailyWindow intentionally mirrors MonthWindow interface.
            snapshots = _enhance_snapshots_for_daily(target, window, snapshots)
            save_snapshots_to_history(target, window, snapshots)
            base_rows.append(_base_row_from_snapshots(target=target, window=window, snapshots=snapshots, run_id=run_id))

            if not skip_chair:
                print(f"[{step}/{total}] {window.as_of_date} {target.company_name}/{target.company_dir} Chair history replay 실행 중...")
                run_chair_from_history(target, window, run_id=run_id, fail_open=fail_open)

    return export_daily_signal_csv(targets=targets, windows=windows, run_id=run_id, field=field, base_rows=base_rows, output_dir=output_dir)

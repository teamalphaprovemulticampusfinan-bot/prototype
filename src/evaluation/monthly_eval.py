from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore


AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


@dataclass(frozen=True)
class MonthWindow:
    """
    Monthly evaluation window.

    start_date/end_date are kept as ISO strings because the existing
    evaluation code filters local files with pandas using these fields.
    start/end properties are provided for Chair replay environment helpers
    and any code path that expects date objects.
    """
    month: str
    start_date: str
    end_date: str
    as_of_date: str
    year: int
    month_num: int

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

@dataclass(frozen=True)
class CompanyTarget:
    field: str
    company_dir: str
    company_name: str
    stock_code: str = ""


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_root() -> Path:
    return project_root() / "data"


def parse_month(month: str) -> MonthWindow:
    m = str(month).strip()
    if not re.fullmatch(r"\d{4}-\d{2}", m):
        raise ValueError("--month는 YYYY-MM 형식이어야 합니다. 예: 2025-01")
    y = int(m[:4])
    mo = int(m[5:7])
    start = date(y, mo, 1)
    if mo == 12:
        next_month = date(y + 1, 1, 1)
    else:
        next_month = date(y, mo + 1, 1)
    end = next_month.fromordinal(next_month.toordinal() - 1)
    return MonthWindow(
        month=m,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        as_of_date=end.isoformat(),
        year=y,
        month_num=mo,
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value)):
        return float(value)
    text = _clean_text(value).replace(",", "")
    if text in {"", "nan", "NaN", "None", "null", "확인 불가", "확인 제한"}:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _safe_div(a: Any, b: Any) -> float | None:
    aa = _to_float(a)
    bb = _to_float(b)
    if aa is None or bb in (None, 0):
        return None
    return aa / bb


def _round(value: Any, ndigits: int = 4) -> float | None:
    v = _to_float(value)
    if v is None:
        return None
    return round(v, ndigits)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _try_read_csv(path: Path) -> Any:
    if pd is None or not path.exists():
        return None
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return None


def _try_read_excel(path: Path, sheet_name: Any = None) -> Any:
    if pd is None or not path.exists():
        return None
    try:
        return pd.read_excel(path, sheet_name=sheet_name)
    except Exception:
        return None


def _find_date_column(df: Any) -> str | None:
    if df is None or not hasattr(df, "columns"):
        return None
    candidates = [
        "date", "Date", "날짜", "일자", "기준일", "게시일시", "발행일", "published_at",
        "published", "pubDate", "period", "fetched_at", "fetched_at_kst",
    ]
    cols = [str(c) for c in df.columns]
    lower_map = {c.lower(): c for c in cols}
    for c in candidates:
        if c in cols:
            return c
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    for c in cols:
        cl = c.lower()
        if "date" in cl or "일" in c or "기간" in c:
            return c
    return None


def _parse_dates(series: Any) -> Any:
    if pd is None:
        return None
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    try:
        return parsed.dt.tz_convert(None)
    except Exception:
        try:
            return parsed.dt.tz_localize(None)
        except Exception:
            return parsed


def _filter_df_by_window(df: Any, window: MonthWindow, *, allow_asof: bool = False) -> Any:
    if pd is None or df is None or len(df) == 0:
        return df
    col = _find_date_column(df)
    if not col:
        return df.iloc[0:0].copy()
    out = df.copy()
    out["__parsed_date"] = _parse_dates(out[col])
    start = pd.Timestamp(window.start_date)
    end = pd.Timestamp(window.end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    if allow_asof:
        out = out[out["__parsed_date"] <= end]
    else:
        out = out[(out["__parsed_date"] >= start) & (out["__parsed_date"] <= end)]
    return out


def _latest_rows_by_date(df: Any, window: MonthWindow) -> Any:
    if pd is None or df is None or len(df) == 0:
        return df
    col = _find_date_column(df)
    if not col:
        return df.iloc[0:0].copy()
    out = df.copy()
    out["__parsed_date"] = _parse_dates(out[col])
    end = pd.Timestamp(window.end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    out = out[out["__parsed_date"] <= end]
    out = out.dropna(subset=["__parsed_date"])
    if len(out) == 0:
        return out
    max_date = out["__parsed_date"].max()
    return out[out["__parsed_date"] == max_date]


def _df_records(df: Any, limit: int = 20) -> list[dict[str, Any]]:
    if pd is None or df is None or len(df) == 0:
        return []
    tmp = df.head(limit).copy()
    for col in list(tmp.columns):
        if str(col).startswith("__"):
            tmp = tmp.drop(columns=[col])
    return json.loads(tmp.where(pd.notnull(tmp), None).to_json(orient="records", force_ascii=False))


def _source_rel(path: Path) -> str:
    try:
        return str(path.relative_to(project_root())).replace("/", "\\")
    except Exception:
        return str(path)


def company_root(target: CompanyTarget) -> Path:
    # 실제 data 폴더는 company_dir가 아니라 한국어 회사명 폴더인 경우가 많다.
    candidates = [
        data_root() / target.field / target.company_name,
        data_root() / target.field / target.company_dir,
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def read_universe(universe_csv: str | Path, *, field: str) -> list[CompanyTarget]:
    path = Path(universe_csv)
    if not path.is_absolute():
        path = project_root() / path
    if not path.exists():
        raise FileNotFoundError(f"universe csv가 없습니다: {path}")

    targets: list[CompanyTarget] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_dir = _clean_text(row.get("company_dir") or row.get("slug") or row.get("기업코드") or row.get("code"))
            company_name = _clean_text(row.get("company") or row.get("company_name") or row.get("기업명") or row.get("name"))
            stock_code = _clean_text(row.get("stock_code") or row.get("ticker") or row.get("종목코드") or row.get("symbol"))
            if not company_dir or not company_name:
                continue
            targets.append(CompanyTarget(field=field, company_dir=company_dir, company_name=company_name, stock_code=stock_code))
    if not targets:
        raise RuntimeError(f"universe csv에서 기업을 읽지 못했습니다: {path}")
    return targets


def _base_snapshot(target: CompanyTarget, window: MonthWindow, agent: str) -> dict[str, Any]:
    return {
        "agent": agent,
        "company": target.company_name,
        "company_name": target.company_name,
        "company_dir": target.company_dir,
        "field": target.field,
        "evaluation_window": {
            "mode": "monthly_asof_replay",
            "month": window.month,
            "start_date": window.start_date,
            "end_date": window.end_date,
            "as_of_date": window.as_of_date,
            "strict_no_future_data": True,
        },
        "data_cutoff_policy": "Only rows dated within the month, or fiscal/source rows knowable as of month-end, are used. No future live snapshot is used for monthly evidence.",
        "claims": [],
        "evidences": [],
        "source_contexts": [],
        "metrics": {},
        "data_quality": {},
    }


def _add_evidence(payload: dict[str, Any], *, evidence_id: str, source_type: str, source_name: str, snippet: str, value: Any = None, period: str | None = None, source_file: str | None = None) -> None:
    payload.setdefault("evidences", []).append({
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_name": source_name,
        "source": source_name,
        "metric": source_type,
        "value": value,
        "period": period,
        "source_file": source_file or "",
        "snippet": snippet,
    })


def _add_claim(payload: dict[str, Any], *, claim_id: str, text: str, evidence_ids: list[str]) -> None:
    payload.setdefault("claims", []).append({
        "claim_id": claim_id,
        "text": text,
        "evidence_ids": evidence_ids,
        "claim_type": "factual_monthly_evidence",
    })


def _find_files(company_dir: Path, agent: str, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    roots = [company_dir / agent, company_dir / "auditor" / "first_auditor" / "compact_agent_packets"]
    for root in roots:
        if not root.exists():
            continue
        for pat in patterns:
            out.extend(root.glob(pat))
    seen = set()
    unique: list[Path] = []
    for p in out:
        sp = str(p)
        if sp not in seen and p.exists():
            seen.add(sp)
            unique.append(p)
    return unique


# ------------------------- Finance -------------------------


def _available_fiscal_year_for_asof(window: MonthWindow) -> int:
    # 2025-01 시점에서는 2024 사업보고서 확정 전일 가능성이 높으므로 2023년까지 사용.
    # 분기/공시일이 별도 제공되면 이 함수 대신 filing_date 기준으로 확장 가능.
    return window.year - 2 if window.month_num <= 3 else window.year - 1


def _read_financials(target: CompanyTarget) -> tuple[Any, str]:
    root = company_root(target)
    paths = [
        root / "valuation" / "intake" / "valuation_normalized_financials.csv",
        root / "finance" / f"{target.company_name}_재무.csv",
        root / "finance" / f"{target.company_name}_재무데이터.csv",
    ]
    for p in paths:
        df = _try_read_csv(p)
        if df is not None and len(df) > 0:
            return df, _source_rel(p)
    return None, ""


def build_finance_snapshot(target: CompanyTarget, window: MonthWindow) -> dict[str, Any]:
    payload = _base_snapshot(target, window, "finance")
    df, source_file = _read_financials(target)
    if df is None or len(df) == 0:
        payload["data_quality"] = {"status": "NO_LOCAL_FINANCE_FILE", "source_file": source_file}
        payload["summary"] = f"{target.company_name} finance snapshot: {window.month} 기준 사용 가능한 로컬 재무 CSV가 없습니다."
        return payload

    work = df.copy()
    year_col = None
    for c in work.columns:
        if str(c).lower() in {"year", "fiscal_year", "연도", "사업연도"}:
            year_col = c
            break
    if year_col is None:
        payload["data_quality"] = {"status": "NO_YEAR_COLUMN", "source_file": source_file}
        payload["summary"] = f"{target.company_name} finance snapshot: 연도 컬럼을 찾지 못했습니다."
        return payload

    work["__year"] = pd.to_numeric(work[year_col], errors="coerce") if pd is not None else work[year_col]
    max_year = _available_fiscal_year_for_asof(window)
    work = work[work["__year"] <= max_year].dropna(subset=["__year"])
    if len(work) == 0:
        payload["data_quality"] = {"status": "NO_FINANCE_ROW_BEFORE_CUTOFF", "max_allowed_fiscal_year": max_year, "source_file": source_file}
        payload["summary"] = f"{target.company_name} finance snapshot: {window.as_of_date} 기준 사용 가능한 과거 재무연도 행이 없습니다."
        return payload

    row = work.sort_values("__year").iloc[-1].to_dict()
    prev = work.sort_values("__year").iloc[-2].to_dict() if len(work) >= 2 else {}

    def val(*names: str) -> float | None:
        for n in names:
            if n in row:
                v = _to_float(row.get(n))
                if v is not None:
                    return v
        return None

    def prev_val(*names: str) -> float | None:
        for n in names:
            if n in prev:
                v = _to_float(prev.get(n))
                if v is not None:
                    return v
        return None

    revenue = val("revenue", "매출액", "sales")
    op = val("operating_profit", "영업이익", "영업이익(손실)")
    net = val("net_income", "당기순이익", "순이익", "net_profit")
    assets = val("assets", "자산", "자산총계")
    liabilities = val("liabilities", "부채", "부채총계")
    equity = val("equity", "자본", "자본총계")
    cfo = val("cfo", "영업활동현금흐름", "operating_cash_flow")
    capex = val("capex", "CAPEX", "유형자산의 취득", "무형자산의 취득")
    fcf = val("fcf", "free_cash_flow", "자유현금흐름")
    if fcf is None and cfo is not None and capex is not None:
        fcf = cfo - abs(capex)

    prev_revenue = prev_val("revenue", "매출액", "sales")
    metrics = {
        "fiscal_year_used": int(row.get("__year")),
        "max_allowed_fiscal_year": max_year,
        "revenue": revenue,
        "operating_profit": op,
        "net_income": net,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "cfo": cfo,
        "capex": capex,
        "fcf": fcf,
        "revenue_growth_yoy_pct": _round((_safe_div(revenue - prev_revenue, prev_revenue) * 100) if revenue is not None and prev_revenue else None, 4),
        "operating_margin_pct": _round((_safe_div(op, revenue) * 100) if op is not None and revenue else None, 4),
        "net_margin_pct": _round((_safe_div(net, revenue) * 100) if net is not None and revenue else None, 4),
        "debt_ratio_pct": _round((_safe_div(liabilities, equity) * 100) if liabilities is not None and equity else None, 4),
        "equity_ratio_pct": _round((_safe_div(equity, assets) * 100) if equity is not None and assets else None, 4),
        "fcf_margin_pct": _round((_safe_div(fcf, revenue) * 100) if fcf is not None and revenue else None, 4),
    }
    payload["metrics"] = metrics
    payload["data_quality"] = {"status": "OK", "source_file": source_file, "source_rows": int(len(df)), "rows_before_cutoff": int(len(work))}
    payload["summary"] = f"{target.company_name} finance snapshot은 {window.as_of_date} 기준 미래 재무제표를 제외하고 FY{metrics['fiscal_year_used']} 로컬 재무행을 사용했습니다."
    _add_evidence(payload, evidence_id="FIN_LOCAL_FISCAL_ROW", source_type="finance_local_csv", source_name="valuation/finance normalized financials", period=str(metrics["fiscal_year_used"]), source_file=source_file, value=metrics, snippet=f"FY{metrics['fiscal_year_used']} revenue={revenue}, operating_profit={op}, fcf={fcf}, debt_ratio_pct={metrics['debt_ratio_pct']}.")
    _add_claim(payload, claim_id="FIN_FACT_001", text=f"{target.company_name}의 {window.month} finance replay는 FY{metrics['fiscal_year_used']}까지의 로컬 재무 데이터만 사용했습니다.", evidence_ids=["FIN_LOCAL_FISCAL_ROW"])
    return payload


# ------------------------- Valuation / Market price -------------------------


def _read_price_history(target: CompanyTarget) -> tuple[Any, str]:
    root = company_root(target)
    paths = [
        root / "valuation" / "intake" / "valuation_price_history.csv",
        root / "finance" / f"{target.company_name}_stock.csv",
        root / "finance" / f"{target.company_name}_주식.csv",
    ]
    for p in paths:
        df = _try_read_csv(p)
        if df is not None and len(df) > 0:
            return df, _source_rel(p)
    return None, ""


def _price_metrics(target: CompanyTarget, window: MonthWindow) -> tuple[dict[str, Any], dict[str, Any]]:
    df, source_file = _read_price_history(target)
    if df is None or len(df) == 0:
        return {}, {"status": "NO_LOCAL_PRICE_HISTORY", "source_file": source_file}
    col = _find_date_column(df)
    if not col:
        return {}, {"status": "NO_DATE_COLUMN", "source_file": source_file, "source_rows": int(len(df))}
    work = df.copy()
    work["__parsed_date"] = _parse_dates(work[col])
    work = work.dropna(subset=["__parsed_date"]).sort_values("__parsed_date")
    start = pd.Timestamp(window.start_date)
    end = pd.Timestamp(window.end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    before = work[work["__parsed_date"] <= end]
    month_df = work[(work["__parsed_date"] >= start) & (work["__parsed_date"] <= end)]
    if len(before) == 0 or len(month_df) == 0:
        return {}, {"status": "NO_PRICE_ROW_IN_MONTH", "source_file": source_file, "source_rows": int(len(df)), "monthly_rows": int(len(month_df))}

    first = month_df.iloc[0]
    last = month_df.iloc[-1]
    close_col = next((c for c in ["close", "Close", "종가", "adj_close", "latest_close"] if c in month_df.columns), None)
    volume_col = next((c for c in ["volume", "Volume", "거래량"] if c in month_df.columns), None)
    trading_col = next((c for c in ["trading_value", "거래대금", "amount"] if c in month_df.columns), None)
    shares_col = next((c for c in ["shares_outstanding", "상장주식수", "발행주식수"] if c in month_df.columns), None)
    market_cap_col = next((c for c in ["market_cap", "시가총액"] if c in month_df.columns), None)
    if close_col is None:
        return {}, {"status": "NO_CLOSE_COLUMN", "source_file": source_file, "source_rows": int(len(df))}

    start_close = _to_float(first.get(close_col))
    end_close = _to_float(last.get(close_col))
    returns = pd.to_numeric(month_df[close_col], errors="coerce").pct_change().dropna() if pd is not None else []
    close_series = pd.to_numeric(month_df[close_col], errors="coerce").dropna() if pd is not None else []
    monthly_return = ((end_close / start_close) - 1.0) if start_close not in (None, 0) and end_close is not None else None
    high = float(close_series.max()) if len(close_series) else None
    low = float(close_series.min()) if len(close_series) else None
    mdd = None
    if len(close_series) >= 2:
        cummax = close_series.cummax()
        dd = close_series / cummax - 1.0
        mdd = float(dd.min())
    vol = float(returns.std() * math.sqrt(252)) if len(returns) >= 2 else None
    trading_value_avg = None
    if trading_col:
        trading_value_avg = _to_float(pd.to_numeric(month_df[trading_col], errors="coerce").mean())
    elif volume_col and close_col:
        trading_value_avg = _to_float((pd.to_numeric(month_df[volume_col], errors="coerce") * pd.to_numeric(month_df[close_col], errors="coerce")).mean())
    shares = _to_float(last.get(shares_col)) if shares_col else None
    market_cap = _to_float(last.get(market_cap_col)) if market_cap_col else (end_close * shares if end_close is not None and shares is not None else None)

    metrics = {
        "price_source_file": source_file,
        "price_monthly_rows": int(len(month_df)),
        "price_asof_date_used": str(last.get(col))[:10],
        "start_close": start_close,
        "end_close": end_close,
        "monthly_return_pct": _round(monthly_return * 100 if monthly_return is not None else None, 4),
        "monthly_high_close": high,
        "monthly_low_close": low,
        "monthly_mdd_pct": _round(mdd * 100 if mdd is not None else None, 4),
        "annualized_volatility_from_month_pct": _round(vol * 100 if vol is not None else None, 4),
        "avg_trading_value_month": trading_value_avg,
        "shares_outstanding_asof": shares,
        "market_cap_asof": market_cap,
    }
    quality = {"status": "OK", "source_file": source_file, "source_rows": int(len(df)), "monthly_rows": int(len(month_df)), "asof_date_used": metrics["price_asof_date_used"]}
    return metrics, quality


def _market_excel_dir() -> Path:
    candidates = [
        data_root() / "market_excel",
        data_root() / "market-excel",
        data_root() / "market excel",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return candidates[0]


def _decode_hash_u_filename(text: str) -> str:
    # zip/Windows 환경에서 한글 파일명이 market_final_#Ud55c... 형태로 보이는 경우 복원용.
    def repl(m: Any) -> str:
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)

    return re.sub(r"#U([0-9A-Fa-f]{4})", repl, text)


def _market_excel_candidate_files(target: CompanyTarget) -> list[Path]:
    base = _market_excel_dir()
    if not base.exists():
        return []

    all_files = sorted(list(base.glob("market_final*.xlsx")) + list(base.glob("*.xlsx")))
    candidates: list[Path] = []
    company_norm = re.sub(r"\s+", "", target.company_name).lower()
    slug_norm = re.sub(r"\s+", "", target.company_dir).lower()

    for p in all_files:
        stem_norm = re.sub(r"\s+", "", _decode_hash_u_filename(p.stem)).lower()
        if company_norm and company_norm in stem_norm:
            candidates.append(p)
        elif slug_norm and slug_norm in stem_norm:
            candidates.append(p)

    # 파일명 매칭이 안 되는 경우도 있으므로 전체 xlsx를 훑으며 내부 기업명으로 최종 판별한다.
    for p in all_files:
        if p not in candidates:
            candidates.append(p)

    return candidates


def _row_matches_company(row: dict[str, Any], target: CompanyTarget) -> bool:
    company_keys = ["기업명", "company", "company_name", "회사명", "name", "종목명"]
    candidates = []
    for k in company_keys:
        if k in row:
            candidates.append(_clean_text(row.get(k)))
    text = " ".join(candidates)
    if not text:
        return False
    return target.company_name in text or target.company_dir.lower() in text.lower()


def _clean_excel_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        key = _clean_text(k)
        if not key or key.startswith("__"):
            continue
        if pd is not None:
            try:
                if pd.isna(v):
                    continue
            except Exception:
                pass
        out[key] = v
    return out


def _read_market_excel(target: CompanyTarget, window: MonthWindow) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read Market Agent Excel DB output without inventing market scores.

    Market Agent 결과는 data/market_excel 또는 data/market-excel 아래의
    market_final_*.xlsx에 저장되는 DB형 산출물이다. 이 파일은 일별 주가가 아니라
    Market Agent가 만든 구조/산업/정책/경쟁 위치 결과이므로, 월별 가격행은
    valuation_price_history.csv에서 따로 가져오고 여기서는 엑셀 원본값을 그대로 담는다.
    """
    if pd is None:
        return {}, {"status": "PANDAS_NOT_AVAILABLE", "source_file": ""}

    checked: list[str] = []
    for p in _market_excel_candidate_files(target):
        checked.append(_source_rel(p))
        try:
            xl = pd.ExcelFile(p)
        except Exception:
            continue

        extracted: dict[str, Any] = {
            "market_excel_source_file": _source_rel(p),
            "market_excel_sheets": list(xl.sheet_names),
        }
        quality: dict[str, Any] = {
            "status": "OK",
            "source_file": _source_rel(p),
            "sheets": list(xl.sheet_names),
            "source_type": "market_agent_excel_db",
        }

        matched_any = False

        for sheet in ["종합현황", "마켓점수", "밸류체인", "경쟁구조"]:
            if sheet not in xl.sheet_names:
                continue
            try:
                df = pd.read_excel(p, sheet_name=sheet)
            except Exception:
                continue
            if df is None or len(df) == 0:
                continue
            rows = [_clean_excel_row(r) for r in df.to_dict(orient="records")]
            matched_rows = [r for r in rows if _row_matches_company(r, target)]
            if not matched_rows and len(rows) == 1:
                # 기업별 workbook은 한 행만 있는 경우가 많다.
                matched_rows = rows
            if not matched_rows:
                continue

            matched_any = True
            row = matched_rows[0]
            key = {"종합현황": "overview", "마켓점수": "score", "밸류체인": "value_chain", "경쟁구조": "competition"}.get(sheet, sheet)
            extracted[f"market_excel_{key}_row"] = row
            quality[f"{key}_rows"] = len(matched_rows)

        # 정부R&D정책은 기업행이 아니라 세그먼트/키워드별 연도 DB라서 2025년 또는 window.year 컬럼만 객관값으로 첨부한다.
        if "정부R&D정책" in xl.sheet_names:
            try:
                df_policy = pd.read_excel(p, sheet_name="정부R&D정책")
                policy_year_col = str(window.year) if str(window.year) in [str(c) for c in df_policy.columns] else None
                # 컬럼명이 int 2025인 경우도 처리
                if policy_year_col is None:
                    for c in df_policy.columns:
                        if str(c) == str(window.year):
                            policy_year_col = c
                            break
                policy_cols = [c for c in ["segment", "keyword", policy_year_col] if c is not None and c in df_policy.columns]
                if policy_cols:
                    extracted["market_excel_policy_year_used"] = window.year
                    extracted["market_excel_policy_rows_sample"] = _df_records(df_policy[policy_cols], limit=20)
                    quality["policy_rows"] = int(len(df_policy))
            except Exception:
                pass

        if matched_any:
            # 주요 숫자/의견은 원본 엑셀 컬럼을 그대로 복사한다. 산식 재계산 없음.
            score_row = extracted.get("market_excel_score_row") or extracted.get("market_excel_overview_row") or {}
            overview_row = extracted.get("market_excel_overview_row") or {}
            vc_row = extracted.get("market_excel_value_chain_row") or {}
            extracted.update({
                "market_excel_company_name": score_row.get("기업명") or overview_row.get("기업명") or target.company_name,
                "market_excel_recommendation_raw": score_row.get("투자의견") or overview_row.get("투자의견"),
                "market_excel_total_score_raw": score_row.get("총점") or overview_row.get("총점"),
                "market_excel_macro_environment_raw": score_row.get("거시환경") or overview_row.get("거시환경"),
                "market_excel_industry_attractiveness_raw": score_row.get("산업매력도") or overview_row.get("산업매력도"),
                "market_excel_competitive_position_raw": score_row.get("경쟁위치") or overview_row.get("경쟁위치"),
                "market_excel_policy_benefit_raw": score_row.get("정책수혜") or overview_row.get("정책수혜"),
                "market_excel_market_momentum_raw": score_row.get("시장모멘텀") or overview_row.get("시장모멘텀"),
                "market_excel_summary_raw": score_row.get("요약") or overview_row.get("요약"),
                "market_excel_vc_role_raw": vc_row.get("vc_role") or overview_row.get("밸류체인 위치"),
                "market_excel_competition_intensity_raw": vc_row.get("competition_intensity"),
                "market_excel_differentiation_raw": vc_row.get("differentiation"),
                "market_excel_updated_at_raw": vc_row.get("updated_at"),
            })
            return extracted, quality

    return {}, {
        "status": "NO_MARKET_EXCEL_FOR_COMPANY",
        "source_file": "",
        "checked_files_sample": checked[:10],
        "source_type": "market_agent_excel_db",
    }


def build_market_snapshot(target: CompanyTarget, window: MonthWindow) -> dict[str, Any]:
    payload = _base_snapshot(target, window, "market")

    price_metrics, price_quality = _price_metrics(target, window)
    excel_metrics, excel_quality = _read_market_excel(target, window)

    metrics = {
        **{f"price_{k}": v for k, v in price_metrics.items()},
        **excel_metrics,
    }
    # 자주 쓰는 가격 컬럼은 prefix 없이도 유지해 기존 Chair/Auditor가 읽을 수 있게 한다.
    for key in [
        "price_source_file",
        "price_monthly_rows",
        "price_asof_date_used",
        "start_close",
        "end_close",
        "monthly_return_pct",
        "monthly_high_close",
        "monthly_low_close",
        "monthly_mdd_pct",
        "annualized_volatility_from_month_pct",
        "avg_trading_value_month",
        "shares_outstanding_asof",
        "market_cap_asof",
    ]:
        if key in price_metrics:
            metrics[key] = price_metrics[key]

    price_ok = price_quality.get("status") == "OK"
    excel_ok = excel_quality.get("status") == "OK"
    if price_ok and excel_ok:
        status = "OK"
    elif price_ok or excel_ok:
        status = "PARTIAL_OK"
    else:
        status = "MISSING_MARKET_INPUTS"

    payload["metrics"] = metrics
    payload["data_quality"] = {
        "status": status,
        "price_quality": price_quality,
        "market_excel_quality": excel_quality,
        "source_file": excel_quality.get("source_file") or price_quality.get("source_file") or "",
        "source_files": [x for x in [excel_quality.get("source_file"), price_quality.get("source_file")] if x],
        "monthly_rows": price_quality.get("monthly_rows", 0),
        "market_excel_rows": {k: v for k, v in excel_quality.items() if str(k).endswith("_rows")},
        "strict_month_filter": f"{window.start_date}~{window.end_date}",
        "note": "Market snapshot combines objective Market Agent Excel DB output from data/market_excel with valuation_price_history.csv rows strictly filtered to the evaluation month.",
    }

    summary_parts = []
    if excel_ok:
        summary_parts.append(
            f"Market Agent Excel DB({excel_quality.get('source_file')})의 총점/투자의견/밸류체인/경쟁구조 원본값을 사용했습니다"
        )
    else:
        summary_parts.append("Market Agent Excel DB에서 해당 기업 행을 찾지 못했습니다")
    if price_ok:
        summary_parts.append(
            f"valuation_price_history 기준 {window.month} 월내 주가행 {price_quality.get('monthly_rows')}개만 결합했습니다"
        )
    else:
        summary_parts.append(f"{window.month} 월내 valuation_price_history 주가행을 확보하지 못했습니다")
    payload["summary"] = f"{target.company_name} market snapshot은 " + "; ".join(summary_parts) + "."

    evidence_ids: list[str] = []
    if excel_ok:
        _add_evidence(
            payload,
            evidence_id="MKT_EXCEL_DB",
            source_type="market_agent_excel_db",
            source_name="data/market_excel/market_final_*.xlsx",
            period="market_agent_structural_db",
            source_file=excel_quality.get("source_file"),
            value=excel_metrics,
            snippet=(
                f"excel recommendation={excel_metrics.get('market_excel_recommendation_raw')}, "
                f"total_score={excel_metrics.get('market_excel_total_score_raw')}, "
                f"vc_role={excel_metrics.get('market_excel_vc_role_raw')}"
            ),
        )
        evidence_ids.append("MKT_EXCEL_DB")
    if price_ok:
        _add_evidence(
            payload,
            evidence_id="MKT_MONTH_PRICE",
            source_type="valuation_price_history_monthly_rows",
            source_name="valuation_price_history.csv",
            period=window.month,
            source_file=price_quality.get("source_file"),
            value=price_metrics,
            snippet=(
                f"{window.month} start_close={price_metrics.get('start_close')}, "
                f"end_close={price_metrics.get('end_close')}, "
                f"monthly_return_pct={price_metrics.get('monthly_return_pct')}, "
                f"mdd_pct={price_metrics.get('monthly_mdd_pct')}"
            ),
        )
        evidence_ids.append("MKT_MONTH_PRICE")
    if evidence_ids:
        _add_claim(
            payload,
            claim_id="MKT_FACT_001",
            text=(
                f"{target.company_name}의 {window.month} market replay는 "
                "data/market_excel의 Market Agent DB 결과와 valuation_price_history.csv의 해당 월 주가행을 결합합니다. "
                "추천/점수는 새로 임의 계산하지 않고 원본 자료값을 evidence로 전달합니다."
            ),
            evidence_ids=evidence_ids,
        )
    return payload


def build_valuation_snapshot(target: CompanyTarget, window: MonthWindow) -> dict[str, Any]:
    payload = _base_snapshot(target, window, "valuation")
    price_metrics, price_quality = _price_metrics(target, window)
    fin_df, fin_source = _read_financials(target)
    max_year = _available_fiscal_year_for_asof(window)
    fin_metrics: dict[str, Any] = {}
    fin_quality: dict[str, Any] = {"status": "NO_LOCAL_FINANCIALS", "source_file": fin_source}
    if fin_df is not None and len(fin_df) > 0 and pd is not None:
        ycol = next((c for c in fin_df.columns if str(c).lower() in {"year", "fiscal_year", "연도", "사업연도"}), None)
        if ycol:
            f = fin_df.copy()
            f["__year"] = pd.to_numeric(f[ycol], errors="coerce")
            f = f[f["__year"] <= max_year].dropna(subset=["__year"]).sort_values("__year")
            if len(f) > 0:
                row = f.iloc[-1].to_dict()
                revenue = _to_float(row.get("revenue") or row.get("매출액"))
                op = _to_float(row.get("operating_profit") or row.get("영업이익"))
                net = _to_float(row.get("net_income") or row.get("당기순이익"))
                equity = _to_float(row.get("equity") or row.get("자본총계"))
                fcf = _to_float(row.get("fcf"))
                if fcf is None:
                    cfo = _to_float(row.get("cfo") or row.get("영업활동현금흐름"))
                    capex = _to_float(row.get("capex"))
                    if cfo is not None and capex is not None:
                        fcf = cfo - abs(capex)
                fin_metrics = {"fiscal_year_used": int(row["__year"]), "revenue": revenue, "operating_profit": op, "net_income": net, "equity": equity, "fcf": fcf}
                fin_quality = {"status": "OK", "source_file": fin_source, "rows_before_cutoff": int(len(f)), "fiscal_year_used": int(row["__year"])}

    market_cap = _to_float(price_metrics.get("market_cap_asof"))
    close = _to_float(price_metrics.get("end_close"))
    shares = _to_float(price_metrics.get("shares_outstanding_asof"))
    revenue = _to_float(fin_metrics.get("revenue"))
    net = _to_float(fin_metrics.get("net_income"))
    equity = _to_float(fin_metrics.get("equity"))
    fcf = _to_float(fin_metrics.get("fcf"))
    valuation_metrics = {
        **price_metrics,
        **{f"financial_{k}": v for k, v in fin_metrics.items()},
        "psr_asof": _round(_safe_div(market_cap, revenue), 4),
        "per_asof": _round(_safe_div(market_cap, net), 4),
        "pbr_asof": _round(_safe_div(market_cap, equity), 4),
        "p_fcf_asof": _round(_safe_div(market_cap, fcf), 4),
        "close_asof": close,
        "market_cap_asof": market_cap,
        "shares_outstanding_asof": shares,
    }
    workbook = company_root(target) / "valuation" / f"{target.company_dir}_valuation_workbook.xlsx"
    if not workbook.exists():
        # company_dir 파일명이 다를 수 있어 valuation 폴더의 첫 workbook도 탐색
        cands = list((company_root(target) / "valuation").glob("*_valuation_workbook.xlsx"))
        workbook = cands[0] if cands else workbook
    payload["metrics"] = valuation_metrics
    payload["data_quality"] = {"status": "OK" if price_quality.get("status") == "OK" or fin_quality.get("status") == "OK" else "PARTIAL_OR_MISSING", "price_quality": price_quality, "financial_quality": fin_quality, "workbook_source_file": _source_rel(workbook) if workbook.exists() else ""}
    payload["summary"] = f"{target.company_name} valuation snapshot은 {window.month} 월말 주가와 {max_year}년까지의 로컬 재무 데이터를 결합했습니다. live 2026 market_snapshot은 사용하지 않습니다."
    if price_quality.get("status") == "OK":
        _add_evidence(payload, evidence_id="VAL_MONTH_PRICE", source_type="valuation_price_history", source_name="valuation_price_history.csv", period=window.month, source_file=price_quality.get("source_file"), value=price_metrics, snippet=f"{window.month} as-of close={close}, market_cap={market_cap}, shares={shares}.")
    if fin_quality.get("status") == "OK":
        _add_evidence(payload, evidence_id="VAL_FISCAL_INPUT", source_type="valuation_normalized_financials", source_name="valuation_normalized_financials.csv", period=str(fin_quality.get("fiscal_year_used")), source_file=fin_quality.get("source_file"), value=fin_metrics, snippet=f"FY{fin_quality.get('fiscal_year_used')} revenue={revenue}, net_income={net}, equity={equity}, fcf={fcf}.")
    ev_ids = [e["evidence_id"] for e in payload.get("evidences", [])]
    if ev_ids:
        _add_claim(payload, claim_id="VAL_FACT_001", text=f"{target.company_name} valuation replay는 {window.month} 월말 주가와 당시 접근 가능한 과거 재무자료로 산출한 valuation metric만 포함합니다.", evidence_ids=ev_ids)
    return payload


# ------------------------- Tech -------------------------


def _deep_get(obj: Any, keys: list[str]) -> Any:
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, "", [], {}):
                return obj[k]
        for v in obj.values():
            found = _deep_get(v, keys)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(obj, list):
        for item in obj[:50]:
            found = _deep_get(item, keys)
            if found not in (None, "", [], {}):
                return found
    return None


def build_tech_snapshot(target: CompanyTarget, window: MonthWindow) -> dict[str, Any]:
    payload = _base_snapshot(target, window, "tech")
    root = company_root(target) / "tech"
    files_used: list[str] = []
    metrics: dict[str, Any] = {}
    summary_parts: list[str] = []

    for p in [root / "tech_chair_summary.json", root / f"{target.company_dir}_tech_chair_summary.json"]:
        if p.exists():
            try:
                js = _read_json(p)
                files_used.append(_source_rel(p))
                metrics.update({
                    "tech_to_value_bridge_score": _deep_get(js, ["tech_to_value_bridge_score", "bridge_score", "peer_adjusted_bridge_score"]),
                    "bridge_grade": _deep_get(js, ["bridge_grade", "grade", "final_grade"]),
                    "technology_differentiation_score": _deep_get(js, ["technology_differentiation_score", "differentiation_score"]),
                    "patent_momentum_score": _deep_get(js, ["patent_momentum_score", "momentum_score"]),
                    "tech_to_value_evidence_confidence": _deep_get(js, ["tech_to_value_evidence_confidence", "evidence_confidence_score"]),
                    "tech_ip_strength_index": _deep_get(js, ["tech_ip_strength_index", "ip_strength_score", "ip_strength_index"]),
                    "patent_records_count": _deep_get(js, ["patent_records_count", "patents", "total_patents"]),
                    "registered_patents_count": _deep_get(js, ["registered_patents_count", "registered_patents"]),
                })
                summary_parts.append(_clean_text(js.get("summary") or js.get("chair_summary") or js.get("investment_view") or ""))
                payload["raw_tech_summary_compact"] = js
                break
            except Exception:
                pass

    excel_metric_rows: list[dict[str, Any]] = []
    for p in [root / "tech_excel_quantified_metrics.csv", root / "quantified_metrics.csv", root / "tech_excel_frame_metrics.csv", root / "tech_excel_frame_items.csv"]:
        df = _try_read_csv(p)
        if df is not None and len(df) > 0:
            files_used.append(_source_rel(p))
            rows = _df_records(df, limit=30)
            excel_metric_rows.extend(rows)
    metrics["excel_frame_metric_row_count"] = len(excel_metric_rows)
    metrics["excel_frame_metrics_sample"] = excel_metric_rows[:20]

    full_json = root / "tech_excel_frame_full.json"
    if full_json.exists():
        try:
            js = _read_json(full_json)
            files_used.append(_source_rel(full_json))
            metrics["excel_frame_full_available"] = True
            payload["tech_excel_frame_full_compact"] = js if len(json.dumps(js, ensure_ascii=False)) < 30000 else {"available": True, "note": "full json exists but omitted from snapshot due to size", "source_file": _source_rel(full_json)}
        except Exception:
            pass

    payload["metrics"] = {k: v for k, v in metrics.items() if v is not None}
    status = "OK" if files_used else "NO_LOCAL_TECH_FILES"
    payload["data_quality"] = {"status": status, "source_files": files_used, "excel_frame_metric_row_count": len(excel_metric_rows), "note": "Tech is structural/as-of evidence. Patent/API collection may not be monthly; local Excel-frame metrics are still included when present."}
    payload["summary"] = " ".join([s for s in summary_parts if s]) or f"{target.company_name} tech snapshot은 로컬 Tech Agent 결과와 Excel-frame 정량 지표를 사용합니다."
    if files_used:
        _add_evidence(payload, evidence_id="TECH_LOCAL_FILES", source_type="tech_local_outputs", source_name="tech_agent local outputs", period="structural_asof", source_file="; ".join(files_used[:5]), value=payload["metrics"], snippet=f"Tech local files used={len(files_used)}, excel_frame_metric_rows={len(excel_metric_rows)}, bridge_score={metrics.get('tech_to_value_bridge_score')}.")
        _add_claim(payload, claim_id="TECH_FACT_001", text=f"{target.company_name} tech replay는 특허 결과가 없는 기업도 tech_excel_* / quantified_metrics 로컬 지표를 함께 반영합니다.", evidence_ids=["TECH_LOCAL_FILES"])
    return payload


# ------------------------- Issue -------------------------


def _walk_dicts(obj: Any) -> Iterable[dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_dicts(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_dicts(item)


def _extract_news_records_from_json(path: Path, target: CompanyTarget, window: MonthWindow) -> list[dict[str, Any]]:
    try:
        js = _read_json(path)
    except Exception:
        return []
    records: list[dict[str, Any]] = []
    for d in _walk_dicts(js):
        title = _clean_text(d.get("title") or d.get("뉴스제목") or d.get("news_title") or d.get("headline"))
        snippet = _clean_text(d.get("summary") or d.get("뉴스요약") or d.get("snippet") or d.get("기사본문") or d.get("text"))
        dt = _clean_text(d.get("date") or d.get("게시일시") or d.get("published_at") or d.get("period") or d.get("pubDate"))
        link = _clean_text(d.get("link") or d.get("url") or d.get("링크"))
        source = _clean_text(d.get("source") or d.get("출처") or d.get("source_name"))
        if not dt or not (title or snippet):
            continue
        parsed = pd.to_datetime([dt], errors="coerce", utc=True)[0] if pd is not None else None
        if pd is None or pd.isna(parsed):
            continue
        parsed = parsed.tz_convert(None) if getattr(parsed, "tzinfo", None) is not None else parsed
        if pd.Timestamp(window.start_date) <= parsed <= pd.Timestamp(window.end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1):
            text_all = f"{title} {snippet}"
            if target.company_name in text_all or target.company_dir.lower() in text_all.lower() or d.get("company") == target.company_name or d.get("기업명") == target.company_name:
                records.append({"date": str(parsed.date()), "title": title, "summary": snippet[:500], "link": link, "source": source, "source_file": _source_rel(path)})
    return records


def _extract_issue_records_from_excel(path: Path, target: CompanyTarget, window: MonthWindow) -> list[dict[str, Any]]:
    if pd is None or not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        xl = pd.ExcelFile(path)
    except Exception:
        return []
    for sheet in xl.sheet_names:
        if target.company_name not in sheet and "전체" not in sheet and "공통" not in sheet and "요약" not in sheet:
            continue
        try:
            df = pd.read_excel(path, sheet_name=sheet)
        except Exception:
            continue
        if len(df) == 0:
            continue
        company_col = next((c for c in df.columns if str(c) in {"기업명", "company", "company_name"}), None)
        if company_col:
            df = df[df[company_col].astype(str).str.contains(re.escape(target.company_name), na=False)]
        dfw = _filter_df_by_window(df, window, allow_asof=False)
        if dfw is None or len(dfw) == 0:
            continue
        for _, row in dfw.head(50).iterrows():
            records.append({
                "date": str(row.get("__parsed_date"))[:10],
                "title": _clean_text(row.get("뉴스제목") or row.get("title") or row.get("headline")),
                "summary": _clean_text(row.get("뉴스요약") or row.get("summary") or row.get("기사본문"))[:500],
                "link": _clean_text(row.get("링크") or row.get("link") or row.get("url")),
                "source": _clean_text(row.get("출처도메인") or row.get("source")),
                "source_file": _source_rel(path),
                "sheet": sheet,
            })
    return records


def build_issue_snapshot(target: CompanyTarget, window: MonthWindow) -> dict[str, Any]:
    payload = _base_snapshot(target, window, "issue")
    root = company_root(target)
    records: list[dict[str, Any]] = []
    source_files: set[str] = set()

    for p in _find_files(root, "issue", ["*.json"]):
        recs = _extract_news_records_from_json(p, target, window)
        if recs:
            records.extend(recs)
            source_files.add(_source_rel(p))

    issue_excel_candidates = [
        data_root() / "Issue_Integration.xlsx",
        data_root() / target.field / "_sector_common" / "data" / "Issue_Integration.xlsx",
        data_root() / target.field / "_sector_common" / "source_data" / "Issue_Integration.xlsx",
    ]
    for p in issue_excel_candidates:
        recs = _extract_issue_records_from_excel(p, target, window)
        if recs:
            records.extend(recs)
            source_files.add(_source_rel(p))

    # 중복 제거: title+date+link 기준
    unique = []
    seen = set()
    for r in records:
        key = (r.get("date"), r.get("title"), r.get("link"))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda x: (x.get("date") or "", x.get("title") or ""))

    payload["metrics"] = {"monthly_issue_count": len(unique), "monthly_issue_records_sample": unique[:15]}
    payload["data_quality"] = {"status": "OK" if unique else "NO_ISSUE_ROWS_IN_MONTH", "source_files": sorted(source_files), "monthly_rows": len(unique), "strict_month_filter": f"{window.start_date}~{window.end_date}"}
    payload["summary"] = f"{target.company_name} issue snapshot은 {window.month}에 날짜가 확인되는 기업 관련 이슈 {len(unique)}건만 포함합니다. 날짜가 없거나 월 밖인 뉴스는 제외했습니다."
    if unique:
        _add_evidence(payload, evidence_id="ISSUE_MONTH_NEWS", source_type="issue_monthly_news", source_name="local issue json/xlsx", period=window.month, source_file="; ".join(sorted(source_files)), value={"monthly_issue_count": len(unique)}, snippet=" | ".join([f"{r.get('date')} {r.get('title')}" for r in unique[:5]]))
        _add_claim(payload, claim_id="ISSUE_FACT_001", text=f"{target.company_name} issue replay는 {window.month} 월내 날짜가 확인되는 뉴스/이슈만 사용했습니다.", evidence_ids=["ISSUE_MONTH_NEWS"])
    return payload


# ------------------------- Macro -------------------------


def _decode_escaped_unicode(text: str) -> str:
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text))


def _split_name_and_date(stem: str) -> tuple[str, str]:
    decoded = _decode_escaped_unicode(stem)
    m = re.match(r"^(?P<base>.+?)_(?P<date>20\d{6})$", decoded)
    if not m:
        return decoded, "00000000"
    return m.group("base"), m.group("date")


def _select_latest_files_by_key(paths: list[Path]) -> list[Path]:
    latest_by_key: dict[str, tuple[str, Path]] = {}
    for path in sorted(paths, key=lambda p: p.name):
        key, d = _split_name_and_date(path.stem)
        old = latest_by_key.get(key)
        if old is None or d > old[0]:
            latest_by_key[key] = (d, path)
    return [item[1] for item in sorted(latest_by_key.values(), key=lambda x: x[1].name)]


def _macro_source_files() -> list[Path]:
    root = data_root() / "_global_common" / "macro"
    if not root.exists():
        return []
    exclude_keys = ["macro_run_summary", "run_summary", "summary"]
    all_files: list[Path] = []
    for pattern in ("*.csv", "*.xlsx", "*.xls", "*.xlsm"):
        all_files.extend([p for p in root.rglob(pattern) if p.is_file()])
    all_files = [p for p in all_files if not any(ex in p.name.lower() for ex in exclude_keys) and "debug" not in [part.lower() for part in p.parts]]
    if not all_files:
        return []
    latest = _select_latest_files_by_key(all_files)
    return latest if latest else sorted(all_files)


def build_macro_snapshot(target: CompanyTarget, window: MonthWindow) -> dict[str, Any]:
    payload = _base_snapshot(target, window, "macro")
    indicator_values: dict[str, Any] = {}
    source_files: list[str] = []
    source_rows_total = 0
    month_rows_total = 0
    asof_dates: dict[str, str] = {}

    for p in _macro_source_files():
        df = _try_read_csv(p)
        if df is None and p.suffix.lower() in {".xlsx", ".xls", ".xlsm"}:
            df = _try_read_excel(p)
        if df is None or len(df) == 0:
            continue
        dcol = _find_date_column(df)
        if not dcol:
            continue
        source_files.append(_source_rel(p))
        source_rows_total += int(len(df))
        month_df = _filter_df_by_window(df, window, allow_asof=False)
        asof_df = month_df if month_df is not None and len(month_df) > 0 else _latest_rows_by_date(df, window)
        if asof_df is None or len(asof_df) == 0:
            continue
        month_rows_total += int(len(month_df)) if month_df is not None else 0
        # 같은 날짜 중복행이 있으면 숫자 컬럼별 마지막 유효값/평균에 가까운 대표값을 만든다.
        for col in asof_df.columns:
            if col == dcol or str(col).startswith("__"):
                continue
            vals = pd.to_numeric(asof_df[col], errors="coerce").dropna() if pd is not None else []
            if len(vals) == 0:
                continue
            indicator_values[str(col)] = _round(vals.iloc[-1], 6)
            try:
                asof_dates[str(col)] = str(asof_df.dropna(subset=[col]).iloc[-1][dcol])[:10]
            except Exception:
                asof_dates[str(col)] = str(asof_df.iloc[-1][dcol])[:10]

    payload["metrics"] = {"macro_indicators": indicator_values, "indicator_asof_dates": asof_dates}
    payload["data_quality"] = {"status": "OK" if indicator_values else "NO_MACRO_ROWS_BEFORE_CUTOFF", "source_files": source_files, "source_rows_total": source_rows_total, "monthly_rows_total": month_rows_total, "note": "Macro indicators are common by sector/month; values differ by month, not necessarily by company."}
    payload["summary"] = f"{target.company_name} macro snapshot은 {window.month} 월내 또는 {window.as_of_date} 이전 최신 거시지표만 사용했습니다. 거시지표는 기업별 값이 아니라 섹터 공통 월별 환경값입니다."
    if indicator_values:
        priority_keys = [
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
        preview_items = [(k, indicator_values[k]) for k in priority_keys if k in indicator_values]
        preview_items.extend((k, v) for k, v in indicator_values.items() if k not in priority_keys)
        _add_evidence(payload, evidence_id="MACRO_MONTH_INDICATORS", source_type="macro_local_csv", source_name="data/_global_common/macro", period=window.month, source_file="; ".join(source_files[:5]), value=payload["metrics"], snippet=f"{window.month} macro indicators: " + ", ".join([f"{k}={v}" for k, v in preview_items[:10]]))
        _add_claim(payload, claim_id="MACRO_FACT_001", text=f"{target.company_name} macro replay는 {window.month} 월내 또는 월말 이전 최신 macro CSV 지표만 사용했습니다.", evidence_ids=["MACRO_MONTH_INDICATORS"])
    return payload


# ------------------------- Snapshot orchestration -------------------------


def build_all_snapshots(target: CompanyTarget, window: MonthWindow) -> dict[str, dict[str, Any]]:
    return {
        "finance": build_finance_snapshot(target, window),
        "market": build_market_snapshot(target, window),
        "tech": build_tech_snapshot(target, window),
        "valuation": build_valuation_snapshot(target, window),
        "issue": build_issue_snapshot(target, window),
        "macro": build_macro_snapshot(target, window),
    }


def save_snapshots_to_history(target: CompanyTarget, window: MonthWindow, snapshots: dict[str, dict[str, Any]]) -> None:
    from common.agent_history import save_agent_snapshot

    for agent, payload in snapshots.items():
        save_agent_snapshot(
            as_of_date=window.as_of_date,
            field=target.field,
            company_dir=target.company_dir,
            company_name=target.company_name,
            agent=agent,
            payload=payload,
            source_file="evaluation.monthly_eval.objective_snapshot",
            source_mode="monthly_objective_local_files_only",
            overwrite=True,
        )


def _extract_json_after_marker(stdout: str, marker: str) -> dict[str, Any] | None:
    idx = stdout.rfind(marker)
    if idx < 0:
        return None
    text = stdout[idx + len(marker):].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def run_chair_from_history(target: CompanyTarget, window: MonthWindow, *, run_id: str, fail_open: bool = True) -> dict[str, Any]:
    """Run the existing Chair/Auditor graph in official history-replay mode.

    chair_agent.graph.py expects these exact environment variable names:
      - ALPHAPROVE_USE_AGENT_HISTORY=1
      - ALPHAPROVE_AS_OF_DATE=<YYYY-MM-DD>
      - ALPHAPROVE_FIELD=<field>
      - ALPHAPROVE_HISTORY_RUN_ID=<run_id>
      - ALPHAPROVE_SHEETS_DB_ONLY=1

    If the old names ALPHAPROVE_HISTORY_AS_OF_DATE or
    ALPHAPROVE_EVALUATION_RUN_ID are used, Chair can still run, but the
    auditor/chair run_results are not saved to Google Sheets. Then exporter sees
    run_results rows=0 and agent signal columns stay blank.
    """
    env = os.environ.copy()
    env.update({
        "ALPHAPROVE_HISTORY_BACKEND": env.get("ALPHAPROVE_HISTORY_BACKEND", "sheets"),
        "ALPHAPROVE_USE_AGENT_HISTORY": "1",
        "ALPHAPROVE_AS_OF_DATE": window.as_of_date,
        "ALPHAPROVE_FIELD": target.field,
        "ALPHAPROVE_HISTORY_RUN_ID": run_id,
        "ALPHAPROVE_SHEETS_DB_ONLY": "1",
        "CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS": "1",
        "CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS": "0",
        "AUDITOR_FIRST_FAIL_OPEN": "1" if fail_open else env.get("AUDITOR_FIRST_FAIL_OPEN", "0"),
        "FINANCE_AS_OF_DATE": window.as_of_date,
        "MARKET_AS_OF_DATE": window.as_of_date,
        "MARKET_END_DATE": window.as_of_date,
        "ISSUE_AS_OF_DATE": window.as_of_date,
        "ISSUE_START_DATE": window.start_s,
        "ISSUE_END_DATE": window.end_s,
        "MACRO_AS_OF_DATE": window.as_of_date,
        "MACRO_END_DATE": window.as_of_date,
        "VALUATION_AS_OF_DATE": window.as_of_date,
        "VALUATION_END_DATE": window.as_of_date,
        "ALPHAPROVE_DATA_CUTOFF_DATE": window.as_of_date,
        "PYTHONUTF8": env.get("PYTHONUTF8", "1"),
        "PYTHONIOENCODING": env.get("PYTHONIOENCODING", "utf-8"),
    })
    src = str(project_root() / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable,
        str(project_root() / "main.py"),
        "chair",
        "--company-dir",
        target.company_dir,
        "--company",
        target.company_name,
        "--no-intake",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(project_root()),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = {
        "company": target.company_name,
        "company_dir": target.company_dir,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }
    if proc.returncode != 0 and not fail_open:
        nl = chr(10)
        message = (
            f"Chair replay failed for {target.company_name}/{target.company_dir}"
            + nl + "STDERR:" + nl + proc.stderr[-4000:]
            + nl + "STDOUT:" + nl + proc.stdout[-4000:]
        )
        raise RuntimeError(message)
    return result


def _load_chair_json(target: CompanyTarget) -> dict[str, Any]:
    """Fallback only.

    The official monthly evaluation result must come from Google Sheets
    run_results for the exact run_id/as_of_date. This local reader is kept only
    as a last-resort diagnostic fallback when old local Chair JSON exists.
    """
    chair_dir = company_root(target) / "chair"
    candidates = [chair_dir / f"{target.company_dir}_chair.json", chair_dir / f"{target.company_dir}_chair_agent_packet.json"]
    candidates += sorted(chair_dir.glob("*chair*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for p in candidates:
        if p.exists():
            try:
                return _read_json(p)
            except Exception:
                continue
    return {}


def _find_first(obj: Any, keys: list[str]) -> Any:
    return _deep_get(obj, keys)


def _payload_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
    return {}


def _load_run_payloads_for_company(
    *,
    run_id: str,
    window: MonthWindow,
    field: str,
    company_dir: str,
) -> dict[str, dict[str, Any]]:
    """Load exact Google Sheets run-result payloads for one company.

    Returned keys are "<agent>:<output_kind>", e.g.
    "auditor:auditor_chair_packet_json" and "chair:chair_agent_packet_json".
    """
    try:
        from common.agent_history import list_run_results
    except Exception:
        return {}

    try:
        rows = list_run_results(
            run_id=run_id,
            as_of_date=window.as_of_date,
            field=field,
            company_dir=company_dir,
            include_payload=True,
        )
    except Exception as exc:
        print(f"[export][warn] Google Sheets run_results 로드 실패: {company_dir}, {exc}")
        return {}

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        agent = str(row.get("agent") or "").strip()
        output_kind = str(row.get("output_kind") or "").strip()
        payload = _payload_dict(row.get("payload"))
        if agent and output_kind:
            out[f"{agent}:{output_kind}"] = payload
    return out


def _extract_quantitative_decision(auditor_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract Auditor stage-3 quantitative decision from all known shapes."""
    candidates: list[Any] = []

    if isinstance(auditor_payload, dict):
        candidates.append(auditor_payload)
        ar = auditor_payload.get("auditor_result")
        if isinstance(ar, dict):
            candidates.append(ar)
            fv = ar.get("final_validation")
            fr = ar.get("final_round")
            if isinstance(fv, dict):
                candidates.append(fv)
            if isinstance(fr, dict):
                candidates.append(fr)

        result = auditor_payload.get("result")
        if isinstance(result, dict):
            candidates.append(result)

    for item in candidates:
        qd = item.get("quantitative_decision") if isinstance(item, dict) else None
        if isinstance(qd, dict) and qd:
            return qd

    return {}


def _compact_packet_by_agent(auditor_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packets = []
    if isinstance(auditor_payload.get("compact_agent_packets"), list):
        packets = auditor_payload.get("compact_agent_packets") or []
    else:
        ar = auditor_payload.get("auditor_result") if isinstance(auditor_payload.get("auditor_result"), dict) else {}
        if isinstance(ar.get("opinions"), list):
            packets = ar.get("opinions") or []
        elif isinstance(ar.get("compact_packets"), list):
            packets = ar.get("compact_packets") or []

    out: dict[str, dict[str, Any]] = {}
    for item in packets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("agent") or item.get("agent_name") or item.get("name") or "").lower().replace("_agent", "")
        if name:
            out[name] = item
    return out


def _round_or_blank(value: Any, digits: int = 4) -> Any:
    rounded = _round(value, digits)
    return "" if rounded is None else rounded


def _agent_signal_exact(
    *,
    agent: str,
    qd: dict[str, Any],
    compact_by_agent: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return agent signal from Auditor output only, without new calculation.

    Priority:
    1) auditor_result.quantitative_decision.agent_decisions[agent]
    2) Auditor compact packet fields created from the same stage decision
    3) blank with source=AUDITOR_SIGNAL_NOT_FOUND
    """
    agent_decisions = qd.get("agent_decisions") if isinstance(qd.get("agent_decisions"), dict) else {}
    dec = agent_decisions.get(agent) if isinstance(agent_decisions.get(agent), dict) else {}

    if dec:
        basis = dec.get("basis")
        if isinstance(basis, list):
            basis_text = " | ".join(str(x) for x in basis[:5])
        else:
            basis_text = str(basis or "")
        return {
            "signal": _round_or_blank(dec.get("signal"), 4),
            "weighted_signal": _round_or_blank(dec.get("weighted_contribution"), 4),
            "recommendation": _clean_text(dec.get("recommendation") or dec.get("label") or ""),
            "weight": _round_or_blank(dec.get("weight"), 4),
            "source": "auditor_quantitative_decision",
            "basis": basis_text,
        }

    cp = compact_by_agent.get(agent) or {}
    if cp:
        basis = cp.get("decision_basis") or cp.get("basis") or []
        if isinstance(basis, list):
            basis_text = " | ".join(str(x) for x in basis[:5])
        else:
            basis_text = str(basis or "")
        return {
            "signal": _round_or_blank(cp.get("auditor_signal") or cp.get("signal"), 4),
            "weighted_signal": _round_or_blank(cp.get("weighted_contribution") or cp.get("weighted_signal"), 4),
            "recommendation": _clean_text(cp.get("auditor_recommendation") or cp.get("recommendation") or ""),
            "weight": _round_or_blank(cp.get("weight"), 4),
            "source": "auditor_compact_packet",
            "basis": basis_text,
        }

    return {
        "signal": "",
        "weighted_signal": "",
        "recommendation": "",
        "weight": "",
        "source": "AUDITOR_SIGNAL_NOT_FOUND",
        "basis": "",
    }


def _agent_signal_from_chair(chair_json: dict[str, Any], agent: str) -> dict[str, Any]:
    """Legacy local-Chair fallback.

    This is no longer used as the primary source because monthly evaluation
    must be tied to the exact Google Sheets run_id.
    """
    agent_block = None
    for key in ["agent_results", "agents", "agent_signals", "weighted_agent_signals", "agent_outputs"]:
        v = chair_json.get(key)
        if isinstance(v, dict):
            agent_block = v.get(agent) or v.get(f"{agent}_agent")
            if agent_block is not None:
                break
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and str(item.get("agent") or item.get("name") or "").lower().replace("_agent", "") == agent:
                    agent_block = item
                    break
    if agent_block is None:
        agent_block = chair_json.get(agent) if isinstance(chair_json.get(agent), dict) else {}
    return {
        "signal": _round(_find_first(agent_block, ["signal", "weighted_signal", "score_signal", "auditor_signal"]), 4),
        "weighted_signal": _round(_find_first(agent_block, ["weighted_signal", "contribution", "weighted_score", "signal_contribution"]), 4),
        "recommendation": _clean_text(_find_first(agent_block, ["recommendation", "opinion", "decision", "label"])) or "",
        "weight": _round(_find_first(agent_block, ["weight", "agent_weight"]), 4),
        "source": "legacy_local_chair_json",
        "basis": "",
    }


def _metric_preview(snapshot: dict[str, Any]) -> str:
    metrics = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}
    if not metrics:
        return ""

    # agent별 핵심 객관값만 CSV 한 칸에 짧게 붙인다. 신호/판단이 아니라 원천 지표 확인용이다.
    if isinstance(metrics.get("macro_indicators"), dict):
        indicators = metrics.get("macro_indicators", {})
        priority_keys = [
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
        items = [(k, indicators[k]) for k in priority_keys if k in indicators]
        items.extend((k, v) for k, v in indicators.items() if k not in priority_keys)
        items = items[:8]
        return "; ".join(f"{k}={v}" for k, v in items)

    if "monthly_issue_count" in metrics:
        recs = metrics.get("monthly_issue_records_sample") or []
        titles = []
        if isinstance(recs, list):
            for r in recs[:3]:
                if isinstance(r, dict):
                    titles.append(f"{r.get('date','')} {str(r.get('title',''))[:40]}")
        return f"monthly_issue_count={metrics.get('monthly_issue_count')}; " + " | ".join(titles)

    preferred = [
        "price_monthly_rows", "price_asof_date_used", "start_close", "end_close",
        "monthly_return_pct", "monthly_mdd_pct", "market_cap_asof",
        "fiscal_year_used", "revenue", "operating_profit", "net_income", "fcf",
        "psr_asof", "per_asof", "pbr_asof", "p_fcf_asof",
        "tech_to_value_bridge_score", "bridge_grade", "technology_differentiation_score",
        "patent_momentum_score", "tech_ip_strength_index", "excel_frame_metric_row_count",
    ]
    parts = []
    for k in preferred:
        if k in metrics and metrics.get(k) not in (None, "", [], {}):
            parts.append(f"{k}={metrics.get(k)}")
        if len(parts) >= 10:
            break
    return "; ".join(parts)


def _snapshot_diag(snapshot: dict[str, Any]) -> dict[str, Any]:
    dq = snapshot.get("data_quality") if isinstance(snapshot.get("data_quality"), dict) else {}
    metrics = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}
    source_file = dq.get("source_file") or dq.get("workbook_source_file") or ""
    if not source_file and isinstance(dq.get("source_files"), list):
        source_file = "; ".join(dq.get("source_files")[:3])
    return {
        "data_status": dq.get("status", ""),
        "source_file": source_file,
        "monthly_rows": dq.get("monthly_rows") or dq.get("monthly_rows_total") or metrics.get("price_monthly_rows") or metrics.get("monthly_issue_count") or "",
        "asof_date_used": dq.get("asof_date_used") or metrics.get("price_asof_date_used") or "",
        "metric_preview": _metric_preview(snapshot),
    }


def export_monthly_signal_csv(
    *,
    targets: list[CompanyTarget],
    window: MonthWindow,
    run_id: str,
    output_dir: str | Path | None = None,
) -> Path:
    if output_dir is None:
        output_dir = data_root() / targets[0].field / "_sector_common" / "history_sheets_exports" / f"monthly_{window.month}_{run_id}"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = out_dir / f"signal_df_{window.month}.csv"

    try:
        from common.agent_history import load_agent_snapshot
    except Exception:
        load_agent_snapshot = None  # type: ignore

    rows = []
    for target in targets:
        run_payloads = _load_run_payloads_for_company(
            run_id=run_id,
            window=window,
            field=target.field,
            company_dir=target.company_dir,
        )
        auditor_payload = run_payloads.get("auditor:auditor_chair_packet_json") or {}
        chair_payload = run_payloads.get("chair:chair_agent_packet_json") or {}
        qd = _extract_quantitative_decision(auditor_payload)
        compact_by_agent = _compact_packet_by_agent(auditor_payload)

        legacy_chair_json: dict[str, Any] = {}
        if not qd and not chair_payload:
            legacy_chair_json = _load_chair_json(target)

        rec = (
            _clean_text(chair_payload.get("opinion"))
            or _clean_text(qd.get("final_recommendation"))
            or _clean_text(auditor_payload.get("final_recommendation"))
            or _clean_text(_find_first(legacy_chair_json, ["recommendation", "final_recommendation", "decision", "opinion"]))
        )
        ws = (
            _round(qd.get("weighted_signal"), 4)
            if qd.get("weighted_signal") is not None
            else _round(auditor_payload.get("weighted_signal") or _find_first(legacy_chair_json, ["weighted_signal", "final_weighted_signal"]), 4)
        )

        row: dict[str, Any] = {
            "date": window.month,
            "ticker": target.company_name,
            "recommendation": rec,
            "weighted_signal": "" if ws is None else ws,
            "stock_code": target.stock_code,
            "company_dir": target.company_dir,
            "field": target.field,
            "as_of_date": window.as_of_date,
            "run_id": run_id,
            "signal_source": "auditor_quantitative_decision" if qd else ("chair_run_result_only" if chair_payload else "legacy_local_chair_json"),
        }

        for agent in AGENTS:
            if qd or compact_by_agent:
                sig = _agent_signal_exact(agent=agent, qd=qd, compact_by_agent=compact_by_agent)
            else:
                sig = _agent_signal_from_chair(legacy_chair_json, agent)

            row[f"{agent}_signal"] = sig["signal"]
            row[f"{agent}_weighted_signal"] = sig["weighted_signal"]
            row[f"{agent}_recommendation"] = sig["recommendation"]
            row[f"{agent}_weight"] = sig["weight"]
            row[f"{agent}_signal_source"] = sig["source"]
            row[f"{agent}_basis"] = sig["basis"]

        # 같은 파일 안에 객관적 source audit columns도 뒤에 붙인다.
        for agent in AGENTS:
            snap = {}
            if load_agent_snapshot is not None:
                try:
                    snap = load_agent_snapshot(as_of_date=window.as_of_date, field=target.field, company_dir=target.company_dir, agent=agent) or {}
                except Exception:
                    snap = {}
            diag = _snapshot_diag(snap)
            row[f"{agent}_data_status"] = diag["data_status"]
            row[f"{agent}_monthly_rows"] = diag["monthly_rows"]
            row[f"{agent}_asof_date_used"] = diag["asof_date_used"]
            row[f"{agent}_source_file"] = diag["source_file"]
            row[f"{agent}_metric_preview"] = diag["metric_preview"]

            if agent == "market":
                dq = snap.get("data_quality") if isinstance(snap.get("data_quality"), dict) else {}
                metrics = snap.get("metrics") if isinstance(snap.get("metrics"), dict) else {}
                price_q = dq.get("price_quality") if isinstance(dq.get("price_quality"), dict) else {}
                excel_q = dq.get("market_excel_quality") if isinstance(dq.get("market_excel_quality"), dict) else {}

                row["market_price_status"] = price_q.get("status", "")
                row["market_price_monthly_rows"] = price_q.get("monthly_rows", "")
                row["market_price_source_file"] = price_q.get("source_file", "")
                row["market_excel_status"] = excel_q.get("status", "")
                row["market_excel_source_file"] = excel_q.get("source_file", "")
                row["market_excel_total_score_raw"] = metrics.get("market_excel_total_score_raw", "")
                row["market_excel_recommendation_raw"] = metrics.get("market_excel_recommendation_raw", "")
                row["market_excel_vc_role_raw"] = metrics.get("market_excel_vc_role_raw", "")
        rows.append(row)

    fieldnames = list(rows[0].keys()) if rows else []
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_csv


def run_monthly_evaluation(
    *,
    month: str,
    universe_csv: str | Path,
    field: str = "반도체",
    limit: int | None = None,
    run_id: str | None = None,
    output_dir: str | Path | None = None,
    fail_open: bool = True,
    skip_chair: bool = False,
) -> Path:
    window = parse_month(month)
    targets = read_universe(universe_csv, field=field)
    if limit:
        targets = targets[:limit]
    if run_id is None:
        run_id = f"eval_month_{window.month}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"[start/objective] month={window.month}, as_of_date={window.as_of_date}, companies={len(targets)}, run_id={run_id}")
    print("[mode] objective local-file snapshots -> Google Sheets history -> existing Chair/Auditor replay -> one CSV export")
    for i, target in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {target.company_name}/{target.company_dir} objective monthly snapshots 저장 중...")
        snapshots = build_all_snapshots(target, window)
        save_snapshots_to_history(target, window, snapshots)
        if not skip_chair:
            print(f"[{i}/{len(targets)}] {target.company_name}/{target.company_dir} Chair history replay 실행 중...")
            run_chair_from_history(target, window, run_id=run_id, fail_open=fail_open)

    out = export_monthly_signal_csv(targets=targets, window=window, run_id=run_id, output_dir=output_dir)
    print(f"[export] monthly signal_df 저장 완료: {out}")
    return out


# CLI helper for direct debugging.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--universe-csv", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-chair", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    run_monthly_evaluation(month=args.month, field=args.field, universe_csv=args.universe_csv, limit=args.limit or None, skip_chair=args.skip_chair, fail_open=not args.strict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

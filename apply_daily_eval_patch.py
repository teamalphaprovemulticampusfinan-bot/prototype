from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

daily_eval_py = r'''
from __future__ import annotations

import argparse
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
    _clean_text,
    _date_column,
    _filter_by_month,
    _jsonable,
    _parse_date_series,
    _read_csv_any,
    _read_json,
    _safe_round,
    _to_float,
    build_all_snapshots,
    project_root,
    read_universe,
    run_chair_from_history,
    save_snapshots_to_history,
)


@dataclass(frozen=True)
class DailyWindow:
    month: str
    start: date
    end: date
    as_of_date: str

    @classmethod
    def parse(cls, day: str) -> "DailyWindow":
        d = datetime.strptime(str(day).strip(), "%Y-%m-%d").date()
        return cls(
            month=d.isoformat(),
            start=d,
            end=d,
            as_of_date=d.isoformat(),
        )

    @property
    def start_s(self) -> str:
        return self.start.isoformat()

    @property
    def end_s(self) -> str:
        return self.end.isoformat()

    @property
    def yyyy_mm(self) -> str:
        return self.as_of_date[:7]


def iter_days(start_date: str, end_date: str) -> list[DailyWindow]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start > end:
        raise ValueError("--start-date는 --end-date보다 늦을 수 없습니다.")

    out = []
    cur = start
    while cur <= end:
        out.append(DailyWindow.parse(cur.isoformat()))
        cur += timedelta(days=1)

    return out


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


def _find_files(patterns: list[str]) -> list[Path]:
    root = project_root()
    out: list[Path] = []
    for pat in patterns:
        out.extend(root.glob(pat))
    seen = set()
    unique = []
    for p in out:
        key = str(p).replace("\\", "/").lower()
        if key not in seen and p.exists() and p.is_file():
            seen.add(key)
            unique.append(p)
    return unique


def _read_excel_all_sheets(path: Path) -> dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(path, sheet_name=None)
    except Exception:
        return {}


def _find_valuation_workbook(target: CompanyTarget) -> Path | None:
    base = _company_root(target) / "valuation"
    patterns = [
        str(base / f"{target.company_dir}_valuation_workbook.xlsx"),
        str(base / "*valuation_workbook*.xlsx"),
        str(base / "*.xlsx"),
    ]

    files: list[Path] = []
    for pat in patterns:
        files.extend(Path().glob(pat) if not Path(pat).is_absolute() else Path(pat).parent.glob(Path(pat).name))

    for p in files:
        name = p.name.lower()
        if "valuation" in name and "workbook" in name:
            return p

    return files[0] if files else None


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
        dates = []
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
    out = {}
    for k, v in row.items():
        if len(out) >= max_cols:
            break
        if pd.isna(v):
            continue
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

    out = {}
    for col in df.columns:
        if len(out) >= max_cols:
            break
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        if not vals.empty:
            out[str(col)] = _safe_round(vals.iloc[-1], 6)
    return out


def _enhance_valuation_with_workbook(
    target: CompanyTarget,
    window: DailyWindow,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    wb = _find_valuation_workbook(target)

    snapshot = dict(snapshot)
    metrics = dict(snapshot.get("metrics") or {})
    raw_payload = dict(snapshot.get("raw_payload") or {})

    metrics.update(
        {
            "valuation_workbook_status": "NO_VALUATION_WORKBOOK",
            "valuation_workbook_source_file": str(wb) if wb else "",
            "valuation_workbook_daily_rows": 0,
            "valuation_workbook_date_column": "",
        }
    )

    if wb is None:
        snapshot["metrics"] = metrics
        snapshot["raw_payload"] = raw_payload
        return snapshot

    sheets = _read_excel_all_sheets(wb)
    matched_rows = []
    date_cols = []
    sheet_hits = []

    for sheet_name, df in sheets.items():
        if df is None or df.empty:
            continue

        day_rows, date_col = _filter_exact_day(df, window)
        if date_col:
            date_cols.append(f"{sheet_name}:{date_col}")

        if not day_rows.empty:
            sheet_hits.append(sheet_name)
            tmp = day_rows.copy()
            tmp["_sheet"] = sheet_name
            matched_rows.append(tmp)

    if matched_rows:
        combined = pd.concat(matched_rows, ignore_index=True)
        metrics.update(
            {
                "valuation_workbook_status": "FOUND_EXACT_DAILY_ROWS",
                "valuation_workbook_source_file": str(wb),
                "valuation_workbook_daily_rows": int(len(combined)),
                "valuation_workbook_date_column": "; ".join(date_cols[:5]),
                "valuation_workbook_sheets": "; ".join(sheet_hits[:10]),
            }
        )
        raw_payload["valuation_workbook_daily_preview"] = _compact_preview(combined)
        raw_payload["valuation_workbook_numeric_summary"] = _numeric_summary(combined)
    else:
        metrics.update(
            {
                "valuation_workbook_status": "NO_EXACT_DAILY_ROW_IN_WORKBOOK",
                "valuation_workbook_source_file": str(wb),
                "valuation_workbook_daily_rows": 0,
                "valuation_workbook_date_column": "; ".join(date_cols[:5]),
            }
        )

    snapshot["metrics"] = metrics
    snapshot["raw_payload"] = raw_payload
    return _jsonable(snapshot)


def _find_market_excel_files() -> list[Path]:
    return _find_files(
        [
            "data/market_excel/market_final_*.xlsx",
            "data/market-excel/market_final_*.xlsx",
            "data/market_excel/*.xlsx",
            "data/market-excel/*.xlsx",
            "data/*/_sector_common/data/Market_*.xlsx",
            "data/*/_sector_common/data/*Market*.xlsx",
        ]
    )


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


def _market_excel_snapshot(target: CompanyTarget, window: DailyWindow) -> dict[str, Any]:
    files = _find_market_excel_files()
    out = {
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

    for path in files:
        sheets = _read_excel_all_sheets(path)
        for sheet_name, df in sheets.items():
            matched = _match_company_rows(df, target)
            if matched.empty:
                continue

            exact, _date_col = _filter_exact_day(matched, window)
            chosen = exact if not exact.empty else matched.tail(1)

            preview = _compact_preview(chosen)
            total_score = ""
            recommendation = ""
            vc_role = ""

            for k, v in preview.items():
                lk = str(k).lower()
                if not total_score and ("총점" in str(k) or "score" in lk):
                    total_score = v
                if not recommendation and ("투자의견" in str(k) or "recommend" in lk or "opinion" in lk):
                    recommendation = v
                if not vc_role and ("vc_role" in lk or "밸류체인" in str(k) or "value_chain" in lk):
                    vc_role = v

            out.update(
                {
                    "market_excel_status": "FOUND_EXACT_DAILY_ROWS" if not exact.empty else "FOUND_COMPANY_ROW_NO_DAILY_DATE",
                    "market_excel_source_file": str(path),
                    "market_excel_daily_rows": int(len(exact)),
                    "market_excel_sheet": sheet_name,
                    "market_excel_total_score_raw": total_score,
                    "market_excel_recommendation_raw": recommendation,
                    "market_excel_vc_role_raw": vc_role,
                    "market_excel_metric_preview": preview,
                }
            )
            return out

    out["market_excel_status"] = "NO_COMPANY_ROW_IN_MARKET_EXCEL"
    out["market_excel_source_file"] = str(files[0])
    return out


def _enhance_market_daily(
    target: CompanyTarget,
    window: DailyWindow,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    snapshot = dict(snapshot)
    metrics = dict(snapshot.get("metrics") or {})
    raw_payload = dict(snapshot.get("raw_payload") or {})

    # build_market_snapshot에서 이미 valuation_price_history.csv를 price source로 쓰되,
    # daily window라서 해당 날짜 row만 들어간다.
    price_rows = metrics.get("price_rows_month")
    price_source = metrics.get("source_file")

    metrics["market_price_status"] = (
        "FOUND_EXACT_DAILY_PRICE_ROW"
        if _to_float(price_rows) and _to_float(price_rows) > 0
        else "NO_EXACT_DAILY_PRICE_ROW"
    )
    metrics["market_price_daily_rows"] = price_rows or 0
    metrics["market_price_monthly_rows"] = price_rows or 0
    metrics["market_price_source_file"] = price_source or ""

    excel_info = _market_excel_snapshot(target, window)
    metrics.update({k: v for k, v in excel_info.items() if k != "market_excel_metric_preview"})
    raw_payload["market_excel_metric_preview"] = excel_info.get("market_excel_metric_preview", {})

    snapshot["metrics"] = metrics
    snapshot["raw_payload"] = raw_payload
    return _jsonable(snapshot)


def _enhance_snapshots_for_daily(
    target: CompanyTarget,
    window: DailyWindow,
    snapshots: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    snapshots = dict(snapshots)
    snapshots["valuation"] = _enhance_valuation_with_workbook(
        target,
        window,
        snapshots.get("valuation", {}),
    )
    snapshots["market"] = _enhance_market_daily(
        target,
        window,
        snapshots.get("market", {}),
    )

    for agent, payload in snapshots.items():
        payload = dict(payload or {})
        payload["evaluation_context"] = {
            "mode": "daily_cutoff",
            "date": window.as_of_date,
            "start_date": window.start_s,
            "end_date": window.end_s,
            "no_future_data": True,
        }
        snapshots[agent] = payload

    return snapshots


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


def _load_run_results(
    *,
    run_id: str,
    field: str,
) -> list[dict[str, Any]]:
    from common.agent_history import list_run_results

    return list_run_results(
        run_id=run_id,
        field=field,
        include_payload=True,
    )


def export_daily_signal_csv(
    *,
    targets: list[CompanyTarget],
    windows: list[DailyWindow],
    run_id: str,
    field: str,
    base_rows: list[dict[str, Any]],
    output_dir: str | Path | None = None,
) -> Path:
    rows = _load_run_results(run_id=run_id, field=field)

    qd_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    qd_source_by_key: dict[tuple[str, str], str] = {}

    for row in rows:
        payload = _payload_dict(row.get("payload"))
        qd = _deep_find_qd(payload)
        if not qd:
            continue

        company_dir = str(row.get("company_dir") or "")
        as_of_date = str(row.get("as_of_date") or "")
        key = (as_of_date, company_dir)
        qd_by_key[key] = qd
        qd_source_by_key[key] = f"google_sheets_run_results:{row.get('agent')}:{row.get('output_kind')}"

    out_rows: list[dict[str, Any]] = []

    for base in base_rows:
        row = dict(base)
        key = (row["as_of_date"], row["company_dir"])
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
            row.setdefault("recommendation", "")
            row.setdefault("weighted_signal", "")
            for agent in AGENTS:
                row.setdefault(f"{agent}_signal", "")
                row.setdefault(f"{agent}_weighted_signal", "")
                row.setdefault(f"{agent}_recommendation", "")
                row.setdefault(f"{agent}_weight", "")
                row.setdefault(f"{agent}_signal_source", "AUDITOR_QD_NOT_FOUND")

        out_rows.append(row)

    if output_dir is None:
        output_dir = (
            project_root()
            / "data"
            / field
            / "_sector_common"
            / "history_sheets_exports"
            / "daily"
            / windows[0].yyyy_mm
            / run_id
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"signal_df_daily_{windows[0].yyyy_mm}.csv"

    df = pd.DataFrame(out_rows)

    front = [
        "date",
        "ticker",
        "recommendation",
        "weighted_signal",
        "auditor_qd_status",
        "auditor_qd_source",
    ]
    cols = front + [c for c in df.columns if c not in front]
    df = df[cols]
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"[DONE] daily signal_df 저장 완료: {out_path}")
    return out_path


def _base_row_from_snapshots(
    *,
    target: CompanyTarget,
    window: DailyWindow,
    snapshots: dict[str, dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    market_metrics = snapshots.get("market", {}).get("metrics", {}) or {}
    valuation_metrics = snapshots.get("valuation", {}).get("metrics", {}) or {}
    issue_metrics = snapshots.get("issue", {}).get("metrics", {}) or {}
    macro_metrics = snapshots.get("macro", {}).get("metrics", {}) or {}
    tech_metrics = snapshots.get("tech", {}).get("metrics", {}) or {}
    finance_metrics = snapshots.get("finance", {}).get("metrics", {}) or {}

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
        "valuation_workbook_sheets": valuation_metrics.get("valuation_workbook_sheets", ""),
        "valuation_workbook_date_column": valuation_metrics.get("valuation_workbook_date_column", ""),

        "issue_status": "FOUND" if _to_float(issue_metrics.get("news_count")) else "NO_ISSUE_ROWS_ON_DATE",
        "issue_news_count": issue_metrics.get("news_count", ""),
        "issue_source_file": issue_metrics.get("issue_source_file", ""),

        "macro_score": macro_metrics.get("macro_score", ""),
        "macro_source_files": "; ".join(macro_metrics.get("macro_source_files", [])[:5]) if isinstance(macro_metrics.get("macro_source_files"), list) else "",

        "tech_source_file": tech_metrics.get("tech_source_file", ""),
        "tech_final_score": tech_metrics.get("final_tech_investor_score", ""),
        "tech_ip_evidence_score": tech_metrics.get("ip_evidence_composite_score", ""),
    }


def run_daily_evaluation(
    *,
    start_date: str,
    end_date: str,
    universe_csv: str | Path,
    field: str = "반도체",
    limit: int | None = None,
    run_id: str | None = None,
    output_dir: str | Path | None = None,
    fail_open: bool = True,
    skip_chair: bool = False,
    date_limit: int | None = None,
) -> Path:
    windows = iter_days(start_date, end_date)
    if date_limit:
        windows = windows[:date_limit]

    targets = read_universe(universe_csv, field=field, limit=limit)
    if not targets:
        raise RuntimeError(f"universe CSV에서 실행 대상을 찾지 못했습니다: {universe_csv}")

    run_id = run_id or f"eval_daily_{windows[0].yyyy_mm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(
        f"[start/daily] dates={windows[0].as_of_date}~{windows[-1].as_of_date}, "
        f"companies={len(targets)}, run_id={run_id}"
    )
    print("[mode] objective daily snapshots -> Google Sheets history -> existing Chair/Auditor replay -> one daily CSV")

    base_rows: list[dict[str, Any]] = []

    total = len(windows) * len(targets)
    step = 0

    for window in windows:
        for target in targets:
            step += 1
            print(f"[{step}/{total}] {window.as_of_date} {target.company_name}/{target.company_dir} daily snapshots 저장 중...")

            snapshots = build_all_snapshots(target, window)  # DailyWindow은 MonthWindow와 같은 interface를 가진다.
            snapshots = _enhance_snapshots_for_daily(target, window, snapshots)

            save_snapshots_to_history(target, window, snapshots)
            base_rows.append(_base_row_from_snapshots(target=target, window=window, snapshots=snapshots, run_id=run_id))

            if not skip_chair:
                print(f"[{step}/{total}] {window.as_of_date} {target.company_name}/{target.company_dir} Chair history replay 실행 중...")
                run_chair_from_history(target, window, run_id=run_id, fail_open=fail_open)

    return export_daily_signal_csv(
        targets=targets,
        windows=windows,
        run_id=run_id,
        field=field,
        base_rows=base_rows,
        output_dir=output_dir,
    )
'''

run_daily_py = r'''
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _bootstrap_paths() -> Path:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"

    for p in (root, src):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)

    os.environ["PYTHONPATH"] = str(src)
    return root


def main(argv: list[str] | None = None) -> int:
    root = _bootstrap_paths()

    from evaluation.daily_eval import run_daily_evaluation

    parser = argparse.ArgumentParser(
        description="AlphaProve 일별 historical evaluation 실행"
    )
    parser.add_argument("--start-date", required=True, help="시작일. 예: 2025-01-01")
    parser.add_argument("--end-date", required=True, help="종료일. 예: 2025-01-31")
    parser.add_argument("--field", default="반도체")
    parser.add_argument(
        "--universe-csv",
        default=str(root / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"),
    )
    parser.add_argument("--limit", type=int, default=0, help="테스트용 기업 수 제한")
    parser.add_argument("--date-limit", type=int, default=0, help="테스트용 날짜 수 제한")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--strict-auditor", action="store_true")
    parser.add_argument("--skip-chair", action="store_true")

    args = parser.parse_args(argv)

    out = run_daily_evaluation(
        start_date=args.start_date,
        end_date=args.end_date,
        universe_csv=args.universe_csv,
        field=args.field,
        limit=args.limit or None,
        date_limit=args.date_limit or None,
        run_id=args.run_id or None,
        output_dir=args.output_dir or None,
        fail_open=not args.strict_auditor,
        skip_chair=args.skip_chair,
    )

    print(f"\n[DONE] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

(ROOT / "src" / "evaluation").mkdir(parents=True, exist_ok=True)
(ROOT / "scripts").mkdir(parents=True, exist_ok=True)

(ROOT / "src" / "evaluation" / "daily_eval.py").write_text(daily_eval_py, encoding="utf-8")
(ROOT / "scripts" / "run_evaluation_daily_30.py").write_text(run_daily_py, encoding="utf-8")

print("[OK] created src/evaluation/daily_eval.py")
print("[OK] created scripts/run_evaluation_daily_30.py")
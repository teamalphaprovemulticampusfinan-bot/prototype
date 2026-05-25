from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.cutoff_env import build_cutoff_env, cutoff_audit_payload


def _ok(detail: str = "") -> dict[str, object]:
    return {"ok": True, "detail": detail}


def _bad(detail: str) -> dict[str, object]:
    return {"ok": False, "detail": detail}


def main() -> int:
    as_of = os.getenv("ALPHAPROVE_CHECK_AS_OF_DATE", "2025-01-31")
    env = build_cutoff_env(as_of, start_date="2021-01-01", include_tech=False, base_env=os.environ)
    os.environ.update(env)

    checks: dict[str, dict[str, object]] = {}

    try:
        from market_agent.data_loader import filter_by_cutoff as market_filter

        df = pd.DataFrame({"date": ["2025-01-01", "2025-02-01"], "x": [1, 2]})
        out = market_filter(df, as_of)
        checks["market_filter_by_cutoff"] = _ok(f"rows={len(out)}") if len(out) == 1 else _bad(f"rows={len(out)}")
    except Exception as exc:
        checks["market_filter_by_cutoff"] = _bad(str(exc))

    try:
        import importlib.util
        issue_loader_path = SRC / "data_intake" / "issue_intake" / "excel_loader.py"
        spec = importlib.util.spec_from_file_location("_cutoff_issue_excel_loader", issue_loader_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        issue_filter = mod.filter_by_cutoff

        df = pd.DataFrame({"published_date": ["2025-01-01", "2025-02-01"], "x": [1, 2]})
        out = issue_filter(df, as_of, date_col="published_date")
        checks["issue_filter_by_cutoff"] = _ok(f"rows={len(out)}") if len(out) == 1 else _bad(f"rows={len(out)}")
    except Exception as exc:
        checks["issue_filter_by_cutoff"] = _bad(str(exc))

    try:
        cutoff = os.environ.get("MACRO_CUTOFF_DATE")
        checks["macro_cutoff_exclusive"] = _ok(f"resolved={cutoff}") if cutoff == "20250201" else _bad(f"resolved={cutoff}")
    except Exception as exc:
        checks["macro_cutoff_exclusive"] = _bad(str(exc))

    try:
        from finance_agent.data_loader import load_finance_data, load_stock_data

        tmp = ROOT / "_tmp_cutoff_check"
        tmp.mkdir(exist_ok=True)
        fcsv = tmp / "finance.csv"
        scsv = tmp / "stock.csv"
        pd.DataFrame({"year": [2024, 2025], "x": [1, 2]}).to_csv(fcsv, index=False, encoding="utf-8-sig")
        pd.DataFrame({"date": ["2025-01-15", "2025-02-15"], "close": [1, 2]}).to_csv(scsv, index=False, encoding="utf-8-sig")
        f = load_finance_data(fcsv)
        s = load_stock_data(scsv)
        f_rows = len(f.get("finance_data", [])) if isinstance(f, dict) else len(f)
        s_rows = len(s.get("recent_1m", [])) if isinstance(s, dict) else len(s)
        detail = f"finance_rows={f_rows}, stock_rows={s_rows}, FINANCE_CUTOFF_YEAR={os.environ.get('FINANCE_CUTOFF_YEAR')}"
        checks["finance_cutoff_loaders"] = _ok(detail) if f_rows == 1 and s_rows == 1 else _bad(detail)
    except Exception as exc:
        checks["finance_cutoff_loaders"] = _bad(str(exc))

    try:
        from valuation_agent.data_loader import load_valuation_financials, load_valuation_price_data, get_valuation_data_range

        tmp = ROOT / "_tmp_cutoff_check"
        tmp.mkdir(exist_ok=True)
        fcsv = tmp / "valuation_financials.csv"
        pcsv = tmp / "valuation_prices.csv"
        pd.DataFrame({"year": [2024, 2025], "x": [1, 2]}).to_csv(fcsv, index=False, encoding="utf-8-sig")
        pd.DataFrame({"date": ["2025-01-15", "2025-02-15"], "close": [1, 2]}).to_csv(pcsv, index=False, encoding="utf-8-sig")
        f = load_valuation_financials(fcsv, year=int(os.environ.get("VALUATION_CUTOFF_YEAR", "2024")))
        p = load_valuation_price_data(pcsv, year_month="2025-02")
        r = get_valuation_data_range(pcsv, start_date="2025-01-01", end_date=as_of)
        f_rows = len(f.get("financials", [])) if isinstance(f, dict) else len(f)
        p_rows = len(p.get("price_history", [])) if isinstance(p, dict) else len(p)
        r_rows = len(r.get("records", [])) if isinstance(r, dict) else len(r)
        detail = f"financial_rows={f_rows}, price_rows={p_rows}, range_rows={r_rows}, VALUATION_CUTOFF_YEAR={os.environ.get('VALUATION_CUTOFF_YEAR')}"
        checks["valuation_cutoff_loaders"] = _ok(detail) if f_rows == 1 and p_rows == 1 and r_rows == 1 else _bad(detail)
    except Exception as exc:
        checks["valuation_cutoff_loaders"] = _bad(str(exc))

    overall = all(v.get("ok") for v in checks.values())
    payload = {
        "as_of_date": as_of,
        "cutoff_env": cutoff_audit_payload(as_of, start_date="2021-01-01", include_tech=False),
        "checks": checks,
        "overall_ok": overall,
        "secret_policy": "No API key, token, raw secret, URL value, or model value is printed.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

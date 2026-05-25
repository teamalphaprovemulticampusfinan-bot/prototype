from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
ENV_FILES = [ROOT / ".env", ROOT / ".env.local", ROOT / ".env.eval", ROOT / "config" / "eval.env"]

SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PW", "PASSWORD", "SERVICE_ACCOUNT", "SPREADSHEET_ID", "KRX_ID")

GROUPS = {
    "core": [
        "PYTHONUTF8", "PYTHONIOENCODING", "ALPHAPROVE_FIELD", "ALPHAPROVE_EVAL_FREQUENCY",
        "ALPHAPROVE_EVAL_MODE", "ALPHAPROVE_EVAL_OUTPUT_LAYOUT", "ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED",
    ],
    "sheets": [
        "ALPHAPROVE_HISTORY_BACKEND", "ALPHAPROVE_HISTORY_SPREADSHEET_ID", "ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE",
    ],
    "source_common": [
        "ALPHAPROVE_SOURCE_SLEEP_SEC", "ALPHAPROVE_EVAL_TRY_PYKRX", "ALPHAPROVE_EVAL_YFINANCE_FALLBACK",
        "ALPHAPROVE_KRX_CAP_FALLBACK_ENABLE", "KRX_ID", "KRX_PW", "DART_API_KEY", "ECOS_API_KEY",
        "FRED_API_KEY", "NEWS_API_KEY", "SERPER_API_KEY", "KIPRIS_PLUS_API_KEY",
    ],
    "finance": [
        "ALPHAPROVE_FINANCE_LOCAL_FIRST", "ALPHAPROVE_FINANCE_USE_EVAL_DAILY",
        "ALPHAPROVE_FINANCE_USE_PRICE_OVERLAY", "ALPHAPROVE_FINANCE_STOCK_GLOBS",
        "ALPHAPROVE_FINANCE_FINANCIAL_GLOBS", "ALPHAPROVE_FINANCE_ANNUAL_LAG_MODE",
    ],
    "valuation": [
        "ALPHAPROVE_VALUATION_LOCAL_FIRST", "ALPHAPROVE_VALUATION_USE_EVAL_PRICE",
        "ALPHAPROVE_VALUATION_USE_PEER_MULTIPLES", "ALPHAPROVE_VALUATION_USE_DILUTION",
        "ALPHAPROVE_VALUATION_PRICE_GLOBS", "ALPHAPROVE_VALUATION_PEER_PATH",
        "ALPHAPROVE_VALUATION_WACC_PATH", "ALPHAPROVE_VALUATION_DEFAULT_TERMINAL_GROWTH",
    ],
    "tech": [
        "ALPHAPROVE_TECH_LOCAL_FIRST", "ALPHAPROVE_TECH_USE_PATENT_ASOF", "ALPHAPROVE_TECH_USE_KIPRIS_CSV",
        "ALPHAPROVE_TECH_USE_HISTORY_TEMPLATES", "ALPHAPROVE_TECH_PATENT_GLOBS", "ALPHAPROVE_TECH_HISTORY_ROOT",
        "ALPHAPROVE_TECH_MIN_MONTHLY_SNAPSHOT", "ALPHAPROVE_TECH_ENABLE_CERTIFICATION_LAYER",
        "ALPHAPROVE_TECH_ENABLE_QUALIFICATION_LAYER", "ALPHAPROVE_TECH_ENABLE_TRL_LAYER",
    ],
    "market": [
        "ALPHAPROVE_MARKET_LOCAL_FIRST", "ALPHAPROVE_MARKET_USE_EXTERNAL_DAILY",
        "ALPHAPROVE_MARKET_USE_SEMICONDUCTOR_CYCLE", "ALPHAPROVE_MARKET_USE_TECHNICALS",
        "ALPHAPROVE_MARKET_COMMON_ROOT", "ALPHAPROVE_MARKET_EXTERNAL_TICKERS", "ALPHAPROVE_MARKET_PRICE_GLOBS",
    ],
    "issue": [
        "ALPHAPROVE_ISSUE_LOCAL_FIRST", "ALPHAPROVE_EVAL_FETCH_EXTERNAL_NEWS",
        "ALPHAPROVE_EVAL_NEWS_MAX_RECORDS_PER_COMPANY", "ALPHAPROVE_ISSUE_CURRENT_MONTH_WEIGHT",
        "ALPHAPROVE_ISSUE_PREVIOUS_MONTH_WEIGHT", "ALPHAPROVE_ISSUE_MAX_LAG_MONTHS",
        "ALPHAPROVE_ISSUE_USE_ATTENTION_PROXY", "ALPHAPROVE_ISSUE_USE_GDELT",
        "ALPHAPROVE_ISSUE_USE_GOOGLE_NEWS_RSS", "ALPHAPROVE_ISSUE_INTEGRATION_PATHS",
    ],
    "macro": [
        "ALPHAPROVE_MACRO_LOCAL_FIRST", "ALPHAPROVE_MACRO_ROOT", "ALPHAPROVE_MACRO_USE_EXTERNAL_DAILY",
        "ALPHAPROVE_MACRO_USE_EXISTING_KOREAN_CSV", "ALPHAPROVE_MACRO_USE_COMPANY_SENSITIVITY",
        "ALPHAPROVE_MACRO_COMPANY_SENSITIVITY_PATH", "ALPHAPROVE_MACRO_EVENT_OVERLAY_CLIP_LOW",
        "ALPHAPROVE_MACRO_EVENT_OVERLAY_CLIP_HIGH", "ALPHAPROVE_MACRO_FRED_SERIES",
    ],
    "dma_backtest": [
        "ALPHAPROVE_HOLD_POLICY", "ALPHAPROVE_DMA_ENABLED", "ALPHAPROVE_DMA_HISTORY_METHOD",
        "ALPHAPROVE_DMA_IC_WINDOW", "ALPHAPROVE_DMA_FORGETTING_FACTOR", "ALPHAPROVE_DMA_NO_FIXED_THRESHOLDS",
    ],
}

ASOF_NAMES = [
    "FINANCE_AS_OF_DATE", "FINANCE_END_DATE", "VALUATION_AS_OF_DATE", "VALUATION_END_DATE",
    "TECH_AS_OF_DATE", "TECH_END_DATE", "MARKET_AS_OF_DATE", "MARKET_END_DATE",
    "ISSUE_AS_OF_DATE", "ISSUE_START_DATE", "ISSUE_END_DATE", "MACRO_AS_OF_DATE", "MACRO_END_DATE",
    "ALPHAPROVE_DATA_CUTOFF_DATE",
]


def load_env_file(path: Path) -> list[str]:
    loaded: list[str] = []
    if not path.exists():
        return loaded
    for raw in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return loaded


def mask(key: str, val: str | None) -> str:
    if val is None or val == "":
        return "MISSING"
    if any(h in key.upper() for h in SECRET_HINTS):
        return "SET(***)"
    if len(val) > 120:
        return val[:117] + "..."
    return val


def print_group(name: str, keys: Iterable[str]) -> None:
    print(f"\n[{name}]")
    for key in keys:
        print(f"- {key}: {mask(key, os.environ.get(key))}")


def path_status(raw: str | None) -> str:
    if not raw:
        return "MISSING"
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return f"{'OK' if p.exists() else 'MISSING'} :: {p}"


def main() -> int:
    print(f"[root] {ROOT}")
    for env_path in ENV_FILES:
        loaded = load_env_file(env_path)
        print(f"[env] {env_path} exists={env_path.exists()} loaded={len(loaded)}")

    for group, keys in GROUPS.items():
        print_group(group, keys)

    print("\n[path checks]")
    for key in [
        "ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE",
        "ALPHAPROVE_VALUATION_PEER_PATH",
        "ALPHAPROVE_VALUATION_WACC_PATH",
        "ALPHAPROVE_TECH_HISTORY_ROOT",
        "ALPHAPROVE_MARKET_COMMON_ROOT",
        "ALPHAPROVE_MACRO_ROOT",
        "ALPHAPROVE_MACRO_COMPANY_SENSITIVITY_PATH",
    ]:
        print(f"- {key}: {path_status(os.environ.get(key))}")

    issue_paths = os.environ.get("ALPHAPROVE_ISSUE_INTEGRATION_PATHS", "")
    print("\n[issue integration paths]")
    for part in [p.strip() for p in issue_paths.split(";") if p.strip()]:
        print(f"- {path_status(part)}")

    print("\n[as-of warning]")
    fixed = [k for k in ASOF_NAMES if os.environ.get(k)]
    if fixed:
        print("WARNING: These as-of/cutoff variables are fixed in the environment:")
        for k in fixed:
            print(f"- {k}: {os.environ.get(k)}")
        print("For range backtests, the runner should set these per window. Remove them from .env unless doing a one-off run.")
    else:
        print("OK: no fixed as-of/cutoff variables detected in .env/runtime.")

    print("\n[recommendation]")
    print("Use config/eval_env_full_v47.env as a template, copy selected values into .env, and keep real secrets out of Git.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

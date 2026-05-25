from __future__ import annotations

from pathlib import Path
import json
import os
import sys

import pandas as pd


def _project_root() -> Path:
    env = os.getenv("ALPHAPROVE_PROJECT_ROOT_OVERRIDE", "").strip().strip('"').strip("'")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists() or not path.is_file():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path)


def _latest_date(path: Path) -> str | None:
    df = _read_csv_any(path)
    if df.empty or "date" not in df.columns:
        return None
    s = pd.to_datetime(df["date"], errors="coerce").dropna()
    if s.empty:
        return None
    return str(pd.Timestamp(s.max()).date())


def main() -> int:
    root = _project_root()
    field = sys.argv[1] if len(sys.argv) > 1 else "반도체"
    market_dir = root / "data" / field / "_sector_common" / "market"
    cache_dir = market_dir / "source_price_cache"
    files = sorted(cache_dir.glob("*.csv")) if cache_dir.exists() else []
    latest = []
    for p in files[:10]:
        latest.append({"file": str(p.relative_to(root)), "rows": len(_read_csv_any(p)), "latest_date": _latest_date(p)})
    out = {
        "project_root": str(root),
        "cache_dir": str(cache_dir.relative_to(root)) if cache_dir.exists() else str(cache_dir),
        "cache_exists": cache_dir.exists(),
        "cache_csv_count": len(files),
        "sample_cache_files": latest,
        "market_signals_daily_latest": _latest_date(market_dir / "market_signals_daily.csv"),
        "market_semiconductor_daily_latest": _latest_date(market_dir / "market_semiconductor_daily.csv"),
        "note": "No API key, token, or raw secret was printed.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

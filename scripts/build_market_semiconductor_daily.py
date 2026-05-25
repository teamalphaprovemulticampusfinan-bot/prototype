from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from data_intake.market_intake.sector_semiconductor import build_market_semiconductor_daily


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build AlphaProve semiconductor market daily dataset")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--start-date", default="2021-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--network-update", action="store_true", help="Best-effort yfinance refresh for SOX/Nasdaq/S&P500/VIX/Korea semiconductor ETF")
    args = parser.parse_args(argv)

    result = build_market_semiconductor_daily(
        field=args.field,
        start_date=args.start_date,
        end_date=args.end_date,
        network_update=args.network_update,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

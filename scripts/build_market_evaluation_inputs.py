from __future__ import annotations

# Backward-compatible wrapper. v51 switched this script to the src_eval-only
# market evaluation intake builder, which fills daily/monthly CSVs from local
# price histories, market_issues.db, Market_통합.xlsx, and issue event CSVs.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_EVAL = ROOT / "src_eval"
SRC = ROOT / "src"

# Keep both import styles valid:
#   - data_intake.* / common.* via ROOT/src
#   - src.common.* via ROOT
# Some operational modules still use src.common.* while CLI users often set
# PYTHONPATH to ROOT/src only. Adding ROOT here prevents ModuleNotFoundError:
# "No module named 'src'" without requiring users to change every command.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if SRC_EVAL.exists() and str(SRC_EVAL) not in sys.path:
    sys.path.insert(0, str(SRC_EVAL))
# operational src is fallback only; never let it shadow src_eval packages
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from data_intake.market_intake.evaluation_builder import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

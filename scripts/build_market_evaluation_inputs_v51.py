from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_EVAL = ROOT / "src_eval"
SRC = ROOT / "src"
if SRC_EVAL.exists() and str(SRC_EVAL) not in sys.path:
    sys.path.insert(0, str(SRC_EVAL))
# operational src is fallback only; never let it shadow src_eval packages
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from data_intake.market_intake.evaluation_builder import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

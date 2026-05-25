from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_SRC = ROOT / "src" / "eval"
SRC = ROOT / "src"
for p in [str(EVAL_SRC), str(SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation.history_runner import main

if __name__ == "__main__":
    main()

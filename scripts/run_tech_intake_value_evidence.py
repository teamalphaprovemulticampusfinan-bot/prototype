from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.tech_intake.value_evidence_bridge import main


if __name__ == "__main__":
    raise SystemExit(main())

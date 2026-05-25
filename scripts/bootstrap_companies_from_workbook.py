from __future__ import annotations

# Backward-compatible wrapper.
# 실제 구현은 Tech Agent 패키지 내부로 이동했습니다.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tech_agent.scripts.bootstrap_companies_from_workbook import main


if __name__ == "__main__":
    main()

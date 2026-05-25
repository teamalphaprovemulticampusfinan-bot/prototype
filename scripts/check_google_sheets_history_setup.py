from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from common.google_sheets_history import ping  # noqa: E402


def main() -> int:
    result = ping()
    print("=" * 80)
    print("[Google Sheets History Setup Check]")
    print("=" * 80)
    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

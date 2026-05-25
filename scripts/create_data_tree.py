from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import DEFAULT_FIELD, KNOWN_COMPANY_DIRS, ensure_standard_tree, rel_project_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create AlphaProve field/company/agent data tree")
    parser.add_argument("--field", default=DEFAULT_FIELD, help="분야명 예: 반도체, 이차전지, 바이오")
    parser.add_argument("--companies", nargs="*", default=KNOWN_COMPANY_DIRS, help="회사 slug 목록")
    args = parser.parse_args()

    made = ensure_standard_tree(args.companies, field=args.field)

    for path in made:
        print(rel_project_path(path))

    print(f"\n[DONE] field={args.field}, companies={len(args.companies)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
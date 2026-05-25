from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/.pytest_cache",
    "**/.mypy_cache",
    "**/.ruff_cache",
]


def iter_targets(root: Path):
    for pattern in DEFAULT_PATTERNS:
        for p in root.glob(pattern):
            if ".venv" in p.parts:
                continue
            yield p


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove safe Python runtime artifacts only.")
    parser.add_argument("--root", default=".", help="프로젝트 루트")
    parser.add_argument("--apply", action="store_true", help="실제 삭제. 없으면 dry-run")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    targets = sorted(set(iter_targets(root)), key=lambda p: str(p))
    print(f"[cleanup] root={root}")
    print(f"[cleanup] targets={len(targets)}")
    for p in targets:
        print(("DELETE " if args.apply else "DRYRUN ") + str(p))
        if args.apply:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass
    if not args.apply:
        print("[cleanup] 실제 삭제하려면 --apply를 붙이세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

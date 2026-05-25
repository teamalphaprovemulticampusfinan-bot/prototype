from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_GENERATED_DIRS = [
    "chair_rerun_outputs",
    "chair_rerun_backups",
    "chair_rerun_logs",
    "chair_rerun_results",
    "chair_replay_logs",
    "chair_replay_results",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="data/<field>/_sector_common 아래에 생긴 Chair 재실행/리플레이 산출물을 정식 기업별 JSON과 구분하기 위해 격리합니다."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--delete", action="store_true", help="격리하지 않고 삭제합니다. 기본은 안전하게 move입니다.")
    parser.add_argument("--dirs", nargs="*", default=DEFAULT_GENERATED_DIRS)
    args = parser.parse_args()

    sector_common = PROJECT_ROOT / "data" / args.field / "_sector_common"
    if not sector_common.exists():
        raise FileNotFoundError(f"sector_common 경로가 없습니다: {sector_common}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    quarantine_root = sector_common / "_archive_generated_outputs" / stamp
    moved = 0
    deleted = 0
    missing = 0

    print("=" * 80)
    print("[Quarantine generated sector_common outputs]")
    print(f"sector_common : {sector_common}")
    print(f"mode          : {'DELETE' if args.delete else 'MOVE'}")
    print(f"target dirs   : {args.dirs}")
    print("=" * 80)

    for name in args.dirs:
        src = sector_common / name
        if not src.exists():
            print(f"[MISSING] {src}")
            missing += 1
            continue

        if args.delete:
            if src.is_dir():
                shutil.rmtree(src)
            else:
                src.unlink()
            print(f"[DELETED] {src}")
            deleted += 1
        else:
            quarantine_root.mkdir(parents=True, exist_ok=True)
            dst = quarantine_root / name
            if dst.exists():
                dst = quarantine_root / f"{name}_{stamp}"
            shutil.move(str(src), str(dst))
            print(f"[MOVED] {src} -> {dst}")
            moved += 1

    print("=" * 80)
    print(f"moved={moved}, deleted={deleted}, missing={missing}")
    if not args.delete:
        print(f"quarantine_root={quarantine_root}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

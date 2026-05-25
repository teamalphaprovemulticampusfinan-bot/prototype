from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.output_paths import (
    DEFAULT_OUTPUT_CATEGORY,
    ensure_company_agent_tree,
    migrate_flat_outputs,
    shared_output_dir,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reorganize data/<분야>/<기업명>/<agent> into data/<분야>/<기업명>/<agent>/<field>/<company_name>/<agent>/"
    )
    parser.add_argument("--move", action="store_true", help="Copy 대신 기존 산출물을 새 위치로 이동합니다.")
    parser.add_argument("--overwrite", action="store_true", help="새 위치에 같은 파일이 있으면 덮어씁니다.")
    parser.add_argument("--cleanup-empty-dirs", action="store_true", help="이동 후 빈 폴더를 정리합니다.")
    parser.add_argument(
        "--category",
        default=DEFAULT_OUTPUT_CATEGORY,
        help="기본 기업 분야 폴더명. 현재 5개 기업은 기본값 반도체를 사용합니다.",
    )
    args = parser.parse_args(argv)

    ensure_company_agent_tree(category=args.category)
    changes = migrate_flat_outputs(
        move=args.move,
        overwrite=args.overwrite,
        cleanup_empty_dirs=args.cleanup_empty_dirs,
        category=args.category,
    )

    summary = {
        "target_structure": "data/<분야>/<기업명>/<agent>/<기업분야>/<기업명>/<agent>/",
        "common_structure": "data/<분야>/<기업명>/<agent>/<기업분야>/common/<agent>/",
        "category": args.category,
        "mode": "move" if args.move else "copy",
        "changed_count": len(changes),
        "action_counts": {},
        "changes": changes,
    }
    for item in changes:
        action = item.get("action", "unknown")
        summary["action_counts"][action] = summary["action_counts"].get(action, 0) + 1

    summary_path = shared_output_dir("migration", category=args.category) / "outputs_migration_summary.json"
    write_json(summary_path, summary)

    print(f"[OK] outputs tree prepared: data/<분야>/<기업명>/<agent>/{args.category}/...")
    print(f"[OK] files scanned: {len(changes)}")
    print(f"[OK] summary: {summary_path}")
    print(json.dumps({k: v for k, v in summary.items() if k != "changes"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

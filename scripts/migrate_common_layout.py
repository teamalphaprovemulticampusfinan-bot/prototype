from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

DEFAULT_FIELD = "반도체"

MACRO_PATTERNS = (
    "ecos_*.csv",
    "ext_*.csv",
    "뉴스_*.csv",
    "규제_*.csv",
    "헬륨_*.csv",
    "희토류_*.csv",
    "macro_*.csv",
    "macro_*.json",
)

COMPANIES = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def safe_move(src: Path, dst: Path, *, move: bool, overwrite: bool) -> str:
    if not src.exists():
        return "missing"

    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        if not overwrite:
            return "skip_exists"
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    if move:
        shutil.move(str(src), str(dst))
        return "moved"

    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

    return "copied"


def migrate_macro_files(*, move: bool, overwrite: bool) -> list[dict[str, str]]:
    target = DATA_DIR / "_global_common" / "macro"
    target.mkdir(parents=True, exist_ok=True)

    changes: list[dict[str, str]] = []

    for base in [ROOT, DATA_DIR]:
        for pattern in MACRO_PATTERNS:
            for src in base.glob(pattern):
                if not src.is_file():
                    continue
                if src.parent.resolve() == target.resolve():
                    continue

                dst = target / src.name
                action = safe_move(src, dst, move=move, overwrite=overwrite)
                changes.append({"action": action, "source": rel(src), "target": rel(dst)})

    return changes


def migrate_field_common(*, field: str, move: bool, overwrite: bool) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []

    field_root = DATA_DIR / field
    old_common = field_root / "common"
    new_field_common = field_root / "_sector_common"
    source_data = new_field_common / "source_data"

    mapping = {
        old_common / "data": source_data,
        old_common / "templates": new_field_common / "templates",
        old_common / "ml_universe": new_field_common / "ml_universe",
        old_common / "scripts": new_field_common / "scripts",
        old_common / "migration": new_field_common / "migration",
        old_common / "tech": new_field_common / "tech",
        old_common / "finance": new_field_common / "finance",
        old_common / "market": new_field_common / "market",
        old_common / "issue": new_field_common / "issue",
        old_common / "macro": new_field_common / "macro",
        old_common / "chair": new_field_common / "chair",
        old_common / "auditor": new_field_common / "auditor",
        field_root / "data": source_data,
    }

    for src, dst in mapping.items():
        if src.exists():
            action = safe_move(src, dst, move=move, overwrite=overwrite)
            changes.append({"action": action, "source": rel(src), "target": rel(dst)})

    return changes


def migrate_company_common(*, field: str, move: bool, overwrite: bool) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []

    field_root = DATA_DIR / field

    for _slug, company_name in COMPANIES.items():
        company_root = field_root / company_name
        old_common = company_root / "common"
        new_common = company_root / "_company_common"

        if old_common.exists():
            for src in old_common.iterdir():
                dst = new_common / src.name
                action = safe_move(src, dst, move=move, overwrite=overwrite)
                changes.append({"action": action, "source": rel(src), "target": rel(dst)})

    return changes


def cleanup_empty_dirs() -> None:
    for d in sorted(DATA_DIR.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if not d.is_dir():
            continue
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate AlphaProve common/macro layout")
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--cleanup-empty-dirs", action="store_true")
    args = parser.parse_args()

    changes = []
    changes += migrate_macro_files(move=args.move, overwrite=args.overwrite)
    changes += migrate_field_common(field=args.field, move=args.move, overwrite=args.overwrite)
    changes += migrate_company_common(field=args.field, move=args.move, overwrite=args.overwrite)

    if args.cleanup_empty_dirs:
        cleanup_empty_dirs()

    for ch in changes:
        print(f"[{ch['action']}] {ch['source']} -> {ch['target']}")

    print(f"\n[DONE] changed={len(changes)}")
    print("[NEXT] python scripts\\verify_data_layout.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

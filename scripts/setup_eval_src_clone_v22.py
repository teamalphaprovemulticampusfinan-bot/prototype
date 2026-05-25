from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

EXCLUDE_NAMES = {
    "eval",
    "__pycache__",
    ".pytest_cache",
}

def copy_any(src: Path, dst: Path, *, force: bool = False) -> None:
    if src.name in EXCLUDE_NAMES:
        return
    if src.is_dir():
        if dst.exists() and force:
            shutil.rmtree(dst)
        shutil.copytree(
            src,
            dst,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if force or not dst.exists():
            shutil.copy2(src, dst)

def overlay_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"overlay payload not found: {src}")
    shutil.copytree(src, dst, dirs_exist_ok=True)

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Clone existing src package layout into src/eval and overlay evaluation-only v22 files."
    )
    ap.add_argument("--project-root", default=".", help="Agent_6.8 project root")
    ap.add_argument("--force", action="store_true", help="Replace existing src/eval before cloning")
    ap.add_argument("--backup-existing", action="store_true", default=True)
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    src_root = project_root / "src"
    eval_root = src_root / "eval"
    patch_root = Path(__file__).resolve().parents[1]
    overlay_root = patch_root / "patch_payload" / "src_eval_overlay"

    if not src_root.exists():
        raise FileNotFoundError(f"src folder not found: {src_root}")

    if eval_root.exists() and args.force:
        backup_root = project_root / "_old_eval_backup"
        backup_root.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_root / f"src_eval_before_v22_{stamp}"
        shutil.move(str(eval_root), str(backup_path))
        print(f"[backup] moved existing src/eval -> {backup_path}")

    eval_root.mkdir(parents=True, exist_ok=True)

    copied = []
    for item in sorted(src_root.iterdir(), key=lambda p: p.name.lower()):
        if item.name in EXCLUDE_NAMES:
            continue
        dst = eval_root / item.name
        copy_any(item, dst, force=False)
        copied.append(item.name)

    overlay_tree(overlay_root, eval_root)

    manifest = {
        "version": "v22",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "src_root": str(src_root),
        "eval_root": str(eval_root),
        "copied_top_level": copied,
        "overlay_root": str(overlay_root),
        "note": "src/eval is an evaluation-only clone. Do not import it for production Chair reports unless PYTHONPATH is intentionally pointed here.",
    }
    (eval_root / "_eval_clone_manifest_v22.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[OK] src/eval clone ready")
    print(f" - eval_root: {eval_root}")
    print(" - copied:", ", ".join(copied))
    print(" - overlay applied: evaluation v22")
    print("")
    print("Next:")
    print(r'  $env:PYTHONPATH=(Resolve-Path ".\src\eval").Path + ";" + (Resolve-Path ".\src").Path')
    print(r"  python .\scripts\check_eval_history_v22_install.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

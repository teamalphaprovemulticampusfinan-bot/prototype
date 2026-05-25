from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIELD = "반도체"

TEXT_SUFFIXES = {".json", ".md", ".csv", ".txt", ".yaml", ".yml", ".jsonl", ".xml", ".html"}
SECTOR_TECH_DIRS = [
    "tech_intake",
    "tech_lifecycle",
    "templates",
    "universe",
    "ml_universe",
    "scripts",
    "tech",
    "tech_certifications",
    "tech_value_evidence",
]


def _normalize_project_paths(text: str) -> str:
    """Remove local Agent_6.8/6.9 absolute prefixes from migrated text files."""
    replacements = [
        ("C:\\\\Agent_6.8\\\\", ""),
        ("C:\\Agent_6.8\\", ""),
        ("C:/Agent_6.8/", ""),
        ("C:\\\\Agent_6.9\\\\", ""),
        ("C:\\Agent_6.9\\", ""),
        ("C:/Agent_6.9/", ""),
        ("workspace\\templates\\", "data\\반도체\\_sector_common\\templates\\"),
        ("workspace/templates/", "data/반도체/_sector_common/templates/"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"[A-Za-z]:[\\/]+Agent_6\.[89][\\/]+", "", text)
    return text


def _copy_file(src: Path, dst: Path, *, overwrite: bool) -> bool:
    if dst.exists() and not overwrite:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() in TEXT_SUFFIXES:
        try:
            content = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = src.read_text(encoding="utf-8-sig", errors="ignore")
        dst.write_text(_normalize_project_paths(content), encoding="utf-8", newline="")
        try:
            shutil.copystat(src, dst)
        except Exception:
            pass
    else:
        shutil.copy2(src, dst)
    return True


def _copy_tree(src: Path, dst: Path, *, overwrite: bool) -> int:
    if not src.exists():
        return 0
    count = 0
    for item in src.rglob("*"):
        if item.is_file():
            rel = item.relative_to(src)
            if _copy_file(item, dst / rel, overwrite=overwrite):
                count += 1
    return count


def _iter_company_dirs(source_root: Path) -> Iterable[Path]:
    """Yield folders that look like data/반도체/<company>/tech containers."""
    for company_dir in sorted(source_root.iterdir(), key=lambda p: p.name):
        if not company_dir.is_dir():
            continue
        if company_dir.name.startswith("_"):
            continue
        if (company_dir / "tech").exists():
            yield company_dir


def sync_legacy_tech_data(
    *,
    source_root: Path,
    target_root: Path,
    field: str = DEFAULT_FIELD,
    overwrite: bool = True,
) -> dict:
    """Merge Agent_6.8 tech data into Agent_6.9 no-workspace layout.

    Expected source examples:
      - C:/Agent_6.8/data/반도체
      - an extracted folder containing 피에스케이/, 넥스틴/, ...
      - an extracted sector-common tech_intake bundle containing tech/, templates/, ml_universe/, ...

    Target is normally:
      - C:/Agent_6.9/data/반도체
    """
    source_root = source_root.resolve()
    target_root = target_root.resolve()
    target_sector_common = target_root / "_sector_common"

    summary = {
        "status": "OK",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_root": str(source_root),
        "target_root": str(target_root),
        "field": field,
        "overwrite": overwrite,
        "sector_common": {},
        "companies": {},
    }

    # Case A: source root itself is sector-common-like with tech/templates/ml_universe.
    for name in SECTOR_TECH_DIRS:
        src = source_root / name
        if src.exists():
            summary["sector_common"][name] = _copy_tree(src, target_sector_common / name, overwrite=overwrite)

    # Case B: source root has _sector_common.
    if (source_root / "_sector_common").exists():
        for name in SECTOR_TECH_DIRS:
            src = source_root / "_sector_common" / name
            if src.exists():
                summary["sector_common"][name] = _copy_tree(src, target_sector_common / name, overwrite=overwrite)

    # Case C: company folders.
    for company_dir in _iter_company_dirs(source_root):
        copied = _copy_tree(company_dir / "tech", target_root / company_dir.name / "tech", overwrite=overwrite)
        if copied:
            summary["companies"][company_dir.name] = copied

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync legacy Agent_6.8 Tech data into Agent_6.9 data layout.")
    parser.add_argument("--source-root", required=True, help="Legacy data/반도체 root or extracted tech bundle root")
    parser.add_argument("--target-root", default=str(ROOT / "data" / DEFAULT_FIELD), help="Current data/반도체 root")
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--no-overwrite", action="store_true", help="Only fill missing files; do not overwrite existing files")
    parser.add_argument("--summary-json", default="")
    args = parser.parse_args()

    summary = sync_legacy_tech_data(
        source_root=Path(args.source_root),
        target_root=Path(args.target_root),
        field=args.field,
        overwrite=not args.no_overwrite,
    )

    out = Path(args.summary_json) if args.summary_json else Path(args.target_root) / "_sector_common" / "migration" / "tech_legacy_sync_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[saved] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

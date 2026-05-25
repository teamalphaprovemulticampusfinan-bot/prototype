from __future__ import annotations

import json
import re
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any

ROOT = Path.cwd().resolve()
TARGETS = [
    company_agent_dir("nepes", "tech") / "tech_chair_summary.json",
    company_agent_dir("nepes", "tech") / "tech_full_appendix.json",
    company_agent_dir("nepes", "tech") / "nepes_chair_compact_tech_test.md",
]
ABS_PAT = re.compile(r"[A-Za-z]:[\\/]|/mnt/|/home/|C:[\\/]")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def walk_strings(data: Any) -> list[str]:
    if isinstance(data, dict):
        out: list[str] = []
        for v in data.values():
            out.extend(walk_strings(v))
        return out
    if isinstance(data, list):
        out: list[str] = []
        for v in data:
            out.extend(walk_strings(v))
        return out
    if isinstance(data, str):
        return [data]
    return []


def check_file(path: Path) -> bool:
    if not path.exists():
        print(f"[SKIP] missing: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
        return True
    text = read_text(path)
    bad = ABS_PAT.findall(text)
    if bad:
        print(f"[WARN] absolute path remains: {path.relative_to(ROOT)}")
        for line in text.splitlines():
            if ABS_PAT.search(line):
                print(f"  {line[:240]}")
        return False
    print(f"[OK] portable paths: {path.relative_to(ROOT)}")
    return True


def main() -> int:
    ok = True
    for path in TARGETS:
        ok = check_file(path) and ok
    if ok:
        print("[DONE] no absolute local paths found in checked Tech/Chair outputs.")
        return 0
    print("[DONE] warnings found. Re-run scripts\\repair_tech_paths.py after regenerating Tech outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

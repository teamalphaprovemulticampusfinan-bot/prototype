from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELD = "반도체"
TEXT_SUFFIXES = {".json", ".md", ".csv", ".txt", ".yaml", ".yml", ".jsonl"}


def _scan_text_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    problems = []
    if "Agent_6.8" in text or "C:/Agent_6.8" in text or "C:\\Agent_6.8" in text:
        problems.append("OLD_AGENT_6_8_ABSOLUTE_PATH")
    if "C:/Agent_6.9" in text or "C:\\Agent_6.9" in text:
        problems.append("LOCAL_AGENT_6_9_ABSOLUTE_PATH")
    return problems


def main() -> int:
    root = ROOT / "data" / FIELD
    sector = root / "_sector_common"
    sector_required = [
        "tech",
        "templates",
        "ml_universe",
        "universe",
        "tech_certifications",
    ]

    result = {
        "root": str(root),
        "sector_required": {},
        "company_tech_dirs": 0,
        "company_tech_file_count": 0,
        "absolute_path_problem_files": [],
    }

    for name in sector_required:
        path = sector / name
        result["sector_required"][name] = {
            "exists": path.exists(),
            "file_count": sum(1 for p in path.rglob("*") if p.is_file()) if path.exists() else 0,
        }

    for company_dir in sorted(root.iterdir(), key=lambda p: p.name):
        if not company_dir.is_dir() or company_dir.name.startswith("_"):
            continue
        tech_dir = company_dir / "tech"
        if not tech_dir.exists():
            continue
        result["company_tech_dirs"] += 1
        result["company_tech_file_count"] += sum(1 for p in tech_dir.rglob("*") if p.is_file())

        for path in tech_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                problems = _scan_text_file(path)
                if problems:
                    result["absolute_path_problem_files"].append(
                        {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "problems": problems}
                    )
                    if len(result["absolute_path_problem_files"]) >= 50:
                        break

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["absolute_path_problem_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
FIELD = "반도체"
COMMON = "common"
SLUG_TO_NAME = {"nepes": "네패스", "hanmi": "한미반도체", "hansol": "한솔케미칼", "duksan": "덕산테코피아", "ltc": "엘티씨"}


def infer_agent(filename: str) -> str:
    name = filename.lower()
    if "chair" in name or "report_quality" in name: return "chair"
    if "finance" in name: return "finance"
    if "market" in name: return "market"
    if "issue" in name: return "issue"
    if "macro" in name: return "macro"
    if "auditor" in name or "audit" in name or "valuation" in name: return "auditor"
    if "tech" in name or "kipris" in name or "patent" in name: return "tech"
    if "data" in name or "reorganize" in name or "migrate" in name or "sync" in name or "verify" in name: return "common"
    return "misc"


def infer_company(filename: str) -> tuple[str, str] | None:
    low = filename.lower()
    for slug, korean in SLUG_TO_NAME.items():
        if slug in low or korean in filename:
            return slug, korean
    return None


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def sync() -> list[dict[str, Any]]:
    manifest = []
    for src in sorted(SCRIPTS.glob("*.py")):
        if src.name.startswith("."): continue
        agent = infer_agent(src.name)
        company = infer_company(src.name)
        if company:
            _, korean = company
            dst = DATA / FIELD / korean / agent / "scripts" / src.name
            company_label = korean
        else:
            dst = DATA / FIELD / COMMON / "scripts" / agent / src.name
            company_label = COMMON
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest.append({"source": rel(src), "target": rel(dst), "company": company_label, "agent": agent})
    manifest_path = DATA / FIELD / COMMON / "scripts" / "script_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / FIELD / COMMON / "scripts" / "README.md").write_text(
        "# data/반도체/common/scripts\n\n"
        "프로젝트 루트의 `scripts/`를 data 구조 안에서도 분야/기업/에이전트 기준으로 확인할 수 있도록 복사한 정리본입니다.\n\n"
        "- 실제 실행 진입점은 기존처럼 루트의 `main.py`와 `scripts/`입니다.\n"
        "- 기업명이 붙은 스크립트는 `data/반도체/<기업명>/<agent>/scripts/`에도 복사됩니다.\n"
        "- src 패키지 구조는 변경하지 않습니다.\n", encoding="utf-8")
    return manifest


def main() -> int:
    manifest = sync()
    print(f"[OK] scripts mirrored into data tree: {len(manifest)} files")
    print(f"[OK] manifest: {rel(DATA / FIELD / COMMON / 'scripts' / 'script_manifest.json')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

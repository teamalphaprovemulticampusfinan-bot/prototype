from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"
ORIGINAL_5 = {"nepes","hanmi","hansol","duksan","ltc"}

def truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1","true","yes","y"}

def read(path: Path) -> str:
    for enc in ("utf-8","utf-8-sig","cp949"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            pass
    return ""

def rows(path: Path, include_original5: bool, only: str) -> list[dict[str,str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        out = [dict(r) for r in csv.DictReader(f) if truthy(r.get("include_in_evaluation","1"))]
    if not include_original5:
        out = [r for r in out if str(r.get("company_dir","")).strip() not in ORIGINAL_5]
    if only:
        out = [r for r in out if str(r.get("company_dir","")).strip() == only]
    return out

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=str(DEFAULT_CSV))
    p.add_argument("--include-original5", action="store_true")
    p.add_argument("--only-company-dir", default="")
    args = p.parse_args()
    results = []
    for r in rows(Path(args.csv), args.include_original5, args.only_company_dir):
        name, slug = str(r["company_name"]).strip(), str(r["company_dir"]).strip()
        report = ROOT / "data" / "반도체" / name / "chair" / f"{slug}_chair_report.md"
        text = read(report) if report.exists() else ""
        results.append({
            "company_name": name,
            "company_dir": slug,
            "report_path": str(report.relative_to(ROOT)),
            "exists": report.exists(),
            "chars": len(text),
            "has_final_recommendation_section": ("최종 추천" in text) or ("최종 의견" in text) or ("투자의견" in text),
            "has_agent_sections": ("재무" in text and "시장" in text and "기술" in text),
        })
    print(json.dumps({"count": len(results), "reports_exist": sum(1 for x in results if x["exists"]), "results": results}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_files(patterns: List[str]) -> List[Path]:
    root = project_root()
    out: List[Path] = []
    for pat in patterns:
        out.extend(root.rglob(pat))
    seen = set()
    uniq = []
    for p in out:
        s = str(p)
        if s not in seen:
            uniq.append(p)
            seen.add(s)
    return uniq


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(project_root())).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Tech ML artifacts and legacy company-universe files.")
    parser.add_argument("--company-dir", default="nepes")
    args = parser.parse_args()
    slug = args.company_dir
    root = project_root()
    slug_to_ko = {"nepes": "네패스", "hanmi": "한미반도체", "hansol": "한솔케미칼", "duksan": "덕산테코피아", "ltc": "엘티씨"}
    ko = slug_to_ko.get(slug, slug)
    tech_dirs = [
        root / "data" / "반도체" / ko / "tech",
        root / "data" / "반도체" / slug / "tech",
    ]
    expected = [
        "tech_ml_signal.json",
        "tech_peer_similarity.json",
        "tech_peer_cluster.json",
        "tech_peer_map.json",
        "tech_peer_percentile_bridge.json",
        "tech_ip_ml.json",
        "tech_differentiation.json",
        "tech_momentum_confidence.json",
        f"{slug}_tech_patent_evidence.json",
        f"{slug}_tech_evidence_harvest.json",
        f"{slug}_tech_high_quality_report.md",
        f"{slug}_tech_full_appendix.md",
    ]
    print("[Tech Artifact Check]")
    for name in expected:
        found = []
        for d in tech_dirs:
            p = d / name
            if p.exists():
                found.append(p)
        status = "OK" if found else "MISSING"
        print(f"- {status:7} {name}")
        for p in found:
            print(f"          {rel(p)}")

    print("\n[Reference / Universe files]")
    refs = find_files(["*valuation_credit_ml_overlay_candidate*.csv", "*reference_universe*.csv", "*ml_quality_summary*.csv", "*209*.xlsx", "*209*.csv", "*반도체*.xlsx", "*semiconductor*.xlsx"])
    if not refs:
        print("- No reference/universe files found by known patterns.")
    else:
        for p in refs:
            print(f"- {rel(p)}")

    print("\n[209-company Excel check]")
    files_209 = [p for p in refs if "209" in p.name or ("반도체" in p.name and p.suffix.lower() in {".xlsx", ".xls"})]
    if files_209:
        for p in files_209:
            print(f"- FOUND: {rel(p)}")
    else:
        print("- NOT FOUND in current repo tree.")
        print("- 현재 repo에는 30개 후보군용 valuation_credit_ml_overlay_candidate.csv 계열만 있는지 확인하세요.")
        print("- 과거에 말한 209개 반도체 기업 엑셀은 별도 원본 파일로 다시 넣어야 할 가능성이 큽니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

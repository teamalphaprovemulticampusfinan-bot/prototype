from __future__ import annotations

import argparse
import re
from pathlib import Path

COMPANY_MAP = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}

EXPECTED = {
    1: "Excel-frame based technology position",
    2: "Tech-to-Value Bridge",
    3: "KIPRIS/IP quantitative signals",
    4: "Patent KMeans clustering",
    5: "Focal-company cosine similarity",
    6: "Reference-universe company-level KMeans peer group",
    7: "UMAP 2D tech peer map",
    8: "Peer-percentile adjusted Tech-to-Value Bridge",
    9: "Tech/IP Strength Index + NMF Topic Modeling",
    10: "Technology Differentiation Score",
    11: "Patent Momentum Score + Tech-to-Value Evidence Confidence",
}

JUNK_PATTERNS = [
    "원문 키워드 정제 필요",
    "필름 이를",
    "상기 반도체",
    "제1 반도체",
    "하기 화학식",
    "형성하는 단계",
    "발명의 기술적",
]

QUALITY_TERMS = [
    "별도 판정 미생성",
    "별도 Auditor 보수 점수 미생성",
    "산출물 원문 확인 필요",
]


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _company_name(slug: str, company: str | None) -> str:
    return company or COMPANY_MAP.get(slug, slug)


def _find_appendix(root: Path, slug: str, company: str | None) -> Path:
    name = _company_name(slug, company)
    candidates = [
        root / "data" / "반도체" / name / "tech" / f"{slug}_tech_full_appendix.md",
        root / "data" / "반도체" / slug / "tech" / f"{slug}_tech_full_appendix.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", default=None)
    parser.add_argument("--build", action="store_true", help="Rebuild appendix before checking")
    args = parser.parse_args()

    root = _root()
    slug = args.company_dir
    if args.build:
        import sys
        sys.path.insert(0, str(root / "src"))
        from tech_agent.tech_full_report import build_tech_full_report
        build_tech_full_report(slug, company=args.company, save=True)

    path = _find_appendix(root, slug, args.company)
    if not path.exists():
        print(f"[MISS] appendix not found: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    print(f"[OK] generated: {path.relative_to(root)}")
    missing = []
    for step, title in EXPECTED.items():
        if re.search(rf"Step\s+{step}\b.*{re.escape(title)}", text, flags=re.I):
            print(f"[OK] Step {step}: {title}")
        else:
            print(f"[MISS] Step {step}: {title}")
            missing.append(step)

    confirm_count = text.count("확인 제한")
    abs_count = len(re.findall(r"[A-Za-z]:\\", text))
    print(f"[INFO] 확인 제한 count: {confirm_count}")
    print(f"[INFO] absolute project path count: {abs_count}")

    if confirm_count > 10:
        print("[WARN] 확인 제한이 많습니다. Step 산출물 JSON/MD가 data/반도체/<회사명>/tech에 있는지 확인하세요.")
    if abs_count > 0:
        print("[WARN] 절대경로가 남아 있습니다. portable path 정규화가 필요합니다.")

    junk_found = [pat for pat in JUNK_PATTERNS if pat in text]
    quality_terms = [pat for pat in QUALITY_TERMS if pat in text]
    if junk_found:
        print("[WARN] 정제 필요 키워드/문장 파편 발견:", ", ".join(junk_found))
    else:
        print("[OK] obvious junk keyword patterns not found")
    if quality_terms:
        print("[INFO] 보수적 fallback 표현 존재:", ", ".join(quality_terms))

    return 1 if missing or junk_found else 0


if __name__ == "__main__":
    raise SystemExit(main())

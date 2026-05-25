from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-name", default="네패스")
    parser.add_argument("--company-slug", default="nepes")
    args = parser.parse_args()

    tech = Path("data") / args.field / args.company_name / "tech"

    summary_json = tech / "tech_chair_summary.json"
    feature_json = tech / "tech_ip_citation_features.json"
    company_md = tech / f"{args.company_slug}_tech_chair_summary.md"

    print(f"[CHECK] feature exists: {feature_json.exists()} {feature_json}")
    print(f"[CHECK] tech_chair_summary.json exists: {summary_json.exists()} {summary_json}")

    if not summary_json.exists():
        print("[FAIL] tech_chair_summary.json이 없습니다. 먼저 python main.py tech ... 를 실행하세요.")
        return 1

    data = read_json(summary_json)

    print("[CHECK] ip_citation_feature_merge_status:", data.get("ip_citation_feature_merge_status"))

    selected = data.get("ip_citation_features") or {}
    print("[CHECK] top-level ip_citation_features keys:", sorted(selected.keys()))

    selected_ml = data.get("selected_ml") or {}
    ip_cit = selected_ml.get("ip_citation_impact") or {}

    print(
        "[CHECK] selected_ml.ip_citation_impact.ip_citation_impact_score_estimated:",
        ip_cit.get("ip_citation_impact_score_estimated"),
    )
    print(
        "[CHECK] selected_ml.ip_citation_impact.bridge_signal:",
        ip_cit.get("bridge_signal"),
    )
    print(
        "[CHECK] selected_ml.ip_citation_impact.bridge_adjustment_points:",
        ip_cit.get("bridge_adjustment_points"),
    )

    print(f"[CHECK] {args.company_slug}_tech_chair_summary.md exists: {company_md.exists()} {company_md}")

    if company_md.exists():
        text = company_md.read_text(encoding="utf-8")
        checks = [
            "IP Citation Impact",
            "IP Citation Bridge Signal",
            "Forward Citations",
            "External Forward Citations",
            "Top Cited Patents",
        ]
        for item in checks:
            print(f"[CHECK] md contains '{item}':", item in text)

    if data.get("ip_citation_feature_merge_status") != "MERGED":
        print("[FAIL] IP Citation feature가 아직 자동 병합되지 않았습니다.")
        return 1

    print("[DONE] IP Citation 자동 병합 검증 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

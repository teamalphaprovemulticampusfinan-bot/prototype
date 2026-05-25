from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tech", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--company-name", required=True)
    args = parser.parse_args()

    tech = Path(args.tech)
    slug = args.slug
    company_name = args.company_name

    summary = tech / "tech_chair_summary.json"
    comp = tech / "tech_ip_evidence_composite.json"
    adjusted = tech / "tech_to_value_bridge_ip_evidence_adjusted.json"
    md = tech / f"{slug}_tech_chair_summary.md"

    print("=" * 80)
    print(f"[IP Evidence Bridge 검증] {company_name} / {slug}")
    print("=" * 80)

    print("[CHECK] summary exists:", summary.exists(), summary)
    print("[CHECK] composite exists:", comp.exists(), comp)
    print("[CHECK] adjusted bridge packet exists:", adjusted.exists(), adjusted)
    print("[CHECK] md exists:", md.exists(), md)

    ok = True

    if not summary.exists():
        ok = False
    if not comp.exists():
        ok = False
    if not adjusted.exists():
        ok = False
    if not md.exists():
        ok = False

    if summary.exists():
        s = read_json(summary)
        tv = s.get("tech_to_value", {}) or {}
        selected = s.get("selected_ml", {}) or {}

        print("[CHECK] ip_evidence_bridge_adjustment_status:", s.get("ip_evidence_bridge_adjustment_status"))
        print("[CHECK] ip_evidence_composite_merge_status:", s.get("ip_evidence_composite_merge_status"))
        print("[CHECK] tech_to_value.ip_evidence_composite_score:", tv.get("ip_evidence_composite_score"))
        print("[CHECK] tech_to_value.ip_evidence_composite_bridge_signal:", tv.get("ip_evidence_composite_bridge_signal"))
        print("[CHECK] tech_to_value.ip_evidence_composite_adjustment_points:", tv.get("ip_evidence_composite_adjustment_points"))
        print("[CHECK] tech_to_value.peer_adjusted_bridge_score_before_ip_evidence:", tv.get("peer_adjusted_bridge_score_before_ip_evidence"))
        print("[CHECK] tech_to_value.final_bridge_score_after_ip_evidence:", tv.get("final_bridge_score_after_ip_evidence"))
        print("[CHECK] tech_to_value.peer_adjusted_bridge_score:", tv.get("peer_adjusted_bridge_score"))
        print("[CHECK] selected_ml.ip_evidence_composite exists:", "ip_evidence_composite" in selected)
        print("[CHECK] selected_ml.ip_evidence_composite_score:", selected.get("ip_evidence_composite_score"))
        print("[CHECK] selected_ml.ip_evidence_bridge_signal:", selected.get("ip_evidence_bridge_signal"))
        print("[CHECK] selected_ml.ip_evidence_bridge_adjustment_points:", selected.get("ip_evidence_bridge_adjustment_points"))
        print("[CHECK] selected_ml.final_bridge_score_after_ip_evidence:", selected.get("final_bridge_score_after_ip_evidence"))

        if s.get("ip_evidence_bridge_adjustment_status") != "APPLIED":
            ok = False
        if s.get("ip_evidence_composite_merge_status") != "MERGED":
            ok = False
        if "ip_evidence_composite" not in selected:
            ok = False

    if md.exists():
        text = md.read_text(encoding="utf-8", errors="replace")
        print("[CHECK] md contains 'IP Evidence Composite':", "IP Evidence Composite" in text)
        print("[CHECK] md contains 'final_bridge_score_after_ip_evidence':", "final_bridge_score_after_ip_evidence" in text)

        if "IP Evidence Composite" not in text:
            ok = False
        if "final_bridge_score_after_ip_evidence" not in text:
            ok = False

    print()
    print("[RESULT] OK:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

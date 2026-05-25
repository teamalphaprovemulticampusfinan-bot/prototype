from __future__ import annotations

import json
from pathlib import Path

from src.tech_agent.ip_evidence_composite_merge import merge_ip_evidence_composite_saved_files


def main() -> int:
    result = merge_ip_evidence_composite_saved_files(
        field="반도체",
        company_name="네패스",
        company_slug="nepes",
    )

    print("[MERGE RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    tech_dir = Path("data") / "반도체" / "네패스" / "tech"
    summary_json = tech_dir / "tech_chair_summary.json"
    summary_md = tech_dir / "nepes_tech_chair_summary.md"

    print()
    print("[CHECK] tech_chair_summary.json exists:", summary_json.exists(), summary_json)

    if summary_json.exists():
        data = json.loads(summary_json.read_text(encoding="utf-8"))
        print("[CHECK] ip_evidence_composite_merge_status:", data.get("ip_evidence_composite_merge_status"))
        print("[CHECK] top-level ip_evidence_composite exists:", "ip_evidence_composite" in data)

        selected_ml = data.get("selected_ml", {}) or {}
        ip_comp = selected_ml.get("ip_evidence_composite", {}) or {}

        print("[CHECK] selected_ml.ip_evidence_composite exists:", bool(ip_comp))
        print("[CHECK] selected_ml.ip_evidence_composite_score:", selected_ml.get("ip_evidence_composite_score"))
        print("[CHECK] selected_ml.ip_evidence_bridge_signal:", selected_ml.get("ip_evidence_bridge_signal"))
        print("[CHECK] selected_ml.ip_evidence_bridge_adjustment_points:", selected_ml.get("ip_evidence_bridge_adjustment_points"))

    print("[CHECK] nepes_tech_chair_summary.md exists:", summary_md.exists(), summary_md)

    if summary_md.exists():
        text = summary_md.read_text(encoding="utf-8", errors="replace")
        checks = [
            "IP Evidence Composite Score",
            "IP_EVIDENCE_NEUTRAL",
            "등록·존속 안정성",
            "청구항 방어 범위",
            "인용 기반 기술 영향력",
            "해외 패밀리 기반 글로벌 확장성",
        ]
        for c in checks:
            print(f"[CHECK] md contains '{c}':", c in text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

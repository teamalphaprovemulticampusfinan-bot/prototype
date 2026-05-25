from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import company_agent_dir  # noqa: E402

DEFAULTS = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}

REQUIRED_ALTERNATIVES = {
    "tech_intake_manifest.json": ["tech_intake_manifest.json"],
    "tech_template_inventory.json": ["tech_template_inventory.json"],
    "tech_excel_frame_full.json": ["tech_excel_frame_full.json"],
    "tech_excel_frame_summary.md": ["tech_excel_frame_summary.md"],
    "quantified_metrics.csv": ["quantified_metrics.csv"],
    "quanified_metrix.csv": ["quanified_metrix.csv"],
    "tech_ip_legal_features.json": ["tech_ip_legal_features.json"],
    "tech_ip_claim_features.json": ["tech_ip_claim_features.json"],
    "tech_ip_citation_features.json": ["tech_ip_citation_features.json"],
    "tech_ip_family_features.json": ["tech_ip_family_features.json"],
    "tech_ip_evidence_composite.json": ["tech_ip_evidence_composite.json"],
    "tech_patent_semantic_features.json": ["tech_patent_semantic_features.json", "{slug}_tech_patent_semantic_features.json"],
    "tech_chair_summary.json": ["tech_chair_summary.json"],
    "tech_chair_summary.md": ["tech_chair_summary.md", "{slug}_tech_chair_summary.md"],
    "tech_to_value_bridge_ip_evidence_adjusted.json": ["tech_to_value_bridge_ip_evidence_adjusted.json"],
}


def _exists_any(tech: Path, slug: str, names: list[str]) -> tuple[bool, str]:
    for name in names:
        n = name.format(slug=slug)
        if (tech / n).exists():
            return True, n
    return False, ""


def check(slug: str, company: str) -> bool:
    tech = company_agent_dir(slug, "tech", create=False)
    print("=" * 90)
    print(f"[CHECK] {company} / {slug}")
    print("=" * 90)
    print("tech_dir:", tech)
    ok = True
    for label, alternatives in REQUIRED_ALTERNATIVES.items():
        exists, used = _exists_any(tech, slug, alternatives)
        print(f"[{'OK' if exists else 'MISS'}] {label}" + (f" -> {used}" if used and used != label else ""))
        if not exists:
            ok = False

    manifest = tech / "tech_intake_manifest.json"
    if manifest.exists():
        try:
            obj = json.loads(manifest.read_text(encoding="utf-8"))
            print("manifest_status:", obj.get("status"))
            print("source_csv:", obj.get("source_csv"))
            print("kipris_plus_network_enabled:", obj.get("kipris_plus_network_enabled"))
            print("excel_frame_status:", obj.get("excel_frame_status"))
            print("excel_frame_item_count:", obj.get("excel_frame_item_count"))
            print("excel_frame_numeric_signal_count:", obj.get("excel_frame_numeric_signal_count"))
            qpath = ((obj.get("excel_frame_output_paths") or {}).get("quantified_metrics_csv"))
            if qpath:
                print("quantified_metrics_csv:", qpath)
            missing = ((obj.get("artifacts") or {}).get("required_missing") or [])
            if missing:
                print("manifest_required_missing:", missing)
        except Exception as exc:
            print("manifest_read_error:", exc)
            ok = False

    comp = tech / "tech_ip_evidence_composite.json"
    if comp.exists():
        try:
            obj = json.loads(comp.read_text(encoding="utf-8"))
            print("ip_evidence_score:", obj.get("ip_evidence_composite_score"))
            print("ip_evidence_signal:", obj.get("bridge_signal"))
        except Exception as exc:
            print("composite_read_error:", exc)
            ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company-dir", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all or not args.company_dir:
        overall = True
        for slug, company in DEFAULTS.items():
            overall = check(slug, company) and overall
        return 0 if overall else 1

    return 0 if check(args.company_dir, args.company or DEFAULTS.get(args.company_dir, args.company_dir)) else 1


if __name__ == "__main__":
    raise SystemExit(main())

from pathlib import Path
import json
import sys

TECH = Path("data/반도체/네패스/tech")
SUMMARY_JSON = TECH / "tech_chair_summary.json"
SUMMARY_MD = TECH / "nepes_tech_chair_summary.md"
BRIDGE_JSON = TECH / "tech_to_value_bridge_ip_evidence_adjusted.json"

print("=" * 80)
print("[IP Evidence Composite → Tech-to-Value Bridge 검증]")
print("=" * 80)

print(f"[CHECK] summary json exists: {SUMMARY_JSON.exists()} {SUMMARY_JSON}")
if not SUMMARY_JSON.exists():
    sys.exit(1)

summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))

tv = summary.get("tech_to_value", {}) or {}
selected_ml = summary.get("selected_ml", {}) or {}

checks = {
    "ip_evidence_bridge_adjustment_status": summary.get("ip_evidence_bridge_adjustment_status"),
    "ip_evidence_composite_merge_status": summary.get("ip_evidence_composite_merge_status"),
    "tech_to_value.ip_evidence_composite_score": tv.get("ip_evidence_composite_score"),
    "tech_to_value.ip_evidence_composite_bridge_signal": tv.get("ip_evidence_composite_bridge_signal"),
    "tech_to_value.ip_evidence_composite_adjustment_points": tv.get("ip_evidence_composite_adjustment_points"),
    "tech_to_value.peer_adjusted_bridge_score_before_ip_evidence": tv.get("peer_adjusted_bridge_score_before_ip_evidence"),
    "tech_to_value.final_bridge_score_after_ip_evidence": tv.get("final_bridge_score_after_ip_evidence"),
    "tech_to_value.peer_adjusted_bridge_score": tv.get("peer_adjusted_bridge_score"),
    "selected_ml.ip_evidence_composite exists": isinstance(selected_ml.get("ip_evidence_composite"), dict),
    "selected_ml.ip_evidence_composite_score": selected_ml.get("ip_evidence_composite_score"),
    "selected_ml.ip_evidence_bridge_signal": selected_ml.get("ip_evidence_bridge_signal"),
    "selected_ml.ip_evidence_bridge_adjustment_points": selected_ml.get("ip_evidence_bridge_adjustment_points"),
    "selected_ml.final_bridge_score_after_ip_evidence": selected_ml.get("final_bridge_score_after_ip_evidence"),
}

for k, v in checks.items():
    print(f"[CHECK] {k}: {v}")

print()
print(f"[CHECK] adjusted bridge packet exists: {BRIDGE_JSON.exists()} {BRIDGE_JSON}")

print()
print(f"[CHECK] summary md exists: {SUMMARY_MD.exists()} {SUMMARY_MD}")
if SUMMARY_MD.exists():
    md = SUMMARY_MD.read_text(encoding="utf-8", errors="replace")
    md_checks = {
        "md contains 'IP Evidence Composite → Tech-to-Value Bridge 반영'": "IP Evidence Composite → Tech-to-Value Bridge 반영" in md,
        "md contains 'IP Evidence Composite Score'": "IP Evidence Composite Score" in md,
        "md contains 'IP_EVIDENCE_NEUTRAL'": "IP_EVIDENCE_NEUTRAL" in md,
        "md contains 'final_bridge_score_after_ip_evidence'": "final_bridge_score_after_ip_evidence" in md,
    }
    for k, v in md_checks.items():
        print(f"[CHECK] {k}: {v}")

print()
expected_ok = (
    summary.get("ip_evidence_bridge_adjustment_status") == "APPLIED"
    and summary.get("ip_evidence_composite_merge_status") == "MERGED"
    and tv.get("ip_evidence_composite_score") is not None
    and tv.get("ip_evidence_composite_bridge_signal") is not None
    and tv.get("ip_evidence_composite_adjustment_points") is not None
    and tv.get("final_bridge_score_after_ip_evidence") is not None
)

print(f"[RESULT] OK: {expected_ok}")

if not expected_ok:
    sys.exit(2)

from pathlib import Path
import json

TECH = Path("data/반도체/네패스/tech")
summary_path = TECH / "tech_chair_summary.json"
md_path = TECH / "nepes_tech_chair_summary.md"

print("[CHECK] tech_chair_summary.json exists:", summary_path.exists(), summary_path)

if not summary_path.exists():
    raise SystemExit(1)

summary = json.loads(summary_path.read_text(encoding="utf-8"))

print("[CHECK] ip_family_feature_merge_status:", summary.get("ip_family_feature_merge_status"))

family = summary.get("ip_family_features", {})
print("[CHECK] top-level ip_family_features keys:", sorted(family.keys()) if isinstance(family, dict) else type(family))

selected_ml = summary.get("selected_ml", {})
ip_global = selected_ml.get("ip_global_extension", {}) if isinstance(selected_ml, dict) else {}

print("[CHECK] selected_ml.ip_global_extension.global_extension_score:", ip_global.get("global_extension_score"))
print("[CHECK] selected_ml.ip_global_extension.bridge_signal:", ip_global.get("bridge_signal"))
print("[CHECK] selected_ml.ip_global_extension.bridge_adjustment_points:", ip_global.get("bridge_adjustment_points"))
print("[CHECK] selected_ml.ip_global_extension.overseas_family_patent_rate:", ip_global.get("overseas_family_patent_rate"))
print("[CHECK] selected_ml.ip_global_extension.detected_overseas_regions:", ip_global.get("detected_overseas_regions"))

print("[CHECK] nepes_tech_chair_summary.md exists:", md_path.exists(), md_path)

if md_path.exists():
    text = md_path.read_text(encoding="utf-8", errors="replace")
    for pattern in [
        "IP Family / Global Extension",
        "IP Global Extension Score",
        "IP Global Bridge Signal",
        "해외 패밀리 보유율",
        "PCT/WO",
        "detected_overseas_regions",
    ]:
        print(f"[CHECK] md contains '{pattern}':", pattern in text)

from __future__ import annotations

import json
from pathlib import Path

TECH = Path("data") / "반도체" / "네패스" / "tech"

summary_path = TECH / "tech_chair_summary.json"
feature_path = TECH / "nepes_kipris_tech_ml_features.json"

if not summary_path.exists():
    raise FileNotFoundError(f"tech_chair_summary.json 없음: {summary_path}")

if not feature_path.exists():
    raise FileNotFoundError(f"KIPRIS feature json 없음: {feature_path}")

summary = json.loads(summary_path.read_text(encoding="utf-8"))
features = json.loads(feature_path.read_text(encoding="utf-8"))

scores = features.get("scores") or {}
adjustment = features.get("tech_to_value_bridge_adjustment") or {}

summary["kipris_tech_ml_features"] = features
summary["kipris_tech_ml_score"] = scores.get("kipris_tech_ml_score")
summary["legal_stability_score_estimated"] = scores.get("legal_stability_score_estimated")
summary["portfolio_momentum_score"] = scores.get("portfolio_momentum_score")
summary["ip_technology_fit_score"] = scores.get("ip_technology_fit_score")
summary["bridge_adjustment_points"] = adjustment.get("bridge_adjustment_points")
summary["bridge_signal"] = adjustment.get("bridge_signal")
summary["kipris_bridge_usage_rule"] = adjustment.get("usage_rule")

summary_path.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("[DONE] tech_chair_summary.json에 KIPRIS Tech ML feature 반영 완료")
print(f"- kipris_tech_ml_score: {summary.get('kipris_tech_ml_score')}")
print(f"- legal_stability_score_estimated: {summary.get('legal_stability_score_estimated')}")
print(f"- bridge_adjustment_points: {summary.get('bridge_adjustment_points')}")
print(f"- bridge_signal: {summary.get('bridge_signal')}")

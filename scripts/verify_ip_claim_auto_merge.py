from __future__ import annotations

import json
from pathlib import Path

TECH_DIR = Path("data") / "반도체" / "네패스" / "tech"
SUMMARY_JSON = TECH_DIR / "tech_chair_summary.json"
SUMMARY_MD = TECH_DIR / "nepes_tech_chair_summary.md"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    data = read_json(SUMMARY_JSON)
    print(f"[CHECK] tech_chair_summary.json exists: {SUMMARY_JSON.exists()} {SUMMARY_JSON}")

    status = data.get("ip_claim_feature_merge_status")
    claim = data.get("ip_claim_features") or {}
    selected_claim = ((data.get("selected_ml") or {}).get("ip_claim_scope") or {})

    print(f"[CHECK] ip_claim_feature_merge_status: {status}")
    print(f"[CHECK] top-level ip_claim_features keys: {sorted(claim.keys()) if isinstance(claim, dict) else []}")
    print(f"[CHECK] selected_ml.ip_claim_scope.claim_defense_score_estimated: {selected_claim.get('claim_defense_score_estimated')}")
    print(f"[CHECK] selected_ml.ip_claim_scope.bridge_signal: {selected_claim.get('bridge_signal')}")
    print(f"[CHECK] selected_ml.ip_claim_scope.bridge_adjustment_points: {selected_claim.get('bridge_adjustment_points')}")
    print(f"[CHECK] selected_ml.ip_claim_scope.claim_count: {selected_claim.get('claim_count')}")
    print(f"[CHECK] selected_ml.ip_claim_scope.independent_claim_count_estimated: {selected_claim.get('independent_claim_count_estimated')}")

    md_text = SUMMARY_MD.read_text(encoding="utf-8") if SUMMARY_MD.exists() else ""
    print(f"[CHECK] nepes_tech_chair_summary.md exists: {SUMMARY_MD.exists()} {SUMMARY_MD}")
    for needle in [
        "IP Claim Defense",
        "IP Claim Bridge Signal",
        "청구항 수집 커버리지",
        "수집 청구항 / 독립항",
        "청구항 방어력 점수",
    ]:
        print(f"[CHECK] md contains '{needle}': {needle in md_text}")

    ok = (
        SUMMARY_JSON.exists()
        and status == "MERGED"
        and bool(claim)
        and bool(selected_claim)
        and "IP Claim Defense" in md_text
        and "청구항 방어력 점수" in md_text
    )
    print("[RESULT]", "OK" if ok else "CHECK_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import shutil
import re


FIELD = "반도체"
COMPANY_NAME = "네패스"
COMPANY_SLUG = "nepes"

TECH_DIR = Path("data") / FIELD / COMPANY_NAME / "tech"

FEATURE_JSON = TECH_DIR / "tech_ip_legal_features.json"

JSON_TARGETS = [
    TECH_DIR / "tech_chair_summary.json",
    TECH_DIR / "tech_full_appendix.json",
    TECH_DIR / "tech.json",
    TECH_DIR / f"{COMPANY_SLUG}_tech.json",
    TECH_DIR / f"{COMPANY_SLUG}_tech_agent_packet.json",
]

MD_TARGETS = [
    TECH_DIR / f"{COMPANY_SLUG}_tech_full_appendix.md",
    TECH_DIR / f"{COMPANY_SLUG}_tech_high_quality_report.md",
    TECH_DIR / f"{COMPANY_SLUG}_tech_chair_summary.md",
]

MARKER_START = "<!-- KIPRIS_IP_LEGAL_FEATURES_START -->"
MARKER_END = "<!-- KIPRIS_IP_LEGAL_FEATURES_END -->"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def backup_once(path: Path) -> None:
    if not path.exists():
        return

    backup = path.with_suffix(path.suffix + ".bak_ip_legal")
    if not backup.exists():
        shutil.copy2(path, backup)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def pct(value: Any) -> str:
    return f"{as_float(value) * 100:.2f}%"


def get_feature_summary(feature: dict[str, Any]) -> dict[str, Any]:
    core_counts = feature.get("core_counts") or {}
    core_rates = feature.get("core_rates") or {}
    coverage = feature.get("data_coverage") or {}
    scores = feature.get("scores") or {}
    bridge = feature.get("tech_to_value_bridge_adjustment") or {}
    interpretation = feature.get("interpretation") or {}

    return {
        "feature_type": feature.get("feature_type") or "kipris_ip_legal_stability_features",
        "source_csv": feature.get("source_csv"),
        "company_slug": feature.get("company_slug") or COMPANY_SLUG,
        "company_name": feature.get("company_name") or COMPANY_NAME,
        "core_counts": {
            "total_patents": core_counts.get("total_patents"),
            "registered_patents_estimated": core_counts.get("registered_patents_estimated"),
            "alive_patents_estimated": core_counts.get("alive_patents_estimated"),
            "negative_disposal_patents_estimated": core_counts.get("negative_disposal_patents_estimated"),
            "recent_5y_application_patents": core_counts.get("recent_5y_application_patents"),
        },
        "core_rates": {
            "registration_rate_estimated": core_rates.get("registration_rate_estimated"),
            "alive_rate_among_registered_estimated": core_rates.get("alive_rate_among_registered_estimated"),
            "negative_disposal_rate_estimated": core_rates.get("negative_disposal_rate_estimated"),
            "recent_5y_application_rate": core_rates.get("recent_5y_application_rate"),
        },
        "data_coverage": {
            "right_holder_coverage": coverage.get("right_holder_coverage"),
            "right_transfer_history_coverage": coverage.get("right_transfer_history_coverage"),
            "fee_payment_status_coverage": coverage.get("fee_payment_status_coverage"),
            "abstract_coverage": coverage.get("abstract_coverage"),
            "drawing_coverage": coverage.get("drawing_coverage"),
        },
        "scores": {
            "legal_stability_score_estimated": scores.get("legal_stability_score_estimated"),
        },
        "tech_to_value_bridge_adjustment": {
            "bridge_adjustment_points": bridge.get("bridge_adjustment_points"),
            "bridge_signal": bridge.get("bridge_signal"),
            "bridge_interpretation": bridge.get("bridge_interpretation"),
        },
        "interpretation": {
            "summary": interpretation.get("summary"),
            "caution": interpretation.get("caution"),
            "bridge_usage_rule": interpretation.get("bridge_usage_rule"),
        },
        "_source_file": str(FEATURE_JSON),
    }


def append_unique_text_list(data: dict[str, Any], key: str, text: str, limit: int | None = None) -> None:
    values = data.get(key)

    if not isinstance(values, list):
        values = []

    if text not in values:
        values.append(text)

    if limit is not None:
        values = values[:limit]

    data[key] = values


def append_unique_dict_list(
    data: dict[str, Any],
    key: str,
    item: dict[str, Any],
    unique_key: str,
) -> None:
    values = data.get(key)

    if not isinstance(values, list):
        values = []

    new_id = item.get(unique_key)

    exists = False
    for value in values:
        if isinstance(value, dict) and value.get(unique_key) == new_id:
            exists = True
            break

    if not exists:
        values.append(item)

    data[key] = values


def merge_json_target(path: Path, feature_summary: dict[str, Any]) -> bool:
    if not path.exists():
        print(f"[SKIP] JSON 없음: {path}")
        return False

    backup_once(path)

    data = read_json(path)

    if not isinstance(data, dict):
        print(f"[SKIP] JSON root가 dict가 아님: {path}")
        return False

    score = feature_summary["scores"]["legal_stability_score_estimated"]
    bridge = feature_summary["tech_to_value_bridge_adjustment"]
    rates = feature_summary["core_rates"]
    counts = feature_summary["core_counts"]

    data["tech_ip_legal_features"] = feature_summary

    # Chair나 Auditor가 바로 읽기 쉽게 핵심 값은 top-level에도 둔다.
    data["legal_stability_score_estimated"] = score
    data["ip_legal_bridge_adjustment_points"] = bridge.get("bridge_adjustment_points")
    data["ip_legal_bridge_signal"] = bridge.get("bridge_signal")

    data.setdefault("tech_to_value_bridge_adjustments", {})
    if isinstance(data["tech_to_value_bridge_adjustments"], dict):
        data["tech_to_value_bridge_adjustments"]["ip_legal_stability"] = bridge

    thesis = (
        f"KIPRIS 기본 서지정보 {counts.get('total_patents')}건 기준 "
        f"권리 안정성 점수는 {score}점이며, "
        f"Tech-to-Value Bridge에는 {bridge.get('bridge_adjustment_points')}점 "
        f"({bridge.get('bridge_signal')})으로 보수 반영한다."
    )

    risk = (
        "right_transfer_history와 fee_payment_status는 현재 원천 CSV에 없어 "
        "권리이전·연차료 납부 기반의 정밀 권리 안정성 검증은 KIPRIS Plus 추가 수집 후 보완해야 한다."
    )

    append_unique_text_list(data, "key_thesis", thesis, limit=12)
    append_unique_text_list(data, "key_risks", risk, limit=12)

    evidence_item = {
        "evidence_id": "tech.ip_legal.ev.001",
        "source_type": "kipris_bibliographic_normalized_csv",
        "source": str(FEATURE_JSON),
        "metric": "legal_stability_score_estimated",
        "value": score,
        "unit": "score",
        "period": "KIPRIS normalized dataset",
        "snippet": (
            f"{COMPANY_NAME} KIPRIS 기본 서지정보 기준 등록률 {pct(rates.get('registration_rate_estimated'))}, "
            f"등록특허 내 존속률 {pct(rates.get('alive_rate_among_registered_estimated'))}, "
            f"부정처분 비중 {pct(rates.get('negative_disposal_rate_estimated'))}, "
            f"권리 안정성 점수 {score}점입니다."
        ),
    }

    claim_item = {
        "claim_id": "tech.ip_legal.cl.001",
        "text": (
            f"{COMPANY_NAME}의 KIPRIS 기본 서지정보 기반 권리 안정성 점수는 {score}점이며, "
            f"Tech-to-Value Bridge에 {bridge.get('bridge_adjustment_points')}점으로 반영됩니다."
        ),
        "evidence_ids": ["tech.ip_legal.ev.001"],
        "audit_safe": True,
    }

    append_unique_dict_list(data, "evidences", evidence_item, "evidence_id")
    append_unique_dict_list(data, "claims", claim_item, "claim_id")

    write_json(path, data)
    print(f"[PATCH] JSON 병합 완료: {path}")
    return True


def render_markdown_block(feature_summary: dict[str, Any]) -> str:
    counts = feature_summary["core_counts"]
    rates = feature_summary["core_rates"]
    coverage = feature_summary["data_coverage"]
    score = feature_summary["scores"]["legal_stability_score_estimated"]
    bridge = feature_summary["tech_to_value_bridge_adjustment"]

    return f"""{MARKER_START}

## 12) KIPRIS IP Legal Stability Features

### 12-1. 권리 안정성 핵심 지표

- 전체 특허 수: {counts.get("total_patents")}건
- 등록 이력 특허 수: {counts.get("registered_patents_estimated")}건
- 존속 가능 등록특허 수: {counts.get("alive_patents_estimated")}건
- 소멸·거절·취하 등 부정처분 추정 특허 수: {counts.get("negative_disposal_patents_estimated")}건
- 최근 5년 출원 특허 수: {counts.get("recent_5y_application_patents")}건

### 12-2. 핵심 비율

- 등록률: {pct(rates.get("registration_rate_estimated"))}
- 등록특허 내 존속률: {pct(rates.get("alive_rate_among_registered_estimated"))}
- 소멸·거절·취하 비중: {pct(rates.get("negative_disposal_rate_estimated"))}
- 최근 5년 출원 비중: {pct(rates.get("recent_5y_application_rate"))}

### 12-3. 데이터 반영률

- 권리자 정보 반영률: {pct(coverage.get("right_holder_coverage"))}
- 권리이전 이력 반영률: {pct(coverage.get("right_transfer_history_coverage"))}
- 연차료 납부상태 반영률: {pct(coverage.get("fee_payment_status_coverage"))}
- 초록 반영률: {pct(coverage.get("abstract_coverage"))}
- 도면 반영률: {pct(coverage.get("drawing_coverage"))}

### 12-4. Tech-to-Value Bridge 반영

- legal_stability_score_estimated: {score}
- bridge_adjustment_points: {bridge.get("bridge_adjustment_points")}
- bridge_signal: {bridge.get("bridge_signal")}
- 해석: {bridge.get("bridge_interpretation")}

> 주의: right_transfer_history와 fee_payment_status는 현재 원천 CSV에 없어 0%로 처리되었습니다. 따라서 현재 점수는 KIPRIS 기본 서지정보 기반 보수 추정값이며, 권리이전·연차료 납부 상태는 KIPRIS Plus 추가 수집 후 보완해야 합니다.

{MARKER_END}
"""


def merge_markdown_target(path: Path, feature_summary: dict[str, Any]) -> bool:
    if not path.exists():
        print(f"[SKIP] MD 없음: {path}")
        return False

    backup_once(path)

    text = path.read_text(encoding="utf-8")
    block = render_markdown_block(feature_summary)

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        flags=re.DOTALL,
    )

    if pattern.search(text):
        text = pattern.sub(block, text)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"

    path.write_text(text, encoding="utf-8")
    print(f"[PATCH] MD 병합 완료: {path}")
    return True


def main() -> int:
    if not FEATURE_JSON.exists():
        print(f"[ERROR] feature JSON이 없습니다: {FEATURE_JSON}")
        print("먼저 scripts\\build_tech_ip_legal_features_nepes.py 를 실행하세요.")
        return 1

    feature = read_json(FEATURE_JSON)
    feature_summary = get_feature_summary(feature)

    print("=" * 80)
    print("[Tech IP Legal Features → Tech Agent 산출물 병합]")
    print(f"- feature: {FEATURE_JSON}")
    print(f"- score: {feature_summary['scores']['legal_stability_score_estimated']}")
    print(f"- bridge: {feature_summary['tech_to_value_bridge_adjustment'].get('bridge_signal')}")
    print("=" * 80)

    json_count = 0
    md_count = 0

    for path in JSON_TARGETS:
        if merge_json_target(path, feature_summary):
            json_count += 1

    for path in MD_TARGETS:
        if merge_markdown_target(path, feature_summary):
            md_count += 1

    print()
    print("[DONE]")
    print(f"- JSON patched: {json_count}")
    print(f"- MD patched: {md_count}")
    print("- backup suffix: .bak_ip_legal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

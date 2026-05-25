from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _round2(value: float) -> float:
    return round(float(value), 2)


def _clamp_score(value: float, min_score: float = 0.0, max_score: float = 100.0) -> float:
    return _round2(max(min_score, min(max_score, float(value))))


def _rel_project_path(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""

    raw = raw.replace("\\", "/")

    try:
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass

    for prefix in ["data", "workspace", "src"]:
        m = re.search(rf"(?:^|.*?){prefix}[\/].*$", raw)
        if m:
            found = m.group(0)
            idx = found.find(prefix + "/")
            if idx >= 0:
                return found[idx:].replace("\\", "/")

    return raw.replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}
    except Exception:
        return {}
    return {}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _score_file_match(path: Path, company_slug: str = "", company_name: str = "") -> int:
    text = str(path).replace("\\", "/").lower()
    score = 0

    if company_slug and company_slug.lower() in text:
        score += 50

    if company_name and company_name.lower() in text:
        score += 50

    if path.name == "tech_ip_evidence_composite.json":
        score += 20

    if company_slug and path.name == f"{company_slug}_tech_ip_evidence_composite.json":
        score += 30

    if "/tech/" in text:
        score += 10

    return score


def resolve_tech_dir(
    field: str = "반도체",
    company_name: str = "",
    company_slug: str = "",
    tech_dir: str | Path | None = None,
) -> Optional[Path]:
    candidates: list[Path] = []

    if tech_dir:
        p = Path(tech_dir)
        candidates.append(p if p.name == "tech" else p / "tech")

    if field and company_name:
        candidates.append(ROOT / "data" / field / company_name / "tech")
        candidates.append(Path("data") / field / company_name / "tech")

    if company_name:
        data_root = ROOT / "data"
        if data_root.exists():
            candidates.extend(data_root.glob(f"*/{company_name}/tech"))

    if company_slug:
        data_root = ROOT / "data"
        if data_root.exists():
            for p in data_root.glob("*/**/tech"):
                if (p / "tech_ip_evidence_composite.json").exists():
                    candidates.append(p)
                if (p / f"{company_slug}_tech_ip_evidence_composite.json").exists():
                    candidates.append(p)

    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                if (p / "tech_ip_evidence_composite.json").exists():
                    return p
                if company_slug and (p / f"{company_slug}_tech_ip_evidence_composite.json").exists():
                    return p
        except Exception:
            continue

    files: list[Path] = []
    data_root = ROOT / "data"
    if data_root.exists():
        files.extend(data_root.glob("**/tech/tech_ip_evidence_composite.json"))
        files.extend(data_root.glob("**/tech/*_tech_ip_evidence_composite.json"))

    files = [p for p in files if p.exists() and p.is_file()]
    if not files:
        return None

    files = sorted(
        files,
        key=lambda p: (_score_file_match(p, company_slug, company_name), p.stat().st_mtime),
        reverse=True,
    )

    best = files[0]
    if _score_file_match(best, company_slug, company_name) <= 0 and len(files) > 1:
        return None

    return best.parent


def load_ip_evidence_composite(
    field: str = "반도체",
    company_name: str = "",
    company_slug: str = "",
    tech_dir: str | Path | None = None,
) -> tuple[dict[str, Any], Optional[Path]]:
    resolved = resolve_tech_dir(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
        tech_dir=tech_dir,
    )

    if resolved is None:
        return {}, None

    candidates: list[Path] = [
        resolved / "tech_ip_evidence_composite.json",
    ]

    if company_slug:
        candidates.append(resolved / f"{company_slug}_tech_ip_evidence_composite.json")

    for path in candidates:
        data = _read_json(path)
        if isinstance(data, dict) and data:
            data = dict(data)
            data.setdefault("_source_file", _rel_project_path(path))
            return data, path

    return {}, None


def _find_bridge_score_key(bridge: dict[str, Any]) -> tuple[Optional[str], Optional[float]]:
    preferred_keys = [
        "score",
        "final_score",
        "tech_to_value_score",
        "tech_to_value_bridge_score",
        "base_bridge_score",
        "total_score",
    ]

    for key in preferred_keys:
        value = _safe_float(bridge.get(key))
        if value is not None:
            return key, value

    return None, None


def _grade_from_score(score: Any, fallback: Any = None) -> str:
    value = _safe_float(score)
    if value is None:
        return _clean_text(fallback) or "TECH_EVIDENCE_WEAK"

    if value >= 85:
        return "VALUE_CONVERSION_CONFIRMED"
    if value >= 70:
        return "COMMERCIALIZATION_WATCH"
    if value >= 55:
        return "TECH_FINANCE_GAP"
    return "TECH_EVIDENCE_WEAK"


def apply_ip_evidence_composite_adjustment_to_score(
    base_score: Any,
    ip_adjustment_points: Any,
) -> Optional[float]:
    base = _safe_float(base_score)
    adj = _safe_float(ip_adjustment_points)

    if base is None:
        return None

    if adj is None:
        adj = 0.0

    return _clamp_score(base + adj)


def apply_ip_evidence_composite_adjustment_to_bridge(
    bridge: dict[str, Any],
    field: str = "반도체",
    company_name: str = "",
    company_slug: str = "",
    tech_dir: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(bridge, dict):
        return bridge

    bridge = dict(bridge)

    if bridge.get("ip_evidence_composite_adjustment_applied") is True:
        return bridge

    feature, feature_path = load_ip_evidence_composite(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
        tech_dir=tech_dir,
    )

    if not feature:
        bridge["ip_evidence_composite_adjustment_status"] = "FEATURE_FILE_NOT_FOUND"
        bridge["ip_evidence_composite_adjustment_applied"] = False
        return bridge

    adjustment = _safe_float(feature.get("bridge_adjustment_points"))
    if adjustment is None:
        adjustment = 0.0

    score_key, base_score = _find_bridge_score_key(bridge)

    bridge["ip_evidence_composite_adjustment_status"] = "LOADED"
    bridge["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
    bridge["ip_evidence_composite_data_coverage_rate"] = feature.get("ip_evidence_data_coverage_rate")
    bridge["ip_evidence_composite_bridge_signal"] = feature.get("bridge_signal")
    bridge["ip_evidence_composite_adjustment_points"] = adjustment
    bridge["ip_evidence_composite_source_file"] = _rel_project_path(feature_path) if feature_path else ""
    bridge["ip_evidence_composite_components"] = feature.get("components", {})
    bridge["ip_evidence_composite_usage_rule"] = (
        feature.get("usage_rule")
        or (feature.get("tech_to_value_bridge") or {}).get("usage_rule")
        or "IP Evidence Composite는 특허 수량이 아니라 법적 안정성·청구항 방어력·인용 영향력·글로벌 패밀리 확장성을 종합한 보조 조정 신호입니다."
    )

    if score_key is None or base_score is None:
        bridge["ip_evidence_composite_adjustment_status"] = "BASE_SCORE_NOT_FOUND"
        bridge["ip_evidence_composite_adjustment_applied"] = False
        return bridge

    adjusted_score = apply_ip_evidence_composite_adjustment_to_score(
        base_score=base_score,
        ip_adjustment_points=adjustment,
    )

    if adjusted_score is None:
        bridge["ip_evidence_composite_adjustment_status"] = "ADJUSTMENT_FAILED"
        bridge["ip_evidence_composite_adjustment_applied"] = False
        return bridge

    old_grade = bridge.get("grade") or bridge.get("base_bridge_grade")

    bridge["base_score_before_ip_evidence"] = _round2(base_score)
    bridge["base_grade_before_ip_evidence"] = old_grade
    bridge["ip_evidence_adjusted_score"] = adjusted_score
    bridge["ip_evidence_adjusted_grade"] = _grade_from_score(adjusted_score, fallback=old_grade)
    bridge["ip_evidence_composite_adjustment_applied"] = True
    bridge["ip_evidence_composite_adjusted_at"] = datetime.now().isoformat(timespec="seconds")
    bridge["ip_evidence_composite_formula"] = (
        "ip_evidence_adjusted_score = base_score_before_ip_evidence "
        "+ ip_evidence_composite_adjustment_points"
    )

    bridge[score_key] = adjusted_score

    if "score" in bridge:
        bridge["score"] = adjusted_score

    if "final_score" in bridge:
        bridge["final_score"] = adjusted_score

    if "grade" in bridge:
        bridge["grade"] = bridge["ip_evidence_adjusted_grade"]

    bridge["ip_evidence_composite_adjustment_status"] = "APPLIED"

    adjustments = bridge.setdefault("adjustments", {})
    if isinstance(adjustments, dict):
        adjustments["ip_evidence_composite"] = {
            "score": feature.get("ip_evidence_composite_score"),
            "bridge_signal": feature.get("bridge_signal"),
            "bridge_adjustment_points": adjustment,
            "source_file": bridge.get("ip_evidence_composite_source_file"),
            "applied": True,
        }

    return bridge


def persist_ip_evidence_adjusted_bridge_packet(
    bridge: dict[str, Any],
    field: str = "반도체",
    company_name: str = "",
    company_slug: str = "",
    tech_dir: str | Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "INIT",
        "updated_files": [],
    }

    resolved = resolve_tech_dir(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
        tech_dir=tech_dir,
    )

    if resolved is None:
        result["status"] = "TECH_DIR_NOT_FOUND"
        return result

    candidates = [
        resolved / "tech_to_value_bridge.json",
        resolved / "tech_bridge.json",
    ]

    if company_slug:
        candidates.extend([
            resolved / f"{company_slug}_tech_to_value_bridge.json",
            resolved / f"{company_slug}_tech_bridge.json",
        ])

    existing_any = False

    for path in candidates:
        if not path.exists():
            continue

        existing_any = True

        data = _read_json(path)
        if not isinstance(data, dict):
            continue

        if data.get("ip_evidence_composite_adjustment_applied") is True:
            adjusted = data
        else:
            adjusted = apply_ip_evidence_composite_adjustment_to_bridge(
                data,
                field=field,
                company_name=company_name,
                company_slug=company_slug,
                tech_dir=resolved,
            )

        _write_json(path, adjusted)
        result["updated_files"].append(_rel_project_path(path))

    if not existing_any:
        result["status"] = "BRIDGE_PACKET_NOT_FOUND"
        return result

    result["status"] = "UPDATED"
    result["ip_evidence_composite_adjustment_status"] = bridge.get("ip_evidence_composite_adjustment_status")
    result["ip_evidence_composite_adjustment_points"] = bridge.get("ip_evidence_composite_adjustment_points")
    result["ip_evidence_adjusted_score"] = bridge.get("ip_evidence_adjusted_score")
    return result

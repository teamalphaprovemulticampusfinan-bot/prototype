from pathlib import Path
import re

path = Path("src/tech_agent/chair_summary.py")
text = path.read_text(encoding="utf-8")

backup = path.with_suffix(".py.bak_ip_evidence_bridge_wrapper")
backup.write_text(text, encoding="utf-8")

START = "# === IP_EVIDENCE_BRIDGE_ADJUSTMENT_WRAPPER_START ==="
END = "# === IP_EVIDENCE_BRIDGE_ADJUSTMENT_WRAPPER_END ==="

# 기존 같은 wrapper가 있으면 제거 후 재삽입
pattern = re.compile(
    re.escape(START) + r".*?" + re.escape(END) + r"\s*",
    flags=re.DOTALL,
)
text = pattern.sub("", text).rstrip() + "\n\n"

block = r'''
# === IP_EVIDENCE_BRIDGE_ADJUSTMENT_WRAPPER_START ===
# Auto-added: apply IP Evidence Composite adjustment to final Tech-to-Value Bridge score.
# Formula:
# final_tech_to_value_score
# = peer_adjusted_bridge_score_before_ip_evidence
# + ip_evidence_composite_adjustment_points

import json as _ipev_bridge_json
from pathlib import Path as _IpevBridgePath
from datetime import datetime as _IpevBridgeDatetime

from tech_agent.ip_evidence_bridge_adjustment import (
    apply_ip_evidence_composite_adjustment_to_bridge as _ipev_apply_bridge_adjustment,
    persist_ip_evidence_adjusted_bridge_packet as _ipev_persist_bridge_packet,
    resolve_tech_dir as _ipev_resolve_tech_dir,
    load_ip_evidence_composite as _ipev_load_composite,
)


def _ipev_clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _ipev_float(value, default=None):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").replace("%", "").strip()
        if not text:
            return default
        return float(text)
    except Exception:
        return default


def _ipev_round2(value):
    x = _ipev_float(value)
    if x is None:
        return None
    return round(float(x), 2)


def _ipev_company_slug(summary, args=None, kwargs=None):
    args = args or ()
    kwargs = kwargs or {}

    candidates = [
        kwargs.get("company_slug"),
        kwargs.get("company_dir"),
        kwargs.get("slug"),
        summary.get("company_slug") if isinstance(summary, dict) else None,
        summary.get("company_dir") if isinstance(summary, dict) else None,
        summary.get("slug") if isinstance(summary, dict) else None,
    ]

    for value in candidates:
        value = _ipev_clean(value)
        if value:
            return value

    for value in args:
        if isinstance(value, str) and value and value.isascii():
            return value.strip()

    return ""


def _ipev_company_name(summary, args=None, kwargs=None):
    args = args or ()
    kwargs = kwargs or {}

    candidates = [
        kwargs.get("company_name"),
        kwargs.get("company"),
        kwargs.get("name"),
        summary.get("company_name") if isinstance(summary, dict) else None,
        summary.get("company") if isinstance(summary, dict) else None,
        summary.get("name") if isinstance(summary, dict) else None,
    ]

    for value in candidates:
        value = _ipev_clean(value)
        if value:
            return value

    for value in args:
        if isinstance(value, str) and value and not value.isascii():
            return value.strip()

    return ""


def _ipev_field(summary, kwargs=None):
    kwargs = kwargs or {}
    candidates = [
        kwargs.get("field"),
        kwargs.get("sector"),
        kwargs.get("industry_field"),
        summary.get("field") if isinstance(summary, dict) else None,
        summary.get("sector") if isinstance(summary, dict) else None,
        summary.get("industry_field") if isinstance(summary, dict) else None,
    ]

    for value in candidates:
        value = _ipev_clean(value)
        if value:
            return value

    return "반도체"


def _ipev_compact_composite(feature):
    if not isinstance(feature, dict):
        return {}

    return {
        "status": feature.get("status"),
        "ip_evidence_composite_score": feature.get("ip_evidence_composite_score"),
        "ip_evidence_data_coverage_rate": feature.get("ip_evidence_data_coverage_rate"),
        "bridge_signal": feature.get("bridge_signal"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "components": feature.get("components", {}),
        "usage_rule": (
            feature.get("usage_rule")
            or (feature.get("tech_to_value_bridge") or {}).get("usage_rule")
            or "IP Evidence Composite는 법적 안정성, 청구항 방어력, 인용 영향력, 글로벌 패밀리 확장성을 종합한 Tech-to-Value Bridge 보조 조정 신호입니다."
        ),
        "source_file": feature.get("_source_file") or feature.get("source_file"),
    }


def _ipev_apply_to_summary(summary, args=None, kwargs=None):
    if not isinstance(summary, dict):
        return summary

    args = args or ()
    kwargs = kwargs or {}

    company_slug = _ipev_company_slug(summary, args=args, kwargs=kwargs)
    company_name = _ipev_company_name(summary, args=args, kwargs=kwargs)
    field = _ipev_field(summary, kwargs=kwargs)

    tv = summary.get("tech_to_value")
    if not isinstance(tv, dict):
        tv = {}
        summary["tech_to_value"] = tv

    feature, feature_path = _ipev_load_composite(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
    )

    if not feature:
        summary["ip_evidence_bridge_adjustment_status"] = "FEATURE_FILE_NOT_FOUND"
        tv["ip_evidence_composite_adjustment_status"] = "FEATURE_FILE_NOT_FOUND"
        return summary

    # Chair summary 기준 최종 점수는 peer-adjusted score를 우선 기준으로 삼는다.
    peer_before = (
        tv.get("peer_adjusted_bridge_score_before_ip_evidence")
        or tv.get("peer_adjusted_bridge_score")
        or tv.get("base_bridge_score")
        or tv.get("ip_evidence_adjusted_score")
        or tv.get("score")
    )

    working_bridge = dict(tv)
    if _ipev_float(working_bridge.get("score")) is None:
        working_bridge["score"] = peer_before

    adjusted_bridge = _ipev_apply_bridge_adjustment(
        working_bridge,
        field=field,
        company_name=company_name,
        company_slug=company_slug,
    )

    adjustment = _ipev_float(
        adjusted_bridge.get("ip_evidence_composite_adjustment_points"),
        0.0,
    )

    peer_before_float = _ipev_float(peer_before)
    if peer_before_float is not None:
        final_score = max(0.0, min(100.0, peer_before_float + adjustment))
        final_score = round(final_score, 2)
    else:
        final_score = adjusted_bridge.get("ip_evidence_adjusted_score") or adjusted_bridge.get("score")

    tv["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
    tv["ip_evidence_composite_bridge_signal"] = feature.get("bridge_signal")
    tv["ip_evidence_composite_adjustment_points"] = adjustment
    tv["ip_evidence_composite_data_coverage_rate"] = feature.get("ip_evidence_data_coverage_rate")
    tv["ip_evidence_composite_source_file"] = (
        str(feature_path).replace("\\", "/") if feature_path else feature.get("_source_file")
    )

    tv["peer_adjusted_bridge_score_before_ip_evidence"] = _ipev_round2(peer_before)
    tv["final_bridge_score_after_ip_evidence"] = _ipev_round2(final_score)
    tv["peer_adjusted_bridge_score"] = _ipev_round2(final_score)
    tv["ip_evidence_adjusted_score"] = _ipev_round2(final_score)
    tv["ip_evidence_formula"] = (
        "final_bridge_score_after_ip_evidence = "
        "peer_adjusted_bridge_score_before_ip_evidence + "
        "ip_evidence_composite_adjustment_points"
    )

    if adjusted_bridge.get("ip_evidence_adjusted_grade"):
        tv["ip_evidence_adjusted_grade"] = adjusted_bridge.get("ip_evidence_adjusted_grade")
        tv["peer_adjusted_grade"] = adjusted_bridge.get("ip_evidence_adjusted_grade")

    summary["ip_evidence_bridge_adjustment_status"] = "APPLIED"
    summary["ip_evidence_bridge_adjustment_applied_at"] = _IpevBridgeDatetime.now().isoformat(timespec="seconds")
    summary["ip_evidence_composite"] = feature
    summary["ip_evidence_composite_merge_status"] = "MERGED"

    selected_ml = summary.get("selected_ml")
    if not isinstance(selected_ml, dict):
        selected_ml = {}
        summary["selected_ml"] = selected_ml

    selected_ml["ip_evidence_composite"] = _ipev_compact_composite(feature)
    selected_ml["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
    selected_ml["ip_evidence_bridge_signal"] = feature.get("bridge_signal")
    selected_ml["ip_evidence_bridge_adjustment_points"] = adjustment
    selected_ml["final_bridge_score_after_ip_evidence"] = _ipev_round2(final_score)

    try:
        _ipev_persist_bridge_packet(
            adjusted_bridge,
            field=field,
            company_name=company_name,
            company_slug=company_slug,
        )
    except Exception as exc:
        summary["ip_evidence_bridge_packet_persist_error"] = repr(exc)

    return summary


def _ipev_write_json(path, data):
    p = _IpevBridgePath(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        _ipev_bridge_json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _ipev_md_block(summary):
    if not isinstance(summary, dict):
        return ""

    tv = summary.get("tech_to_value") or {}

    lines = []
    lines.append("<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->")
    lines.append("## IP Evidence Composite → Tech-to-Value Bridge 반영")
    lines.append("")
    lines.append("- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.")
    lines.append("- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points")
    lines.append("")
    lines.append(f"- IP Evidence Composite Score: {tv.get('ip_evidence_composite_score')}")
    lines.append(f"- IP Evidence Bridge Signal: {tv.get('ip_evidence_composite_bridge_signal')}")
    lines.append(f"- IP Evidence Adjustment Points: {tv.get('ip_evidence_composite_adjustment_points')}")
    lines.append(f"- Peer-adjusted Score Before IP Evidence: {tv.get('peer_adjusted_bridge_score_before_ip_evidence')}")
    lines.append(f"- Final Bridge Score After IP Evidence: {tv.get('final_bridge_score_after_ip_evidence')}")
    lines.append(f"- Source: `{tv.get('ip_evidence_composite_source_file')}`")
    lines.append("")
    lines.append("해석:")
    lines.append("- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.")
    lines.append("- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.")
    lines.append("<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->")
    lines.append("")
    return "\n".join(lines)


def _ipev_replace_or_append_md(path, block):
    p = _IpevBridgePath(path)
    if not p.exists() or not block:
        return

    text = p.read_text(encoding="utf-8", errors="replace")

    start = "<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->"
    end = "<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->"

    if start in text and end in text:
        before = text.split(start, 1)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        new_text = before + "\n\n" + block.strip() + "\n\n" + after
    else:
        new_text = text.rstrip() + "\n\n" + block.strip() + "\n"

    p.write_text(new_text, encoding="utf-8")


def _ipev_persist_summary(summary, args=None, kwargs=None):
    if not isinstance(summary, dict):
        return

    args = args or ()
    kwargs = kwargs or {}

    company_slug = _ipev_company_slug(summary, args=args, kwargs=kwargs)
    company_name = _ipev_company_name(summary, args=args, kwargs=kwargs)
    field = _ipev_field(summary, kwargs=kwargs)

    tech_dir = _ipev_resolve_tech_dir(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
    )

    if tech_dir is None:
        return

    json_candidates = [
        tech_dir / "tech_chair_summary.json",
    ]

    if company_slug:
        json_candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.json")

    wrote = False
    for path in json_candidates:
        if path.exists():
            _ipev_write_json(path, summary)
            wrote = True

    if not wrote:
        _ipev_write_json(tech_dir / "tech_chair_summary.json", summary)

    block = _ipev_md_block(summary)

    md_candidates = [
        tech_dir / "tech_chair_summary.md",
    ]

    if company_slug:
        md_candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.md")

    for path in md_candidates:
        _ipev_replace_or_append_md(path, block)


_ipev_original_build_tech_chair_summary = globals().get("build_tech_chair_summary")

if callable(_ipev_original_build_tech_chair_summary):

    def build_tech_chair_summary(*args, **kwargs):
        summary = _ipev_original_build_tech_chair_summary(*args, **kwargs)

        if isinstance(summary, dict):
            summary = _ipev_apply_to_summary(summary, args=args, kwargs=kwargs)
            _ipev_persist_summary(summary, args=args, kwargs=kwargs)

        return summary

# === IP_EVIDENCE_BRIDGE_ADJUSTMENT_WRAPPER_END ===
'''

text = text + block.strip() + "\n"

path.write_text(text, encoding="utf-8")

print("[DONE] chair_summary.py wrapper patch applied")
print(f"[BACKUP] {backup}")

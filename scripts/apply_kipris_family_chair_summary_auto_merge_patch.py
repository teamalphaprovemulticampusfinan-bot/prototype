from __future__ import annotations

from pathlib import Path
from datetime import datetime

PATCH_PATH = Path("src/tech_agent/chair_summary.py")
MARKER_START = "# === KIPRIS IP FAMILY AUTO MERGE START ==="
MARKER_END = "# === KIPRIS IP FAMILY AUTO MERGE END ==="

PATCH_CODE = r'''
# === KIPRIS IP FAMILY AUTO MERGE START ===
# Auto-added: merge KIPRIS Plus family/global-extension features into Tech Chair summary.
# This block intentionally wraps build_tech_chair_summary without changing the original body.

from pathlib import Path as _KiprisFamilyPath
import json as _kipris_family_json


def _kipris_family_clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _kipris_family_safe_dict(value):
    return value if isinstance(value, dict) else {}


def _kipris_family_read_json(path):
    try:
        p = _KiprisFamilyPath(path)
        if not p.exists():
            return {}
        return _kipris_family_json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _kipris_family_write_json(path, data):
    p = _KiprisFamilyPath(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        _kipris_family_json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _kipris_family_find_tech_dir(summary, args=None, kwargs=None):
    summary = _kipris_family_safe_dict(summary)
    args = args or ()
    kwargs = kwargs or {}

    candidates = []

    for key in ["tech_dir", "output_dir", "save_dir", "base_dir"]:
        value = kwargs.get(key) or summary.get(key)
        if value:
            p = _KiprisFamilyPath(str(value))
            candidates.append(p)
            if p.name != "tech":
                candidates.append(p / "tech")

    company_slug = (
        kwargs.get("company_slug")
        or kwargs.get("company_dir")
        or summary.get("company_slug")
        or summary.get("company_dir")
        or summary.get("slug")
        or ""
    )
    company_name = (
        kwargs.get("company_name")
        or kwargs.get("company")
        or summary.get("company_name")
        or summary.get("company")
        or ""
    )
    field = kwargs.get("field") or summary.get("field") or "반도체"

    if company_name:
        candidates.append(_KiprisFamilyPath("data") / str(field) / str(company_name) / "tech")
        candidates.extend(_KiprisFamilyPath("data").glob(f"*/{company_name}/tech"))

    if company_slug:
        candidates.extend(_KiprisFamilyPath("data").glob(f"*/*/tech/{company_slug}_tech_ip_family_features.json"))

    # Existing feature paths inside summary may reveal tech dir.
    for block_key in [
        "ip_legal_features",
        "ip_claim_features",
        "ip_citation_features",
        "ip_family_features",
    ]:
        block = summary.get(block_key)
        if isinstance(block, dict):
            for path_key in [
                "input_csv",
                "family_csv",
                "claim_csv",
                "citation_csv",
                "source_file",
                "raw_jsonl",
                "request_targets_csv",
            ]:
                value = block.get(path_key)
                if value:
                    p = _KiprisFamilyPath(str(value))
                    parts = list(p.parts)
                    if "tech" in parts:
                        idx = parts.index("tech")
                        candidates.append(_KiprisFamilyPath(*parts[: idx + 1]))

    normalized_candidates = []
    for c in candidates:
        try:
            c = _KiprisFamilyPath(c)
            if c.is_file():
                c = c.parent
            normalized_candidates.append(c)
        except Exception:
            pass

    for c in normalized_candidates:
        if (c / "tech_ip_family_features.json").exists():
            return c
        if company_slug and (c / f"{company_slug}_tech_ip_family_features.json").exists():
            return c

    # Last fallback: search under data.
    found = list(_KiprisFamilyPath("data").glob("*/**/tech/tech_ip_family_features.json"))
    if company_name:
        for p in found:
            if company_name in str(p):
                return p.parent

    if found:
        return found[0].parent

    return None


def _kipris_family_load_feature(tech_dir, company_slug=""):
    if not tech_dir:
        return {}, None

    tech_dir = _KiprisFamilyPath(tech_dir)

    candidates = []
    if company_slug:
        candidates.append(tech_dir / f"{company_slug}_tech_ip_family_features.json")
    candidates.append(tech_dir / "tech_ip_family_features.json")

    for path in candidates:
        if path.exists():
            data = _kipris_family_read_json(path)
            if isinstance(data, dict) and data:
                return data, path

    return {}, None


def _kipris_family_compact_feature(feature, feature_path=None):
    feature = _kipris_family_safe_dict(feature)

    keys = [
        "status",
        "target_patent_count",
        "family_record_count",
        "patents_with_family",
        "patents_with_overseas_family",
        "overseas_family_record_count",
        "family_collection_coverage",
        "overseas_family_patent_rate",
        "pct_patents",
        "us_patents",
        "jp_patents",
        "ep_patents",
        "cn_patents",
        "detected_overseas_regions",
        "global_extension_score",
        "bridge_adjustment_points",
        "bridge_signal",
        "top_overseas_family_patents",
        "usage_rule",
        "parse_error_count",
        "raw_jsonl",
        "family_csv",
        "request_targets_csv",
        "created_at",
    ]

    compact = {k: feature.get(k) for k in keys if k in feature}

    if feature_path:
        compact["source_file"] = str(feature_path)

    return compact


def _kipris_family_bridge_view(feature):
    feature = _kipris_family_safe_dict(feature)

    return {
        "status": feature.get("status"),
        "global_extension_score": feature.get("global_extension_score"),
        "bridge_signal": feature.get("bridge_signal"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "overseas_family_patent_rate": feature.get("overseas_family_patent_rate"),
        "patents_with_overseas_family": feature.get("patents_with_overseas_family"),
        "pct_patents": feature.get("pct_patents"),
        "us_patents": feature.get("us_patents"),
        "jp_patents": feature.get("jp_patents"),
        "ep_patents": feature.get("ep_patents"),
        "cn_patents": feature.get("cn_patents"),
        "detected_overseas_regions": feature.get("detected_overseas_regions"),
        "top_overseas_family_patents": feature.get("top_overseas_family_patents", [])[:10],
        "interpretation": (
            "KIPRIS Plus 패밀리 특허 기반 글로벌 권리확장 지표입니다. "
            "해외 패밀리, PCT/WO, 미국·일본·유럽·중국 확장 여부를 통해 "
            "기술의 해외 방어 범위와 글로벌 확장 가능성을 Tech-to-Value Bridge에 반영합니다."
        ),
    }


def _kipris_family_merge_into_summary(summary, args=None, kwargs=None):
    if not isinstance(summary, dict):
        return summary

    company_slug = (
        summary.get("company_slug")
        or summary.get("company_dir")
        or summary.get("slug")
        or (kwargs or {}).get("company_slug")
        or (kwargs or {}).get("company_dir")
        or ""
    )

    tech_dir = _kipris_family_find_tech_dir(summary, args=args, kwargs=kwargs)
    feature, feature_path = _kipris_family_load_feature(tech_dir, company_slug=company_slug)

    if not feature:
        summary["ip_family_feature_merge_status"] = "MISSING"
        summary["ip_family_feature_merge_message"] = (
            "tech_ip_family_features.json 또는 "
            f"{company_slug}_tech_ip_family_features.json 파일을 찾지 못했습니다."
        )
        return summary

    compact = _kipris_family_compact_feature(feature, feature_path=feature_path)
    bridge_view = _kipris_family_bridge_view(feature)

    summary["ip_family_feature_merge_status"] = "MERGED"
    summary["ip_family_features"] = compact

    selected_ml = summary.get("selected_ml")
    if not isinstance(selected_ml, dict):
        selected_ml = {}
        summary["selected_ml"] = selected_ml

    selected_ml["ip_global_extension"] = bridge_view

    # Tech-to-Value Bridge에서 바로 읽기 쉬운 별도 키도 제공.
    summary["tech_to_value_ip_global_extension"] = {
        "global_extension_score": feature.get("global_extension_score"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "bridge_signal": feature.get("bridge_signal"),
        "usage_rule": feature.get("usage_rule"),
    }

    return summary


def _kipris_family_build_md_block(summary):
    summary = _kipris_family_safe_dict(summary)
    feature = _kipris_family_safe_dict(summary.get("ip_family_features"))

    if not feature:
        return ""

    regions = feature.get("detected_overseas_regions") or []
    if isinstance(regions, list):
        regions_text = ", ".join(str(x) for x in regions)
    else:
        regions_text = str(regions)

    top_items = feature.get("top_overseas_family_patents") or []

    lines = []
    lines.append("")
    lines.append("<!-- IP_FAMILY_AUTO_MERGE_START -->")
    lines.append("## IP Family / Global Extension")
    lines.append("")
    lines.append(f"- IP Family Merge Status: {summary.get('ip_family_feature_merge_status')}")
    lines.append(f"- IP Global Extension Score: {feature.get('global_extension_score')}")
    lines.append(f"- IP Global Bridge Signal: {feature.get('bridge_signal')}")
    lines.append(f"- IP Global Bridge Adjustment: {feature.get('bridge_adjustment_points')}")
    lines.append(f"- 전체 분석 특허 수: {feature.get('target_patent_count')}")
    lines.append(f"- 패밀리 확인 특허 수: {feature.get('patents_with_family')}")
    lines.append(f"- 해외 패밀리 보유 특허 수: {feature.get('patents_with_overseas_family')}")
    lines.append(f"- 해외 패밀리 보유율: {feature.get('overseas_family_patent_rate')}")
    lines.append(f"- PCT/WO: {feature.get('pct_patents')}")
    lines.append(f"- US: {feature.get('us_patents')}")
    lines.append(f"- JP: {feature.get('jp_patents')}")
    lines.append(f"- EP: {feature.get('ep_patents')}")
    lines.append(f"- CN: {feature.get('cn_patents')}")
    lines.append(f"- detected_overseas_regions: {regions_text}")
    lines.append("")
    lines.append("### 핵심 해외 패밀리 보유 Top 10")
    if top_items:
        for i, item in enumerate(top_items[:10], start=1):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or ""
            app_no = item.get("application_number") or ""
            family_count = item.get("family_record_count")
            overseas_count = item.get("overseas_family_record_count")
            jurisdictions = item.get("jurisdictions") or []
            if isinstance(jurisdictions, list):
                jurisdictions = ",".join(str(x) for x in jurisdictions)
            lines.append(
                f"{i}. {app_no} / {title} / "
                f"family={family_count} / overseas={overseas_count} / regions={jurisdictions}"
            )
    else:
        lines.append("- 해외 패밀리 보유 핵심 특허가 확인되지 않았습니다.")
    lines.append("<!-- IP_FAMILY_AUTO_MERGE_END -->")
    lines.append("")

    return "\n".join(lines)


def _kipris_family_replace_or_append_md(md_path, block):
    if not block:
        return

    path = _KiprisFamilyPath(md_path)
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    start = "<!-- IP_FAMILY_AUTO_MERGE_START -->"
    end = "<!-- IP_FAMILY_AUTO_MERGE_END -->"

    if start in text and end in text:
        before = text.split(start, 1)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        new_text = before + "\n" + block.strip() + "\n" + after
    else:
        new_text = text.rstrip() + "\n\n" + block.strip() + "\n"

    path.write_text(new_text, encoding="utf-8")


def _kipris_family_persist_summary(summary, tech_dir):
    if not isinstance(summary, dict) or not tech_dir:
        return

    tech_dir = _KiprisFamilyPath(tech_dir)
    company_slug = (
        summary.get("company_slug")
        or summary.get("company_dir")
        or summary.get("slug")
        or ""
    )

    json_candidates = [
        tech_dir / "tech_chair_summary.json",
    ]
    if company_slug:
        json_candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.json")

    wrote_json = False
    for path in json_candidates:
        if path.exists():
            _kipris_family_write_json(path, summary)
            wrote_json = True

    if not wrote_json:
        _kipris_family_write_json(tech_dir / "tech_chair_summary.json", summary)

    md_block = _kipris_family_build_md_block(summary)
    md_candidates = [
        tech_dir / "tech_chair_summary.md",
    ]
    if company_slug:
        md_candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.md")

    for path in md_candidates:
        _kipris_family_replace_or_append_md(path, md_block)


try:
    _kipris_family_original_build_tech_chair_summary
except NameError:
    try:
        _kipris_family_original_build_tech_chair_summary = build_tech_chair_summary

        def build_tech_chair_summary(*args, **kwargs):
            summary = _kipris_family_original_build_tech_chair_summary(*args, **kwargs)

            if isinstance(summary, dict):
                summary = _kipris_family_merge_into_summary(summary, args=args, kwargs=kwargs)
                tech_dir = _kipris_family_find_tech_dir(summary, args=args, kwargs=kwargs)
                _kipris_family_persist_summary(summary, tech_dir)

            return summary

    except NameError:
        # If the original function is not defined, do not break import.
        pass
# === KIPRIS IP FAMILY AUTO MERGE END ===
'''

def main() -> int:
    if not PATCH_PATH.exists():
        print(f"[ERROR] 파일이 없습니다: {PATCH_PATH}")
        return 1

    text = PATCH_PATH.read_text(encoding="utf-8", errors="replace")

    if MARKER_START in text and MARKER_END in text:
        print("[SKIP] 이미 KIPRIS IP Family 자동 병합 패치가 적용되어 있습니다.")
        return 0

    backup = PATCH_PATH.with_suffix(
        PATCH_PATH.suffix + f".bak_family_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    backup.write_text(text, encoding="utf-8")

    new_text = text.rstrip() + "\n\n" + PATCH_CODE.strip() + "\n"
    PATCH_PATH.write_text(new_text, encoding="utf-8")

    print("[DONE] chair_summary.py에 KIPRIS IP Family 자동 병합 패치 적용 완료")
    print(f"- patched: {PATCH_PATH}")
    print(f"- backup : {backup}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

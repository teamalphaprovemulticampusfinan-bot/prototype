from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path


TARGET = Path("src/tech_agent/chair_summary.py")
MARKER = "# === IP_CITATION_AUTO_MERGE_PATCH_V1 ==="


PATCH_CODE = r'''
# === IP_CITATION_AUTO_MERGE_PATCH_V1 ===
# KIPRIS Plus 인용/피인용 기반 IP 영향력 feature를 Tech Chair Summary에 자동 병합한다.
# - input : data/<field>/<company_name>/tech/tech_ip_citation_features.json
# - output: tech_chair_summary.json, *_tech_chair_summary.md
# - 목적 : Tech-to-Value Bridge에 "기술 영향력/시장 내 참조 가치" 신호를 자동 반영

import json as _ipcit_json
import re as _ipcit_re
from pathlib import Path as _IpCitPath
from datetime import datetime as _IpCitDatetime


def _ipcit_now_iso() -> str:
    return _IpCitDatetime.now().isoformat(timespec="seconds")


def _ipcit_clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _ipcit_slug_from_result_or_args(result, args, kwargs):
    candidates = [
        kwargs.get("company_slug"),
        kwargs.get("company_dir"),
        kwargs.get("slug"),
        kwargs.get("company_code"),
    ]

    if isinstance(result, dict):
        candidates.extend([
            result.get("company_slug"),
            result.get("company_dir"),
            result.get("slug"),
            result.get("company_code"),
        ])

    for value in candidates:
        value = _ipcit_clean(value)
        if value:
            return value

    # positional fallback
    for value in args:
        if isinstance(value, str) and value and value.isascii():
            return value.strip()

    return ""


def _ipcit_company_name_from_result_or_args(result, args, kwargs):
    candidates = [
        kwargs.get("company_name"),
        kwargs.get("company"),
        kwargs.get("name"),
    ]

    if isinstance(result, dict):
        candidates.extend([
            result.get("company_name"),
            result.get("company"),
            result.get("name"),
        ])

    for value in candidates:
        value = _ipcit_clean(value)
        if value:
            return value

    # positional fallback: Korean company name likely non-ascii
    for value in args:
        if isinstance(value, str) and value and not value.isascii():
            return value.strip()

    return ""


def _ipcit_field_from_result_or_args(result, args, kwargs):
    candidates = [
        kwargs.get("field"),
        kwargs.get("sector"),
        kwargs.get("industry_field"),
    ]

    if isinstance(result, dict):
        candidates.extend([
            result.get("field"),
            result.get("sector"),
            result.get("industry_field"),
        ])

    for value in candidates:
        value = _ipcit_clean(value)
        if value:
            return value

    return "반도체"


def _ipcit_score_path(path: _IpCitPath, company_slug: str, company_name: str) -> int:
    text = str(path).replace("\\", "/").lower()
    score = 0

    if company_slug and company_slug.lower() in text:
        score += 50

    if company_name and company_name.lower() in text:
        score += 50

    if path.name == "tech_ip_citation_features.json":
        score += 20

    if path.name.endswith("_tech_ip_citation_features.json"):
        score += 10

    if "/tech/" in text:
        score += 10

    return score


def _ipcit_find_feature_file(field: str, company_name: str, company_slug: str) -> _IpCitPath | None:
    root = _IpCitPath.cwd()

    direct_candidates = []

    if field and company_name:
        direct_candidates.append(root / "data" / field / company_name / "tech" / "tech_ip_citation_features.json")
        if company_slug:
            direct_candidates.append(root / "data" / field / company_name / "tech" / f"{company_slug}_tech_ip_citation_features.json")

    if field and company_slug:
        direct_candidates.append(root / "data" / field / company_slug / "tech" / "tech_ip_citation_features.json")
        direct_candidates.append(root / "data" / field / company_slug / "tech" / f"{company_slug}_tech_ip_citation_features.json")

    for path in direct_candidates:
        if path.exists():
            return path

    files = []
    data_root = root / "data"
    if data_root.exists():
        files.extend(data_root.glob("**/tech_ip_citation_features.json"))
        files.extend(data_root.glob("**/*_tech_ip_citation_features.json"))

    files = [p for p in files if p.exists() and p.is_file()]
    if not files:
        return None

    files = sorted(
        files,
        key=lambda p: (_ipcit_score_path(p, company_slug, company_name), p.stat().st_mtime),
        reverse=True,
    )

    best = files[0]
    if _ipcit_score_path(best, company_slug, company_name) <= 0 and len(files) > 1:
        return None

    return best


def _ipcit_load_json(path: _IpCitPath) -> dict:
    try:
        return _ipcit_json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return _ipcit_json.loads(path.read_text(encoding="utf-8-sig"))


def _ipcit_selected_feature(feature: dict, feature_path: _IpCitPath) -> dict:
    keys = [
        "status",
        "target_patent_count",
        "patents_with_citation_data",
        "citation_collection_coverage",
        "forward_citation_count_total",
        "backward_citation_count_total",
        "self_forward_citation_count",
        "external_forward_citation_count",
        "external_forward_citation_rate",
        "avg_forward_citations_per_patent",
        "max_forward_citations_single_patent",
        "cited_patent_count",
        "cited_patent_rate",
        "top10_forward_citation_share",
        "ip_citation_impact_score_estimated",
        "bridge_adjustment_points",
        "bridge_signal",
        "parse_error_count",
        "usage_rule",
        "top_cited_patents",
    ]

    selected = {k: feature.get(k) for k in keys if k in feature}
    selected["source_file"] = str(feature_path.as_posix())
    selected["merged_at"] = _ipcit_now_iso()
    return selected


def _ipcit_merge_into_summary_dict(summary: dict, selected: dict) -> dict:
    if not isinstance(summary, dict):
        return summary

    summary["ip_citation_feature_merge_status"] = "MERGED"
    summary["ip_citation_features"] = selected

    summary["ip_citation_impact_score_estimated"] = selected.get("ip_citation_impact_score_estimated")
    summary["ip_citation_bridge_adjustment_points"] = selected.get("bridge_adjustment_points")
    summary["ip_citation_bridge_signal"] = selected.get("bridge_signal")

    selected_ml = summary.setdefault("selected_ml", {})
    if isinstance(selected_ml, dict):
        selected_ml["ip_citation_impact"] = selected

    tech_ml_features = summary.setdefault("tech_ml_features", {})
    if isinstance(tech_ml_features, dict):
        tech_ml_features["ip_citation_impact"] = selected

    adjustments = summary.setdefault("tech_to_value_bridge_adjustments", {})
    if isinstance(adjustments, dict):
        adjustments["ip_citation_impact"] = {
            "bridge_adjustment_points": selected.get("bridge_adjustment_points"),
            "bridge_signal": selected.get("bridge_signal"),
            "usage_rule": selected.get("usage_rule"),
            "source_file": selected.get("source_file"),
        }

    return summary


def _ipcit_find_summary_json_paths(feature_path: _IpCitPath, company_slug: str) -> list[_IpCitPath]:
    tech_dir = feature_path.parent
    paths = [
        tech_dir / "tech_chair_summary.json",
    ]

    if company_slug:
        paths.append(tech_dir / f"{company_slug}_tech_chair_summary.json")

    return paths


def _ipcit_update_summary_json_files(feature_path: _IpCitPath, company_slug: str, selected: dict, result) -> None:
    paths = _ipcit_find_summary_json_paths(feature_path, company_slug)

    for path in paths:
        if path.exists():
            try:
                existing = _ipcit_load_json(path)
                if isinstance(existing, dict):
                    existing = _ipcit_merge_into_summary_dict(existing, selected)
                    path.write_text(_ipcit_json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                print(f"[IP Citation Merge] JSON update skipped: {path} / {exc}")

    # common summary가 없고 result가 dict이면 생성
    common_path = feature_path.parent / "tech_chair_summary.json"
    if not common_path.exists() and isinstance(result, dict):
        try:
            merged = _ipcit_merge_into_summary_dict(dict(result), selected)
            common_path.write_text(_ipcit_json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"[IP Citation Merge] JSON create skipped: {common_path} / {exc}")


def _ipcit_build_md_section(selected: dict) -> str:
    top = selected.get("top_cited_patents") or []

    lines = []
    lines.append("## IP Citation Impact")
    lines.append("")
    lines.append("- 의미: KIPRIS Plus 인용/피인용 기반으로 특허가 외부 기술 문헌에서 얼마나 참조되는지 측정한 IP 영향력 지표입니다.")
    lines.append("- 주의: 이 지표는 기술 영향력/참조 가치 신호이며, 고객 채택·양산·매출·FCF 전환을 직접 증명하는 근거는 아닙니다.")
    lines.append("")
    lines.append(f"- IP Citation Impact Score: {selected.get('ip_citation_impact_score_estimated')}")
    lines.append(f"- Citation Coverage: {selected.get('citation_collection_coverage')}")
    lines.append(f"- Forward Citations: {selected.get('forward_citation_count_total')}")
    lines.append(f"- Backward Citations: {selected.get('backward_citation_count_total')}")
    lines.append(f"- External Forward Citations: {selected.get('external_forward_citation_count')}")
    lines.append(f"- Self Forward Citations: {selected.get('self_forward_citation_count')}")
    lines.append(f"- External Forward Citation Rate: {selected.get('external_forward_citation_rate')}")
    lines.append(f"- IP Citation Bridge Adjustment: {selected.get('bridge_adjustment_points')}")
    lines.append(f"- IP Citation Bridge Signal: {selected.get('bridge_signal')}")
    lines.append(f"- Source: `{selected.get('source_file')}`")
    lines.append("")

    lines.append("### Top Cited Patents")
    lines.append("")

    if not top:
        lines.append("- 핵심 피인용 특허 Top 10 없음")
    else:
        lines.append("| rank | application_number | forward | external | self | title |")
        lines.append("|---:|---|---:|---:|---:|---|")
        for i, item in enumerate(top[:10], start=1):
            title = str(item.get("invention_title", "")).replace("|", "/")[:80]
            lines.append(
                f"| {i} | {item.get('application_number', '')} | "
                f"{item.get('forward_citation_count', 0)} | "
                f"{item.get('external_forward_citation_count', 0)} | "
                f"{item.get('self_forward_citation_count', 0)} | "
                f"{title} |"
            )

    return "\n".join(lines).rstrip() + "\n"


def _ipcit_update_summary_md_files(feature_path: _IpCitPath, company_slug: str, selected: dict) -> None:
    tech_dir = feature_path.parent
    candidates = []

    if company_slug:
        candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.md")

    candidates.append(tech_dir / "tech_chair_summary.md")

    section = _ipcit_build_md_section(selected)

    for path in candidates:
        if not path.exists():
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig")

        pattern = _ipcit_re.compile(
            r"\n## IP Citation Impact\n.*?(?=\n## |\Z)",
            flags=_ipcit_re.DOTALL,
        )

        if "## IP Citation Impact" in text:
            new_text = pattern.sub("\n" + section.rstrip() + "\n", text)
        else:
            new_text = text.rstrip() + "\n\n" + section

        path.write_text(new_text, encoding="utf-8")


def _ipcit_auto_merge_ip_citation_features(result, args, kwargs):
    company_slug = _ipcit_slug_from_result_or_args(result, args, kwargs)
    company_name = _ipcit_company_name_from_result_or_args(result, args, kwargs)
    field = _ipcit_field_from_result_or_args(result, args, kwargs)

    feature_path = _ipcit_find_feature_file(field, company_name, company_slug)

    if feature_path is None:
        if isinstance(result, dict):
            result["ip_citation_feature_merge_status"] = "FEATURE_NOT_FOUND"
        print("[IP Citation Merge] tech_ip_citation_features.json not found. Merge skipped.")
        return result

    try:
        feature = _ipcit_load_json(feature_path)
        selected = _ipcit_selected_feature(feature, feature_path)

        if isinstance(result, dict):
            result = _ipcit_merge_into_summary_dict(result, selected)

        _ipcit_update_summary_json_files(feature_path, company_slug, selected, result)
        _ipcit_update_summary_md_files(feature_path, company_slug, selected)

        print(
            "[IP Citation Merge] merged: "
            f"score={selected.get('ip_citation_impact_score_estimated')}, "
            f"signal={selected.get('bridge_signal')}, "
            f"adjustment={selected.get('bridge_adjustment_points')}"
        )

        return result

    except Exception as exc:
        if isinstance(result, dict):
            result["ip_citation_feature_merge_status"] = "MERGE_ERROR"
            result["ip_citation_feature_merge_error"] = repr(exc)
        print(f"[IP Citation Merge] merge error: {exc}")
        return result


def build_tech_chair_summary(*args, **kwargs):
    result = _build_tech_chair_summary_original(*args, **kwargs)
    return _ipcit_auto_merge_ip_citation_features(result, args, kwargs)
'''


def main() -> int:
    if not TARGET.exists():
        raise FileNotFoundError(f"대상 파일이 없습니다: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    if MARKER in text:
        print("[SKIP] 이미 IP Citation 자동 병합 패치가 적용되어 있습니다.")
        return 0

    backup = TARGET.with_suffix(
        TARGET.suffix + f".bak_ip_citation_auto_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(TARGET, backup)
    print(f"[BACKUP] {backup}")

    if "_build_tech_chair_summary_original" not in text:
        pattern = re.compile(r"^def\s+build_tech_chair_summary\s*\(", flags=re.MULTILINE)
        match = pattern.search(text)
        if not match:
            raise RuntimeError(
                "chair_summary.py에서 def build_tech_chair_summary(...) 함수를 찾지 못했습니다. "
                "현재 파일이 깨졌거나 함수명이 바뀐 상태입니다."
            )

        start, end = match.span()
        text = text[:start] + "def _build_tech_chair_summary_original(" + text[end:]
        print("[PATCH] build_tech_chair_summary -> _build_tech_chair_summary_original 로 래핑 준비 완료")

    text = text.rstrip() + "\n\n" + PATCH_CODE.strip() + "\n"

    TARGET.write_text(text, encoding="utf-8")
    print(f"[DONE] patched: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from common.data_paths import company_agent_dir, company_root, field_common_dir, normalize_field_name

DEFAULT_FIELD = "반도체"

CERTIFICATION_SCHEMA: dict[str, dict[str, Any]] = {
    "ISO_9001": {
        "aliases": ["ISO 9001", "ISO9001", "품질경영시스템", "quality management system"],
        "category": "general_quality",
        "weight": 8,
    },
    "ISO_14001": {
        "aliases": ["ISO 14001", "ISO14001", "환경경영시스템", "environmental management"],
        "category": "environment_compliance",
        "weight": 5,
    },
    "ISO_45001": {
        "aliases": ["ISO 45001", "ISO45001", "안전보건경영시스템", "occupational health"],
        "category": "safety_compliance",
        "weight": 4,
    },
    "IATF_16949": {
        "aliases": ["IATF 16949", "IATF16949", "자동차 품질경영", "automotive quality"],
        "category": "sector_specific_quality",
        "weight": 14,
    },
    "UL": {
        "aliases": ["UL 인증", "UL certified", "Underwriters Laboratories", "UL Listed", "UL Recognized"],
        "category": "product_safety_compliance",
        "weight": 9,
    },
    "CE": {
        "aliases": ["CE 인증", "CE marking", "CE mark", "유럽 CE"],
        "category": "product_safety_compliance",
        "weight": 7,
    },
    "RoHS": {
        "aliases": ["RoHS", "유해물질 제한", "restriction of hazardous substances"],
        "category": "material_regulatory_compliance",
        "weight": 8,
    },
    "REACH": {
        "aliases": ["REACH", "Registration, Evaluation, Authorisation", "화학물질 등록 평가", "EU REACH"],
        "category": "material_regulatory_compliance",
        "weight": 8,
    },
    "GMP": {
        "aliases": ["GMP", "Good Manufacturing Practice", "우수 제조", "의약품 제조"],
        "category": "bio_manufacturing_quality",
        "weight": 12,
    },
    "KGMP": {
        "aliases": ["KGMP", "K-GMP", "한국우수의약품", "한국 우수 제조"],
        "category": "bio_manufacturing_quality",
        "weight": 12,
    },
    "FDA": {
        "aliases": ["FDA", "미국 식품의약국", "510(k)", "PMA", "FDA 승인", "FDA clearance", "FDA approval"],
        "category": "regulatory_approval",
        "weight": 16,
    },
    "KC": {
        "aliases": ["KC 인증", "KC certification", "국가통합인증", "전기용품 안전인증"],
        "category": "domestic_product_compliance",
        "weight": 6,
    },
    "CUSTOMER_QUALITY_CERTIFICATION": {
        "aliases": ["고객사 품질 인증", "고객 품질 승인", "품질 승인", "고객 인증", "고객사 인증", "vendor approval", "approved vendor", "qualified vendor", "벤더 등록"],
        "category": "customer_quality_gate",
        "weight": 18,
    },
    "SEMICONDUCTOR_QUALIFICATION": {
        "aliases": ["qualification", "퀄리피케이션", "퀄", "고객사 qualification", "양산 승인", "양산 적용", "고객사 평가", "샘플 승인", "process qualification", "mass production approval"],
        "category": "semiconductor_customer_qualification",
        "weight": 22,
    },
}

EXTERNAL_FILENAMES = [
    "certification_standards_external_signals.csv",
    "tech_certification_external_signals.csv",
    "certification_standards.csv",
    "quality_certifications.csv",
]

EXTERNAL_WORKBOOK_FILENAMES = [
    "certification_standards_external_signals.xlsx",
    "tech_certification_external_signals.xlsx",
    "quality_certifications.xlsx",
]

REVIEW_STATUSES = {"", "NEED_REVIEW", "검토필요", "PENDING_REVIEW", "TODO", "미확인"}

TEXT_SUFFIXES = {".txt", ".md", ".json", ".csv"}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _safe_round(value: float | None, ndigits: int = 4) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(float(value), ndigits)


def _load_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def _contains_alias(text: str, aliases: Iterable[str]) -> str | None:
    lower = text.lower()
    for alias in aliases:
        a = str(alias).strip()
        if a and a.lower() in lower:
            return a
    return None


def _evidence_directness(source_type: str, text: str) -> str:
    st = source_type.lower()
    lower = text.lower()
    if any(x in st for x in ["manual", "external", "dart", "ir", "homepage", "cert"]):
        return "DIRECT_OR_COMPANY_DISCLOSED"
    if any(x in lower for x in ["인증서", "certified", "certificate", "승인", "approval", "approved", "등록", "qualification", "양산 승인"]):
        return "DIRECT_OR_COMPANY_DISCLOSED"
    return "TEXT_MENTION"


def _status_from_text(text: str) -> str:
    lower = text.lower()
    if any(x in lower for x in ["취소", "만료", "실효", "cancel", "expired", "revoked", "withdrawn"]):
        return "EXPIRED_OR_REVOKED"
    if any(x in lower for x in ["진행", "신청", "심사", "pending", "under review", "in progress"]):
        return "IN_PROGRESS"
    if any(x in lower for x in ["인증", "획득", "승인", "등록", "certified", "approved", "approval", "qualified", "clearance", "obtained"]):
        return "CONFIRMED"
    return "MENTIONED"


def _confidence_from_source(source_type: str, directness: str, status: str) -> str:
    st = source_type.lower()
    if status == "EXPIRED_OR_REVOKED":
        return "HIGH_NEGATIVE"
    if status == "CONFIRMED" and ("external" in st or "manual" in st or "dart" in st or "ir" in st or "homepage" in st or directness == "DIRECT_OR_COMPANY_DISCLOSED"):
        return "HIGH"
    if status in {"CONFIRMED", "IN_PROGRESS"}:
        return "MEDIUM"
    return "LOW"


def _extract_year(text: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", text)
    if not m:
        return None
    y = int(m.group(0))
    return y if 1900 <= y <= 2100 else None


def _sentence_window(text: str, alias: str, max_chars: int = 320) -> str:
    idx = text.lower().find(alias.lower())
    if idx < 0:
        return _clean(text[:max_chars])
    start = max(0, idx - max_chars // 2)
    end = min(len(text), idx + max_chars // 2)
    snippet = text[start:end]
    # Avoid very long JSON/CSV fragments.
    return _clean(snippet)


def _source_paths(company_dir: str, field: str, tech_dir: Path) -> list[Path]:
    paths: list[Path] = []
    try:
        root = company_root(company_dir, field=field, create=False)
    except TypeError:
        root = company_root(company_dir, create=False)
    candidates = [
        tech_dir / "source",
        tech_dir / "intake",
        root / "intake",
        root / "_company_common",
        root / "common",
    ]
    for base in candidates:
        if base.exists():
            paths.extend([p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES])
    # Keep deterministic and avoid duplicated resolved paths.
    seen: set[str] = set()
    out: list[Path] = []
    for p in sorted(paths):
        key = str(p.resolve())
        if key not in seen and p.stat().st_size <= 5_000_000:
            seen.add(key)
            out.append(p)
    return out


def _read_text_file(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        try:
            df = _load_csv(path)
            return "\n".join(" | ".join(_clean(v) for v in row) for row in df.astype(str).head(500).values.tolist())
        except Exception:
            pass
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    return ""


def _external_signal_paths(field: str, tech_dir: Path) -> list[Path]:
    """Return supported external signal files.

    Supports the legacy CSV flow and the new Excel workbook flow.
    The workbook is intended for company-by-company manual verification, while
    this loader filters rows to the company currently being analyzed.
    """
    paths: list[Path] = []
    for sub in ["tech_certifications", "certification_standards", "tech_intake"]:
        base = field_common_dir(sub, field=field, create=True)
        for name in EXTERNAL_FILENAMES + EXTERNAL_WORKBOOK_FILENAMES:
            p = base / name
            if p.exists():
                paths.append(p)
    for name in EXTERNAL_FILENAMES + EXTERNAL_WORKBOOK_FILENAMES:
        for p in [tech_dir / name, tech_dir / "source" / name, tech_dir / "intake" / name]:
            if p.exists():
                paths.append(p)
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _load_external_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        # Preferred sheet name created by scripts/create_tech_certification_workbook.py.
        # Fallback to first visible sheet if users renamed it.
        try:
            return pd.read_excel(path, sheet_name="입력_인증근거")
        except Exception:
            return pd.read_excel(path, sheet_name=0)
    return _load_csv(path)


def _row_matches_company(row: pd.Series, slug: str, display: str | None) -> bool:
    keys = ["company_dir", "slug", "company_slug", "company", "company_name", "기업명", "종목명"]
    values = {_clean(row.get(k)) for k in keys if k in row.index}
    values = {v for v in values if v}
    if not values:
        return True  # Legacy CSV without company columns: keep old behavior.
    display_clean = _clean(display)
    return slug in values or display_clean in values


def _row_has_evidence(row: pd.Series) -> bool:
    status = _clean(row.get("status") or row.get("상태") or "")
    evidence_text = _clean(row.get("evidence_text") or row.get("근거문장") or row.get("description") or row.get("note") or "")
    source_name = _clean(row.get("source_name") or row.get("출처명") or row.get("source_url") or row.get("url") or "")
    raw_cert = _clean(row.get("certification") or row.get("standard") or row.get("certification_type") or row.get("type") or row.get("인증유형") or "")
    # Rows auto-created for review should not become false evidence.
    if status.upper() in REVIEW_STATUSES and not evidence_text and not source_name:
        return False
    return bool(raw_cert and (evidence_text or source_name or status.upper() not in REVIEW_STATUSES))


def _load_external_evidence(field: str, tech_dir: Path, slug: str, display: str | None = None) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for path in _external_signal_paths(field, tech_dir):
        try:
            df = _load_external_table(path)
        except Exception:
            continue
        for _, row in df.iterrows():
            if not _row_matches_company(row, slug, display):
                continue
            if not _row_has_evidence(row):
                continue
            raw_cert = _clean(row.get("certification") or row.get("standard") or row.get("certification_type") or row.get("type") or row.get("인증유형"))
            evidence_text = _clean(row.get("evidence_text") or row.get("근거문장") or row.get("description") or row.get("note") or row.to_dict())
            default_source_type = "external_workbook" if path.suffix.lower().startswith(".xl") else "external_csv"
            source_type = _clean(row.get("source_type") or row.get("출처유형") or default_source_type)
            source_name = _clean(row.get("source_name") or row.get("출처명") or row.get("source_url") or row.get("url") or path.name)
            status = _clean(row.get("status") or row.get("상태") or "") or _status_from_text(" ".join([raw_cert, evidence_text]))
            year = row.get("year") if "year" in row.index else row.get("확인연도") if "확인연도" in row.index else None
            cert_key = None
            matched_alias = None
            haystack = " ".join([raw_cert, evidence_text])
            for key, spec in CERTIFICATION_SCHEMA.items():
                matched_alias = _contains_alias(haystack, spec.get("aliases") or [])
                if matched_alias:
                    cert_key = key
                    break
            if not cert_key:
                continue
            directness = _clean(row.get("directness") or row.get("근거직접성") or "") or _evidence_directness(source_type, evidence_text)
            confidence = _clean(row.get("confidence") or row.get("신뢰도") or "") or _confidence_from_source(source_type, directness, status)
            evidence.append({
                "certification_key": cert_key,
                "matched_alias": matched_alias,
                "category": CERTIFICATION_SCHEMA[cert_key]["category"],
                "status": status,
                "year": int(year) if str(year).strip().isdigit() else _extract_year(evidence_text),
                "expiry_date": _clean(row.get("expiry_date") or row.get("valid_until") or row.get("만료일") or ""),
                "source_type": source_type,
                "source_name": source_name,
                "source_path": str(path),
                "source_url": _clean(row.get("source_url") or row.get("url") or ""),
                "evidence_text": evidence_text[:500],
                "directness": directness,
                "confidence": confidence,
            })
    return evidence


def _scan_text_evidence(company_dir: str, field: str, tech_dir: Path) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for path in _source_paths(company_dir, field, tech_dir):
        text = _read_text_file(path)
        if not text:
            continue
        for key, spec in CERTIFICATION_SCHEMA.items():
            alias = _contains_alias(text, spec.get("aliases") or [])
            if not alias:
                continue
            snippet = _sentence_window(text, alias)
            source_type = "local_text_scan"
            status = _status_from_text(snippet)
            directness = _evidence_directness(source_type, snippet)
            confidence = _confidence_from_source(source_type, directness, status)
            evidence.append({
                "certification_key": key,
                "matched_alias": alias,
                "category": spec.get("category"),
                "status": status,
                "year": _extract_year(snippet),
                "expiry_date": "",
                "source_type": source_type,
                "source_name": path.name,
                "source_path": str(path),
                "evidence_text": snippet,
                "directness": directness,
                "confidence": confidence,
            })
    return evidence


def _dedupe_evidence(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        key = (str(r.get("certification_key")), str(r.get("source_path")), str(r.get("evidence_text"))[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _quality_gate_stage(evidence: list[dict[str, Any]]) -> tuple[int, str]:
    confirmed = [e for e in evidence if str(e.get("status")) in {"CONFIRMED", "MENTIONED", "IN_PROGRESS"}]
    keys = {str(e.get("certification_key")) for e in confirmed}
    if "SEMICONDUCTOR_QUALIFICATION" in keys:
        return 5, "SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED"
    if "CUSTOMER_QUALITY_CERTIFICATION" in keys:
        return 4, "CUSTOMER_QUALITY_CERTIFICATION_MENTIONED"
    if keys & {"FDA", "GMP", "KGMP", "IATF_16949"}:
        return 3, "SECTOR_OR_REGULATORY_CERTIFICATION_MENTIONED"
    if keys & {"UL", "CE", "RoHS", "REACH", "KC"}:
        return 2, "PRODUCT_OR_MATERIAL_COMPLIANCE_MENTIONED"
    if keys & {"ISO_9001", "ISO_14001", "ISO_45001"}:
        return 1, "GENERAL_MANAGEMENT_SYSTEM_MENTIONED"
    return 0, "NOT_PROVIDED"


def _score_evidence(evidence: list[dict[str, Any]]) -> float:
    best_by_key: dict[str, float] = {}
    for e in evidence:
        key = str(e.get("certification_key"))
        base = float(CERTIFICATION_SCHEMA.get(key, {}).get("weight", 0))
        status = str(e.get("status") or "")
        conf = str(e.get("confidence") or "")
        if status == "EXPIRED_OR_REVOKED":
            val = -min(base, 10)
        elif status == "IN_PROGRESS":
            val = base * 0.45
        elif status == "MENTIONED":
            val = base * 0.65
        else:
            val = base
        if conf == "LOW":
            val *= 0.6
        elif conf == "MEDIUM":
            val *= 0.85
        elif conf == "HIGH_NEGATIVE":
            val = -min(base, 10)
        best_by_key[key] = max(best_by_key.get(key, -999), val)
    score = sum(v for v in best_by_key.values() if v > 0) + sum(v for v in best_by_key.values() if v < 0)
    return max(0.0, min(100.0, score))


def _signal(score: float, stage: int, evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "NOT_PROVIDED"
    if any(str(e.get("status")) == "EXPIRED_OR_REVOKED" for e in evidence):
        return "CERTIFICATION_RISK_CHECK"
    if stage >= 5 or score >= 65:
        return "CERTIFICATION_STRONG"
    if stage >= 3 or score >= 35:
        return "CERTIFICATION_PARTIAL"
    if score > 0:
        return "CERTIFICATION_LIMITED"
    return "NOT_PROVIDED"


def _summary(signal: str, stage_label: str, confirmed_keys: list[str], evidence_count: int) -> str:
    if signal == "NOT_PROVIDED":
        return "기술 표준·인증 데이터가 아직 제공되지 않았습니다. 이는 감점이 아니라 확인 제한으로 처리합니다."
    names = ", ".join(confirmed_keys[:5]) if confirmed_keys else "인증/표준 근거"
    if signal == "CERTIFICATION_STRONG":
        return f"{names} 관련 근거가 확인되어 고객 품질·상용화 게이트 통과 가능성을 강하게 보강합니다. 단계: {stage_label}."
    if signal == "CERTIFICATION_PARTIAL":
        return f"{names} 관련 근거가 일부 확인되어 상용화 준비도 보조 신호로 활용할 수 있습니다. 단계: {stage_label}."
    if signal == "CERTIFICATION_RISK_CHECK":
        return f"{names} 관련 만료·취소·실효 가능성 문구가 있어 인증 상태 재확인이 필요합니다."
    return f"{names} 관련 언급은 있으나 직접 인증서/승인 근거는 제한적입니다. evidence_count={evidence_count}."


def build_certification_standard_features(
    *,
    company_dir: str,
    company: str | None = None,
    field: str = DEFAULT_FIELD,
    write: bool = True,
) -> dict[str, Any]:
    field = normalize_field_name(field)
    slug = company_dir
    display = company or slug
    tech_dir = company_agent_dir(slug, "tech", create=True)

    external = _load_external_evidence(field, tech_dir, slug, display)
    scanned = _scan_text_evidence(slug, field, tech_dir)
    evidence = _dedupe_evidence(external + scanned)
    score = _score_evidence(evidence)
    stage, stage_label = _quality_gate_stage(evidence)
    sig = _signal(score, stage, evidence)

    confirmed_keys = sorted({str(e.get("certification_key")) for e in evidence if str(e.get("status")) != "EXPIRED_OR_REVOKED"})
    expired_keys = sorted({str(e.get("certification_key")) for e in evidence if str(e.get("status")) == "EXPIRED_OR_REVOKED"})
    by_category: dict[str, int] = {}
    for e in evidence:
        by_category[str(e.get("category") or "unknown")] = by_category.get(str(e.get("category") or "unknown"), 0) + 1

    result: dict[str, Any] = {
        "feature_name": "certification_standards",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "company_dir": slug,
        "company": display,
        "status": "OK" if evidence else "NOT_PROVIDED",
        "certification_signal": sig,
        "certification_score": _safe_round(score, 2),
        "quality_gate_stage": stage,
        "quality_gate_stage_label": stage_label,
        "confirmed_certification_keys": confirmed_keys,
        "expired_or_revoked_keys": expired_keys,
        "evidence_count": len(evidence),
        "evidence_by_category": by_category,
        "summary": _summary(sig, stage_label, confirmed_keys, len(evidence)),
        "evidence": evidence,
        "schema_keys": list(CERTIFICATION_SCHEMA.keys()),
        "external_signal_paths": [str(p) for p in _external_signal_paths(field, tech_dir)],
        "interpretation_policy": {
            "missing_data_rule": "인증/표준 데이터 없음은 부정이 아니라 확인 제한으로 처리합니다.",
            "direct_evidence_rule": "공시·IR·홈페이지·수동 CSV의 인증/승인 근거는 직접 또는 회사공시 근거로 분류합니다.",
            "customer_gate_rule": "고객사 품질 인증과 반도체 qualification은 ISO 일반 인증보다 상용화 게이트 신호를 더 강하게 봅니다.",
        },
    }
    if write:
        _persist_outputs(result, tech_dir, slug)
    return result


def render_certification_md(feature: dict[str, Any]) -> str:
    lines = [
        "# Certification & Standards Features",
        "",
        f"- company: {feature.get('company')}",
        f"- status: {feature.get('status')}",
        f"- certification_signal: {feature.get('certification_signal')}",
        f"- certification_score: {feature.get('certification_score')}",
        f"- quality_gate_stage: {feature.get('quality_gate_stage')} / {feature.get('quality_gate_stage_label')}",
        f"- evidence_count: {feature.get('evidence_count')}",
        "",
        "## Summary",
        str(feature.get("summary") or ""),
        "",
        "## Confirmed Keys",
        ", ".join(feature.get("confirmed_certification_keys") or []) or "-",
        "",
        "## Evidence",
        "| certification | status | confidence | source | evidence |",
        "|---|---:|---:|---|---|",
    ]
    for e in (feature.get("evidence") or [])[:30]:
        txt = str(e.get("evidence_text") or "").replace("|", "/")[:180]
        lines.append(f"| {e.get('certification_key')} | {e.get('status')} | {e.get('confidence')} | {e.get('source_name')} | {txt} |")
    return "\n".join(lines).rstrip() + "\n"


def merge_certification_into_summary(summary: dict[str, Any], feature: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    compact = {
        "status": feature.get("status"),
        "certification_signal": feature.get("certification_signal"),
        "certification_score": feature.get("certification_score"),
        "quality_gate_stage": feature.get("quality_gate_stage"),
        "quality_gate_stage_label": feature.get("quality_gate_stage_label"),
        "confirmed_certification_keys": (feature.get("confirmed_certification_keys") or [])[:8],
        "evidence_count": feature.get("evidence_count"),
        "summary": feature.get("summary"),
    }
    summary["certification_standards"] = compact
    selected = dict(summary.get("selected_ml_signals") or {})
    selected["certification_standards"] = compact
    selected["certification_score"] = compact.get("certification_score")
    selected["certification_signal"] = compact.get("certification_signal")
    summary["selected_ml_signals"] = selected
    return summary


def _persist_outputs(feature: dict[str, Any], tech_dir: Path, slug: str) -> None:
    tech_dir.mkdir(parents=True, exist_ok=True)
    json_path = tech_dir / "tech_certification_features.json"
    md_path = tech_dir / "tech_certification_features.md"
    csv_path = tech_dir / "tech_certification_evidence.csv"

    json_path.write_text(json.dumps(feature, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_certification_md(feature), encoding="utf-8")
    if feature.get("evidence"):
        pd.json_normalize(feature.get("evidence") or []).to_csv(csv_path, index=False, encoding="utf-8-sig")

    packet_path = tech_dir / "tech_extra_intake_packet.json"
    packet: dict[str, Any] = {}
    if packet_path.exists():
        try:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
        except Exception:
            packet = {}
    packet.update({
        "company_dir": feature.get("company_dir"),
        "company": feature.get("company"),
        "field": feature.get("field"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })
    packet["certification_standards"] = {
        "status": feature.get("status"),
        "certification_signal": feature.get("certification_signal"),
        "certification_score": feature.get("certification_score"),
        "quality_gate_stage": feature.get("quality_gate_stage"),
        "quality_gate_stage_label": feature.get("quality_gate_stage_label"),
        "summary": feature.get("summary"),
        "source_file": "tech_certification_features.json",
    }
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Build certification/standards features for Tech Intake.")
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", default="")
    args = parser.parse_args()
    out = build_certification_standard_features(company_dir=args.company_dir, company=args.company or None, field=args.field, write=True)
    print(json.dumps({
        "status": out.get("status"),
        "company": out.get("company"),
        "certification_signal": out.get("certification_signal"),
        "certification_score": out.get("certification_score"),
        "quality_gate_stage": out.get("quality_gate_stage"),
        "evidence_count": out.get("evidence_count"),
    }, ensure_ascii=False, indent=2))

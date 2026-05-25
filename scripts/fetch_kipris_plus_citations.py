from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv


load_dotenv()


DEFAULT_FIELD = "반도체"
DEFAULT_COMPANY_NAME = "네패스"
DEFAULT_COMPANY_SLUG = "nepes"

ENV_KEY_NAMES = [
    "KIPRIS_PLUS_API_KEY",
    "KIPRIS_API_KEY",
    "KIPRIS_ACCESS_KEY",
    "KIPRIS_PLUS_ACCESS_KEY",
]

ENV_ENDPOINT_NAMES = [
    "KIPRIS_PLUS_CITATION_ENDPOINT",
    "KIPRIS_CITATION_ENDPOINT",
    "KIPRIS_PLUS_CITING_ENDPOINT",
]


SELF_APPLICANT_KEYWORDS = [
    "네패스",
    "nepes",
    "nepes laweh",
    "네패스라웨",
    "네패스야하드",
    "네패스하임",
    "네패스엘이디",
    "네패스이앤씨",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = text.replace("\ufeff", "").replace("\u200b", "")
    return text.strip()


def normalize_number(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""

    # pandas float-like values: 1020190019874.0 -> 1020190019874
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    text = re.sub(r"[^0-9]", "", text)
    return text


def normalize_date(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""

    if re.fullmatch(r"\d{8}\.0", text):
        text = text[:-2]

    digits = re.sub(r"[^0-9]", "", text)

    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    return text


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def get_env_first(names: list[str]) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


def project_root() -> Path:
    return Path.cwd()


def tech_dir(field: str, company_name: str) -> Path:
    return project_root() / "data" / field / company_name / "tech"


def input_bibliographic_csv(field: str, company_name: str, company_slug: str) -> Path:
    return tech_dir(field, company_name) / f"{company_slug}_kipris_bibliographic_normalized.csv"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_bibliographic_targets(path: Path, max_patents: int) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"입력 normalized CSV가 없습니다: {path}")

    df = pd.read_csv(path, dtype=str).fillna("")

    if "application_number" not in df.columns:
        raise ValueError("normalized CSV에 application_number 컬럼이 없습니다.")

    df["application_number"] = df["application_number"].map(normalize_number)

    if "register_status" not in df.columns:
        df["register_status"] = ""

    if "final_disposal" not in df.columns:
        df["final_disposal"] = ""

    if "right_holder" not in df.columns:
        if "applicant_name" in df.columns:
            df["right_holder"] = df["applicant_name"]
        else:
            df["right_holder"] = ""

    if "invention_title" not in df.columns:
        df["invention_title"] = ""

    if "ipc_number" not in df.columns:
        df["ipc_number"] = ""

    if "application_date" not in df.columns:
        df["application_date"] = ""

    if "register_date" not in df.columns:
        df["register_date"] = ""

    df = df[df["application_number"].astype(str).str.len() > 0].copy()

    # 우선순위: 등록/존속 가능 + 최근 출원 + 반도체 IPC
    def priority_score(row: pd.Series) -> float:
        status = clean_text(row.get("register_status", ""))
        final_disposal = clean_text(row.get("final_disposal", ""))
        ipc = clean_text(row.get("ipc_number", "")).upper()
        app_date = normalize_date(row.get("application_date", ""))

        score = 0.0

        if "등록" in status or "REGISTERED" in final_disposal:
            score += 30
        if "소멸" not in status and "거절" not in status and "취하" not in status:
            score += 15
        if any(code in ipc for code in ["H01L", "H10", "G06F", "C09J", "B23K"]):
            score += 20

        year = 0
        if re.match(r"\d{4}-", app_date):
            year = safe_int(app_date[:4])
        if year >= 2020:
            score += 20
        elif year >= 2015:
            score += 10

        return score

    df["_citation_fetch_priority"] = df.apply(priority_score, axis=1)
    df = df.sort_values(
        by=["_citation_fetch_priority", "application_number"],
        ascending=[False, True],
    ).reset_index(drop=True)

    if max_patents and max_patents > 0:
        df = df.head(max_patents).copy()

    return df


@dataclass
class KiprisEndpoint:
    url: str
    key: str

    @property
    def is_template(self) -> bool:
        return "{" in self.url and "}" in self.url


def get_endpoint() -> KiprisEndpoint:
    api_key = get_env_first(ENV_KEY_NAMES)
    endpoint = get_env_first(ENV_ENDPOINT_NAMES)

    if not api_key:
        raise RuntimeError(
            "KIPRIS Plus API key를 찾지 못했습니다. "
            ".env에 KIPRIS_PLUS_API_KEY=... 형태로 넣어주세요."
        )

    if not endpoint:
        raise RuntimeError(
            "KIPRIS 인용/피인용 endpoint가 설정되어 있지 않습니다.\n"
            ".env에 KIPRIS_PLUS_CITATION_ENDPOINT=... 를 추가해야 합니다.\n\n"
            "예시 형태:\n"
            "KIPRIS_PLUS_CITATION_ENDPOINT=http://plus.kipris.or.kr/openapi/rest/.../citingInfo\n\n"
            "또는 템플릿 형태:\n"
            "KIPRIS_PLUS_CITATION_ENDPOINT=http://.../citingInfo?applicationNumber={application_number}&accessKey={access_key}\n\n"
            "정확한 URL은 KIPRIS Plus에서 '특허·실용 인용문헌 / Citing Patents·Utility Models / citingInfo' "
            "서비스 신청 화면의 REST URL을 확인해서 넣으면 됩니다."
        )

    return KiprisEndpoint(url=endpoint, key=api_key)


def build_request_variants(endpoint: KiprisEndpoint, application_number: str) -> list[tuple[str, dict[str, str]]]:
    url = endpoint.url
    key = endpoint.key

    if endpoint.is_template:
        rendered = url.format(
            application_number=application_number,
            applicationNumber=application_number,
            access_key=key,
            accessKey=key,
            service_key=key,
            ServiceKey=key,
        )
        return [(rendered, {})]

    variants = [
        {"applicationNumber": application_number, "accessKey": key},
        {"applicationNumber": application_number, "ServiceKey": key},
        {"application_number": application_number, "accessKey": key},
        {"appNum": application_number, "accessKey": key},
    ]

    return [(url, params) for params in variants]


def http_get_with_fallback(
    endpoint: KiprisEndpoint,
    application_number: str,
    timeout: int,
) -> dict[str, Any]:
    last_error = ""

    for url, params in build_request_variants(endpoint, application_number):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            text = response.text or ""

            payload = {
                "request_url": response.url,
                "status_code": response.status_code,
                "ok": response.ok,
                "text": text,
                "headers": dict(response.headers),
            }

            if response.ok and text.strip():
                return payload

            last_error = f"status={response.status_code}, text={text[:300]}"
        except Exception as exc:
            last_error = repr(exc)

    return {
        "request_url": endpoint.url,
        "status_code": None,
        "ok": False,
        "text": "",
        "headers": {},
        "error": last_error,
    }


def strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def flatten_xml_element(elem: ET.Element) -> dict[str, str]:
    row: dict[str, str] = {}

    for child in elem.iter():
        tag = strip_namespace(child.tag)
        text = clean_text(child.text)
        if tag and text:
            if tag not in row:
                row[tag] = text

    return row


def parse_xml_records(text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        return []

    candidates = []
    for elem in root.iter():
        tag = strip_namespace(elem.tag).lower()
        if tag in {"item", "record", "row", "citation", "citinginfo", "citing"}:
            flat = flatten_xml_element(elem)
            if flat:
                candidates.append(flat)

    if not candidates:
        flat = flatten_xml_element(root)
        if flat:
            candidates.append(flat)

    return candidates


def parse_json_records(obj: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            lower_keys = {str(k).lower() for k in value.keys()}
            if any("citation" in k or "citing" in k or "application" in k for k in lower_keys):
                records.append(value)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)

    walk(obj)

    if not records and isinstance(obj, dict):
        records.append(obj)

    return records


def parse_response_text(text: str) -> tuple[list[dict[str, Any]], str]:
    raw = text.strip()

    if not raw:
        return [], "EMPTY_RESPONSE"

    if raw.startswith("<"):
        records = parse_xml_records(raw)
        return records, "XML"

    try:
        obj = json.loads(raw)
        records = parse_json_records(obj)
        return records, "JSON"
    except Exception:
        pass

    # CSV/TSV-like fallback
    lines = [line for line in raw.splitlines() if line.strip()]
    if len(lines) >= 2 and ("," in lines[0] or "\t" in lines[0]):
        delimiter = "\t" if "\t" in lines[0] else ","
        reader = csv.DictReader(lines, delimiter=delimiter)
        return [dict(row) for row in reader], "TEXT_TABLE"

    return [{"raw_text": raw[:2000]}], "RAW_TEXT"


FIELD_ALIASES = {
    "source_application_number": [
        "applicationNumber",
        "application_number",
        "applno",
        "출원번호",
        "원출원번호",
    ],
    "cited_application_number": [
        "citedApplicationNumber",
        "cited_application_number",
        "citedAppNum",
        "referenceApplicationNumber",
        "referenceAppNum",
        "인용문헌출원번호",
        "인용출원번호",
        "피인용대상출원번호",
    ],
    "citing_application_number": [
        "citingApplicationNumber",
        "citing_application_number",
        "citingAppNum",
        "citingApplNo",
        "피인용출원번호",
        "인용한출원번호",
        "후행출원번호",
    ],
    "citing_invention_title": [
        "citingInventionTitle",
        "citing_title",
        "inventionTitle",
        "발명의명칭",
        "명칭",
    ],
    "citing_applicant_name": [
        "citingApplicantName",
        "applicantName",
        "applicant",
        "출원인",
        "출원인명",
    ],
    "citation_date": [
        "citationDate",
        "citedDate",
        "인용일자",
        "피인용일자",
    ],
    "citation_category": [
        "citationCategory",
        "citationType",
        "kind",
        "분류",
        "문헌구분",
    ],
}


def get_by_alias(record: dict[str, Any], canonical: str) -> str:
    aliases = FIELD_ALIASES.get(canonical, [])
    normalized_lookup = {
        re.sub(r"[\s_\-./()\[\]{}:]+", "", str(k)).lower(): k
        for k in record.keys()
    }

    for alias in aliases:
        key = re.sub(r"[\s_\-./()\[\]{}:]+", "", alias).lower()
        if key in normalized_lookup:
            return clean_text(record.get(normalized_lookup[key], ""))

    # fuzzy
    for key, value in record.items():
        k = str(key).lower()
        if canonical == "citing_application_number" and "citing" in k and "application" in k:
            return clean_text(value)
        if canonical == "cited_application_number" and "cited" in k and "application" in k:
            return clean_text(value)
        if canonical == "citing_applicant_name" and "applicant" in k:
            return clean_text(value)

    return ""


def is_self_citation(applicant: str, holder: str) -> bool:
    text = f"{applicant} {holder}".lower()
    return any(keyword.lower() in text for keyword in SELF_APPLICANT_KEYWORDS)


def normalize_citation_records(
    target_row: pd.Series,
    records: list[dict[str, Any]],
    parse_type: str,
    raw_status: dict[str, Any],
) -> list[dict[str, Any]]:
    target_app = normalize_number(target_row.get("application_number", ""))
    holder = clean_text(target_row.get("right_holder", ""))
    title = clean_text(target_row.get("invention_title", ""))
    ipc = clean_text(target_row.get("ipc_number", ""))
    app_date = normalize_date(target_row.get("application_date", ""))
    reg_status = clean_text(target_row.get("register_status", ""))
    final_disposal = clean_text(target_row.get("final_disposal", ""))

    normalized: list[dict[str, Any]] = []

    for idx, record in enumerate(records, start=1):
        cited_app = normalize_number(get_by_alias(record, "cited_application_number"))
        citing_app = normalize_number(get_by_alias(record, "citing_application_number"))
        source_app = normalize_number(get_by_alias(record, "source_application_number"))

        citing_title = clean_text(get_by_alias(record, "citing_invention_title"))
        citing_applicant = clean_text(get_by_alias(record, "citing_applicant_name"))
        citation_date = normalize_date(get_by_alias(record, "citation_date"))
        citation_category = clean_text(get_by_alias(record, "citation_category"))

        # KIPRIS citingInfo가 "이 출원을 인용한 후행문헌"을 주는 경우가 일반적이므로
        # citing_app이 있으면 forward citation으로 본다.
        if not source_app:
            source_app = target_app

        if not cited_app:
            cited_app = target_app

        direction = "UNKNOWN"
        if citing_app and cited_app == target_app:
            direction = "FORWARD_CITATION"
        elif citing_app and source_app == target_app:
            direction = "FORWARD_CITATION"
        elif cited_app and cited_app != target_app:
            direction = "BACKWARD_CITATION"
        elif citing_app:
            direction = "FORWARD_CITATION_ESTIMATED"
        elif cited_app:
            direction = "BACKWARD_CITATION_ESTIMATED"

        normalized.append(
            {
                "source_application_number": target_app,
                "source_invention_title": title,
                "source_ipc_number": ipc,
                "source_application_date": app_date,
                "source_register_status": reg_status,
                "source_final_disposal": final_disposal,
                "source_right_holder": holder,
                "citation_record_index": idx,
                "citation_direction": direction,
                "cited_application_number": cited_app,
                "citing_application_number": citing_app,
                "citing_invention_title": citing_title,
                "citing_applicant_name": citing_applicant,
                "citation_date": citation_date,
                "citation_category": citation_category,
                "is_self_citation_estimated": is_self_citation(citing_applicant, holder),
                "parse_type": parse_type,
                "http_status_code": raw_status.get("status_code"),
                "request_ok": bool(raw_status.get("ok")),
                "request_url": raw_status.get("request_url", ""),
            }
        )

    return normalized


def compute_features(
    target_df: pd.DataFrame,
    citation_df: pd.DataFrame,
    company_slug: str,
    company_name: str,
    input_csv: Path,
    output_csv: Path,
) -> dict[str, Any]:
    target_count = len(target_df)

    if citation_df.empty:
        return {
            "status": "NO_CITATIONS_COLLECTED",
            "company_slug": company_slug,
            "company_name": company_name,
            "created_at": now_iso(),
            "input_csv": str(input_csv),
            "citations_csv": str(output_csv),
            "target_patent_count": target_count,
            "patents_with_citation_data": 0,
            "citation_collection_coverage": 0.0,
            "forward_citation_count_total": 0,
            "backward_citation_count_total": 0,
            "self_forward_citation_count": 0,
            "external_forward_citation_count": 0,
            "external_forward_citation_rate": 0.0,
            "avg_forward_citations_per_patent": 0.0,
            "max_forward_citations_single_patent": 0,
            "top_cited_patents": [],
            "ip_citation_impact_score_estimated": 0.0,
            "bridge_adjustment_points": 0.0,
            "bridge_signal": "IP_CITATION_DATA_NOT_AVAILABLE",
            "usage_rule": "Citation feature was not collected. Do not use as Tech-to-Value Bridge evidence.",
        }

    df = citation_df.copy()

    forward = df[df["citation_direction"].astype(str).str.contains("FORWARD", na=False)].copy()
    backward = df[df["citation_direction"].astype(str).str.contains("BACKWARD", na=False)].copy()

    patents_with_data = df["source_application_number"].nunique()
    coverage = patents_with_data / target_count if target_count else 0.0

    forward_total = len(forward)
    backward_total = len(backward)

    self_forward = int(forward["is_self_citation_estimated"].sum()) if not forward.empty else 0
    external_forward = max(0, forward_total - self_forward)
    external_rate = external_forward / forward_total if forward_total else 0.0

    forward_counts = forward.groupby("source_application_number").size().to_dict() if not forward.empty else {}
    avg_forward = forward_total / target_count if target_count else 0.0
    max_forward = max(forward_counts.values()) if forward_counts else 0

    source_meta = target_df.set_index("application_number").to_dict(orient="index")

    top_counter = Counter(forward["source_application_number"].tolist()) if not forward.empty else Counter()
    top_cited = []

    for app_no, count in top_counter.most_common(10):
        sub = forward[forward["source_application_number"] == app_no]
        external_count = int((~sub["is_self_citation_estimated"].astype(bool)).sum())
        meta = source_meta.get(app_no, {})
        top_cited.append(
            {
                "application_number": app_no,
                "forward_citation_count": int(count),
                "external_forward_citation_count": external_count,
                "self_forward_citation_count": int(count - external_count),
                "invention_title": clean_text(meta.get("invention_title", "")),
                "ipc_number": clean_text(meta.get("ipc_number", "")),
                "application_date": normalize_date(meta.get("application_date", "")),
                "register_status": clean_text(meta.get("register_status", "")),
                "final_disposal": clean_text(meta.get("final_disposal", "")),
                "right_holder": clean_text(meta.get("right_holder", "")),
            }
        )

    # 점수 설계:
    # - coverage: 수집 신뢰도
    # - citation_intensity: 피인용 총량
    # - externality: 외부 참조 비중
    # - breadth: 여러 특허가 고르게 인용되는지
    # - concentration_quality: Top 10에 집중되어도 외부인용이 있으면 핵심특허 존재로 일부 가점
    citation_intensity = math.log1p(forward_total) / math.log1p(max(10, target_count * 3)) if target_count else 0.0
    citation_intensity = min(1.0, citation_intensity)

    cited_patent_count = len(top_counter)
    breadth = cited_patent_count / target_count if target_count else 0.0
    breadth = min(1.0, breadth)

    top10_forward = sum(item["forward_citation_count"] for item in top_cited)
    top10_share = top10_forward / forward_total if forward_total else 0.0

    concentration_quality = 0.0
    if forward_total > 0:
        if 0.15 <= top10_share <= 0.75:
            concentration_quality = 1.0
        elif top10_share > 0.75:
            concentration_quality = 0.65
        else:
            concentration_quality = 0.5

    impact_score = (
        25.0 * coverage
        + 30.0 * citation_intensity
        + 25.0 * external_rate
        + 10.0 * breadth
        + 10.0 * concentration_quality
    )
    impact_score = round(max(0.0, min(100.0, impact_score)), 2)

    if impact_score >= 80 and external_forward >= max(5, target_count * 0.15):
        bridge_adjustment = 2.0
        signal = "IP_CITATION_IMPACT_STRONG_POSITIVE"
    elif impact_score >= 60:
        bridge_adjustment = 1.0
        signal = "IP_CITATION_IMPACT_POSITIVE"
    elif impact_score >= 40:
        bridge_adjustment = 0.0
        signal = "IP_CITATION_IMPACT_NEUTRAL"
    elif coverage < 0.3:
        bridge_adjustment = 0.0
        signal = "IP_CITATION_DATA_INSUFFICIENT"
    else:
        bridge_adjustment = -1.0
        signal = "IP_CITATION_IMPACT_WEAK"

    return {
        "status": "OK",
        "company_slug": company_slug,
        "company_name": company_name,
        "created_at": now_iso(),
        "input_csv": str(input_csv),
        "citations_csv": str(output_csv),
        "target_patent_count": target_count,
        "patents_with_citation_data": int(patents_with_data),
        "citation_collection_coverage": round(coverage, 4),
        "forward_citation_count_total": int(forward_total),
        "backward_citation_count_total": int(backward_total),
        "self_forward_citation_count": int(self_forward),
        "external_forward_citation_count": int(external_forward),
        "external_forward_citation_rate": round(external_rate, 4),
        "avg_forward_citations_per_patent": round(avg_forward, 4),
        "max_forward_citations_single_patent": int(max_forward),
        "cited_patent_count": int(cited_patent_count),
        "cited_patent_rate": round(breadth, 4),
        "top10_forward_citation_share": round(top10_share, 4),
        "ip_citation_impact_score_estimated": impact_score,
        "bridge_adjustment_points": bridge_adjustment,
        "bridge_signal": signal,
        "top_cited_patents": top_cited,
        "score_components": {
            "coverage": round(coverage, 4),
            "citation_intensity": round(citation_intensity, 4),
            "external_forward_citation_rate": round(external_rate, 4),
            "cited_patent_breadth": round(breadth, 4),
            "top10_concentration_quality": round(concentration_quality, 4),
        },
        "usage_rule": (
            "Use as an IP influence / market reference feature in Tech-to-Value Bridge. "
            "This is not direct commercialization evidence; combine with customer adoption, production, revenue, and FCF evidence."
        ),
    }


def write_markdown(feature: dict[str, Any], path: Path) -> None:
    lines = []
    lines.append(f"# {feature.get('company_name', '')} KIPRIS Plus 인용/피인용 기반 IP 영향력 Feature")
    lines.append("")
    lines.append(f"- status: {feature.get('status')}")
    lines.append(f"- created_at: {feature.get('created_at')}")
    lines.append(f"- input_csv: `{feature.get('input_csv')}`")
    lines.append(f"- citations_csv: `{feature.get('citations_csv')}`")
    lines.append("")
    lines.append("## 1. 수집 범위")
    lines.append("")
    lines.append(f"- target_patent_count: {feature.get('target_patent_count')}")
    lines.append(f"- patents_with_citation_data: {feature.get('patents_with_citation_data')}")
    lines.append(f"- citation_collection_coverage: {feature.get('citation_collection_coverage')}")
    lines.append("")
    lines.append("## 2. 인용/피인용 핵심 지표")
    lines.append("")
    lines.append(f"- forward_citation_count_total: {feature.get('forward_citation_count_total')}")
    lines.append(f"- backward_citation_count_total: {feature.get('backward_citation_count_total')}")
    lines.append(f"- self_forward_citation_count: {feature.get('self_forward_citation_count')}")
    lines.append(f"- external_forward_citation_count: {feature.get('external_forward_citation_count')}")
    lines.append(f"- external_forward_citation_rate: {feature.get('external_forward_citation_rate')}")
    lines.append(f"- avg_forward_citations_per_patent: {feature.get('avg_forward_citations_per_patent')}")
    lines.append(f"- max_forward_citations_single_patent: {feature.get('max_forward_citations_single_patent')}")
    lines.append("")
    lines.append("## 3. Tech-to-Value Bridge 반영")
    lines.append("")
    lines.append(f"- ip_citation_impact_score_estimated: {feature.get('ip_citation_impact_score_estimated')}")
    lines.append(f"- bridge_adjustment_points: {feature.get('bridge_adjustment_points')}")
    lines.append(f"- bridge_signal: {feature.get('bridge_signal')}")
    lines.append(f"- usage_rule: {feature.get('usage_rule')}")
    lines.append("")
    lines.append("## 4. 핵심 피인용 특허 Top 10")
    lines.append("")

    top = feature.get("top_cited_patents") or []
    if not top:
        lines.append("- 없음")
    else:
        lines.append("| rank | application_number | forward | external | self | title | status | ipc |")
        lines.append("|---:|---|---:|---:|---:|---|---|---|")
        for i, item in enumerate(top, start=1):
            title = str(item.get("invention_title", "")).replace("|", "/")[:80]
            ipc = str(item.get("ipc_number", "")).replace("|", "/")[:80]
            lines.append(
                f"| {i} | {item.get('application_number', '')} | "
                f"{item.get('forward_citation_count', 0)} | "
                f"{item.get('external_forward_citation_count', 0)} | "
                f"{item.get('self_forward_citation_count', 0)} | "
                f"{title} | {item.get('register_status', '')}/{item.get('final_disposal', '')} | {ipc} |"
            )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME)
    parser.add_argument("--company-slug", default=DEFAULT_COMPANY_SLUG)
    parser.add_argument("--max-patents", type=int, default=5, help="0이면 전체")
    parser.add_argument("--sleep-sec", type=float, default=0.3)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--endpoint", default="", help="환경변수 대신 직접 endpoint 지정")
    args = parser.parse_args()

    if args.endpoint:
        os.environ["KIPRIS_PLUS_CITATION_ENDPOINT"] = args.endpoint

    base = tech_dir(args.field, args.company_name)
    source_dir = base / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    in_csv = input_bibliographic_csv(args.field, args.company_name, args.company_slug)

    raw_jsonl = source_dir / f"{args.company_slug}_kipris_plus_citations_raw.jsonl"
    citations_csv = base / f"{args.company_slug}_kipris_citations_normalized.csv"
    feature_json = base / f"{args.company_slug}_tech_ip_citation_features.json"
    common_feature_json = base / "tech_ip_citation_features.json"
    feature_md = base / f"{args.company_slug}_tech_ip_citation_features.md"

    target_df = read_bibliographic_targets(in_csv, args.max_patents)

    endpoint = get_endpoint()

    all_rows: list[dict[str, Any]] = []
    parse_error_count = 0

    if raw_jsonl.exists() and not args.force:
        print(f"[SKIP FETCH] raw jsonl already exists: {raw_jsonl}")
        print("다시 수집하려면 --force 옵션을 붙이세요.")
    else:
        if raw_jsonl.exists():
            raw_jsonl.unlink()

        with raw_jsonl.open("w", encoding="utf-8") as f:
            for idx, row in target_df.iterrows():
                app_no = normalize_number(row.get("application_number", ""))
                print(f"[FETCH] {idx + 1}/{len(target_df)} application_number={app_no}")

                raw_status = http_get_with_fallback(endpoint, app_no, timeout=args.timeout)
                text = raw_status.get("text", "")

                records, parse_type = parse_response_text(text)
                if not records or parse_type in {"EMPTY_RESPONSE", "RAW_TEXT"}:
                    parse_error_count += 1

                normalized_rows = normalize_citation_records(
                    target_row=row,
                    records=records,
                    parse_type=parse_type,
                    raw_status=raw_status,
                )
                all_rows.extend(normalized_rows)

                f.write(
                    json.dumps(
                        {
                            "application_number": app_no,
                            "fetched_at": now_iso(),
                            "raw_status": {
                                "request_url": raw_status.get("request_url", ""),
                                "status_code": raw_status.get("status_code"),
                                "ok": raw_status.get("ok"),
                                "error": raw_status.get("error", ""),
                            },
                            "parse_type": parse_type,
                            "record_count": len(records),
                            "text_head": text[:1000],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                if args.sleep_sec > 0:
                    time.sleep(args.sleep_sec)

    if not all_rows and raw_jsonl.exists():
        # raw jsonl만 있고 normalized를 재생성해야 하는 경우:
        # 원문 재파싱은 text_head만 저장되어 불완전하므로 빈 결과로 처리.
        pass

    citation_df = pd.DataFrame(all_rows)

    if citation_df.empty:
        citation_df = pd.DataFrame(
            columns=[
                "source_application_number",
                "source_invention_title",
                "source_ipc_number",
                "source_application_date",
                "source_register_status",
                "source_final_disposal",
                "source_right_holder",
                "citation_record_index",
                "citation_direction",
                "cited_application_number",
                "citing_application_number",
                "citing_invention_title",
                "citing_applicant_name",
                "citation_date",
                "citation_category",
                "is_self_citation_estimated",
                "parse_type",
                "http_status_code",
                "request_ok",
                "request_url",
            ]
        )

    citation_df.to_csv(citations_csv, index=False, encoding="utf-8-sig")

    feature = compute_features(
        target_df=target_df,
        citation_df=citation_df,
        company_slug=args.company_slug,
        company_name=args.company_name,
        input_csv=in_csv,
        output_csv=citations_csv,
    )
    feature["parse_error_count"] = parse_error_count
    feature["raw_jsonl"] = str(raw_jsonl)

    feature_json.write_text(json.dumps(feature, ensure_ascii=False, indent=2), encoding="utf-8")
    common_feature_json.write_text(json.dumps(feature, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(feature, feature_md)

    print("[DONE] KIPRIS Plus citation features created")
    print(f"- input csv: {in_csv}")
    print(f"- raw jsonl: {raw_jsonl}")
    print(f"- citations csv: {citations_csv}")
    print(f"- feature json: {feature_json}")
    print(f"- common feature json: {common_feature_json}")
    print(f"- feature md: {feature_md}")
    print()
    print("[FEATURE SUMMARY]")
    summary_keys = [
        "status",
        "target_patent_count",
        "patents_with_citation_data",
        "citation_collection_coverage",
        "forward_citation_count_total",
        "backward_citation_count_total",
        "self_forward_citation_count",
        "external_forward_citation_count",
        "external_forward_citation_rate",
        "ip_citation_impact_score_estimated",
        "bridge_adjustment_points",
        "bridge_signal",
        "parse_error_count",
    ]
    print(json.dumps({k: feature.get(k) for k in summary_keys}, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
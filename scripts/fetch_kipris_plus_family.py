from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return str(value).strip()
    return default


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text.strip()


def _digits(value: Any) -> str:
    text = _clean_text(value)
    if text.endswith(".0") and re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return re.sub(r"\D+", "", text)


def _norm_key(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[\s_\-./()\[\]{}:]+", "", text)


def _safe_int(value: Any, default: int = 30) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(str(value).strip()))
    except Exception:
        return default


def _round4(value: float) -> float:
    return round(float(value), 4)


def _round2(value: float) -> float:
    return round(float(value), 2)


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc, dtype=str).fillna("")
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV 읽기 실패: {path} / {last_error}")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _strip_xml_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _is_sensitive_key(name: str) -> bool:
    nk = _norm_key(name)
    return nk in {
        "accesskey",
        "servicekey",
        "apikey",
        "apiaccesskey",
        "kiprisplusapikey",
        "kiprisapikey",
        "key",
    }


def _mask_url(url: str, api_key: str = "") -> str:
    if not url:
        return ""

    try:
        parts = urlsplit(url)
        query = parse_qsl(parts.query, keep_blank_values=True)

        masked_query: list[tuple[str, str]] = []
        for key, value in query:
            if _is_sensitive_key(key):
                masked_query.append((key, "***KEY***"))
            elif api_key and api_key in value:
                masked_query.append((key, value.replace(api_key, "***KEY***")))
            else:
                masked_query.append((key, value))

        masked = urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(masked_query, doseq=True),
                parts.fragment,
            )
        )

        if api_key:
            masked = masked.replace(api_key, "***KEY***")

        return masked

    except Exception:
        if api_key:
            return url.replace(api_key, "***KEY***")
        return url


def _safe_params(params: list[tuple[str, str]], api_key: str = "") -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in params:
        if _is_sensitive_key(key):
            safe[key] = "***KEY***"
        elif api_key and api_key in value:
            safe[key] = value.replace(api_key, "***KEY***")
        else:
            safe[key] = value
    return safe


def _flatten_json_records(obj: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def looks_like_family_record(d: dict[str, Any]) -> bool:
        if not d:
            return False

        keys = " ".join(str(k).lower() for k in d.keys())
        values = " ".join(
            _clean_text(v).lower()
            for v in d.values()
            if not isinstance(v, (dict, list))
        )
        combined = keys + " " + values

        markers = [
            "family", "fam", "패밀리",
            "country", "nation", "국가", "jurisdiction",
            "application", "appl", "출원",
            "publication", "공개", "공보",
            "priority", "우선권",
            "pct", "wo", "us", "jp", "ep", "cn",
            "docdb",
        ]
        return any(marker in combined for marker in markers)

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            simple = {
                k: v
                for k, v in x.items()
                if not isinstance(v, (dict, list))
            }

            if looks_like_family_record(simple):
                records.append(simple)

            for v in x.values():
                if isinstance(v, (dict, list)):
                    walk(v)

        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in records:
        sig = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        if sig not in seen:
            deduped.append(rec)
            seen.add(sig)

    return deduped


def _elem_to_dict(elem: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}

    for child in list(elem):
        key = _strip_xml_ns(child.tag)
        value = _clean_text(child.text)

        if value:
            result[key] = value

        for grand in list(child):
            gkey = _strip_xml_ns(grand.tag)
            gvalue = _clean_text(grand.text)
            if gvalue:
                result[gkey] = gvalue

    return result


def _looks_like_family_record(d: dict[str, Any]) -> bool:
    combined = (
        " ".join(str(k).lower() for k in d.keys())
        + " "
        + " ".join(_clean_text(v).lower() for v in d.values())
    )

    markers = [
        "family", "fam", "패밀리",
        "country", "nation", "국가", "jurisdiction",
        "application", "appl", "출원",
        "publication", "공개",
        "priority", "우선권",
        "pct", "wo", "us", "jp", "ep", "cn",
        "docdb",
    ]
    return any(marker in combined for marker in markers)


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()

    for rec in records:
        sig = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        if sig not in seen:
            deduped.append(rec)
            seen.add(sig)

    return deduped


def _flatten_xml_records(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    try:
        root = ET.fromstring(text)
    except Exception:
        try:
            root = ET.fromstring(text.encode("utf-8"))
        except Exception:
            return records

    # KIPRIS Plus 응답은 보통 body/items/item 구조다.
    # 우선 item 태그만 직접 추출한다.
    item_elems = [
        elem
        for elem in root.iter()
        if _strip_xml_ns(elem.tag).lower() == "item"
    ]

    if item_elems:
        for item in item_elems:
            d = _elem_to_dict(item)
            if d and _looks_like_family_record(d):
                records.append(d)
        return _dedupe_records(records)

    # item이 없는 변형 응답이면 fallback으로 모든 element를 훑는다.
    for elem in root.iter():
        d = _elem_to_dict(elem)
        if len(d) >= 2 and _looks_like_family_record(d):
            records.append(d)

    return _dedupe_records(records)


def _parse_response_text(text: str) -> list[dict[str, Any]]:
    text = _clean_text(text)
    if not text:
        return []

    try:
        obj = json.loads(text)
        return _flatten_json_records(obj)
    except Exception:
        pass

    return _flatten_xml_records(text)


def _pick(raw: dict[str, Any], aliases: list[str]) -> str:
    norm_map: dict[str, Any] = {}
    for k, v in raw.items():
        norm_map[_norm_key(k)] = v

    for alias in aliases:
        key = _norm_key(alias)
        if key in norm_map:
            return _clean_text(norm_map[key])

    for alias in aliases:
        key = _norm_key(alias)
        for nk, v in norm_map.items():
            if key and (key in nk or nk in key):
                return _clean_text(v)

    return ""


def _normalize_family_record(
    raw: dict[str, Any],
    source_application_number: str,
) -> dict[str, Any]:
    family_id = _pick(raw, [
        "family_id",
        "familyId",
        "familyNo",
        "familyNumber",
        "docdbFamilyID",
        "docdbFamilyId",
        "inpadocFamilyId",
        "패밀리번호",
        "패밀리ID",
    ])

    family_type = _pick(raw, [
        "family_type",
        "familyType",
        "relationType",
        "familyRelation",
        "패밀리구분",
        "관계구분",
    ])

    application_country_code = _pick(raw, [
        "applicationCountryCode",
        "application_country_code",
        "appCountryCode",
        "applicationCountry",
        "appCountry",
        "출원국가코드",
        "출원국",
    ])

    publication_country_code = _pick(raw, [
        "publicationCountryCode",
        "publication_country_code",
        "pubCountryCode",
        "publicationCountry",
        "pubCountry",
        "공개국가코드",
        "공보국가코드",
        "공개국",
        "공보국",
    ])

    priority_country_code = _pick(raw, [
        "priorityCountryCode",
        "priority_country_code",
        "priorityCountry",
        "우선권국가",
    ])

    country_code = _pick(raw, [
        "country_code",
        "countryCode",
        "nationCode",
        "country",
        "nation",
        "jurisdiction",
        "국가",
    ])

    if not country_code:
        country_code = publication_country_code or application_country_code or priority_country_code

    family_application_number = _pick(raw, [
        "application_number",
        "applicationNumber",
        "applicationNo",
        "appNo",
        "applNo",
        "familyApplicationNumber",
        "출원번호",
    ])

    family_application_date = _pick(raw, [
        "applicationDate",
        "application_date",
        "appDate",
        "applDate",
        "출원일자",
        "출원일",
    ])

    family_publication_number = _pick(raw, [
        "publication_number",
        "publicationNumber",
        "publicationNo",
        "pubNo",
        "openNumber",
        "공개번호",
        "공보번호",
    ])

    family_publication_date = _pick(raw, [
        "publicationDate",
        "publication_date",
        "pubDate",
        "openDate",
        "공개일자",
        "공보일자",
    ])

    family_registration_number = _pick(raw, [
        "registration_number",
        "registrationNumber",
        "registrationNo",
        "regNo",
        "registerNumber",
        "등록번호",
    ])

    priority_number = _pick(raw, [
        "priority_number",
        "priorityNumber",
        "priorityNo",
        "우선권번호",
    ])

    pct_application_number = _pick(raw, [
        "pct_application_number",
        "pctApplicationNumber",
        "pctNo",
        "pctNumber",
        "PCT",
        "PCT출원번호",
    ])

    title = _pick(raw, [
        "title",
        "inventionTitle",
        "invention_title",
        "발명의명칭",
        "명칭",
        "titleOfInvention",
    ])

    applicant = _pick(raw, [
        "applicant",
        "applicantName",
        "applicant_name",
        "출원인",
        "권리자",
    ])

    legal_status = _pick(raw, [
        "legal_status",
        "legalStatus",
        "status",
        "registerStatus",
        "상태",
        "법적상태",
    ])

    return {
        "source_application_number": source_application_number,
        "family_id": family_id,
        "family_type": family_type,
        "country_code": country_code,
        "application_country_code": application_country_code,
        "publication_country_code": publication_country_code,
        "priority_country_code": priority_country_code,
        "family_application_number": family_application_number,
        "family_application_date": family_application_date,
        "family_publication_number": family_publication_number,
        "family_publication_date": family_publication_date,
        "family_registration_number": family_registration_number,
        "priority_number": priority_number,
        "pct_application_number": pct_application_number,
        "title": title,
        "applicant": applicant,
        "legal_status": legal_status,
        "_raw_keys": "|".join(str(k) for k in raw.keys()),
    }


def _add_region_from_country_value(value: Any, jurisdictions: set[str]) -> None:
    country = _clean_text(value).upper()

    if country in {"KR", "KOR", "KOREA", "대한민국", "한국"}:
        jurisdictions.add("KR")
    elif country in {"US", "USA", "UNITED STATES", "미국"}:
        jurisdictions.add("US")
    elif country in {"JP", "JPN", "JAPAN", "일본"}:
        jurisdictions.add("JP")
    elif country in {"EP", "EPO", "EU", "EUROPE", "유럽"}:
        jurisdictions.add("EP")
    elif country in {"CN", "CHN", "CHINA", "중국"}:
        jurisdictions.add("CN")
    elif country in {"WO", "PCT", "WIPO"}:
        jurisdictions.add("WO")


def _infer_jurisdictions(row: dict[str, Any]) -> set[str]:
    jurisdictions: set[str] = set()

    for key in [
        "country_code",
        "application_country_code",
        "publication_country_code",
        "priority_country_code",
    ]:
        _add_region_from_country_value(row.get(key), jurisdictions)

    text = " ".join(_clean_text(v) for v in row.values()).upper()

    patterns = {
        "US": [r"\bUS\b", r"\bUS\d+", "UNITED STATES", "미국"],
        "JP": [r"\bJP\b", r"\bJP\d+", "JAPAN", "일본"],
        "EP": [r"\bEP\b", r"\bEP\d+", "EPO", "EUROPE", "유럽"],
        "CN": [r"\bCN\b", r"\bCN\d+", "CHINA", "중국"],
        "WO": [r"\bWO\b", r"\bWO\d+", "PCT", "WIPO"],
        "KR": [r"\bKR\b", r"\bKR\d+", "KOREA", "대한민국", "한국"],
    }

    for code, pats in patterns.items():
        for pat in pats:
            if re.search(pat, text):
                jurisdictions.add(code)

    if not jurisdictions:
        jurisdictions.add("UNKNOWN")

    return jurisdictions


def _is_overseas(jurisdictions: set[str]) -> bool:
    overseas = jurisdictions - {"KR", "UNKNOWN"}
    return len(overseas) > 0


def _score_global_extension(
    target_patent_count: int,
    patents_with_family: int,
    patents_with_overseas_family: int,
    region_codes: set[str],
    pct_patents: int,
) -> float:
    if target_patent_count <= 0:
        return 0.0

    family_coverage = patents_with_family / target_patent_count
    overseas_ratio = patents_with_overseas_family / target_patent_count
    pct_ratio = pct_patents / target_patent_count

    overseas_regions = region_codes - {"KR", "UNKNOWN"}
    region_diversity_score = min(len(overseas_regions), 5) / 5

    score = (
        family_coverage * 30
        + overseas_ratio * 40
        + region_diversity_score * 20
        + pct_ratio * 10
    )

    return _round2(max(0.0, min(100.0, score)))


def _bridge_signal(
    score: float,
    overseas_ratio: float,
    region_count: int,
) -> tuple[float, str]:
    if score >= 75 and overseas_ratio >= 0.25 and region_count >= 3:
        return 2.0, "IP_GLOBAL_EXTENSION_STRONG_POSITIVE"
    if score >= 55 and overseas_ratio >= 0.10:
        return 1.0, "IP_GLOBAL_EXTENSION_POSITIVE"
    if score >= 35:
        return 0.0, "IP_GLOBAL_EXTENSION_NEUTRAL"
    return -1.0, "IP_GLOBAL_EXTENSION_WEAK"


@dataclass
class FetchConfig:
    endpoint: str
    api_key: str
    app_param: str
    key_param: str
    timeout: int
    sleep_sec: float


def _fetch_family_raw(
    application_number: str,
    config: FetchConfig,
) -> dict[str, Any]:
    params: list[tuple[str, str]] = []

    if config.api_key:
        params.append((config.key_param, config.api_key))

    params.append((config.app_param, application_number))

    response = requests.get(
        config.endpoint,
        params=params,
        timeout=config.timeout,
    )

    return {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "application_number": application_number,
        "url": _mask_url(response.url, config.api_key),
        "request_params": _safe_params(params, config.api_key),
        "status_code": response.status_code,
        "ok": response.ok,
        "text": response.text,
    }


def _load_targets(input_csv: Path, max_patents: int) -> pd.DataFrame:
    df = _read_csv(input_csv)

    if "application_number" not in df.columns:
        raise RuntimeError(f"application_number 컬럼이 없습니다: {input_csv}")

    df["application_number"] = df["application_number"].map(_digits)
    df = df[df["application_number"] != ""].copy()
    df = df.drop_duplicates(subset=["application_number"]).reset_index(drop=True)

    if max_patents and max_patents > 0:
        df = df.head(max_patents).copy()

    return df


def _build_family_features(
    targets: pd.DataFrame,
    family_df: pd.DataFrame,
    company_slug: str,
    company_name: str,
    input_csv: Path,
    output_csv: Path,
) -> dict[str, Any]:
    target_patent_count = int(len(targets))

    if family_df.empty:
        return {
            "company_slug": company_slug,
            "company_name": company_name,
            "status": "NO_FAMILY_COLLECTED",
            "input_csv": str(input_csv),
            "family_csv": str(output_csv),
            "target_patent_count": target_patent_count,
            "family_record_count": 0,
            "patents_with_family": 0,
            "patents_with_overseas_family": 0,
            "overseas_family_record_count": 0,
            "family_collection_coverage": 0.0,
            "overseas_family_patent_rate": 0.0,
            "pct_patents": 0,
            "us_patents": 0,
            "jp_patents": 0,
            "ep_patents": 0,
            "cn_patents": 0,
            "detected_overseas_regions": [],
            "global_extension_score": 0.0,
            "bridge_adjustment_points": -1.0,
            "bridge_signal": "IP_GLOBAL_EXTENSION_DATA_NOT_AVAILABLE",
            "top_overseas_family_patents": [],
            "usage_rule": (
                "KIPRIS Plus family data was not collected. "
                "Do not add global expansion premium."
            ),
        }

    rows = family_df.to_dict(orient="records")

    source_to_regions: dict[str, set[str]] = {}
    for row in rows:
        source_app = _clean_text(row.get("source_application_number"))
        if not source_app:
            continue

        regions = _infer_jurisdictions(row)
        source_to_regions.setdefault(source_app, set()).update(regions)

    patents_with_family = len(source_to_regions)
    patents_with_overseas_family = sum(
        1
        for regions in source_to_regions.values()
        if _is_overseas(regions)
    )

    all_regions: set[str] = set()
    for regions in source_to_regions.values():
        all_regions.update(regions)

    def count_patents_by_region(code: str) -> int:
        return sum(
            1
            for regions in source_to_regions.values()
            if code in regions
        )

    pct_patents = count_patents_by_region("WO")
    us_patents = count_patents_by_region("US")
    jp_patents = count_patents_by_region("JP")
    ep_patents = count_patents_by_region("EP")
    cn_patents = count_patents_by_region("CN")

    overseas_family_record_count = 0
    for row in rows:
        if _is_overseas(_infer_jurisdictions(row)):
            overseas_family_record_count += 1

    family_collection_coverage = (
        patents_with_family / target_patent_count
        if target_patent_count
        else 0.0
    )
    overseas_family_patent_rate = (
        patents_with_overseas_family / target_patent_count
        if target_patent_count
        else 0.0
    )

    global_extension_score = _score_global_extension(
        target_patent_count=target_patent_count,
        patents_with_family=patents_with_family,
        patents_with_overseas_family=patents_with_overseas_family,
        region_codes=all_regions,
        pct_patents=pct_patents,
    )

    overseas_regions = sorted(all_regions - {"KR", "UNKNOWN"})
    bridge_points, bridge_signal = _bridge_signal(
        score=global_extension_score,
        overseas_ratio=overseas_family_patent_rate,
        region_count=len(overseas_regions),
    )

    title_map: dict[str, str] = {}
    for _, row in targets.iterrows():
        app_no = _clean_text(row.get("application_number"))
        title = _clean_text(row.get("invention_title"))
        if app_no and title:
            title_map[app_no] = title

    top_items: list[dict[str, Any]] = []
    for source_app, regions in source_to_regions.items():
        related = family_df[
            family_df["source_application_number"].astype(str) == source_app
        ].copy()

        overseas_records = []
        for _, r in related.iterrows():
            rdict = r.to_dict()
            if _is_overseas(_infer_jurisdictions(rdict)):
                overseas_records.append(rdict)

        top_items.append({
            "application_number": source_app,
            "title": title_map.get(source_app, ""),
            "family_record_count": int(len(related)),
            "overseas_family_record_count": int(len(overseas_records)),
            "jurisdictions": sorted(regions),
            "has_pct_or_wo": "WO" in regions,
            "has_us": "US" in regions,
            "has_jp": "JP" in regions,
            "has_ep": "EP" in regions,
            "has_cn": "CN" in regions,
        })

    top_items = sorted(
        top_items,
        key=lambda x: (
            x["overseas_family_record_count"],
            len(set(x["jurisdictions"]) - {"KR", "UNKNOWN"}),
            1 if x["has_pct_or_wo"] else 0,
            x["family_record_count"],
        ),
        reverse=True,
    )[:10]

    return {
        "company_slug": company_slug,
        "company_name": company_name,
        "status": "OK",
        "input_csv": str(input_csv),
        "family_csv": str(output_csv),
        "target_patent_count": target_patent_count,
        "family_record_count": int(len(family_df)),
        "patents_with_family": int(patents_with_family),
        "patents_with_overseas_family": int(patents_with_overseas_family),
        "overseas_family_record_count": int(overseas_family_record_count),
        "family_collection_coverage": _round4(family_collection_coverage),
        "overseas_family_patent_rate": _round4(overseas_family_patent_rate),
        "pct_patents": int(pct_patents),
        "us_patents": int(us_patents),
        "jp_patents": int(jp_patents),
        "ep_patents": int(ep_patents),
        "cn_patents": int(cn_patents),
        "detected_overseas_regions": overseas_regions,
        "global_extension_score": global_extension_score,
        "bridge_adjustment_points": bridge_points,
        "bridge_signal": bridge_signal,
        "top_overseas_family_patents": top_items,
        "usage_rule": (
            "Use this as an IP global expansion feature in Tech-to-Value Bridge. "
            "It indicates whether the patent portfolio has overseas family extension, "
            "but it is not direct revenue or commercialization evidence."
        ),
    }


def _build_markdown(feature: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append(
        f"# {feature.get('company_name', '')} "
        "KIPRIS Plus 패밀리 특허 / 글로벌 확장성 Feature"
    )
    lines.append("")
    lines.append("## 1. Summary")
    lines.append(f"- status: {feature.get('status')}")
    lines.append(f"- target_patent_count: {feature.get('target_patent_count')}")
    lines.append(f"- family_record_count: {feature.get('family_record_count')}")
    lines.append(f"- patents_with_family: {feature.get('patents_with_family')}")
    lines.append(
        f"- patents_with_overseas_family: "
        f"{feature.get('patents_with_overseas_family')}"
    )
    lines.append(
        f"- overseas_family_patent_rate: "
        f"{feature.get('overseas_family_patent_rate')}"
    )
    lines.append("")

    lines.append("## 2. Jurisdiction Coverage")
    lines.append(f"- PCT/WO patents: {feature.get('pct_patents')}")
    lines.append(f"- US patents: {feature.get('us_patents')}")
    lines.append(f"- JP patents: {feature.get('jp_patents')}")
    lines.append(f"- EP patents: {feature.get('ep_patents')}")
    lines.append(f"- CN patents: {feature.get('cn_patents')}")
    lines.append(
        f"- detected_overseas_regions: "
        f"{', '.join(feature.get('detected_overseas_regions', []))}"
    )
    lines.append("")

    lines.append("## 3. Tech-to-Value Bridge")
    lines.append(f"- global_extension_score: {feature.get('global_extension_score')}")
    lines.append(
        f"- bridge_adjustment_points: "
        f"{feature.get('bridge_adjustment_points')}"
    )
    lines.append(f"- bridge_signal: {feature.get('bridge_signal')}")
    lines.append(f"- usage_rule: {feature.get('usage_rule')}")
    lines.append("")

    lines.append("## 4. 핵심 해외 패밀리 보유 Top 10")
    top = feature.get("top_overseas_family_patents", []) or []

    if not top:
        lines.append("- 해외 패밀리 보유 핵심 특허가 확인되지 않았습니다.")
    else:
        for i, item in enumerate(top, start=1):
            lines.append(
                f"{i}. {item.get('application_number')} / "
                f"{item.get('title', '')} / "
                f"family={item.get('family_record_count')} / "
                f"overseas={item.get('overseas_family_record_count')} / "
                f"regions={','.join(item.get('jurisdictions', []))}"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    default_app_param = _env_first(
        "KIPRIS_PLUS_FAMILY_APP_PARAM",
        "KIPRIS_PLUS_APPNO_PARAM",
        "KIPRIS_PLUS_APP_PARAM",
        default="applicationNumber",
    )

    default_key_param = _env_first(
        "KIPRIS_PLUS_FAMILY_KEY_PARAM",
        "KIPRIS_PLUS_API_KEY_PARAM",
        "KIPRIS_PLUS_KEY_PARAM",
        default="ServiceKey",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Fetch KIPRIS Plus patent family data and build "
            "IP global extension features."
        )
    )
    parser.add_argument("--field", required=True, help="예: 반도체")
    parser.add_argument("--company-name", required=True, help="예: 네패스")
    parser.add_argument("--company-slug", required=True, help="예: nepes")
    parser.add_argument("--max-patents", type=int, default=5, help="0이면 전체")
    parser.add_argument("--sleep-sec", type=float, default=0.3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--app-param", default=default_app_param)
    parser.add_argument("--key-param", default=default_key_param)
    parser.add_argument(
        "--timeout",
        type=int,
        default=_safe_int(os.getenv("REQUEST_TIMEOUT"), 30),
    )

    args = parser.parse_args()

    tech_dir = Path("data") / args.field / args.company_name / "tech"
    source_dir = tech_dir / "source"

    input_csv = tech_dir / f"{args.company_slug}_kipris_bibliographic_normalized.csv"
    if not input_csv.exists():
        fallback = tech_dir / f"{args.company_slug}_kipris_patents_normalized.csv"
        if fallback.exists():
            input_csv = fallback
        else:
            raise FileNotFoundError(
                f"normalized KIPRIS CSV를 찾지 못했습니다: {input_csv}"
            )

    endpoint = _env_first(
        "KIPRIS_PLUS_FAMILY_URL",
        "KIPRIS_FAMILY_URL",
    )

    api_key = _env_first(
        "KIPRIS_PLUS_API_KEY",
        "KIPRIS_API_KEY",
        "KIPRIS_ACCESS_KEY",
        "KIPRIS_PLUS_SERVICE_KEY",
        "KIPRIS_SERVICE_KEY",
    )

    if not endpoint:
        print("[ERROR] KIPRIS_PLUS_FAMILY_URL 환경변수가 없습니다.")
        print("예시:")
        print(
            '$env:KIPRIS_PLUS_FAMILY_URL='
            '"KIPRIS Plus 패밀리 API URL"'
        )
        return 2

    if not api_key:
        print("[ERROR] KIPRIS Plus API 키 환경변수가 없습니다.")
        print("아래 중 하나를 .env 또는 현재 터미널에 설정하세요.")
        print("- KIPRIS_PLUS_API_KEY")
        print("- KIPRIS_API_KEY")
        print("- KIPRIS_ACCESS_KEY")
        print("주의: 키 값은 채팅에 붙여넣지 마세요.")
        return 2

    print("[CONFIG]")
    print(f"- endpoint: {endpoint}")
    print(f"- key_param: {args.key_param}")
    print(f"- app_param: {args.app_param}")
    print(f"- api_key: ***KEY***")
    print()

    targets = _load_targets(input_csv, args.max_patents)

    source_dir.mkdir(parents=True, exist_ok=True)

    raw_jsonl = source_dir / f"{args.company_slug}_kipris_plus_family_raw.jsonl"
    request_targets_csv = tech_dir / f"{args.company_slug}_kipris_plus_family_request_targets.csv"
    family_csv = tech_dir / f"{args.company_slug}_kipris_family_normalized.csv"
    feature_json = tech_dir / f"{args.company_slug}_tech_ip_family_features.json"
    common_feature_json = tech_dir / "tech_ip_family_features.json"
    feature_md = tech_dir / f"{args.company_slug}_tech_ip_family_features.md"

    targets.to_csv(request_targets_csv, index=False, encoding="utf-8-sig")

    if raw_jsonl.exists() and not args.force:
        print(
            "[SKIP] raw jsonl already exists. "
            f"Use --force to refetch: {raw_jsonl}"
        )
    else:
        config = FetchConfig(
            endpoint=endpoint,
            api_key=api_key,
            app_param=args.app_param,
            key_param=args.key_param,
            timeout=args.timeout,
            sleep_sec=args.sleep_sec,
        )

        with raw_jsonl.open("w", encoding="utf-8") as f:
            for idx, row in targets.iterrows():
                app_no = _clean_text(row.get("application_number"))
                print(
                    f"[FETCH] {idx + 1}/{len(targets)} "
                    f"application_number={app_no}"
                )

                try:
                    raw = _fetch_family_raw(app_no, config)
                except Exception as exc:
                    raw = {
                        "fetched_at": datetime.now().isoformat(timespec="seconds"),
                        "application_number": app_no,
                        "ok": False,
                        "error": repr(exc),
                        "text": "",
                    }

                f.write(json.dumps(raw, ensure_ascii=False) + "\n")
                time.sleep(args.sleep_sec)

    normalized_rows: list[dict[str, Any]] = []
    parse_error_count = 0

    with raw_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            raw = json.loads(line)
            app_no = _clean_text(raw.get("application_number"))
            text = _clean_text(raw.get("text"))

            records = _parse_response_text(text)
            if not records:
                parse_error_count += 1
                continue

            for rec in records:
                normalized = _normalize_family_record(rec, app_no)
                regions = sorted(_infer_jurisdictions(normalized))
                normalized["jurisdictions_inferred"] = "|".join(regions)
                normalized["is_overseas_family"] = (
                    "Y"
                    if _is_overseas(set(regions))
                    else "N"
                )
                normalized_rows.append(normalized)

    if normalized_rows:
        family_df = pd.DataFrame(normalized_rows).drop_duplicates()
    else:
        family_df = pd.DataFrame(columns=[
            "source_application_number",
            "family_id",
            "family_type",
            "country_code",
            "application_country_code",
            "publication_country_code",
            "priority_country_code",
            "family_application_number",
            "family_application_date",
            "family_publication_number",
            "family_publication_date",
            "family_registration_number",
            "priority_number",
            "pct_application_number",
            "title",
            "applicant",
            "legal_status",
            "jurisdictions_inferred",
            "is_overseas_family",
        ])

    family_df.to_csv(family_csv, index=False, encoding="utf-8-sig")

    feature = _build_family_features(
        targets=targets,
        family_df=family_df,
        company_slug=args.company_slug,
        company_name=args.company_name,
        input_csv=input_csv,
        output_csv=family_csv,
    )

    feature["parse_error_count"] = parse_error_count
    feature["raw_jsonl"] = str(raw_jsonl)
    feature["request_targets_csv"] = str(request_targets_csv)
    feature["created_at"] = datetime.now().isoformat(timespec="seconds")
    feature["request_config"] = {
        "endpoint": endpoint,
        "key_param": args.key_param,
        "app_param": args.app_param,
        "api_key": "***KEY***",
        "timeout": args.timeout,
        "sleep_sec": args.sleep_sec,
    }

    _write_json(feature_json, feature)
    _write_json(common_feature_json, feature)
    _write_text(feature_md, _build_markdown(feature))

    print("[DONE] KIPRIS Plus family features created")
    print(f"- input csv: {input_csv.resolve()}")
    print(f"- raw jsonl: {raw_jsonl.resolve()}")
    print(f"- family csv: {family_csv.resolve()}")
    print(f"- feature json: {feature_json.resolve()}")
    print(f"- common feature json: {common_feature_json.resolve()}")
    print(f"- feature md: {feature_md.resolve()}")
    print()
    print("[FEATURE SUMMARY]")
    print(json.dumps({
        "status": feature.get("status"),
        "target_patent_count": feature.get("target_patent_count"),
        "family_record_count": feature.get("family_record_count"),
        "patents_with_family": feature.get("patents_with_family"),
        "patents_with_overseas_family": feature.get("patents_with_overseas_family"),
        "overseas_family_patent_rate": feature.get("overseas_family_patent_rate"),
        "pct_patents": feature.get("pct_patents"),
        "us_patents": feature.get("us_patents"),
        "jp_patents": feature.get("jp_patents"),
        "ep_patents": feature.get("ep_patents"),
        "cn_patents": feature.get("cn_patents"),
        "detected_overseas_regions": feature.get("detected_overseas_regions"),
        "global_extension_score": feature.get("global_extension_score"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "bridge_signal": feature.get("bridge_signal"),
        "parse_error_count": feature.get("parse_error_count"),
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
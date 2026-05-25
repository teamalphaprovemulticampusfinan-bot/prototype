from __future__ import annotations

import argparse
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


CLAIM_TEXT_KEYS = {
    "claim",
    "claims",
    "claimtext",
    "claim_text",
    "claimcontent",
    "claim_content",
    "claimscope",
    "claim_scope",
    "claimdescription",
    "claim_description",
    "청구항",
    "청구범위",
    "청구항내용",
    "청구항전문",
}

CLAIM_NO_KEYS = {
    "claimno",
    "claim_no",
    "claimnumber",
    "claim_number",
    "claimseq",
    "claim_seq",
    "claimserialnumber",
    "claim_serial_number",
    "청구항번호",
    "청구항일련번호",
    "항번호",
}

DEPENDENCY_KEYS = {
    "dependent",
    "dependence",
    "dependentclaim",
    "dependent_claim",
    "independent",
    "independentclaim",
    "independent_claim",
    "종속항여부",
    "독립항여부",
}

CORE_TECH_KEYWORDS = [
    "반도체 패키지",
    "패키지",
    "재배선",
    "재배선층",
    "재배선 구조",
    "RDL",
    "fan-out",
    "fanout",
    "FOWLP",
    "WLP",
    "웨이퍼레벨",
    "몰딩",
    "밀봉층",
    "도전성 비아",
    "도전성 필라",
    "범프",
    "브릿지 칩",
    "EMI",
    "차폐",
    "테스트",
    "소켓",
    "레이저 컷팅",
    "소재",
    "전구체",
    "박막",
    "식각",
    "세정",
    "CMP",
]

KIPRIS_ERROR_MARKERS = {
    "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
    "INVALID_REQUEST_PARAMETER_ERROR",
    "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR",
    "SERVICE_ACCESS_DENIED_ERROR",
    "APPLICATION_ERROR",
    "NO_OPENAPI_SERVICE_ERROR",
}

AUTH_ERROR_MARKERS = {
    "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
    "SERVICE_ACCESS_DENIED_ERROR",
    "INVALID_REQUEST_PARAMETER_ERROR",
    "NO_OPENAPI_SERVICE_ERROR",
}

API_KEY_ENV_CANDIDATES = [
    "KIPRIS_PLUS_CLAIMS_API_KEY",
    "KIPRIS_PLUS_API_KEY",
    "KIPRIS_API_KEY",
    "KIPRIS_ACCESS_KEY",
    "KIPRIS_PLUS_ACCESS_KEY",
]


def _root_dir() -> Path:
    return Path.cwd()


def _tech_dir(field: str, company_name: str) -> Path:
    return _root_dir() / "data" / field / company_name / "tech"


def _clean_text(value: Any, limit: int | None = None) -> str:
    text = str(value or "")
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _norm_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_\-./()\[\]{}:]+", "", text)
    return text


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", _safe_str(value))


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return str(value).strip()
    return default


def _candidate_api_keys() -> list[tuple[str, str]]:
    forced = os.getenv("KIPRIS_PLUS_CLAIMS_API_KEY_ENV", "").strip()
    names: list[str] = []
    if forced:
        names.append(forced)
    names.extend(API_KEY_ENV_CANDIDATES)

    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        value = os.getenv(name, "").strip()
        if value:
            pairs.append((name, value))
    return pairs


def _mask_key_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


def _parse_extra_params() -> dict[str, str]:
    raw = os.getenv("KIPRIS_PLUS_EXTRA_PARAMS_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"KIPRIS_PLUS_EXTRA_PARAMS_JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("KIPRIS_PLUS_EXTRA_PARAMS_JSON은 JSON object 형태여야 합니다.")
    return {str(k): str(v) for k, v in data.items()}


def _load_input_csv(tech_dir: Path, company_slug: str) -> Path:
    candidates = [
        tech_dir / f"{company_slug}_kipris_bibliographic_normalized.csv",
        tech_dir / f"{company_slug}_kipris_patents_normalized.csv",
        tech_dir / f"{company_slug}_tech_patent_normalized.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "KIPRIS normalized CSV를 찾지 못했습니다. 확인 위치:\n"
        + "\n".join(f"- {p}" for p in candidates)
    )


def _load_patent_rows(input_csv: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(input_csv, dtype=str, encoding="utf-8-sig").fillna("")
    rows = df.to_dict(orient="records")

    clean_rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in rows:
        app_no = _digits(row.get("application_number")) or _digits(row.get("applicationNumber")) or _digits(row.get("application_no"))
        if not app_no:
            continue
        if app_no in seen:
            continue
        row = dict(row)
        row["application_number"] = app_no
        if not _safe_str(row.get("invention_title")):
            row["invention_title"] = _safe_str(row.get("title")) or _safe_str(row.get("발명의명칭"))
        if not _safe_str(row.get("right_holder")):
            row["right_holder"] = _safe_str(row.get("applicant")) or _safe_str(row.get("applicant_name")) or _safe_str(row.get("출원인"))
        seen.add(app_no)
        clean_rows.append(row)

    return clean_rows


def _write_request_targets(
    *,
    tech_dir: Path,
    company_slug: str,
    rows: list[dict[str, Any]],
) -> Path:
    out_path = tech_dir / f"{company_slug}_kipris_plus_claim_request_targets.csv"
    cols = [
        "application_number",
        "open_number",
        "register_number",
        "register_status",
        "final_disposal",
        "invention_title",
        "right_holder",
    ]

    target_rows = []
    for row in rows:
        target_rows.append({col: _safe_str(row.get(col)) for col in cols})

    pd.DataFrame(target_rows).to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def _build_request_params(
    row: dict[str, Any],
    *,
    api_key: str,
    key_param: str,
    appno_param: str,
) -> dict[str, str]:
    if not api_key:
        raise RuntimeError(".env에 KIPRIS Plus API 키가 없습니다. KIPRIS_PLUS_CLAIMS_API_KEY 또는 KIPRIS_PLUS_API_KEY를 설정하세요.")

    app_no = _digits(row.get("application_number"))
    open_no = _digits(row.get("open_number"))
    reg_no = _digits(row.get("register_number"))

    params: dict[str, str] = {
        key_param: api_key,
        appno_param: app_no,
    }

    if open_no:
        params.setdefault("openNumber", open_no)
        params.setdefault("publicationNumber", open_no)
    if reg_no:
        params.setdefault("registerNumber", reg_no)
        params.setdefault("registrationNumber", reg_no)

    params.update(_parse_extra_params())
    return params


def _mask_url(url: str) -> str:
    if not url:
        return ""
    try:
        key_values = {value for _, value in _candidate_api_keys() if value}
        parts = urlsplit(url)
        pairs = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if _norm_key(key) in {"servicekey", "accesskey", "apikey", "key"} or value in key_values:
                pairs.append((key, "***KEY***"))
            else:
                pairs.append((key, value))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))
    except Exception:
        masked = url
        for _, value in _candidate_api_keys():
            if value:
                masked = masked.replace(value, "***KEY***")
        return masked


def _response_result(text: str) -> tuple[str, str]:
    if not text:
        return "", ""
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        try:
            root = ET.fromstring(text)
        except Exception:
            return "", ""

    result_code = ""
    result_msg = ""
    for elem in root.iter():
        tag = _norm_key(_local_name(elem.tag))
        if tag == "resultcode":
            result_code = _clean_text("".join(elem.itertext()))
        elif tag == "resultmsg":
            result_msg = _clean_text("".join(elem.itertext()))
    return result_code, result_msg


def _is_success_response(text: str) -> bool:
    code, msg = _response_result(text)
    if not code and not msg:
        return bool(text and len(text) > 30)
    if code in {"00", "0"}:
        return True
    return "success" in msg.lower() or "normal service" in msg.lower()


def _is_key_or_param_error(text: str) -> bool:
    _, msg = _response_result(text)
    upper = str(text or "").upper() + " " + msg.upper()
    return any(marker in upper for marker in KIPRIS_ERROR_MARKERS)


def _request_with_params(endpoint: str, params: dict[str, str], timeout: int) -> tuple[int | None, str, str]:
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
    except Exception as exc:
        return None, f"[REQUEST_ERROR] {exc}", ""

    text = response.text or ""
    if response.status_code >= 400:
        return response.status_code, text[:3000], _mask_url(response.url)

    return response.status_code, text, _mask_url(response.url)


def _request_one(
    *,
    endpoint: str,
    row: dict[str, Any],
    timeout: int,
    key_param: str,
    appno_param: str,
    retry_param_variants: bool,
) -> tuple[int | None, str, str, str, str, str]:
    api_keys = _candidate_api_keys()
    if not api_keys:
        raise RuntimeError("KIPRIS Plus API 키가 없습니다. .env에 KIPRIS_PLUS_CLAIMS_API_KEY 또는 KIPRIS_PLUS_API_KEY를 설정하세요.")

    key_variants = [key_param]
    if retry_param_variants:
        key_variants += ["ServiceKey", "accessKey", "serviceKey", "AccessKey", "apiKey"]
    app_variants = [appno_param]
    if retry_param_variants:
        app_variants += ["applicationNumber", "applicationNo", "application_number", "appNum", "appNo", "applicationnum"]

    seen: set[tuple[str, str, str]] = set()
    last: tuple[int | None, str, str, str, str, str] | None = None

    for api_key_env, api_key in api_keys:
        for kp in key_variants:
            for ap in app_variants:
                token = (api_key_env, kp, ap)
                if token in seen:
                    continue
                seen.add(token)
                params = _build_request_params(row, api_key=api_key, key_param=kp, appno_param=ap)
                status_code, text, url = _request_with_params(endpoint, params, timeout)
                last = (status_code, text, url, api_key_env, kp, ap)

                if _is_success_response(text):
                    return last

                # If retry is disabled, return the first result immediately.
                if not retry_param_variants:
                    return last

    assert last is not None
    return last


def _local_name(tag: str) -> str:
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    return tag


def _elem_text(elem: ET.Element) -> str:
    return _clean_text(" ".join(t for t in elem.itertext() if t))


def _xml_children_dict(elem: ET.Element) -> dict[str, str]:
    data: dict[str, str] = {}
    for child in list(elem):
        key = _norm_key(_local_name(child.tag))
        value = _elem_text(child)
        if key and value:
            data[key] = value
    return data


def _first_value(record: dict[str, Any], keys: set[str]) -> str:
    norm_map = {_norm_key(k): v for k, v in record.items()}
    for key in keys:
        norm = _norm_key(key)
        if norm in norm_map:
            value = _clean_text(norm_map[norm])
            if value:
                return value
    return ""


def _extract_claim_records_from_xml(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        try:
            root = ET.fromstring(text)
        except Exception:
            return []

    records: list[dict[str, Any]] = []

    for elem in root.iter():
        child_data = _xml_children_dict(elem)
        if not child_data:
            continue

        has_claim_text = any(_norm_key(k) in {_norm_key(x) for x in CLAIM_TEXT_KEYS} for k in child_data)
        if has_claim_text:
            child_data["__container_tag"] = _local_name(elem.tag)
            records.append(child_data)

    if not records:
        for elem in root.iter():
            tag = _norm_key(_local_name(elem.tag))
            value = _elem_text(elem)
            if tag in {_norm_key(x) for x in CLAIM_TEXT_KEYS} and len(value) >= 20:
                records.append({"claim_text": value, "__container_tag": _local_name(elem.tag)})

    return records


def _walk_json_objects(obj: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    if isinstance(obj, dict):
        found.append(obj)
        for value in obj.values():
            found.extend(_walk_json_objects(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk_json_objects(item))

    return found


def _extract_claim_records_from_json(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except Exception:
        return []

    records: list[dict[str, Any]] = []
    for obj in _walk_json_objects(data):
        norm_keys = {_norm_key(k) for k in obj.keys()}
        if norm_keys & {_norm_key(x) for x in CLAIM_TEXT_KEYS}:
            records.append(obj)

    return records


def _extract_claim_text_from_record(record: dict[str, Any]) -> str:
    direct = _first_value(record, CLAIM_TEXT_KEYS)
    if direct:
        return direct

    for key, value in record.items():
        nk = _norm_key(key)
        text = _clean_text(value)
        if "claim" in nk and len(text) >= 20:
            return text
        if "청구" in str(key) and len(text) >= 20:
            return text

    return ""


def _extract_claim_no_from_record(record: dict[str, Any], fallback_no: int) -> int:
    value = _first_value(record, CLAIM_NO_KEYS)
    if value:
        m = re.search(r"\d+", value)
        if m:
            return int(m.group())
    claim_text = _extract_claim_text_from_record(record)
    m = re.match(r"\s*(\d+)\s*[.항)]", claim_text)
    if m:
        return int(m.group(1))
    return fallback_no


def _explicit_dependency_value(record: dict[str, Any]) -> str:
    return _first_value(record, DEPENDENCY_KEYS)


def _infer_is_dependent(claim_text: str, explicit_value: str = "") -> bool:
    text = _clean_text(claim_text)

    ev = explicit_value.strip().lower()
    if ev:
        if ev in {"y", "yes", "true", "1", "dependent", "종속", "종속항"}:
            return True
        if ev in {"n", "no", "false", "0", "independent", "독립", "독립항"}:
            return False
        if "종속" in ev:
            return True
        if "독립" in ev:
            return False

    dependent_patterns = [
        r"제\s*\d+\s*항에\s*있어서",
        r"제\s*\d+\s*항\s*내지\s*제\s*\d+\s*항",
        r"제\s*\d+\s*항\s*또는\s*제\s*\d+\s*항",
        r"청구항\s*\d+\s*에\s*있어서",
        r"어느\s*한\s*항에\s*있어서",
        r"어느\s*한\s*항의",
        r"전항에\s*있어서",
    ]
    return any(re.search(pattern, text) for pattern in dependent_patterns)


def _extract_claims_from_response(
    *,
    response_text: str,
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    if not _is_success_response(response_text):
        return []

    records = _extract_claim_records_from_json(response_text)
    if not records:
        records = _extract_claim_records_from_xml(response_text)

    claims: list[dict[str, Any]] = []
    for i, record in enumerate(records, start=1):
        claim_text = _extract_claim_text_from_record(record)
        if not claim_text or len(claim_text) < 10:
            continue

        claim_no = _extract_claim_no_from_record(record, i)
        explicit = _explicit_dependency_value(record)
        is_dependent = _infer_is_dependent(claim_text, explicit)
        is_independent = not is_dependent

        claims.append(
            {
                "application_number": _digits(row.get("application_number")),
                "open_number": _digits(row.get("open_number")),
                "register_number": _digits(row.get("register_number")),
                "register_status": _safe_str(row.get("register_status")),
                "final_disposal": _safe_str(row.get("final_disposal")),
                "invention_title": _safe_str(row.get("invention_title")) or _safe_str(row.get("title")),
                "right_holder": _safe_str(row.get("right_holder")) or _safe_str(row.get("applicant_name")) or _safe_str(row.get("applicant")),
                "claim_no": claim_no,
                "claim_text": claim_text,
                "claim_char_len": len(claim_text),
                "is_dependent_estimated": bool(is_dependent),
                "is_independent_estimated": bool(is_independent),
                "dependency_source": "explicit_or_regex_estimated",
            }
        )

    claims = sorted(claims, key=lambda x: int(x.get("claim_no") or 9999))
    return claims


def _count_keyword_matches(text: str) -> int:
    lower = text.lower()
    count = 0
    for kw in CORE_TECH_KEYWORDS:
        if kw.lower() in lower:
            count += 1
    return count


def _score_claim_defense(
    *,
    claim_count: int,
    independent_claim_count: int,
    avg_independent_claim_chars: float,
    core_keyword_claim_rate: float,
    registered_claim_patent_rate: float,
) -> float:
    independent_score = min(35.0, independent_claim_count * 7.0)
    length_score = min(25.0, avg_independent_claim_chars / 40.0)
    keyword_score = min(25.0, core_keyword_claim_rate * 25.0)
    registered_score = min(15.0, registered_claim_patent_rate * 15.0)

    score = independent_score + length_score + keyword_score + registered_score

    if claim_count == 0:
        return 0.0
    if claim_count < 3:
        score = min(score, 45.0)

    return round(max(0.0, min(100.0, score)), 2)


def _build_features(
    *,
    claims_df: pd.DataFrame,
    target_patent_count: int,
    source_endpoint: str,
) -> dict[str, Any]:
    if claims_df.empty:
        return {
            "feature_name": "ip_claim_scope_features",
            "status": "NO_CLAIMS_COLLECTED",
            "source_endpoint_host": urlparse(source_endpoint).netloc if source_endpoint else "",
            "target_patent_count": target_patent_count,
            "patents_with_claims": 0,
            "claim_collection_coverage": 0.0,
            "claim_count": 0,
            "independent_claim_count_estimated": 0,
            "dependent_claim_count_estimated": 0,
            "claim_defense_score_estimated": 0.0,
            "bridge_adjustment_points": 0.0,
            "bridge_signal": "IP_CLAIM_DATA_NOT_AVAILABLE",
            "usage_rule": "청구항 데이터가 수집되지 않아 Tech-to-Value Bridge 가산에 사용하지 않습니다.",
        }

    df = claims_df.copy()
    df["claim_char_len"] = pd.to_numeric(df["claim_char_len"], errors="coerce").fillna(0)
    df["keyword_match_count"] = df["claim_text"].map(_count_keyword_matches)
    df["has_core_keyword"] = df["keyword_match_count"] > 0

    patents_with_claims = df["application_number"].nunique()
    claim_count = len(df)
    independent_df = df[df["is_independent_estimated"] == True].copy()
    independent_claim_count = len(independent_df)

    avg_claim_chars = round(float(df["claim_char_len"].mean()), 2) if claim_count else 0.0
    avg_independent_claim_chars = (
        round(float(independent_df["claim_char_len"].mean()), 2) if independent_claim_count else 0.0
    )

    core_keyword_claim_rate = round(float(df["has_core_keyword"].mean()), 4) if claim_count else 0.0

    patent_level = df.groupby("application_number").agg(
        claim_count=("claim_no", "count"),
        independent_claim_count=("is_independent_estimated", "sum"),
        has_core_keyword=("has_core_keyword", "max"),
        register_status=("register_status", "first"),
        final_disposal=("final_disposal", "first"),
        invention_title=("invention_title", "first"),
    ).reset_index()

    registered_mask = patent_level["register_status"].astype(str).str.contains("등록", na=False) | patent_level[
        "final_disposal"
    ].astype(str).str.contains("REGISTERED", na=False)
    registered_claim_patent_rate = round(float(registered_mask.mean()), 4) if len(patent_level) else 0.0

    claim_defense_score = _score_claim_defense(
        claim_count=claim_count,
        independent_claim_count=independent_claim_count,
        avg_independent_claim_chars=avg_independent_claim_chars,
        core_keyword_claim_rate=core_keyword_claim_rate,
        registered_claim_patent_rate=registered_claim_patent_rate,
    )

    if claim_defense_score >= 80:
        bridge_adjustment = 2.0
        bridge_signal = "IP_CLAIM_SCOPE_STRONG"
    elif claim_defense_score >= 65:
        bridge_adjustment = 1.0
        bridge_signal = "IP_CLAIM_SCOPE_POSITIVE"
    elif claim_defense_score >= 45:
        bridge_adjustment = 0.0
        bridge_signal = "IP_CLAIM_SCOPE_NEUTRAL"
    else:
        bridge_adjustment = -1.0
        bridge_signal = "IP_CLAIM_SCOPE_WEAK_OR_INSUFFICIENT"

    top_core_claims = []
    core_df = df[df["has_core_keyword"] == True].copy()
    if not core_df.empty:
        core_df = core_df.sort_values(
            ["is_independent_estimated", "keyword_match_count", "claim_char_len"],
            ascending=[False, False, False],
        )
        for _, row in core_df.head(8).iterrows():
            top_core_claims.append(
                {
                    "application_number": row.get("application_number"),
                    "claim_no": int(row.get("claim_no") or 0),
                    "is_independent_estimated": bool(row.get("is_independent_estimated")),
                    "keyword_match_count": int(row.get("keyword_match_count") or 0),
                    "invention_title": _clean_text(row.get("invention_title"), 120),
                    "claim_text_preview": _clean_text(row.get("claim_text"), 260),
                }
            )

    top_titles = Counter(str(x) for x in patent_level["invention_title"].dropna().tolist() if str(x).strip())

    return {
        "feature_name": "ip_claim_scope_features",
        "status": "OK",
        "source_endpoint_host": urlparse(source_endpoint).netloc if source_endpoint else "",
        "target_patent_count": int(target_patent_count),
        "patents_with_claims": int(patents_with_claims),
        "claim_collection_coverage": round(patents_with_claims / target_patent_count, 4) if target_patent_count else 0.0,
        "claim_count": int(claim_count),
        "independent_claim_count_estimated": int(independent_claim_count),
        "dependent_claim_count_estimated": int(claim_count - independent_claim_count),
        "avg_claim_chars": avg_claim_chars,
        "avg_independent_claim_chars": avg_independent_claim_chars,
        "core_keyword_claim_rate": core_keyword_claim_rate,
        "registered_claim_patent_rate": registered_claim_patent_rate,
        "claim_defense_score_estimated": claim_defense_score,
        "bridge_adjustment_points": bridge_adjustment,
        "bridge_signal": bridge_signal,
        "usage_rule": (
            "청구항 전문 기반 지표는 특허의 방어범위와 핵심기술 보호 가능성을 보조적으로 평가합니다. "
            "다만 고객 채택·양산·매출 전환의 직접 증거는 아니므로 Tech-to-Value Bridge에는 보수적 가산/감산만 적용합니다."
        ),
        "top_core_claims": top_core_claims,
        "top_invention_titles_with_claims": dict(top_titles.most_common(10)),
    }


def _write_feature_md(path: Path, features: dict[str, Any], company_name: str) -> None:
    lines = [
        f"# {company_name} KIPRIS Plus 청구항 기반 IP 방어력 Feature",
        "",
        "## 1. 핵심 지표",
        "",
        f"- status: {features.get('status')}",
        f"- target_patent_count: {features.get('target_patent_count')}",
        f"- patents_with_claims: {features.get('patents_with_claims')}",
        f"- claim_collection_coverage: {features.get('claim_collection_coverage')}",
        f"- claim_count: {features.get('claim_count')}",
        f"- independent_claim_count_estimated: {features.get('independent_claim_count_estimated')}",
        f"- dependent_claim_count_estimated: {features.get('dependent_claim_count_estimated')}",
        f"- avg_claim_chars: {features.get('avg_claim_chars')}",
        f"- avg_independent_claim_chars: {features.get('avg_independent_claim_chars')}",
        f"- core_keyword_claim_rate: {features.get('core_keyword_claim_rate')}",
        f"- registered_claim_patent_rate: {features.get('registered_claim_patent_rate')}",
        "",
        "## 2. Tech-to-Value Bridge 반영",
        "",
        f"- claim_defense_score_estimated: {features.get('claim_defense_score_estimated')}",
        f"- bridge_adjustment_points: {features.get('bridge_adjustment_points')}",
        f"- bridge_signal: {features.get('bridge_signal')}",
        f"- usage_rule: {features.get('usage_rule')}",
        "",
        "## 3. 핵심기술 관련 대표 청구항",
        "",
    ]

    top_core_claims = features.get("top_core_claims") or []
    if not top_core_claims:
        lines.append("- 수집된 청구항 중 핵심기술 키워드 매칭 청구항이 확인되지 않았습니다.")
    else:
        for item in top_core_claims:
            lines.append(
                f"- [{item.get('application_number')}] claim {item.get('claim_no')} "
                f"/ independent={item.get('is_independent_estimated')} "
                f"/ keyword_matches={item.get('keyword_match_count')} "
                f"/ {item.get('invention_title')}: {item.get('claim_text_preview')}"
            )

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    default_key_param = _env_first(
        "KIPRIS_PLUS_CLAIMS_KEY_PARAM",
        "KIPRIS_PLUS_API_KEY_PARAM",
        "KIPRIS_PLUS_KEY_PARAM",
        default="ServiceKey",
    )
    default_app_param = _env_first(
        "KIPRIS_PLUS_CLAIMS_APP_PARAM",
        "KIPRIS_PLUS_APPNO_PARAM",
        "KIPRIS_PLUS_APP_PARAM",
        default="applicationNumber",
    )

    parser = argparse.ArgumentParser(
        description="Fetch KIPRIS Plus claim text and build claim-scope Tech ML features."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-name", default="네패스")
    parser.add_argument("--company-slug", default="nepes")
    parser.add_argument("--max-patents", type=int, default=0, help="0이면 전체")
    parser.add_argument("--sleep-sec", type=float, default=0.25)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--key-param", default=default_key_param)
    parser.add_argument("--app-param", default=default_app_param)
    parser.add_argument("--no-param-variant-retry", action="store_true")
    args = parser.parse_args()

    tech_dir = _tech_dir(args.field, args.company_name)
    tech_dir.mkdir(parents=True, exist_ok=True)
    source_dir = tech_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    input_csv = _load_input_csv(tech_dir, args.company_slug)
    patent_rows = _load_patent_rows(input_csv)

    if args.max_patents and args.max_patents > 0:
        patent_rows = patent_rows[: args.max_patents]

    request_targets_path = _write_request_targets(
        tech_dir=tech_dir,
        company_slug=args.company_slug,
        rows=patent_rows,
    )

    endpoint = os.getenv("KIPRIS_PLUS_CLAIMS_ENDPOINT", "").strip()

    if not endpoint:
        print("[STOP] .env에 KIPRIS_PLUS_CLAIMS_ENDPOINT가 아직 없습니다.")
        print("KIPRIS Plus 포털에서 청구항/전문 조회 REST endpoint를 확인한 뒤 .env에 넣어주세요.")
        print(f"- request target csv: {request_targets_path}")
        print(f"- input csv: {input_csv}")
        return 2

    raw_jsonl = source_dir / f"{args.company_slug}_kipris_plus_claims_raw.jsonl"
    claims_csv = tech_dir / f"{args.company_slug}_kipris_claims_normalized.csv"
    features_json = tech_dir / f"{args.company_slug}_tech_ip_claim_features.json"
    common_features_json = tech_dir / "tech_ip_claim_features.json"
    features_md = tech_dir / f"{args.company_slug}_tech_ip_claim_features.md"

    if raw_jsonl.exists() and not args.force:
        print(f"[INFO] 기존 raw jsonl 사용: {raw_jsonl}")
        print("[INFO] 전체 재수집이 필요하면 --force 옵션을 사용하세요.")
    else:
        with raw_jsonl.open("w", encoding="utf-8") as f:
            for idx, row in enumerate(patent_rows, start=1):
                app_no = _digits(row.get("application_number"))
                print(f"[FETCH] {idx}/{len(patent_rows)} application_number={app_no}")

                status_code, response_text, request_url, used_api_key_env, used_key_param, used_app_param = _request_one(
                    endpoint=endpoint,
                    row=row,
                    timeout=args.timeout,
                    key_param=args.key_param,
                    appno_param=args.app_param,
                    retry_param_variants=not args.no_param_variant_retry,
                )

                result_code, result_msg = _response_result(response_text)
                item = {
                    "application_number": app_no,
                    "status_code": status_code,
                    "result_code": result_code,
                    "result_msg": result_msg,
                    "request_url": request_url,
                    "used_api_key_env": used_api_key_env,
                    "used_key_param": used_key_param,
                    "used_app_param": used_app_param,
                    "request_row": row,
                    "response_text": response_text,
                }
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                time.sleep(max(0.0, args.sleep_sec))

    all_claims: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    success_response_count = 0

    with raw_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            row = item.get("request_row") or {}
            response_text = item.get("response_text") or ""
            status_code = item.get("status_code")
            result_code = item.get("result_code") or _response_result(response_text)[0]
            result_msg = item.get("result_msg") or _response_result(response_text)[1]

            if _is_success_response(response_text):
                success_response_count += 1

            claims = _extract_claims_from_response(response_text=response_text, row=row)
            if claims:
                all_claims.extend(claims)
            else:
                errors.append(
                    {
                        "application_number": item.get("application_number"),
                        "status_code": status_code,
                        "result_code": result_code,
                        "result_msg": result_msg,
                        "request_url": item.get("request_url", ""),
                        "used_api_key_env": item.get("used_api_key_env", ""),
                        "used_key_param": item.get("used_key_param", ""),
                        "used_app_param": item.get("used_app_param", ""),
                        "response_preview": _clean_text(response_text, 300),
                    }
                )

    claims_df = pd.DataFrame(all_claims)
    if not claims_df.empty:
        claims_df = claims_df.sort_values(["application_number", "claim_no"])
    else:
        claims_df = pd.DataFrame(
            columns=[
                "application_number",
                "open_number",
                "register_number",
                "register_status",
                "final_disposal",
                "invention_title",
                "right_holder",
                "claim_no",
                "claim_text",
                "claim_char_len",
                "is_dependent_estimated",
                "is_independent_estimated",
                "dependency_source",
            ]
        )
    claims_df.to_csv(claims_csv, index=False, encoding="utf-8-sig")

    features = _build_features(
        claims_df=claims_df,
        target_patent_count=len(patent_rows),
        source_endpoint=endpoint,
    )

    if claims_df.empty and errors:
        msg_blob = " ".join(str(e.get("result_msg", "")) + " " + str(e.get("response_preview", "")) for e in errors[:50]).upper()
        if any(marker in msg_blob for marker in AUTH_ERROR_MARKERS):
            features["status"] = "CLAIMS_API_AUTH_OR_PARAMETER_FAILED"
            features["bridge_signal"] = "IP_CLAIM_API_AUTH_OR_PARAMETER_FAILED"
            features["failure_reason"] = (
                "KIPRIS Plus Claims API returned authentication/parameter errors for all sampled requests. "
                "Run scripts/probe_kipris_plus_claims_params.py to identify the working key/env/parameter combination."
            )
    features["company_slug"] = args.company_slug
    features["company_name"] = args.company_name
    features["input_csv"] = str(input_csv)
    features["claims_csv"] = str(claims_csv)
    features["raw_jsonl"] = str(raw_jsonl)
    features["success_response_count"] = success_response_count
    features["parse_error_count"] = len(errors)
    features["parse_errors_sample"] = errors[:20]
    features["request_config"] = {
        "key_param": args.key_param,
        "app_param": args.app_param,
        "param_variant_retry": not args.no_param_variant_retry,
        "api_key_env_candidates_with_values": [name for name, _ in _candidate_api_keys()],
        "api_key": "***KEY***",
    }

    features_json.write_text(json.dumps(features, ensure_ascii=False, indent=2), encoding="utf-8")
    common_features_json.write_text(json.dumps(features, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_feature_md(features_md, features, args.company_name)

    print("[DONE] KIPRIS Plus claim features created")
    print(f"- input csv: {input_csv}")
    print(f"- raw jsonl: {raw_jsonl}")
    print(f"- claims csv: {claims_csv}")
    print(f"- feature json: {features_json}")
    print(f"- common feature json: {common_features_json}")
    print(f"- feature md: {features_md}")
    print()
    print("[FEATURE SUMMARY]")
    print(
        json.dumps(
            {
                "status": features.get("status"),
                "target_patent_count": features.get("target_patent_count"),
                "success_response_count": features.get("success_response_count"),
                "patents_with_claims": features.get("patents_with_claims"),
                "claim_collection_coverage": features.get("claim_collection_coverage"),
                "claim_count": features.get("claim_count"),
                "independent_claim_count_estimated": features.get("independent_claim_count_estimated"),
                "claim_defense_score_estimated": features.get("claim_defense_score_estimated"),
                "bridge_adjustment_points": features.get("bridge_adjustment_points"),
                "bridge_signal": features.get("bridge_signal"),
                "parse_error_count": features.get("parse_error_count"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

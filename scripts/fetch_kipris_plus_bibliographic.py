from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from common.data_paths import company_agent_dir, company_config_path, normalize_field_name, rel_project_path
except Exception:  # pragma: no cover
    company_agent_dir = None  # type: ignore
    company_config_path = None  # type: ignore
    normalize_field_name = lambda value=None, default="반도체": str(value or default).strip() or default  # type: ignore
    rel_project_path = lambda value: str(value)  # type: ignore

DEFAULT_FIELD = "반도체"

# KIPRIS Plus public/register bibliographic service is configured mainly by env.
# Built-in candidates are intentionally conservative guesses; when KIPRIS portal
# shows an exact URL in the API spec, put it in KIPRIS_PLUS_BIBLIO_ENDPOINT(S).
DEFAULT_ENDPOINT_CANDIDATES = [
    "http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/applicantNameSearchInfo",
    "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getApplicantNameSearch",
    "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getWordSearch",
    "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/patUtiModInfoSearchSevice/applSearchList",
    "http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/applSearchList",
]

OUTPUT_COLUMNS = [
    "application_number",
    "application_no",
    "open_number",
    "publication_no",
    "register_number",
    "registration_no",
    "register_status",
    "final_disposal",
    "legal_status",
    "invention_title",
    "title",
    "right_holder",
    "applicant",
    "inventor",
    "application_date",
    "application_year",
    "open_date",
    "publication_date",
    "register_date",
    "registration_date",
    "ipc_number",
    "ipc",
    "cpc_number",
    "cpc",
    "abstract",
    "claim_text",
    "claims",
    "url",
    "drawing",
    "is_registered",
    "is_alive_estimated",
    "has_negative_disposal_estimated",
    "tech_keyword_match_count",
    "source_file",
    "source_sheet",
    "source_row",
]

FIELD_ALIASES: dict[str, list[str]] = {
    "application_number": ["applicationNumber", "application_number", "appNo", "app_no", "applNo", "출원번호"],
    "open_number": ["openNumber", "openingNumber", "publicationNumber", "publication_number", "pubNo", "공개번호", "공개번호"],
    "register_number": ["registerNumber", "registrationNumber", "registration_number", "regNo", "등록번호"],
    "register_status": ["registerStatus", "registrationStatus", "status", "등록상태", "법적상태"],
    "final_disposal": ["finalDisposal", "finalStatus", "disposal", "registerStatus", "처분상태", "최종상태", "권리상태"],
    "invention_title": ["inventionTitle", "inventionName", "title", "patentTitle", "발명의명칭", "발명명칭", "명칭"],
    "right_holder": ["applicantName", "applicant", "rightHolder", "assignee", "owner", "registerOwner", "출원인", "권리자", "등록권자"],
    "inventor": ["inventorName", "inventor", "발명자", "발명자명"],
    "application_date": ["applicationDate", "filingDate", "appDate", "출원일자", "출원일"],
    "open_date": ["openDate", "openingDate", "publicationDate", "publicDate", "pubDate", "공개일자", "공개일"],
    "register_date": ["registerDate", "registrationDate", "regDate", "등록일자", "등록일"],
    "ipc_number": ["ipcNumber", "internationalpatentclassificationNumber", "internationalPatentClassificationNumber", "ipc", "ipcCode", "IPC분류", "국제특허분류"],
    "cpc_number": ["cpcNumber", "cpc", "cpcCode", "CPC분류"],
    "abstract": ["abstract", "astrtCont", "summary", "초록", "요약"],
    "claim_text": ["claim", "claims", "claimText", "claim_text", "청구항", "청구범위"],
    "url": ["url", "link", "detailUrl", "detail_url"],
    "drawing": ["drawing", "bigDrawing", "drawingPath", "thumbnailPath", "대표도", "대표도면"],
}

NEGATIVE_STATUS_HINTS = ["거절", "취하", "소멸", "포기", "무효", "말소", "INVALID", "REJECT", "ABANDON"]
REGISTERED_HINTS = ["등록", "registered", "grant", "granted"]
TECH_KEYWORDS = [
    "반도체", "패키지", "패키징", "웨이퍼", "wafer", "wlp", "fowlp", "fo-wlp", "fan-out", "fanout",
    "범프", "bump", "테스트", "test", "소자", "chip", "칩", "기판", "substrate", "interposer", "인터포저",
    "probe", "프로브", "전구체", "precursor", "ald", "cvd", "소재", "식각", "증착", "세정", "포토레지스트",
]

COMPANY_QUERY_ALIASES: dict[str, list[str]] = {
    "DB하이텍": ["DB하이텍", "디비하이텍", "주식회사 디비하이텍", "주식회사 DB하이텍"],
    "LX세미콘": ["LX세미콘", "엘엑스세미콘", "주식회사 엘엑스세미콘"],
    "GST": ["GST", "지에스티", "주식회사 지에스티", "글로벌스탠다드테크놀로지"],
    "ISC": ["ISC", "아이에스시", "주식회사 아이에스시"],
    "SFA반도체": ["SFA반도체", "에스에프에이반도체", "주식회사 에스에프에이반도체"],
    "TCK": ["TCK", "티씨케이", "주식회사 티씨케이"],
    "엘티씨": ["엘티씨", "LTC", "주식회사 엘티씨"],
    "피에스케이": ["피에스케이", "PSK", "주식회사 피에스케이"],
    "원익IPS": ["원익IPS", "원익아이피에스", "주식회사 원익아이피에스"],
    "이엔에프테크놀로지": ["이엔에프테크놀로지", "ENF테크놀로지", "주식회사 이엔에프테크놀로지"],
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").strip()
    if text.lower() in {"nan", "none", "null", "nat"}:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return re.sub(r"\s+", " ", text).strip()


def _norm_key(value: Any) -> str:
    return re.sub(r"[\s_\-./()\[\]{}:：]+", "", _clean(value).lower())


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", _clean(value))


def _normalize_application_number(value: Any) -> str:
    d = _digits(value)
    if not d:
        return ""
    if d.startswith("10") and len(d) >= 11:
        return d
    if len(d) >= 10 and d[:4].isdigit():
        try:
            year = int(d[:4])
        except Exception:
            year = 0
        if 1990 <= year <= datetime.now().year + 1:
            return "10" + d
    return d


def _year(value: Any) -> int | str:
    m = re.search(r"(19\d{2}|20\d{2})", _clean(value))
    if not m:
        return ""
    year = int(m.group(1))
    return year if 1980 <= year <= datetime.now().year + 1 else ""


def _split_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    items: list[str] = []
    for token in re.split(r"[;\n]+", raw):
        token = token.strip()
        if token:
            items.append(token)
    return items


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return ""


def _get_api_key() -> str:
    return _first_env(
        "KIPRIS_PLUS_BIBLIO_API_KEY",
        "KIPRIS_PLUS_API_KEY",
        "KIPRIS_API_KEY",
        "KIPRIS_ACCESS_KEY",
    )


def _endpoint_candidates() -> list[str]:
    env_items: list[str] = []
    for name in (
        "KIPRIS_PLUS_BIBLIO_ENDPOINTS",
        "KIPRIS_PLUS_PUBLIC_REGISTER_ENDPOINTS",
        "KIPRIS_PLUS_PATENT_SEARCH_ENDPOINTS",
    ):
        env_items.extend(_split_env(name))
    for name in (
        "KIPRIS_PLUS_BIBLIO_ENDPOINT",
        "KIPRIS_PLUS_PUBLIC_REGISTER_ENDPOINT",
        "KIPRIS_PLUS_PATENT_SEARCH_ENDPOINT",
        "KIPRIS_PLUS_SEARCH_ENDPOINT",
    ):
        value = _first_env(name)
        if value:
            env_items.append(value)
    if env_items:
        return list(dict.fromkeys(env_items))
    if str(os.getenv("KIPRIS_PLUS_BIBLIO_USE_DEFAULT_ENDPOINTS", "1")).strip().lower() in {"0", "false", "no"}:
        return []
    return DEFAULT_ENDPOINT_CANDIDATES[:]


def _key_param_candidates(explicit: str = "") -> list[str]:
    raw = explicit or _first_env("KIPRIS_PLUS_BIBLIO_KEY_PARAM", "KIPRIS_PLUS_KEY_PARAM")
    if raw:
        return [raw]
    # KIPRIS Plus endpoints have historically used both names depending on product/gateway.
    return ["accessKey", "ServiceKey"]


def _query_param_candidates(explicit: str = "") -> list[str]:
    raw = explicit or _first_env("KIPRIS_PLUS_BIBLIO_QUERY_PARAM", "KIPRIS_PLUS_SEARCH_QUERY_PARAM")
    if raw:
        return [raw]
    return ["applicant", "applicantName", "rightHolder", "word", "query", "searchString"]


def _page_param_candidates() -> tuple[str, str]:
    page_param = _first_env("KIPRIS_PLUS_BIBLIO_PAGE_PARAM") or "pageNo"
    rows_param = _first_env("KIPRIS_PLUS_BIBLIO_ROWS_PARAM") or "numOfRows"
    return page_param, rows_param


def _company_yaml_aliases(slug: str) -> list[str]:
    if company_config_path is None:
        return []
    try:
        path = company_config_path(slug, create_parent=False)
        if not path.exists():
            return []
        try:
            import yaml  # type: ignore
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except UnicodeDecodeError:
            import yaml  # type: ignore
            cfg = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
        except Exception:
            return []
        values: list[str] = []
        for key in ("corp_name", "display_name", "output_name", "name", "corp_name_en", "stock_code"):
            if cfg.get(key):
                values.append(str(cfg.get(key)))
        for x in cfg.get("aliases") or []:
            if x:
                values.append(str(x))
        return values
    except Exception:
        return []


def _query_values(company_name: str, slug: str) -> list[str]:
    values = [company_name]
    values.extend(_company_yaml_aliases(slug))
    values.extend(COMPANY_QUERY_ALIASES.get(company_name, []))
    if company_name and not company_name.startswith("주식회사"):
        values.append("주식회사 " + company_name)
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        text = _clean(v)
        if not text or text.lower() in {slug.lower(), "kospi", "kosdaq"}:
            continue
        if re.fullmatch(r"\d{6}(?:\.K[QS])?", text, flags=re.I):
            continue
        key = text.lower()
        if key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _flatten_xml_node(node: ET.Element, prefix: str = "") -> dict[str, str]:
    data: dict[str, str] = {}
    children = list(node)
    if not children:
        key = prefix or _strip_ns(node.tag)
        data[key] = _clean(node.text)
        return data
    for child in children:
        key = _strip_ns(child.tag)
        full_key = f"{prefix}.{key}" if prefix else key
        child_data = _flatten_xml_node(child, full_key)
        for k, v in child_data.items():
            if v and k not in data:
                data[k] = v
        if child.text and _clean(child.text) and key not in data:
            data[key] = _clean(child.text)
    return data


def _flatten_json(obj: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten_json(v, key))
        return out
    if isinstance(obj, list):
        return {prefix: json.dumps(obj, ensure_ascii=False)}
    return {prefix: _clean(obj)}


def _find_records_in_json(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        if all(isinstance(x, dict) for x in obj):
            return [dict(x) for x in obj]
        return []
    if not isinstance(obj, dict):
        return []
    for key in ("items", "item", "data", "result", "results", "body", "response"):
        if key in obj:
            found = _find_records_in_json(obj[key])
            if found:
                return found
    records: list[dict[str, Any]] = []
    for value in obj.values():
        found = _find_records_in_json(value)
        if found:
            records.extend(found)
    return records


def _parse_response(content: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = content.decode("utf-8", errors="replace").strip()
    meta: dict[str, Any] = {"raw_prefix": text[:300]}
    if not text:
        return [], {**meta, "error": "EMPTY_RESPONSE"}
    if text.startswith("{") or text.startswith("["):
        try:
            obj = json.loads(text)
            rows = _find_records_in_json(obj)
            if not rows and isinstance(obj, dict):
                rows = [obj]
            flat_rows = [_flatten_json(r) for r in rows]
            meta["format"] = "json"
            return flat_rows, meta
        except Exception as exc:
            meta["json_error"] = str(exc)
    try:
        root = ET.fromstring(content)
    except Exception as exc:
        return [], {**meta, "error": f"XML_PARSE_FAILED: {exc}"}

    meta["format"] = "xml"
    for tag in ("errorCode", "resultCode", "code", "returnCode"):
        value = root.findtext(f".//{tag}")
        if value:
            meta[tag] = value
    for tag in ("errorMessage", "resultMsg", "message", "returnMessage"):
        value = root.findtext(f".//{tag}")
        if value:
            meta[tag] = value
    for tag in ("totalCount", "total", "count"):
        value = root.findtext(f".//{tag}")
        if value:
            meta[tag] = value

    item_nodes = [node for node in root.iter() if _strip_ns(node.tag).lower() in {"item", "row", "doc", "patent", "patentutilityinfo"}]
    if not item_nodes:
        # fallback: one level children with enough fields
        item_nodes = [node for node in list(root) if len(list(node)) >= 3]
    rows = [_flatten_xml_node(node) for node in item_nodes]
    return rows, meta


def _value_from_aliases(raw: dict[str, Any], aliases: Iterable[str]) -> str:
    norm_map: dict[str, str] = {}
    for k, v in raw.items():
        base = str(k).split(".")[-1]
        norm_map[_norm_key(base)] = _clean(v)
        norm_map[_norm_key(k)] = _clean(v)
    for alias in aliases:
        key = _norm_key(alias)
        if key in norm_map and norm_map[key]:
            return norm_map[key]
    for alias in aliases:
        key = _norm_key(alias)
        for nk, value in norm_map.items():
            if value and (key in nk or nk in key):
                return value
    return ""


def _status_flags(register_number: str, register_date: str, register_status: str, final_disposal: str) -> tuple[bool, bool, bool]:
    joined = " ".join([register_number, register_date, register_status, final_disposal]).lower()
    is_registered = bool(register_number or register_date) or any(h.lower() in joined for h in REGISTERED_HINTS)
    negative = any(h.lower() in joined for h in NEGATIVE_STATUS_HINTS)
    return bool(is_registered), bool(is_registered and not negative), bool(negative)


def _tech_keyword_count(row: dict[str, Any]) -> int:
    joined = " ".join(str(row.get(k) or "") for k in ("invention_title", "abstract", "claim_text", "ipc_number", "cpc_number")).lower()
    return sum(1 for kw in TECH_KEYWORDS if kw.lower() in joined)


def _normalize_record(raw: dict[str, Any], *, source_label: str, source_row: int) -> dict[str, Any]:
    app = _normalize_application_number(_value_from_aliases(raw, FIELD_ALIASES["application_number"]))
    open_no = _digits(_value_from_aliases(raw, FIELD_ALIASES["open_number"]))
    reg_no = _digits(_value_from_aliases(raw, FIELD_ALIASES["register_number"]))
    status = _value_from_aliases(raw, FIELD_ALIASES["register_status"])
    final = _value_from_aliases(raw, FIELD_ALIASES["final_disposal"])
    title = _value_from_aliases(raw, FIELD_ALIASES["invention_title"])
    holder = _value_from_aliases(raw, FIELD_ALIASES["right_holder"])
    inventor = _value_from_aliases(raw, FIELD_ALIASES["inventor"])
    app_date = _value_from_aliases(raw, FIELD_ALIASES["application_date"])
    open_date = _value_from_aliases(raw, FIELD_ALIASES["open_date"])
    reg_date = _value_from_aliases(raw, FIELD_ALIASES["register_date"])
    ipc = _value_from_aliases(raw, FIELD_ALIASES["ipc_number"])
    cpc = _value_from_aliases(raw, FIELD_ALIASES["cpc_number"])
    abstract = _value_from_aliases(raw, FIELD_ALIASES["abstract"])
    claim = _value_from_aliases(raw, FIELD_ALIASES["claim_text"])
    url = _value_from_aliases(raw, FIELD_ALIASES["url"])
    drawing = _value_from_aliases(raw, FIELD_ALIASES["drawing"])
    is_reg, is_alive, negative = _status_flags(reg_no, reg_date, status, final)
    item = {
        "application_number": app,
        "application_no": app,
        "open_number": open_no,
        "publication_no": open_no,
        "register_number": reg_no,
        "registration_no": reg_no,
        "register_status": status,
        "final_disposal": final or status,
        "legal_status": " ".join(x for x in [status, final] if x),
        "invention_title": title,
        "title": title,
        "right_holder": holder,
        "applicant": holder,
        "inventor": inventor,
        "application_date": app_date,
        "application_year": _year(app_date),
        "open_date": open_date,
        "publication_date": open_date,
        "register_date": reg_date,
        "registration_date": reg_date,
        "ipc_number": ipc,
        "ipc": ipc,
        "cpc_number": cpc,
        "cpc": cpc,
        "abstract": abstract,
        "claim_text": claim,
        "claims": claim,
        "url": url,
        "drawing": drawing,
        "is_registered": is_reg,
        "is_alive_estimated": is_alive,
        "has_negative_disposal_estimated": negative,
        "source_file": source_label,
        "source_sheet": "KIPRIS_PLUS_BIBLIOGRAPHIC",
        "source_row": source_row,
    }
    item["tech_keyword_match_count"] = _tech_keyword_count(item)
    return item


def _matches_company(item: dict[str, Any], aliases: list[str]) -> bool:
    hay = " ".join(str(item.get(k) or "") for k in ("right_holder", "applicant", "invention_title", "title")).lower()
    if not hay:
        return True
    for alias in aliases:
        a = _clean(alias).lower()
        if not a or len(a) < 2:
            continue
        if re.fullmatch(r"\d{6}(?:\.k[qs])?", a):
            continue
        if a in hay:
            return True
    return False


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("application_number") or "").strip()
        if not key:
            key = "|".join([str(row.get("title") or "")[:120], str(row.get("right_holder") or "")[:80], str(row.get("application_date") or "")])
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _request_url(endpoint: str, params: dict[str, Any]) -> str:
    if "{" in endpoint and "}" in endpoint:
        try:
            return endpoint.format(**params)
        except Exception:
            pass
    joiner = "&" if "?" in endpoint else "?"
    return endpoint + joiner + urlencode(params, doseq=False)


def _fetch_one(url: str, timeout: int) -> tuple[int, bytes, str]:
    resp = requests.get(url, timeout=timeout)
    return resp.status_code, resp.content, resp.text[:300]


def _is_applicant_name_search_info(endpoint: str) -> bool:
    return "applicantNameSearchInfo".lower() in str(endpoint).lower()


def _build_request_params(
    *,
    endpoint: str,
    key_param: str,
    key: str,
    query_param: str,
    query_value: str,
    page_param: str,
    rows_param: str,
    page_no: int,
    rows_per_page: int,
) -> dict[str, Any]:
    """
    Build request params by KIPRIS Plus endpoint profile.

    applicantNameSearchInfo is the confirmed public/register bibliographic
    applicant search endpoint. It rejects getWordSearch-style params such as
    year/patent/utility/pageNo/numOfRows. For this endpoint, docsStart means
    document start index. Use 1, 31, 61... when rows_per_page=30.
    """
    if _is_applicant_name_search_info(endpoint):
        start = ((max(page_no, 1) - 1) * max(rows_per_page, 1)) + 1
        return {
            key_param or "accessKey": key,
            query_param or "applicant": query_value,
            page_param or "docsStart": str(start),
        }

    params = {
        key_param: key,
        query_param: query_value,
        page_param: page_no,
        rows_param: rows_per_page,
    }
    # Common aliases; harmless for getWordSearch-style endpoints.
    params.setdefault("pageNo", page_no)
    params.setdefault("numOfRows", rows_per_page)

    raw_extra = os.getenv("KIPRIS_PLUS_BIBLIO_EXTRA_PARAMS_JSON", "").strip()
    if raw_extra:
        try:
            extra_obj = json.loads(raw_extra)
            if isinstance(extra_obj, dict):
                for k, v in extra_obj.items():
                    if v is not None and str(k).strip():
                        params.setdefault(str(k), v)
        except Exception:
            pass
    return params


def _collect(
    *,
    company_name: str,
    slug: str,
    key: str,
    endpoints: list[str],
    key_params: list[str],
    query_params: list[str],
    max_records: int,
    max_pages: int,
    rows_per_page: int,
    sleep_sec: float,
    timeout: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    page_param, rows_param = _page_param_candidates()
    aliases = _query_values(company_name, slug)
    raw_logs: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    source_row = 0

    for endpoint in endpoints:
        endpoint_found = False
        for query_value in aliases:
            for query_param in query_params:
                for key_param in key_params:
                    any_rows_for_combo = False
                    for page_no in range(1, max_pages + 1):
                        params = _build_request_params(
                            endpoint=endpoint,
                            key_param=key_param,
                            key=key,
                            query_param=query_param,
                            query_value=query_value,
                            page_param=page_param,
                            rows_param=rows_param,
                            page_no=page_no,
                            rows_per_page=rows_per_page,
                        )
                        url = _request_url(endpoint, params)
                        started = datetime.now().isoformat(timespec="seconds")
                        try:
                            status_code, content, prefix = _fetch_one(url, timeout=timeout)
                            rows, meta = _parse_response(content)
                            log = {
                                "endpoint": endpoint,
                                "query": query_value,
                                "query_param": query_param,
                                "key_param": key_param,
                                "page_no": page_no,
                                "status_code": status_code,
                                "row_count_raw": len(rows),
                                "meta": meta,
                                "started_at": started,
                                "ended_at": datetime.now().isoformat(timespec="seconds"),
                            }
                            raw_logs.append(log)
                            if status_code >= 400:
                                break
                            if not rows:
                                break
                            before_count = len(normalized)
                            for raw in rows:
                                source_row += 1
                                item = _normalize_record(raw, source_label=endpoint, source_row=source_row)
                                if not any(item.get(k) for k in ("application_number", "invention_title", "right_holder", "abstract", "ipc_number")):
                                    continue
                                if _matches_company(item, aliases):
                                    normalized.append(item)
                            if len(normalized) > before_count:
                                any_rows_for_combo = True
                            if max_records and len(_dedupe(normalized)) >= max_records:
                                return _dedupe(normalized)[:max_records], raw_logs
                            time.sleep(max(0.0, sleep_sec))
                        except Exception as exc:
                            raw_logs.append(
                                {
                                    "endpoint": endpoint,
                                    "query": query_value,
                                    "query_param": query_param,
                                    "key_param": key_param,
                                    "page_no": page_no,
                                    "status": "EXCEPTION",
                                    "error": str(exc),
                                    "traceback": traceback.format_exc(limit=3),
                                    "started_at": started,
                                    "ended_at": datetime.now().isoformat(timespec="seconds"),
                                }
                            )
                            break
                    if any_rows_for_combo:
                        endpoint_found = True
                        break
                if endpoint_found:
                    break
            if endpoint_found:
                break
        if normalized:
            break
    result = _dedupe(normalized)
    if max_records:
        result = result[:max_records]
    return result, raw_logs


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        keys: list[str] = []
        for row in rows:
            for k in row.keys():
                if k not in keys:
                    keys.append(k)
        columns = keys
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_outputs(tech_dir: Path, slug: str, rows: list[dict[str, Any]], logs: list[dict[str, Any]], summary: dict[str, Any], *, force: bool) -> dict[str, str]:
    source_dir = tech_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    raw_jsonl = source_dir / f"{slug}_kipris_plus_bibliographic_raw.jsonl"
    raw_csv = source_dir / f"{slug}_kipris_plus_bibliographic_raw.csv"
    normalized_csv = tech_dir / f"{slug}_kipris_bibliographic_normalized.csv"
    patents_csv = tech_dir / f"{slug}_kipris_patents_normalized.csv"
    tech_patent_csv = tech_dir / f"{slug}_tech_patent_normalized.csv"
    targets_csv = tech_dir / f"{slug}_kipris_plus_request_targets.csv"
    summary_json = tech_dir / f"{slug}_kipris_plus_bibliographic_summary.json"
    summary_md = tech_dir / f"{slug}_kipris_plus_bibliographic_summary.md"

    if rows or force or not raw_jsonl.exists():
        with raw_jsonl.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if rows or force or not raw_csv.exists():
        _write_csv(raw_csv, rows, OUTPUT_COLUMNS)
    if rows or force or not normalized_csv.exists():
        _write_csv(normalized_csv, rows, OUTPUT_COLUMNS)
        _write_csv(patents_csv, rows, OUTPUT_COLUMNS)
        _write_csv(tech_patent_csv, rows, OUTPUT_COLUMNS)
        target_cols = ["application_number", "open_number", "register_number", "register_status", "final_disposal", "invention_title", "right_holder"]
        _write_csv(targets_csv, rows, target_cols)

    logs_path = tech_dir / f"{slug}_kipris_plus_bibliographic_request_log.json"
    logs_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")

    summary["output_files"] = {
        "raw_jsonl": str(raw_jsonl),
        "raw_csv": str(raw_csv),
        "normalized_csv": str(normalized_csv),
        "patents_csv": str(patents_csv),
        "tech_patent_csv": str(tech_patent_csv),
        "request_targets_csv": str(targets_csv),
        "request_log_json": str(logs_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        f"# KIPRIS Plus Bibliographic Fetch Summary - {summary.get('company_name')} ({summary.get('company_slug')})",
        "",
        f"- status: {summary.get('status')}",
        f"- rows_after_dedupe: {summary.get('rows_after_dedupe')}",
        f"- request_count: {summary.get('request_count')}",
        f"- endpoint_count: {summary.get('endpoint_count')}",
        f"- query_values: {', '.join(summary.get('query_values') or [])}",
        "",
        "## Output Files",
        *[f"- {k}: `{rel_project_path(v)}`" for k, v in summary.get("output_files", {}).items()],
    ]
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {k: str(v) for k, v in summary["output_files"].items()}


def run(
    *,
    field: str,
    company_name: str,
    company_slug: str,
    max_patents: int,
    max_pages: int,
    rows_per_page: int,
    sleep_sec: float,
    timeout: int,
    endpoint: str,
    key_param: str,
    query_param: str,
    force: bool,
) -> dict[str, Any]:
    field = normalize_field_name(field)
    if company_agent_dir is not None:
        tech_dir = Path(company_agent_dir(company_slug, "tech", create=True))
    else:
        tech_dir = ROOT / "data" / field / company_name / "tech"
    tech_dir.mkdir(parents=True, exist_ok=True)
    (tech_dir / "source").mkdir(parents=True, exist_ok=True)

    key = _get_api_key()
    endpoints = [endpoint] if endpoint else _endpoint_candidates()
    key_params = _key_param_candidates(key_param)
    query_params = _query_param_candidates(query_param)
    query_values = _query_values(company_name, company_slug)

    if not key:
        rows: list[dict[str, Any]] = []
        logs: list[dict[str, Any]] = []
        status = "SKIPPED_NO_API_KEY"
    elif not endpoints:
        rows = []
        logs = []
        status = "SKIPPED_NO_ENDPOINT"
    else:
        rows, logs = _collect(
            company_name=company_name,
            slug=company_slug,
            key=key,
            endpoints=endpoints,
            key_params=key_params,
            query_params=query_params,
            max_records=max_patents,
            max_pages=max_pages,
            rows_per_page=rows_per_page,
            sleep_sec=sleep_sec,
            timeout=timeout,
        )
        status = "OK" if rows else "NO_ROWS"

    summary: dict[str, Any] = {
        "script": "fetch_kipris_plus_bibliographic.py",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "company_name": company_name,
        "company_slug": company_slug,
        "tech_dir": str(tech_dir),
        "has_key": bool(key),
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "key_params_tried": key_params,
        "query_params_tried": query_params,
        "query_values": query_values,
        "max_patents": max_patents,
        "max_pages": max_pages,
        "rows_per_page": rows_per_page,
        "request_count": len(logs),
        "rows_after_dedupe": len(rows),
        "registered_patents_estimated": sum(1 for r in rows if r.get("is_registered")),
        "alive_patents_estimated": sum(1 for r in rows if r.get("is_alive_estimated")),
    }
    _write_outputs(tech_dir, company_slug, rows, logs, summary, force=force)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch KIPRIS Plus public/register bibliographic patents by company/applicant query.")
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-slug", required=True)
    parser.add_argument("--max-patents", type=int, default=0, help="0이면 수집 제한 없음")
    parser.add_argument("--max-pages", type=int, default=int(os.getenv("KIPRIS_PLUS_BIBLIO_MAX_PAGES", "20")))
    parser.add_argument("--rows-per-page", type=int, default=int(os.getenv("KIPRIS_PLUS_BIBLIO_ROWS_PER_PAGE", "500")))
    parser.add_argument("--sleep-sec", type=float, default=float(os.getenv("KIPRIS_PLUS_BIBLIO_SLEEP_SEC", "0.5")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("KIPRIS_PLUS_BIBLIO_TIMEOUT", "30")))
    parser.add_argument("--endpoint", default="", help="환경변수 대신 직접 endpoint 지정")
    parser.add_argument("--key-param", default="", help="ServiceKey/accessKey 등. 미지정 시 둘 다 시도")
    parser.add_argument("--query-param", default="", help="applicantName/applicant/word 등. 미지정 시 후보 순차 시도")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    result = run(
        field=args.field,
        company_name=args.company_name,
        company_slug=args.company_slug,
        max_patents=args.max_patents,
        max_pages=args.max_pages,
        rows_per_page=args.rows_per_page,
        sleep_sec=args.sleep_sec,
        timeout=args.timeout,
        endpoint=args.endpoint,
        key_param=args.key_param,
        query_param=args.query_param,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())

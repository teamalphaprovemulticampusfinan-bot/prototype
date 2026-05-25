from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY_ENV_CANDIDATES = [
    "KIPRIS_PLUS_CLAIMS_API_KEY",
    "KIPRIS_PLUS_API_KEY",
    "KIPRIS_API_KEY",
    "KIPRIS_ACCESS_KEY",
    "KIPRIS_PLUS_ACCESS_KEY",
]
KEY_PARAM_CANDIDATES = ["ServiceKey", "accessKey", "serviceKey", "AccessKey", "apiKey"]
APP_PARAM_CANDIDATES = [
    "applicationNumber",
    "applicationNo",
    "application_number",
    "appNum",
    "appNo",
    "applicationnum",
]


def _root() -> Path:
    return Path.cwd()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _safe(value) -> str:
    text = str(value or "").strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def _norm_key(value) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s_\-./()\[\]{}:]+", "", text)


def _candidate_api_keys() -> list[tuple[str, str]]:
    forced = os.getenv("KIPRIS_PLUS_CLAIMS_API_KEY_ENV", "").strip()
    names: list[str] = []
    if forced:
        names.append(forced)
    names.extend(API_KEY_ENV_CANDIDATES)
    seen = set()
    out = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        value = os.getenv(name, "").strip()
        if value:
            out.append((name, value))
    return out


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _result(text: str) -> tuple[str, str]:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        try:
            root = ET.fromstring(text)
        except Exception:
            return "", ""
    code = ""
    msg = ""
    for elem in root.iter():
        tag = _norm_key(_local_name(elem.tag))
        val = " ".join(t.strip() for t in elem.itertext() if t and t.strip())
        if tag == "resultcode":
            code = val
        elif tag == "resultmsg":
            msg = val
    return code, msg


def _claim_count(text: str) -> int:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        try:
            root = ET.fromstring(text)
        except Exception:
            return 0
    cnt = 0
    for elem in root.iter():
        tag = _norm_key(_local_name(elem.tag))
        if tag in {"claim", "claims", "claimtext", "claimcontent", "청구항", "청구범위", "청구항내용", "청구항전문"}:
            text_val = " ".join(t.strip() for t in elem.itertext() if t and t.strip())
            if len(text_val) >= 10:
                cnt += 1
    return cnt


def _mask_url(url: str, key_values: set[str]) -> str:
    try:
        parts = urlsplit(url)
        pairs = []
        for k, v in parse_qsl(parts.query, keep_blank_values=True):
            if _norm_key(k) in {"servicekey", "accesskey", "apikey", "key"} or v in key_values:
                pairs.append((k, "***KEY***"))
            else:
                pairs.append((k, v))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))
    except Exception:
        masked = url
        for value in key_values:
            masked = masked.replace(value, "***KEY***")
        return masked


def _load_rows(field: str, company_name: str, company_slug: str, max_rows: int) -> list[dict]:
    tech = _root() / "data" / field / company_name / "tech"
    candidates = [
        tech / f"{company_slug}_kipris_bibliographic_normalized.csv",
        tech / f"{company_slug}_kipris_patents_normalized.csv",
        tech / f"{company_slug}_tech_patent_normalized.csv",
    ]
    source = next((p for p in candidates if p.exists()), None)
    if source is None:
        raise FileNotFoundError("normalized KIPRIS CSV not found:\n" + "\n".join(str(p) for p in candidates))
    df = pd.read_csv(source, dtype=str, encoding="utf-8-sig").fillna("")
    rows = []
    seen = set()
    for row in df.to_dict(orient="records"):
        app_no = _digits(row.get("application_number") or row.get("applicationNumber") or row.get("application_no"))
        if not app_no or app_no in seen:
            continue
        seen.add(app_no)
        row = dict(row)
        row["application_number"] = app_no
        rows.append(row)
        if max_rows and len(rows) >= max_rows:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe KIPRIS Plus Claims API key/parameter combinations without leaking keys.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-name", default="한미반도체")
    parser.add_argument("--company-slug", default="hanmi")
    parser.add_argument("--max-probe-patents", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--endpoint", default=os.getenv("KIPRIS_PLUS_CLAIMS_ENDPOINT", "").strip())
    args = parser.parse_args()

    endpoint = args.endpoint.strip()
    if not endpoint:
        print("[STOP] KIPRIS_PLUS_CLAIMS_ENDPOINT is missing in .env")
        return 2

    api_keys = _candidate_api_keys()
    if not api_keys:
        print("[STOP] No API key env found. Set KIPRIS_PLUS_CLAIMS_API_KEY or KIPRIS_PLUS_API_KEY.")
        return 2

    rows = _load_rows(args.field, args.company_name, args.company_slug, args.max_probe_patents)
    key_values = {v for _, v in api_keys}
    results = []

    print("=" * 90)
    print("KIPRIS Plus Claims API Probe")
    print("=" * 90)
    print(f"company={args.company_name} / {args.company_slug}")
    print(f"endpoint={endpoint}")
    print(f"probe_patents={len(rows)}")
    print(f"api_key_env_candidates={[name for name, _ in api_keys]}")
    print("=" * 90)

    for row in rows:
        app_no = _digits(row.get("application_number"))
        open_no = _digits(row.get("open_number"))
        reg_no = _digits(row.get("register_number"))
        print(f"\n[PROBE PATENT] application_number={app_no}")
        for key_env, api_key in api_keys:
            for key_param in KEY_PARAM_CANDIDATES:
                for app_param in APP_PARAM_CANDIDATES:
                    params = {key_param: api_key, app_param: app_no}
                    if open_no:
                        params.setdefault("openNumber", open_no)
                        params.setdefault("publicationNumber", open_no)
                    if reg_no:
                        params.setdefault("registerNumber", reg_no)
                        params.setdefault("registrationNumber", reg_no)
                    try:
                        resp = requests.get(endpoint, params=params, timeout=args.timeout)
                        text = resp.text or ""
                        code, msg = _result(text)
                        claims = _claim_count(text)
                        masked_url = _mask_url(resp.url, key_values)
                    except Exception as exc:
                        code, msg, claims, masked_url = "REQUEST_ERROR", str(exc), 0, ""
                        text = ""
                    item = {
                        "application_number": app_no,
                        "api_key_env": key_env,
                        "key_param": key_param,
                        "app_param": app_param,
                        "result_code": code,
                        "result_msg": msg,
                        "claim_count": claims,
                        "request_url": masked_url,
                        "response_preview": re.sub(r"\s+", " ", text[:240]),
                    }
                    results.append(item)
                    if code in {"00", "0"} or claims > 0:
                        print("[SUCCESS]")
                        print(json.dumps(item, ensure_ascii=False, indent=2))
                        print("\nRecommended .env settings:")
                        print(f"KIPRIS_PLUS_CLAIMS_API_KEY_ENV={key_env}")
                        print(f"KIPRIS_PLUS_CLAIMS_KEY_PARAM={key_param}")
                        print(f"KIPRIS_PLUS_CLAIMS_APP_PARAM={app_param}")
                        return 0

    # Print compact failure counts, not every result.
    from collections import Counter
    summary = Counter((r["result_code"], r["result_msg"]) for r in results)
    print("\n[NO SUCCESS] result summary")
    for (code, msg), count in summary.most_common(20):
        print(f"- count={count} code={code} msg={msg}")
    print("\nFirst 5 masked samples:")
    print(json.dumps(results[:5], ensure_ascii=False, indent=2))
    print("\n해석: 모든 조합이 SERVICE_KEY_IS_NOT_REGISTERED_ERROR이면 현재 키가 Claims API 서비스에 등록되지 않았거나 endpoint가 다른 서비스일 가능성이 큽니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

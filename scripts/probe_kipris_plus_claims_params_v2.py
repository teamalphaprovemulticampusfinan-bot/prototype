from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("[ERROR] requests is required. Run: pip install requests")
    raise


DEFAULT_ENDPOINT = "http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo"


def load_dotenv(path: Path) -> None:
    """Tiny .env loader. Does not print secrets."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def mask_value(s: str) -> str:
    if not s:
        return s
    # Mask query parameters that probably contain service keys.
    parsed = urllib.parse.urlsplit(s)
    qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    masked = []
    for k, v in qs:
        if k.lower() in {"servicekey", "accesskey", "apikey", "key", "service_key"}:
            masked.append((k, "***KEY***"))
        else:
            masked.append((k, v))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(masked), parsed.fragment)
    )


def find_company_dir(root: Path, field: str, company_name: str) -> Path:
    direct = root / "data" / field / company_name / "tech"
    if direct.exists():
        return direct
    # Fallback: search likely tech dirs.
    matches = list((root / "data").glob(f"**/{company_name}/tech"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Cannot find tech dir for company={company_name!r}. Tried: {direct}")


def find_bibliographic_csv(tech_dir: Path, slug: str) -> Path:
    preferred = tech_dir / f"{slug}_kipris_bibliographic_normalized.csv"
    if preferred.exists():
        return preferred
    candidates = sorted(tech_dir.glob("*kipris*bibliographic*normalized*.csv"))
    if candidates:
        return candidates[0]
    candidates = sorted(tech_dir.glob("*bibliographic*.csv"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"Cannot find bibliographic normalized CSV in {tech_dir}")


def normalize_app_no(v: Any) -> str:
    s = str(v or "").strip()
    s = re.sub(r"[^0-9]", "", s)
    return s


def read_application_numbers(csv_path: Path, limit: int) -> List[str]:
    possible_cols = [
        "application_number",
        "applicationNumber",
        "application_no",
        "applicationNo",
        "출원번호",
        "app_num",
        "appNo",
        "appNum",
    ]
    rows: List[str] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        picked_col = None
        for c in possible_cols:
            if c in headers:
                picked_col = c
                break
        if picked_col is None:
            # fallback: first column that contains application/app/출원
            for c in headers:
                lc = c.lower()
                if "application" in lc or "app" in lc or "출원" in c:
                    picked_col = c
                    break
        if picked_col is None:
            raise ValueError(f"Cannot infer application number column. Headers={headers}")

        for row in reader:
            app = normalize_app_no(row.get(picked_col))
            if app:
                rows.append(app)
            if limit and len(rows) >= limit:
                break

    # keep order, unique
    seen = set()
    out = []
    for app in rows:
        if app not in seen:
            seen.add(app)
            out.append(app)
    return out


def get_text_by_names(root: ET.Element, names: Iterable[str]) -> str:
    wanted = {n.lower() for n in names}
    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower()
        if tag in wanted and elem.text:
            return elem.text.strip()
    return ""


def parse_xml_response(text: str) -> Tuple[str, str, int]:
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except Exception:
        return "PARSE_ERROR", "XML_PARSE_ERROR", 0

    code = get_text_by_names(root, ["resultCode", "returnCode", "code"]) or ""
    msg = get_text_by_names(root, ["resultMsg", "returnMsg", "message", "msg"]) or ""

    claim_count = 0
    # Common claim-like tags. This is intentionally broad for KIPRIS variants.
    claim_tag_hints = [
        "claim",
        "claims",
        "claimtext",
        "claimcontent",
        "claimscope",
        "claimscopecontent",
        "청구",
    ]
    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower()
        text_val = (elem.text or "").strip()
        if not text_val:
            continue
        if any(h in tag for h in claim_tag_hints):
            if len(text_val) >= 5:
                claim_count += 1

    return code or "UNKNOWN", msg or "", claim_count


def build_key_env_candidates(cli_candidates: Optional[str]) -> List[str]:
    if cli_candidates:
        names = [x.strip() for x in cli_candidates.split(",") if x.strip()]
    else:
        names = [
            "KIPRIS_PLUS_CLAIMS_API_KEY",
            "KIPRIS_PLUS_API_KEY",
            "KIPRIS_API_KEY",
            "KIPRIS_ACCESS_KEY",
            "KIPRIS_PLUS_ACCESS_KEY",
        ]
    # Only keep envs that exist and are non-empty.
    return [n for n in names if os.environ.get(n)]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--company-name", default="한미반도체")
    p.add_argument("--company-slug", default="hanmi")
    p.add_argument("--field", default="반도체")
    p.add_argument("--root", default=".")
    p.add_argument("--endpoint", default=os.environ.get("KIPRIS_PLUS_CLAIMS_ENDPOINT", DEFAULT_ENDPOINT))
    p.add_argument("--max-probe-patents", type=int, default=1)
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--sleep-sec", type=float, default=0.15)
    p.add_argument("--api-key-env-candidates", default="")
    p.add_argument("--save-json", action="store_true", default=True)
    args = p.parse_args()

    root = Path(args.root).resolve()
    load_dotenv(root / ".env")

    endpoint = args.endpoint or os.environ.get("KIPRIS_PLUS_CLAIMS_ENDPOINT") or DEFAULT_ENDPOINT
    key_envs = build_key_env_candidates(args.api_key_env_candidates or None)
    if not key_envs:
        print("[ERROR] No API key env candidates found.")
        print("Set one of: KIPRIS_PLUS_CLAIMS_API_KEY, KIPRIS_PLUS_API_KEY, KIPRIS_API_KEY, KIPRIS_ACCESS_KEY, KIPRIS_PLUS_ACCESS_KEY")
        return 2

    key_params = [
        os.environ.get("KIPRIS_PLUS_CLAIMS_KEY_PARAM", "").strip(),
        os.environ.get("KIPRIS_PLUS_KEY_PARAM", "").strip(),
        os.environ.get("KIPRIS_PLUS_API_KEY_PARAM", "").strip(),
        "ServiceKey",
        "accessKey",
        "serviceKey",
        "AccessKey",
        "apiKey",
        "key",
        "service_key",
    ]
    app_params = [
        os.environ.get("KIPRIS_PLUS_CLAIMS_APP_PARAM", "").strip(),
        "applicationNumber",
        "applicationNo",
        "application_number",
        "appNum",
        "appNo",
        "appno",
    ]
    key_params = list(dict.fromkeys([x for x in key_params if x]))
    app_params = list(dict.fromkeys([x for x in app_params if x]))

    tech_dir = find_company_dir(root, args.field, args.company_name)
    csv_path = find_bibliographic_csv(tech_dir, args.company_slug)
    apps = read_application_numbers(csv_path, args.max_probe_patents)

    samples: List[Dict[str, Any]] = []
    source_dir = tech_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 90)
    print("KIPRIS Plus Claims API Probe v2")
    print("=" * 90)
    print(f"company={args.company_name} / {args.company_slug}")
    print(f"endpoint={endpoint}")
    print(f"csv={csv_path}")
    print(f"probe_patents={len(apps)}")
    print(f"api_key_env_candidates={key_envs}")
    print(f"key_params={key_params}")
    print(f"app_params={app_params}")
    print("=" * 90)

    session = requests.Session()

    for app_no in apps:
        print(f"\n[PROBE PATENT] application_number={app_no}")
        for api_key_env in key_envs:
            api_key = os.environ.get(api_key_env, "")
            for key_param in key_params:
                for app_param in app_params:
                    params = {
                        key_param: api_key,
                        app_param: app_no,
                    }
                    try:
                        r = session.get(endpoint, params=params, timeout=args.timeout)
                        text = r.text or ""
                        code, msg, claim_count = parse_xml_response(text)
                        url = mask_value(r.url)
                        samples.append(
                            {
                                "application_number": app_no,
                                "api_key_env": api_key_env,
                                "key_param": key_param,
                                "app_param": app_param,
                                "http_status": r.status_code,
                                "result_code": code,
                                "result_msg": msg,
                                "claim_count": claim_count,
                                "request_url": url,
                                "response_preview": re.sub(r"\s+", " ", text[:500]).strip(),
                            }
                        )
                    except Exception as e:
                        samples.append(
                            {
                                "application_number": app_no,
                                "api_key_env": api_key_env,
                                "key_param": key_param,
                                "app_param": app_param,
                                "http_status": None,
                                "result_code": "REQUEST_EXCEPTION",
                                "result_msg": repr(e),
                                "claim_count": 0,
                                "request_url": "",
                                "response_preview": "",
                            }
                        )
                    time.sleep(args.sleep_sec)

    out_path = source_dir / f"{args.company_slug}_claims_probe_samples_v2.json"
    out_path.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")

    counter = Counter((str(s.get("result_code")), str(s.get("result_msg"))) for s in samples)
    print("\n[RESULT SUMMARY]")
    for (code, msg), count in counter.most_common():
        print(f"- count={count} code={code} msg={msg}")

    by_code: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for s in samples:
        by_code[str(s.get("result_code"))].append(s)

    print("\n[SAMPLES BY RESULT CODE]")
    for code in ["00", "22", "30", "PARSE_ERROR", "REQUEST_EXCEPTION", "UNKNOWN"]:
        if code not in by_code:
            continue
        print("\n" + "=" * 90)
        print(f"result_code = {code} / showing up to 10")
        print("=" * 90)
        print(json.dumps(by_code[code][:10], ensure_ascii=False, indent=2))

    # Also show any non-30 samples even if result code is unusual.
    non30 = [s for s in samples if str(s.get("result_code")) != "30"]
    if non30:
        print("\n" + "=" * 90)
        print("NON-30 SAMPLES / showing up to 20")
        print("=" * 90)
        print(json.dumps(non30[:20], ensure_ascii=False, indent=2))

    success = [s for s in samples if str(s.get("result_code")) == "00" or int(s.get("claim_count") or 0) > 0]
    if success:
        best = success[0]
        print("\n[SUCCESS] Recommended .env settings")
        print(f"KIPRIS_PLUS_CLAIMS_API_KEY_ENV={best['api_key_env']}")
        print(f"KIPRIS_PLUS_CLAIMS_KEY_PARAM={best['key_param']}")
        print(f"KIPRIS_PLUS_CLAIMS_APP_PARAM={best['app_param']}")
        print(f"saved_samples={out_path}")
        return 0

    print("\n[NO SUCCESS]")
    print(f"saved_samples={out_path}")
    print("If result_code=22 exists, the service/key combination was recognized but quota is exhausted.")
    print("If result_code=30 exists only for a key, that key is not registered for this endpoint/service.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

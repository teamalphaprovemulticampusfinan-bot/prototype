from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


SEMICONDUCTOR_KEYWORDS = [
    "반도체",
    "패키지",
    "패키징",
    "WLP",
    "FOWLP",
    "FOP",
    "PLP",
    "Bumping",
    "범핑",
    "웨이퍼",
    "재배선",
    "RDL",
    "기판",
    "소자",
    "테스트",
    "방열",
    "차폐",
    "공정",
]

IPC_RE = re.compile(r"\b[A-HY]\d{2}[A-Z]\b", re.I)


def _clean(text: Any, limit: int | None = None) -> str:
    s = "" if text is None else str(text)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("|", " | ")
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        return s[:limit].rstrip() + "..."
    return s


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        s = str(value).strip().replace(",", "")
        if not s:
            return default
        return int(float(s))
    except Exception:
        return default


def _year_from_date(value: Any) -> int | None:
    s = str(value or "")
    m = re.search(r"(19|20)\d{2}", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def _read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = path.read_text(encoding="cp949", errors="ignore")
    return _clean(text, limit=limit)


def _find_dart_sentence(company_dir: str) -> str:
    src_dir = tech_source_dir(company_dir)
    dart_path = src_dir / "dart_latest_business_report.txt"
    text = _read_text(dart_path)

    if not text:
        return ""

    candidates = []
    for sent in re.split(r"(?<=[.!?。])\s+|[\n\r]+", text):
        s = _clean(sent)
        if len(s) < 40:
            continue
        score = 0
        for kw in ["WLP", "FOWLP", "PLP", "Bumping", "반도체", "패키징", "Chip", "웨이퍼"]:
            if kw.lower() in s.lower():
                score += 1
        if score > 0:
            candidates.append((score, len(s), s))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return _clean(candidates[0][2], 700)

    return _clean(text, 700)


def _find_rnd_sentence(company_dir: str) -> str:
    src_dir = tech_source_dir(company_dir)
    dart_path = src_dir / "dart_latest_business_report.txt"
    text = _read_text(dart_path)

    if not text:
        return ""

    candidates = []
    for sent in re.split(r"(?<=[.!?。])\s+|[\n\r]+", text):
        s = _clean(sent)
        if len(s) < 30:
            continue
        score = 0
        for kw in ["연구개발", "개발", "R&D", "투자", "설비", "공정", "기술"]:
            if kw.lower() in s.lower():
                score += 1
        if score > 0:
            candidates.append((score, len(s), s))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return _clean(candidates[0][2], 600)

    return ""


def _normalize_row_keys(row: dict[str, Any]) -> dict[str, str]:
    out = {}
    for k, v in row.items():
        key = _clean(k).lower().replace(" ", "").replace("_", "")
        out[key] = _clean(v)
    return out


def _get(row: dict[str, str], *keys: str) -> str:
    normalized = {}
    for k, v in row.items():
        kk = k.lower().replace(" ", "").replace("_", "")
        normalized[kk] = v

    for key in keys:
        kk = key.lower().replace(" ", "").replace("_", "")
        if kk in normalized:
            return normalized[kk]

    return ""


def _find_kipris_files(company_dir: str) -> list[Path]:
    src_dir = tech_source_dir(company_dir)
    if not src_dir.exists():
        return []

    patterns = [
        "*kipris*.csv",
        "*KIPRIS*.csv",
        "*patent*.csv",
        "*특허*.csv",
        "*kipris*.xlsx",
        "*KIPRIS*.xlsx",
        "*patent*.xlsx",
        "*특허*.xlsx",
        "*kipris*.txt",
        "*KIPRIS*.txt",
        "*patent*.txt",
        "*특허*.txt",
    ]

    files: list[Path] = []
    for pat in patterns:
        files.extend(src_dir.glob(pat))

    seen = set()
    unique = []
    for p in files:
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        unique.append(p)

    return unique


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last_error = None

    for enc in encodings:
        try:
            with path.open("r", encoding=enc, errors="ignore", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                delimiter = ","
                if sample.count("\t") > sample.count(","):
                    delimiter = "\t"
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = [_normalize_row_keys(r) for r in reader if isinstance(r, dict)]
                if rows:
                    return rows
        except Exception as exc:
            last_error = exc

    if last_error:
        return []
    return []


def _parse_ipc_codes(text: str) -> list[str]:
    if not text:
        return []
    codes = []
    for match in IPC_RE.findall(str(text).upper()):
        codes.append(match.upper())
    return codes


def _keyword_hits(text: str) -> list[str]:
    low = str(text or "").lower()
    hits = []
    for kw in SEMICONDUCTOR_KEYWORDS:
        if kw.lower() in low:
            hits.append(kw)
    return hits


def _is_registered(status: str, reg_no: str = "") -> bool:
    s = str(status or "")
    if "등록" in s:
        return True
    if _clean(reg_no):
        return True
    return False


def _is_alive(status: str) -> bool:
    s = str(status or "")
    negative = ["소멸", "거절", "취하", "포기", "무효", "만료"]
    if any(x in s for x in negative):
        return False
    if "등록" in s or "공개" in s or "출원" in s:
        return True
    return False


def _load_patent_metrics(company_dir: str, company_name: str) -> dict[str, Any]:
    files = _find_kipris_files(company_dir)
    rows: list[dict[str, str]] = []

    for path in files:
        if path.suffix.lower() == ".csv":
            rows.extend(_read_csv_rows(path))

    company_core = company_name.replace("주식회사", "").replace("(주)", "").replace("㈜", "").strip()
    if not company_core:
        company_core = company_dir

    normalized_rows = []
    for row in rows:
        title = _get(row, "inventiontitle", "발명의명칭", "title", "명칭")
        applicant = _get(row, "applicantname", "출원인명", "applicant", "출원인", "권리자")
        status = _get(row, "registerstatus", "등록상태", "status", "상태")
        app_no = _get(row, "applicationnumber", "출원번호", "appno")
        reg_no = _get(row, "registernumber", "등록번호", "regno")
        app_date = _get(row, "applicationdate", "출원일자", "출원일")
        reg_date = _get(row, "registerdate", "등록일자", "등록일")
        ipc = _get(row, "ipcnumber", "ipc", "ipccode", "ipc코드")
        abstract = _get(row, "astrtcont", "abstract", "초록", "요약")

        blob = " ".join([title, applicant, status, app_no, reg_no, app_date, reg_date, ipc, abstract])
        company_match = company_core in applicant or company_name in applicant or company_dir.lower() in blob.lower()

        if not company_match and rows:
            # KIPRIS 파일 자체가 해당 기업명으로 저장되어 있으면 너무 강하게 제외하지 않음.
            if company_dir.lower() not in " ".join(str(f).lower() for f in files):
                continue

        app_year = _year_from_date(app_date) or _year_from_date(reg_date)

        normalized_rows.append(
            {
                "title": title,
                "applicant": applicant,
                "status": status,
                "application_number": app_no,
                "register_number": reg_no,
                "application_date": app_date,
                "register_date": reg_date,
                "application_year": app_year,
                "ipc_raw": ipc,
                "ipc_codes": _parse_ipc_codes(ipc),
                "abstract": abstract,
                "keyword_hits": _keyword_hits(blob),
                "is_registered": _is_registered(status, reg_no),
                "is_alive": _is_alive(status),
            }
        )

    current_year = datetime.now().year
    recent_cutoff = current_year - 5

    ipc_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()

    for row in normalized_rows:
        ipc_counter.update(row["ipc_codes"])
        keyword_counter.update(row["keyword_hits"])

    registered = [r for r in normalized_rows if r["is_registered"]]
    alive = [r for r in normalized_rows if r["is_alive"]]
    recent = [
        r for r in normalized_rows
        if isinstance(r.get("application_year"), int) and r["application_year"] >= recent_cutoff
    ]

    semiconductor_ipc_count = sum(
        1 for r in normalized_rows
        if any(code in {"H01L", "H10B", "H10W", "G01R", "G06F"} for code in r["ipc_codes"])
    )

    def rep_score(row: dict[str, Any]) -> tuple[int, int, int]:
        return (
            1 if row["is_registered"] else 0,
            len(row["keyword_hits"]),
            int(row["application_year"] or 0),
        )

    representatives = sorted(normalized_rows, key=rep_score, reverse=True)[:10]

    return {
        "source_files": [str(p) for p in files],
        "raw_row_count": len(rows),
        "normalized_patent_count": len(normalized_rows),
        "registered_patent_count": len(registered),
        "alive_patent_count": len(alive),
        "recent_5y_patent_count": len(recent),
        "semiconductor_ipc_patent_count": semiconductor_ipc_count,
        "top_ipc": ipc_counter.most_common(8),
        "top_keywords": keyword_counter.most_common(8),
        "year_min": min([r["application_year"] for r in normalized_rows if r["application_year"]], default=None),
        "year_max": max([r["application_year"] for r in normalized_rows if r["application_year"]], default=None),
        "representative_patents": representatives,
    }


def _make_evidence(evidence_id: str, source_type: str, source: str, metric: str, value: Any, unit: str, snippet: str, period: str = "") -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source": source,
        "metric": metric,
        "value": value,
        "unit": unit,
        "period": period,
        "snippet": _clean(snippet, 1000),
    }


def _make_claim(claim_id: str, text: str, evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "text": _clean(text, 700),
        "evidence_ids": evidence_ids,
    }


def build_auditor_safe_tech_packet(
    *,
    company_dir: str,
    company: dict[str, Any],
    bridge: dict[str, Any] | None = None,
    score_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    company_name = _clean(company.get("corp_name") or company.get("name") or company_dir)
    bridge = dict(bridge or {})
    score_report = dict(score_report or {})

    dart_sentence = _find_dart_sentence(company_dir)
    rnd_sentence = _find_rnd_sentence(company_dir)
    patent = _load_patent_metrics(company_dir, company_name)

    total_score = _safe_int(score_report.get("total_score"), default=0)
    bridge_score = _safe_int(bridge.get("score"), default=0)
    bridge_grade = _clean(bridge.get("grade") or bridge.get("decision") or "COMMERCIALIZATION_WATCH")

    products = company.get("products") or []
    if isinstance(products, list):
        product_text = ", ".join(_clean(x) for x in products[:8] if _clean(x))
    else:
        product_text = _clean(products)

    top_ipc_text = ", ".join(f"{code} {cnt}건" for code, cnt in patent["top_ipc"][:6]) or "IPC 확인 제한"
    top_kw_text = ", ".join(f"{kw} {cnt}건" for kw, cnt in patent["top_keywords"][:6]) or "키워드 확인 제한"
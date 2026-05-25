from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from common.data_paths import (
        ROOT_DIR,
        company_agent_dir,
        company_name as resolve_company_name,
        company_slug as resolve_company_slug,
        safe_name,
    )
except Exception:  # pragma: no cover - direct file execution fallback
    ROOT_DIR = Path(__file__).resolve().parents[3]

    def safe_name(value: Any, default: str = "output") -> str:
        text = str(value or "").strip().strip('"').strip("'")
        text = re.sub(r'[\\/:*?"<>|]+', "_", text)
        text = re.sub(r"\s+", "_", text).strip("._ ")
        return text or default

    def resolve_company_slug(value: Any, default: str | None = None) -> str:
        return safe_name(value or default or "unknown_company")

    def resolve_company_name(value: Any) -> str:
        return safe_name(value or "unknown_company")

    def company_agent_dir(company_dir: str, agent_name: str, create: bool = True) -> Path:
        base = ROOT_DIR / "data"
        for field_dir in base.iterdir() if base.exists() else []:
            if not field_dir.is_dir():
                continue
            for company_path in field_dir.iterdir():
                if not company_path.is_dir():
                    continue
                if company_path.name == company_dir or company_dir.lower() in company_path.name.lower():
                    out = company_path / agent_name
                    if create:
                        out.mkdir(parents=True, exist_ok=True)
                    return out
        out = base / "반도체" / company_dir / agent_name
        if create:
            out.mkdir(parents=True, exist_ok=True)
        return out

ROOT = Path(ROOT_DIR)
URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"'`]+", re.IGNORECASE)
HANGUL_SENTENCE_SPLIT_RE = re.compile(r"\n+|(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=요\.)\s+|(?<=음\.)\s+|(?<=임\.)\s+")
SUPPORTED_TEXT_EXTS = {".json", ".jsonl", ".md", ".txt", ".csv", ".tsv", ".yaml", ".yml"}
SUPPORTED_OPTIONAL_EXTS = {".xlsx", ".xlsm"}
MAX_FILE_BYTES = int(os.getenv("ALPHAPROVE_VALUE_EVIDENCE_MAX_FILE_BYTES", "1200000"))
MAX_SOURCE_FILES_PER_GROUP = int(os.getenv("ALPHAPROVE_VALUE_EVIDENCE_MAX_FILES_PER_GROUP", "80"))

DIRECT_STATUS = "DIRECT_EVIDENCE"
INDIRECT_STATUS = "INDIRECT_EVIDENCE"
PARTIAL_STATUS = "PARTIAL_EVIDENCE"
NOT_FOUND_STATUS = "NOT_FOUND"
CROSS_CHECK_STATUS = "CROSS_CHECK_REQUIRED"

DIMENSION_LABELS = {
    "customer_adoption": "고객 채택",
    "mass_production": "양산",
    "revenue_conversion": "매출 전환",
    "ip_quality": "IP 품질",
    "margin_cashflow_linkage": "마진·원가·현금흐름 연결",
}

STATUS_KR = {
    DIRECT_STATUS: "직접 근거 확인",
    INDIRECT_STATUS: "간접 근거 확인",
    PARTIAL_STATUS: "부분 근거 확인",
    NOT_FOUND_STATUS: "확인 제한",
    CROSS_CHECK_STATUS: "교차 검증 필요",
}

STATUS_SCORE = {
    DIRECT_STATUS: 85.0,
    INDIRECT_STATUS: 62.0,
    PARTIAL_STATUS: 50.0,
    CROSS_CHECK_STATUS: 42.0,
    NOT_FOUND_STATUS: 25.0,
}

# Direct keywords are intentionally strict. The goal is to avoid converting vague
# technology claims into customer/revenue/FCF evidence.
DIMENSION_RULES: Dict[str, Dict[str, Sequence[str]]] = {
    "customer_adoption": {
        "direct": [
            "고객사", "주요 고객", "고객 채택", "채택", "납품", "공급계약", "공급 계약", "수주", "design win",
            "Design Win", "qualification", "Qualified", "approved vendor", "customer approval", "삼성전자", "SK하이닉스",
        ],
        "indirect": [
            "적용", "적용처", "제품군", "고객", "application", "solution", "package", "패키징", "PMIC", "WLP", "FOWLP", "Fan-out",
        ],
    },
    "mass_production": {
        "direct": [
            "양산", "대량생산", "본격 생산", "상업 생산", "mass production", "volume production", "ramp-up", "ramp up",
        ],
        "indirect": [
            "생산능력", "CAPA", "증설", "라인", "공장", "설비", "capacity", "production line", "fab", "제조", "후공정",
        ],
    },
    "revenue_conversion": {
        "direct": [
            "매출", "제품 매출", "사업부 매출", "매출액", "수주잔고", "수주", "revenue", "sales", "order backlog", "billing",
        ],
        "indirect": [
            "사업부", "제품군", "성장", "수요", "판매", "market demand", "ASP", "shipment", "출하",
        ],
    },
    "margin_cashflow_linkage": {
        "direct": [
            "마진", "영업이익률", "매출총이익률", "원가율", "현금흐름", "영업현금흐름", "FCF", "free cash flow",
            "EBITDA", "수익성", "profitability", "gross margin", "operating margin", "cost reduction",
        ],
        "indirect": [
            "원가", "수율", "yield", "생산성", "CAPEX", "감가상각", "비용", "효율", "automation", "throughput",
        ],
    },
}

SOURCE_GROUP_FALLBACK_URLS = {
    # URL이 원본 산출물에서 직접 검출되지 않을 때, 사람이 바로 확인할 수 있는 대체 조회 URL이다.
    # 회사별 정확 URL을 임의로 단정하지 않고, DART/KIPRIS/KIND/검색 URL을 함께 제공한다.
    "DART": [
        "https://dart.fss.or.kr/",
        "https://dart.fss.or.kr/dsab007/main.do?option=corp",
        "https://opendart.fss.or.kr/",
        "https://www.google.com/search?q={company_quote}+DART+%EC%82%AC%EC%97%85%EB%B3%B4%EA%B3%A0%EC%84%9C",
        "https://www.google.com/search?q={company_quote}+%EB%B6%84%EA%B8%B0%EB%B3%B4%EA%B3%A0%EC%84%9C+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C",
    ],
    "IR_HOMEPAGE": [
        "https://www.google.com/search?q={company_quote}+IR",
        "https://www.google.com/search?q={company_quote}+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C",
        "https://www.google.com/search?q={company_quote}+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88",
        "https://www.google.com/search?q={company_quote}+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88",
    ],
    "KIPRIS": [
        "https://www.kipris.or.kr/khome/main.jsp",
        "https://plus.kipris.or.kr/",
        "https://www.google.com/search?q={company_quote}+KIPRIS+%ED%8A%B9%ED%97%88",
        "https://www.google.com/search?q={company_quote}+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC",
    ],
    "VALUATION": [
        "https://dart.fss.or.kr/",
        "https://finance.naver.com/",
        "https://comp.fnguide.com/",
        "https://www.google.com/search?q={company_quote}+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF",
        "https://www.google.com/search?q={company_quote}+%EC%9B%90%EA%B0%80%EC%9C%A8+%EC%98%81%EC%97%85%EC%9D%B4%EC%9D%B5%EB%A5%A0+CAPEX",
    ],
    "FINANCE": [
        "https://dart.fss.or.kr/",
        "https://opendart.fss.or.kr/",
        "https://finance.naver.com/",
        "https://comp.fnguide.com/",
        "https://www.google.com/search?q={company_quote}+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%EC%9B%90%EA%B0%80%EC%9C%A8+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84",
    ],
    "TECH_OUTPUT": [
        "https://www.google.com/search?q={company_quote}+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95",
        "https://www.google.com/search?q={company_quote}+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98",
    ],
}


@dataclass
class SourceDoc:
    source_group: str
    source_file: str
    rel_path: str
    text: str
    urls: List[str]
    fallback_urls: List[str]


@dataclass
class EvidenceItem:
    source_group: str
    source_file: str
    evidence_level: str
    matched_keywords: List[str]
    snippet: str
    urls: List[str]
    fallback_urls: List[str]


def _rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        s = str(path).replace("\\", "/")
        for marker in ("data/", "workspace/", "src/", "scripts/"):
            idx = s.find(marker)
            if idx >= 0:
                return s[idx:]
        return s


def _clean_url(url: str) -> str:
    return str(url or "").strip().rstrip(".,;:)]}>'\"")


def _extract_urls(text: Any) -> List[str]:
    found: List[str] = []
    raw = str(text or "")
    for m in URL_RE.finditer(raw):
        url = _clean_url(m.group(0))
        if url and url not in found:
            found.append(url)
    return found[:20]


def _walk_values(obj: Any, limit: int = 20000) -> str:
    chunks: List[str] = []
    total = 0

    def walk(x: Any, key: str = "") -> None:
        nonlocal total
        if total >= limit:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, str(k))
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        else:
            s = str(x or "").strip()
            if not s:
                return
            if key:
                s = f"{key}: {s}"
            chunks.append(s)
            total += len(s)

    walk(obj)
    return "\n".join(chunks)[:limit]


def _read_json_text(path: Path) -> str:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return _walk_values(obj)


def _read_csv_text(path: Path, max_rows: int = 400) -> str:
    lines: List[str] = []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, errors="replace", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
                reader = csv.DictReader(f, dialect=dialect)
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    lines.append(" | ".join(f"{k}: {v}" for k, v in row.items() if v not in (None, "")))
            return "\n".join(lines)
        except Exception:
            continue
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES]
    except Exception:
        return ""


def _read_xlsx_text(path: Path, max_sheets: int = 5, max_rows: int = 120, max_cols: int = 24) -> str:
    try:
        import openpyxl  # type: ignore
    except Exception:
        return ""
    chunks: List[str] = []
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets[:max_sheets]:
            chunks.append(f"[sheet] {ws.title}")
            for r_i, row in enumerate(ws.iter_rows(max_row=max_rows, max_col=max_cols, values_only=True)):
                if r_i >= max_rows:
                    break
                vals = [str(v).strip() for v in row if v not in (None, "")]
                if vals:
                    chunks.append(" | ".join(vals))
        wb.close()
    except Exception:
        return ""
    return "\n".join(chunks)[:MAX_FILE_BYTES]


def _read_file_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES and path.suffix.lower() not in {".csv", ".xlsx", ".xlsm"}:
            return path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES]
    except Exception:
        pass
    ext = path.suffix.lower()
    try:
        if ext == ".json":
            return _read_json_text(path)
        if ext == ".jsonl":
            rows = []
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:400]:
                try:
                    rows.append(_walk_values(json.loads(line), 2000))
                except Exception:
                    rows.append(line)
            return "\n".join(rows)[:MAX_FILE_BYTES]
        if ext in {".csv", ".tsv"}:
            return _read_csv_text(path)
        if ext in {".xlsx", ".xlsm"}:
            return _read_xlsx_text(path)
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES]
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")[:MAX_FILE_BYTES]
    except Exception:
        return ""


def _fallback_urls(source_group: str, company: str) -> List[str]:
    quote = urllib.parse.quote(str(company or ""))
    urls: List[str] = []
    for u in SOURCE_GROUP_FALLBACK_URLS.get(source_group, []):
        urls.append(u.format(company_quote=quote))
    return urls


def _infer_source_group(path: Path) -> str:
    s = str(path).lower().replace("\\", "/")
    name = path.name.lower()
    if any(k in s for k in ["kipris", "patent", "claim", "citation", "family", "ip_legal", "ip_evidence"]):
        return "KIPRIS"
    if any(k in s for k in ["valuation"]):
        return "VALUATION"
    if any(k in s for k in ["finance", "financial", "dart", "사업보고서", "분기보고서", "반기보고서"]):
        return "DART" if "dart" in s or "보고서" in s else "FINANCE"
    if any(k in s for k in ["homepage", "home", "ir", "web", "evidence_harvest", "source/"]):
        return "IR_HOMEPAGE"
    if any(k in name for k in ["tech", "formula", "template", "excel"]):
        return "TECH_OUTPUT"
    return "TECH_OUTPUT"


def _iter_candidate_paths(company_dir: str, field: str = "반도체") -> List[Path]:
    roots: List[Path] = []
    for agent in ["tech", "valuation", "finance"]:
        try:
            roots.append(company_agent_dir(company_dir, agent, create=False))
        except Exception:
            pass
    # Conservative fallbacks for zip-extracted #U paths or legacy layout.
    data_root = ROOT / "data"
    if data_root.exists():
        slug = resolve_company_slug(company_dir, default=company_dir)
        for p in data_root.glob(f"**/{slug}"):
            if p.is_dir():
                roots.extend([p / "tech", p / "valuation", p / "finance"])
        for p in data_root.glob("**/*"):
            if p.is_dir() and company_dir.lower() in p.name.lower():
                roots.extend([p / "tech", p / "valuation", p / "finance"])
    seen_roots: List[Path] = []
    seen = set()
    for r in roots:
        try:
            key = str(r.resolve())
        except Exception:
            key = str(r)
        if key not in seen and r.exists():
            seen.add(key)
            seen_roots.append(r)

    paths: List[Path] = []
    seen_files: set[str] = set()
    for root in seen_roots:
        local_count: Dict[str, int] = {}
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext not in SUPPORTED_TEXT_EXTS and ext not in SUPPORTED_OPTIONAL_EXTS:
                continue
            if p.name.startswith("~$") or ".git" in p.parts:
                continue
            group = _infer_source_group(p)
            local_count[group] = local_count.get(group, 0) + 1
            if local_count[group] > MAX_SOURCE_FILES_PER_GROUP:
                continue
            try:
                key = str(p.resolve())
            except Exception:
                key = str(p)
            if key not in seen_files:
                seen_files.add(key)
                paths.append(p)
    return paths


def collect_source_documents(company_dir: str, company: str, field: str = "반도체") -> List[SourceDoc]:
    docs: List[SourceDoc] = []
    for p in _iter_candidate_paths(company_dir, field=field):
        text = _read_file_text(p)
        if not text:
            continue
        urls = _extract_urls(text)
        group = _infer_source_group(p)
        docs.append(
            SourceDoc(
                source_group=group,
                source_file=p.name,
                rel_path=_rel(p),
                text=text,
                urls=urls,
                fallback_urls=[] if urls else _fallback_urls(group, company),
            )
        )
    return docs


def _sentence_candidates(text: str, keywords: Sequence[str]) -> List[Tuple[str, List[str]]]:
    out: List[Tuple[str, List[str]]] = []
    chunks = HANGUL_SENTENCE_SPLIT_RE.split(text or "")
    for raw in chunks:
        s = re.sub(r"\s+", " ", raw).strip()
        if len(s) < 8:
            continue
        matched = [kw for kw in keywords if kw and kw.lower() in s.lower()]
        if matched:
            out.append((s[:420], matched[:8]))
    if not out:
        # Fallback to local context around keyword for long files without sentence boundaries.
        lower = (text or "").lower()
        for kw in keywords:
            pos = lower.find(kw.lower())
            if pos >= 0:
                start = max(0, pos - 160)
                end = min(len(text), pos + 260)
                snippet = re.sub(r"\s+", " ", text[start:end]).strip()
                out.append((snippet[:420], [kw]))
    return out


def _dedupe_evidence(items: List[EvidenceItem], limit: int = 8) -> List[EvidenceItem]:
    result: List[EvidenceItem] = []
    seen = set()
    priority = {DIRECT_STATUS: 0, PARTIAL_STATUS: 1, INDIRECT_STATUS: 2, CROSS_CHECK_STATUS: 3, NOT_FOUND_STATUS: 4}
    for item in sorted(items, key=lambda x: (priority.get(x.evidence_level, 9), x.source_group, x.source_file)):
        key = re.sub(r"\W+", "", item.snippet.lower())[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _extract_dimension_evidence(docs: Sequence[SourceDoc], dimension: str) -> Dict[str, Any]:
    rules = DIMENSION_RULES[dimension]
    direct_terms = list(rules["direct"])
    indirect_terms = list(rules["indirect"])
    all_terms = direct_terms + [x for x in indirect_terms if x not in direct_terms]
    evidence: List[EvidenceItem] = []

    for doc in docs:
        # These dimensions should mainly rely on DART/valuation/finance/company source,
        # but tech outputs can still provide indirect product evidence.
        for snippet, matched in _sentence_candidates(doc.text, all_terms):
            has_direct = any(kw.lower() in snippet.lower() for kw in direct_terms)
            has_indirect = any(kw.lower() in snippet.lower() for kw in indirect_terms)
            if has_direct:
                level = DIRECT_STATUS
            elif has_indirect:
                level = INDIRECT_STATUS
            else:
                level = PARTIAL_STATUS
            # Margin/FCF needs finance/valuation cross-check when only tech wording exists.
            if dimension == "margin_cashflow_linkage" and doc.source_group in {"TECH_OUTPUT", "IR_HOMEPAGE"} and level != DIRECT_STATUS:
                level = CROSS_CHECK_STATUS
            evidence.append(
                EvidenceItem(
                    source_group=doc.source_group,
                    source_file=doc.rel_path,
                    evidence_level=level,
                    matched_keywords=matched,
                    snippet=snippet,
                    urls=doc.urls[:5],
                    fallback_urls=doc.fallback_urls[:5],
                )
            )

    evidence = _dedupe_evidence(evidence, limit=8)
    direct = sum(1 for x in evidence if x.evidence_level == DIRECT_STATUS)
    indirect = sum(1 for x in evidence if x.evidence_level == INDIRECT_STATUS)
    partial = sum(1 for x in evidence if x.evidence_level in {PARTIAL_STATUS, CROSS_CHECK_STATUS})

    if direct:
        status = DIRECT_STATUS
    elif indirect:
        status = INDIRECT_STATUS
    elif partial:
        status = CROSS_CHECK_STATUS if dimension == "margin_cashflow_linkage" else PARTIAL_STATUS
    else:
        status = NOT_FOUND_STATUS

    return {
        "dimension": dimension,
        "label": DIMENSION_LABELS.get(dimension, dimension),
        "status": status,
        "status_kr": STATUS_KR.get(status, status),
        "score": STATUS_SCORE.get(status, 0.0),
        "direct_evidence_count": direct,
        "indirect_evidence_count": indirect,
        "partial_or_cross_check_count": partial,
        "limited_evidence_count": 0 if evidence else 1,
        "evidence": [asdict(x) for x in evidence],
        "summary": _dimension_summary(dimension, status, direct, indirect, partial),
    }


def _dimension_summary(dimension: str, status: str, direct: int, indirect: int, partial: int) -> str:
    label = DIMENSION_LABELS.get(dimension, dimension)
    if status == DIRECT_STATUS:
        return f"{label} 관련 직접 근거가 {direct}건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다."
    if status == INDIRECT_STATUS:
        return f"{label} 관련 간접 근거가 {indirect}건 확인됩니다. 고객사·계약·제품별 매출 등 직접 근거는 추가 확인이 필요합니다."
    if status == PARTIAL_STATUS:
        return f"{label} 관련 부분 근거가 {partial}건 확인됩니다. 직접 근거로 단정하지 않고 보조 신호로만 반영합니다."
    if status == CROSS_CHECK_STATUS:
        return f"{label}는 일부 단서가 있으나 finance/valuation 지표와 교차 검증해야 합니다."
    return f"{label} 관련 직접/간접 근거가 원천 산출물에서 충분히 확인되지 않았습니다."


def _count_csv_rows(path: Path) -> int:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, errors="replace", newline="") as f:
                return max(0, sum(1 for _ in csv.DictReader(f)))
        except Exception:
            continue
    return 0


def _load_first_json(paths: Iterable[Path]) -> Dict[str, Any]:
    for p in paths:
        if not p.exists() or p.suffix.lower() != ".json":
            continue
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            return json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
    return {}


def _find_tech_dir(company_dir: str) -> Path:
    try:
        return company_agent_dir(company_dir, "tech", create=True)
    except Exception:
        return ROOT / "data" / "반도체" / company_dir / "tech"


def _ip_feature_paths(tech_dir: Path, slug: str) -> Dict[str, List[Path]]:
    return {
        "legal": list(tech_dir.glob("*tech_ip_legal_features.json")) + list(tech_dir.glob("*ip_legal*.json")),
        "claim": list(tech_dir.glob("*tech_ip_claim_features.json")) + list(tech_dir.glob("*claims*.json")) + list(tech_dir.glob("*claims*.csv")),
        "citation": list(tech_dir.glob("*tech_ip_citation_features.json")) + list(tech_dir.glob("*citations*.json")) + list(tech_dir.glob("*citations*.csv")),
        "family": list(tech_dir.glob("*tech_ip_family_features.json")) + list(tech_dir.glob("*family*.json")) + list(tech_dir.glob("*family*.csv")),
        "composite": list(tech_dir.glob("*tech_ip_evidence_composite.json")) + list(tech_dir.glob("*ip_evidence_composite*.json")),
    }


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def _first_numeric(obj: Any, keys: Sequence[str]) -> Optional[float]:
    found: Optional[float] = None

    def walk(x: Any) -> None:
        nonlocal found
        if found is not None:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                if str(k) in keys:
                    n = _num(v)
                    if n is not None:
                        found = n
                        return
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return found


def _extract_ip_quality(company_dir: str, company: str, docs: Sequence[SourceDoc]) -> Dict[str, Any]:
    slug = resolve_company_slug(company_dir, default=company_dir)
    tech_dir = _find_tech_dir(slug)
    paths = _ip_feature_paths(tech_dir, slug)
    legal = _load_first_json(paths["legal"])
    claim = _load_first_json(paths["claim"])
    citation = _load_first_json(paths["citation"])
    family = _load_first_json(paths["family"])
    composite = _load_first_json(paths["composite"])

    claim_csv_rows = sum(_count_csv_rows(p) for p in paths["claim"] if p.suffix.lower() == ".csv")
    citation_csv_rows = sum(_count_csv_rows(p) for p in paths["citation"] if p.suffix.lower() == ".csv")
    family_csv_rows = sum(_count_csv_rows(p) for p in paths["family"] if p.suffix.lower() == ".csv")

    claim_count = _first_numeric(claim, ["claim_count", "claims_count", "total_claims", "independent_claim_count_estimated"]) or claim_csv_rows
    forward_citations = _first_numeric(citation, ["forward_citation_count_total", "external_forward_citation_count", "forward_citations"]) or citation_csv_rows
    family_count = _first_numeric(family, ["family_patent_count", "overseas_family_patents", "family_count", "pct_patents"]) or family_csv_rows
    legal_score = _first_numeric(legal, ["legal_stability_score_estimated", "registration_rate_estimated", "alive_rate_among_registered_estimated"])
    composite_score = _first_numeric(composite, ["ip_evidence_composite_score", "score"])

    components = {
        "legal_status": {
            "status": "COLLECTED" if legal else "NOT_FOUND",
            "score_or_rate": legal_score,
            "source_file": _rel(paths["legal"][0]) if paths["legal"] else None,
        },
        "claims": {
            "status": "COLLECTED" if claim_count and claim_count > 0 else "NO_CLAIMS_COLLECTED",
            "count": claim_count,
            "source_file": _rel(paths["claim"][0]) if paths["claim"] else None,
        },
        "citations": {
            "status": "COLLECTED" if forward_citations and forward_citations > 0 else "NO_CITATION_COLLECTED",
            "count": forward_citations,
            "source_file": _rel(paths["citation"][0]) if paths["citation"] else None,
        },
        "family": {
            "status": "COLLECTED" if family_count and family_count > 0 else "NO_FAMILY_COLLECTED",
            "count": family_count,
            "source_file": _rel(paths["family"][0]) if paths["family"] else None,
        },
        "composite": {
            "status": "COLLECTED" if composite else "NOT_FOUND",
            "score": composite_score,
            "bridge_signal": composite.get("bridge_signal") if isinstance(composite, dict) else None,
            "source_file": _rel(paths["composite"][0]) if paths["composite"] else None,
        },
    }

    collected = sum(1 for k in ["legal_status", "claims", "citations", "family"] if components[k]["status"] == "COLLECTED")
    if collected >= 3:
        status = DIRECT_STATUS
    elif collected >= 1:
        status = PARTIAL_STATUS
    else:
        status = NOT_FOUND_STATUS

    evidence_items: List[EvidenceItem] = []
    for key, comp in components.items():
        if comp.get("source_file"):
            evidence_items.append(
                EvidenceItem(
                    source_group="KIPRIS",
                    source_file=str(comp.get("source_file")),
                    evidence_level=DIRECT_STATUS if comp.get("status") == "COLLECTED" else PARTIAL_STATUS,
                    matched_keywords=[key, str(comp.get("status"))],
                    snippet=f"{key}: status={comp.get('status')}, count={comp.get('count')}, score={comp.get('score') or comp.get('score_or_rate')}, signal={comp.get('bridge_signal')}",
                    urls=[],
                    fallback_urls=_fallback_urls("KIPRIS", company),
                )
            )

    return {
        "dimension": "ip_quality",
        "label": DIMENSION_LABELS["ip_quality"],
        "status": status,
        "status_kr": STATUS_KR.get(status, status),
        "score": composite_score if composite_score is not None else STATUS_SCORE.get(status, 0.0),
        "direct_evidence_count": collected,
        "indirect_evidence_count": 0,
        "partial_or_cross_check_count": max(0, 4 - collected),
        "limited_evidence_count": 0 if collected else 1,
        "components": components,
        "evidence": [asdict(x) for x in evidence_items],
        "summary": (
            "KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. "
            "특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다."
        ),
    }


def _all_urls_from_docs(docs: Sequence[SourceDoc]) -> Dict[str, Any]:
    by_group: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        bucket = by_group.setdefault(d.source_group, {"detected_urls": [], "fallback_urls": []})
        for u in d.urls:
            if u not in bucket["detected_urls"]:
                bucket["detected_urls"].append(u)
        for u in d.fallback_urls:
            if u not in bucket["fallback_urls"]:
                bucket["fallback_urls"].append(u)
    return by_group


def _build_next_checkpoints(dimensions: Dict[str, Dict[str, Any]]) -> List[str]:
    cp: List[str] = []
    ca = dimensions.get("customer_adoption", {})
    mp = dimensions.get("mass_production", {})
    rv = dimensions.get("revenue_conversion", {})
    ip = dimensions.get("ip_quality", {})
    mf = dimensions.get("margin_cashflow_linkage", {})

    if ca.get("status") != DIRECT_STATUS:
        cp.append("고객 채택: 고객사별 design-win, 공급계약, 납품 공시 또는 주요 고객 승인 근거를 우선 확인")
    else:
        cp.append("고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인")

    if mp.get("status") != DIRECT_STATUS:
        cp.append("양산: CAPA, 생산라인, 양산 개시, 고객 승인 양산 공급 여부를 DART·IR·홈페이지 원천으로 추가 확인")
    else:
        cp.append("양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인")

    if rv.get("status") != DIRECT_STATUS:
        cp.append("매출 전환: 제품군별 매출, 수주잔고, 출하량과 핵심 기술 키워드의 연결 여부 확인")
    else:
        cp.append("매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인")

    ip_components = ip.get("components") or {}
    weak_ip = [k for k in ["legal_status", "claims", "citations", "family"] if (ip_components.get(k) or {}).get("status") != "COLLECTED"]
    if weak_ip:
        cp.append(f"IP 품질: {', '.join(weak_ip)} 데이터 보강 후 청구항·인용·패밀리·존속 상태를 재점수화")
    else:
        cp.append("IP 품질: 청구항·인용·패밀리·존속 상태가 수집된 상태이므로 IP Evidence Composite와 Bridge 조정값의 방향성을 점검")

    if mf.get("status") != DIRECT_STATUS:
        cp.append("마진·원가·현금흐름: 원가율, 영업이익률, CAPEX, 영업현금흐름, FCF 개선과 기술 적용의 교차 검증")
    else:
        cp.append("마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인")

    return cp


def _overall_score(dimensions: Dict[str, Dict[str, Any]]) -> float:
    weights = {
        "customer_adoption": 0.25,
        "mass_production": 0.20,
        "revenue_conversion": 0.25,
        "ip_quality": 0.15,
        "margin_cashflow_linkage": 0.15,
    }
    total = 0.0
    wsum = 0.0
    for k, w in weights.items():
        v = dimensions.get(k, {})
        score = _num(v.get("score"))
        if score is None:
            score = STATUS_SCORE.get(v.get("status"), 0.0)
        total += float(score) * w
        wsum += w
    return round(total / max(wsum, 1e-9), 2)


def _overall_label(score: float) -> str:
    if score >= 75:
        return "VALUE_EVIDENCE_STRONG"
    if score >= 60:
        return "VALUE_EVIDENCE_PARTIAL_POSITIVE"
    if score >= 45:
        return "VALUE_EVIDENCE_WATCH"
    return "VALUE_EVIDENCE_WEAK"


def render_value_evidence_bridge_md(payload: Dict[str, Any]) -> str:
    company = payload.get("company") or payload.get("company_dir") or "기업"
    lines = [
        f"# {company} Tech Intake Value Evidence Bridge",
        "",
        "## 1. 요약",
        f"- 생성 시각: {payload.get('created_at')}",
        f"- 종합 점수: {payload.get('value_evidence_score')}/100",
        f"- 종합 라벨: {payload.get('value_evidence_label')}",
        f"- 원천 문서 수: {payload.get('source_document_count')}개",
        "",
        "## 2. 기술 → 사업화 → 재무 연결 근거",
        "| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    dims = payload.get("dimensions") or {}
    for key in ["customer_adoption", "mass_production", "revenue_conversion", "ip_quality", "margin_cashflow_linkage"]:
        d = dims.get(key) or {}
        lines.append(
            f"| {d.get('label') or key} | {d.get('status_kr') or d.get('status')} | {d.get('score')} | "
            f"{d.get('direct_evidence_count', 0)} | {d.get('indirect_evidence_count', 0)} | {d.get('partial_or_cross_check_count', 0)} | {d.get('summary', '')} |"
        )

    lines += ["", "## 3. 대표 근거"]
    for key, d in dims.items():
        lines += ["", f"### {d.get('label') or key}"]
        evs = d.get("evidence") or []
        if not evs:
            lines.append("- 확인된 근거 없음")
            continue
        for ev in evs[:5]:
            urls = ev.get("urls") or ev.get("fallback_urls") or []
            url_text = ", ".join(urls[:2]) if urls else "URL 확인 제한"
            lines.append(
                f"- [{ev.get('evidence_level')}] {ev.get('snippet')} "
                f"(source={ev.get('source_file')}, keywords={', '.join(ev.get('matched_keywords') or [])}, urls={url_text})"
            )

    lines += ["", "## 4. 다음 확인 포인트"]
    for cp in payload.get("next_checkpoints_refined") or []:
        lines.append(f"- {cp}")

    lines += ["", "## 5. URL 인식 결과 및 대체 조회 URL"]
    by_group = payload.get("source_url_map") or {}
    for group, data in by_group.items():
        detected = data.get("detected_urls") or []
        fallback = data.get("fallback_urls") or []
        lines.append(f"- **{group}**")
        if detected:
            for u in detected[:6]:
                lines.append(f"  - detected: {u}")
        else:
            lines.append("  - detected: URL 확인 제한")
        for u in fallback[:4]:
            lines.append(f"  - fallback: {u}")

    return "\n".join(lines).strip() + "\n"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def merge_value_evidence_into_summary(summary: Dict[str, Any], bridge: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(summary, dict) or not isinstance(bridge, dict) or not bridge:
        return summary
    summary["value_evidence_bridge"] = bridge
    summary["value_evidence_bridge_merge_status"] = "MERGED"
    summary["value_evidence_score"] = bridge.get("value_evidence_score")
    summary["value_evidence_label"] = bridge.get("value_evidence_label")
    summary["next_checkpoints_refined"] = bridge.get("next_checkpoints_refined") or []

    # Also expose a compact form under tech_to_value for Chair/Auditor compatibility.
    tv = summary.get("tech_to_value")
    if not isinstance(tv, dict):
        tv = {}
        summary["tech_to_value"] = tv
    tv["value_evidence_score"] = bridge.get("value_evidence_score")
    tv["value_evidence_label"] = bridge.get("value_evidence_label")

    policies = list(summary.get("chair_policy") or [])
    policy = "Value Evidence Bridge는 고객 채택·양산·매출 전환·IP 품질·마진/FCF 연결 근거를 분리해 Chair 다음 확인 포인트에 우선 반영합니다."
    if policy not in policies:
        policies.append(policy)
    summary["chair_policy"] = policies
    return summary


def _summary_paths(company_dir: str) -> List[Path]:
    tech_dir = _find_tech_dir(company_dir)
    slug = resolve_company_slug(company_dir, default=company_dir)
    candidates = [
        tech_dir / "tech_chair_summary.json",
        tech_dir / f"{slug}_tech_chair_summary.json",
    ]
    return [p for p in candidates if p.exists()]


def merge_bridge_into_saved_summary(company_dir: str, bridge: Dict[str, Any]) -> List[str]:
    wrote: List[str] = []
    for p in _summary_paths(company_dir):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        data = merge_value_evidence_into_summary(data, bridge)
        _write_json(p, data)
        wrote.append(_rel(p))
    return wrote


def generate_value_evidence_bridge(
    *,
    company_dir: str,
    company: str | None = None,
    field: str = "반도체",
    write: bool = True,
    merge_summary: bool = True,
) -> Dict[str, Any]:
    slug = resolve_company_slug(company_dir, default=company_dir)
    display_company = company or resolve_company_name(slug)
    docs = collect_source_documents(slug, display_company, field=field)
    dimensions: Dict[str, Dict[str, Any]] = {}
    for dim in ["customer_adoption", "mass_production", "revenue_conversion", "margin_cashflow_linkage"]:
        dimensions[dim] = _extract_dimension_evidence(docs, dim)
    dimensions["ip_quality"] = _extract_ip_quality(slug, display_company, docs)

    score = _overall_score(dimensions)
    payload: Dict[str, Any] = {
        "agent": "tech_intake",
        "artifact": "tech_intake_value_evidence_bridge",
        "version": "value_evidence_bridge_v2_url_fallback_batch_ready",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "company": display_company,
        "company_dir": slug,
        "company_slug": slug,
        "source_document_count": len(docs),
        "source_documents": [
            {
                "source_group": d.source_group,
                "source_file": d.rel_path,
                "detected_url_count": len(d.urls),
                "fallback_url_count": len(d.fallback_urls),
            }
            for d in docs[:160]
        ],
        "source_url_map": _all_urls_from_docs(docs),
        "dimensions": dimensions,
        "value_evidence_score": score,
        "value_evidence_label": _overall_label(score),
        "next_checkpoints_refined": _build_next_checkpoints(dimensions),
        "usage_rule": (
            "This artifact does not claim that technology already generated revenue or FCF. "
            "It separates direct evidence, indirect evidence, partial evidence, and cross-check-required items for Chair reporting."
        ),
    }

    if write:
        tech_dir = _find_tech_dir(slug)
        json_path = tech_dir / "tech_intake_value_evidence.json"
        md_path = tech_dir / "tech_intake_value_evidence.md"
        pref_json_path = tech_dir / f"{slug}_tech_intake_value_evidence.json"
        pref_md_path = tech_dir / f"{slug}_tech_intake_value_evidence.md"
        _write_json(json_path, payload)
        _write_json(pref_json_path, payload)
        md = render_value_evidence_bridge_md(payload)
        _write_text(md_path, md)
        _write_text(pref_md_path, md)
        payload["output_files"] = {
            "json": _rel(json_path),
            "md": _rel(md_path),
            "prefixed_json": _rel(pref_json_path),
            "prefixed_md": _rel(pref_md_path),
        }
        # Re-write with output_files included.
        _write_json(json_path, payload)
        _write_json(pref_json_path, payload)

    if merge_summary:
        payload["merged_summary_files"] = merge_bridge_into_saved_summary(slug, payload)

    return payload


def load_value_evidence_bridge(company_dir: str) -> Dict[str, Any]:
    tech_dir = _find_tech_dir(company_dir)
    slug = resolve_company_slug(company_dir, default=company_dir)
    for p in [tech_dir / "tech_intake_value_evidence.json", tech_dir / f"{slug}_tech_intake_value_evidence.json"]:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                return json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
    return {}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Tech Intake Value Evidence Bridge for Chair next checkpoints.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", default="")
    parser.add_argument("--no-merge-summary", action="store_true")
    args = parser.parse_args(argv)

    payload = generate_value_evidence_bridge(
        company_dir=args.company_dir,
        company=args.company or None,
        field=args.field,
        write=True,
        merge_summary=not args.no_merge_summary,
    )
    print("=" * 80)
    print("[Tech Intake Value Evidence Bridge]")
    print(f"company     : {payload.get('company')} / {payload.get('company_dir')}")
    print(f"score       : {payload.get('value_evidence_score')}")
    print(f"label       : {payload.get('value_evidence_label')}")
    print(f"source docs : {payload.get('source_document_count')}")
    print(f"outputs     : {payload.get('output_files')}")
    print(f"merged      : {payload.get('merged_summary_files')}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

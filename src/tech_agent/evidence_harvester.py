from __future__ import annotations

import csv
import html
import json
import os
import re
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

try:
    from openpyxl import load_workbook
except Exception:  # pragma: no cover
    load_workbook = None

from .config import DEFAULT_TEMPLATE_PATH, OUTPUT_DIR, REQUEST_TIMEOUT, ROOT_DIR, USER_AGENT
from .dart_client import OpenDartClient
from .formula_rules import extract_quantitative_signals, load_formula_rules
from .source_planner import load_template_framework
from .utils import clean_text, ensure_dir

URL_RE = re.compile(r"https?://[^\s)\]}>,\"']+")
LINK_RE = re.compile(r"(?is)<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>")
TAG_RE = re.compile(r"(?is)<[^>]+>")

SKIP_DIRS = {".venv", ".git", ".cache", "__pycache__", "node_modules"}
SKIP_EVIDENCE_DIRS = {"outputs", "audit", "templates"}
TECH_NUM_RE = re.compile(
    r"(?P<value>[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[-+]?\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|배|건|개|개사|곳|억원|백만원|천만원|원|년|개월|회|종|명|라인|단|nm|㎚|um|μm|㎛|℃|도|GWh|MWh|mm|㎜)?"
)

SEMICONDUCTOR_TERMS = [
    "WLP", "FOWLP", "FO-WLP", "FOPLP", "FO-PLP", "PLP", "Bumping", "범핑", "패키징", "후공정", "Test", "테스트",
    "PMIC", "DDI", "CIS", "SiP", "AiP", "EMI", "Shielding", "차폐", "리드탭", "전구체", "Precursor", "ALD", "CVD",
    "고순도", "micro bump", "μm", "nm", "HBM", "AI", "HPC", "5G", "EV", "Mobility", "Wearable", "양산", "공정", "수율",
]

NOISE_TOKENS = [
    "본문기", "맵 -->", "청캠", "기보", "주보", "공보", "복리", "CAREERS", "FAQ", "ESG News", "KR EN", "사이트맵",
    "개인정보", "이용약관", "COPYRIGHT", "copyright", "로그인", "회원가입", "메뉴", "상단", "하단", "검색", "Language",
]
FINANCE_NOISE = ["금융자산", "금융부채", "공정가치", "당기손익", "상각후원가", "리스부채", "파생상품", "법인세"]

CATEGORY_TERMS: dict[str, list[str]] = {
    "대표 기술": ["기술", "공정", "패키징", "WLP", "FOWLP", "PLP", "Bumping", "범핑", "전구체", "소재", "양산", "수율", "성능", "고순도", "후공정"],
    "핵심 제품/서비스": ["제품", "서비스", "매출", "사업", "Bumping", "WLP", "FOWLP", "PLP", "SiP", "TEST", "테스트", "반도체", "전자재료", "리드탭"],
    "고객 구매 이유": ["고객", "채택", "공급", "양산", "수주", "성능", "원가", "효율", "신뢰성", "소형화", "박형화", "차폐", "수율", "품질"],
    "경쟁 우위/대체가능성": ["특허", "산업재산권", "노하우", "국산화", "진입장벽", "대체", "독자", "기술력", "공정", "양산", "승인", "인증"],
    "활용 및 확장 산업": ["AI", "HPC", "5G", "EV", "전장", "모바일", "자동차", "서버", "데이터센터", "디스플레이", "Application", "응용", "시장"],
    "진입 부담/장벽": ["양산", "공정", "수율", "검증", "승인", "인증", "Qualification", "라인", "설비", "노하우", "고객 승인", "품질"],
    "R&D 강도": ["연구개발", "R&D", "개발", "개발과제", "설비투자", "투자", "인력", "센터", "특허", "과제"],
}

ITEM_TERMS: dict[str, list[str]] = {
    "핵심 기술 키워드": ["기술", "공정", "패키징", "WLP", "FOWLP", "PLP", "Bumping", "범핑", "후공정", "전구체", "소재"],
    "적용 방식": ["적용", "Application", "응용", "공정", "제품", "양산", "라인", "패키징", "테스트"],
    "핵심 성능 요소": ["성능", "수율", "고성능", "고밀도", "고방열", "신뢰성", "소형화", "박형화", "고순도", "nm", "μm", "%"],
    "제품명/서비스명": ["Bumping", "WLP", "FOWLP", "PLP", "SiP", "TEST", "테스트", "전자재료", "리드탭", "제품", "서비스"],
    "적용 기술": ["적용", "기술", "공정", "패키징", "소재", "양산"],
    "주요 고객군": ["고객", "고객사", "공급", "납품", "수주", "양산", "자동차", "모바일", "서버", "AI"],
    "고객 효익": ["효익", "성능", "원가", "품질", "신뢰성", "수율", "소형화", "박형화", "차폐", "고방열"],
    "경쟁 제품 대비 장점": ["대비", "경쟁", "장점", "우위", "개선", "차별", "원가", "성능", "효율"],
    "실제 적용 사례": ["적용", "사례", "양산", "공급", "고객", "수주", "자동차", "센서", "PMIC", "DDI", "CIS"],
    "등록 특허": ["특허", "산업재산권", "등록", "출원", "청구항", "IPC", "CPC"],
    "제조 노하우": ["노하우", "공정", "양산", "수율", "제조", "검증", "라인"],
    "고객사 레퍼런스": ["고객", "고객사", "공급", "승인", "레퍼런스", "양산", "수주"],
    "대체가능성": ["대체", "진입장벽", "경쟁", "회피", "독자", "국산화"],
    "활용 산업": ["AI", "HPC", "5G", "EV", "전장", "모바일", "서버", "자동차", "디스플레이"],
    "확장 가능 제품": ["확장", "신규", "제품", "Application", "응용", "포트폴리오"],
    "전방 시장": ["시장", "전방", "수요", "AI", "HPC", "전장", "모바일", "서버", "자동차"],
    "인증/승인": ["인증", "승인", "고객 승인", "Qualification", "검증", "품질"],
    "양산 난이도": ["양산", "수율", "공정", "라인", "설비", "난이도", "검증"],
    "전환 비용": ["전환", "비용", "교체", "대체", "승인", "검증", "장기"],
    "연구개발비": ["연구개발비", "R&D", "개발비", "연구개발", "투자", "억원", "백만원"],
    "개발 과제": ["개발과제", "과제", "개발", "국책", "연구", "기술개발"],
    "설비투자/인력": ["설비투자", "CAPEX", "투자", "인력", "연구원", "센터", "라인"],
}

PROCESS_PRODUCT_TERMS = ["Bumping", "WLP", "FOWLP", "FO-WLP", "PLP", "FO-PLP", "SiP", "TEST", "테스트", "PMIC", "DDI", "CIS", "EMI", "리드탭", "전구체", "전자재료", "패키징"]
INDUSTRY_TERMS = ["AI", "HPC", "5G", "EV", "전장", "자동차", "모바일", "서버", "데이터센터", "디스플레이", "웨어러블", "Wearable", "스마트폰", "TV", "Monitor"]
BENEFIT_TERMS = ["소형화", "박형화", "고성능", "고방열", "고신뢰성", "원가", "생산성", "수율", "불량률", "처리속도", "수명", "효율", "차폐", "품질"]
BARRIER_TERMS = ["특허", "산업재산권", "고객 승인", "인증", "Qualification", "양산", "공정", "노하우", "국산화", "독자", "진입장벽", "수율", "검증"]
RD_TERMS = ["연구개발", "R&D", "개발", "설비투자", "CAPEX", "투자", "과제", "인력", "센터", "양산기술", "특허"]


def _lst(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        out: list[Any] = []
        for x in v.values():
            out += _lst(x)
        return out
    return [v]


def _line_clean(line: Any) -> str:
    s = clean_text(line)
    s = re.sub(r"\s+", " ", s).strip(" -\t\r\n")
    return s


def _is_noise_line(line: str) -> bool:
    s = _line_clean(line)
    if len(s) < 8:
        return True
    if any(tok.lower() in s.lower() for tok in NOISE_TOKENS):
        return True
    if len(s) > 260 and sum(s.count(x) for x in ["-->", "|", ">", "<"]) >= 2:
        return True
    korean_english_digits = len(re.findall(r"[가-힣A-Za-z0-9]", s))
    if korean_english_digits / max(len(s), 1) < 0.45:
        return True
    # 홈페이지 메뉴가 길게 붙은 문장 제거
    menu_hits = sum(1 for t in ["COMPANY", "BUSINESS", "R&D", "IR", "CAREERS", "ESG"] if t in s)
    if menu_hits >= 3 and len(s) > 120:
        return True
    return False


def _normalize_source_text(raw: str, max_chars: int = 90000) -> str:
    raw = str(raw or "")[:max_chars]
    raw = html.unescape(raw)
    raw = re.sub(r"(?is)<script.*?>.*?</script>", "\n", raw)
    raw = re.sub(r"(?is)<style.*?>.*?</style>", "\n", raw)
    raw = re.sub(r"(?is)<(br|p|div|li|tr|td|th|h[1-6]|section|article|span)[^>]*>", "\n", raw)
    raw = TAG_RE.sub("\n", raw)
    raw = raw.replace("\r", "\n")
    raw = re.sub(r"[ \t]+", " ", raw)
    lines: list[str] = []
    seen: set[str] = set()
    for line in raw.split("\n"):
        s = _line_clean(line)
        if _is_noise_line(s):
            continue
        key = s[:120]
        if key in seen:
            continue
        seen.add(key)
        lines.append(s)
        if sum(len(x) for x in lines) > 50000:
            break
    return "\n".join(lines)


def identity_terms(company: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for k in ["corp_name", "name", "corp_name_en", "slug", "stock_code"]:
        v = clean_text(company.get(k))
        if v and v not in out:
            out.append(v)
    for v in _lst(company.get("aliases")):
        v = clean_text(v)
        if v and v not in out:
            out.append(v)
    return out


def company_terms(company: dict[str, Any]) -> list[str]:
    out = identity_terms(company)
    for k in ["keywords", "core_keywords", "tech_keywords", "products"]:
        for v in _lst(company.get(k)):
            v = clean_text(v)
            if v and v not in out:
                out.append(v)
    for t in SEMICONDUCTOR_TERMS:
        if t not in out:
            out.append(t)
    return out


def official_domains(company: dict[str, Any]) -> set[str]:
    domains: set[str] = set()
    for u in [company.get("homepage_url"), company.get("ir_url"), *_lst(company.get("extra_urls"))]:
        u = clean_text(u)
        if u.startswith("http"):
            try:
                domains.add(urlparse(u).netloc.lower().replace("www.", ""))
            except Exception:
                pass
    return domains


def _source_kind_from_url(url: str, company: dict[str, Any] | None = None) -> str:
    u = clean_text(url).lower()
    if "dart.fss" in u or "opendart" in u:
        return "dart_filing"
    if "kipris" in u or "patent" in u or "특허" in u:
        return "patent"
    if "ir" in u or "invest" in u:
        return "ir"
    if company:
        try:
            net = urlparse(url).netloc.lower().replace("www.", "") if url.startswith("http") else ""
            if any(net.endswith(d) for d in official_domains(company)):
                return "official_homepage"
        except Exception:
            pass
    return "web"


def relevance(text: str, company: dict[str, Any], url: str = "", title: str = "") -> tuple[float, list[str]]:
    joined = clean_text(" ".join([title, text, url])).lower()
    score = 0.0
    reasons: list[str] = []
    ids = identity_terms(company)
    if any(x.lower() in joined for x in ids if x):
        score += 9
        reasons.append("회사 식별어 매칭")
    hits = []
    for x in company_terms(company):
        if x and x.lower() in joined:
            hits.append(x)
    if hits:
        score += min(9, len(set(hits)) * 0.7)
        reasons.append("기술/제품 키워드: " + ", ".join(list(dict.fromkeys(hits))[:10]))
    if url.startswith("http"):
        net = urlparse(url).netloc.lower().replace("www.", "")
        if any(net.endswith(d) for d in official_domains(company)):
            score += 12
            reasons.append(f"공식 도메인: {net}")
        if any(x in net for x in ["dart.fss", "opendart", "kind.krx"]):
            score += 6
            reasons.append("공시/거래소 계열 출처")
    return max(score, 0), reasons


def _safe_get(url: str) -> tuple[str, str, str, list[str]]:
    if os.getenv("TECH_FETCH_URL_TEXT", "1").lower() not in {"1", "true", "yes", "y"}:
        return "", "", "SKIPPED", []
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=min(REQUEST_TIMEOUT, 12), allow_redirects=True)
        if r.status_code >= 400:
            return "", "", f"HTTP_{r.status_code}", []
        raw = r.text[:120000]
        mt = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
        title = _line_clean(_normalize_source_text(mt.group(1))) if mt else url
        links: list[str] = []
        for href, anchor in LINK_RE.findall(raw[:120000]):
            abs_url = urljoin(url, html.unescape(href))
            anchor_text = _line_clean(_normalize_source_text(anchor))
            if abs_url.startswith("http") and anchor_text:
                links.append(abs_url)
        return title, _normalize_source_text(raw), "OK", links[:120]
    except Exception as e:
        return "", "", f"ERROR:{type(e).__name__}", []


def _read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".yaml", ".yml"}:
            return _normalize_source_text(path.read_text(encoding="utf-8", errors="ignore")[:180000])
        if suffix == ".json":
            return _normalize_source_text(json.dumps(json.loads(path.read_text(encoding="utf-8", errors="ignore")), ensure_ascii=False)[:180000])
        if suffix in {".csv", ".tsv"}:
            rows: list[str] = []
            for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
                try:
                    with path.open("r", encoding=enc, errors="ignore", newline="") as f:
                        reader = csv.reader(f, delimiter="\t" if suffix == ".tsv" else ",")
                        for i, row in enumerate(reader):
                            if i > 500:
                                break
                            vals = [_line_clean(x) for x in row if _line_clean(x)]
                            if vals:
                                rows.append(" | ".join(vals))
                    break
                except Exception:
                    continue
            return _normalize_source_text("\n".join(rows))
        if suffix in {".xlsx", ".xlsm"} and load_workbook:
            wb = load_workbook(path, data_only=True, read_only=True)
            parts: list[str] = []
            for ws in wb.worksheets[:12]:
                parts.append(f"[sheet:{ws.title}]")
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i > 300:
                        break
                    vals = [_line_clean(x) for x in row[:30] if _line_clean(x)]
                    if vals:
                        parts.append(" | ".join(vals))
            return _normalize_source_text("\n".join(parts))
    except Exception:
        return ""
    return ""


def _url_contexts(text: str, window: int = 280) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in URL_RE.finditer(text or ""):
        url = m.group(0).rstrip(".,;]")
        context = clean_text(text[max(0, m.start() - window) : min(len(text), m.end() + window)])
        if url and all(url != x[0] for x in out):
            out.append((url, context))
    return out


def _should_skip_file(path: Path) -> bool:
    parts = set(path.parts)
    if path.name.lower() == ".env" or any(x in parts for x in SKIP_DIRS):
        return True
    rel = path.as_posix().lower()
    if "/data/<분야>/common/templates/" in rel or "/workspace/outputs/" in rel or "/workspace/audit/" in rel:
        return True
    name = path.name.lower()
    skip_name_tokens = ["stock", "market", "finance", "financial", "price", "ohlcv", "주식", "재무", "시세", "#uc8fc#uc2dd", "#uc7ac#ubb34"]
    if any(tok in name for tok in skip_name_tokens):
        return True
    if path.suffix.lower() not in {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".tsv", ".xlsx", ".xlsm"}:
        return True
    return False


def _source_kind_from_file(path: Path) -> str:
    p = path.as_posix().lower()
    name = path.name.lower()
    if "dart" in p or "사업보고서" in name or "분기보고서" in name or "반기보고서" in name:
        return "dart_filing"
    if "ir" in p or "ir" in name or "invest" in name:
        return "ir"
    if "kipris" in p or "patent" in p or "특허" in name:
        return "patent"
    if "companies" in p and name == "company.yaml":
        return "company_yaml"
    if "tech_sources" in p:
        return "local_tech_source"
    return "local_data"


def _add_doc(docs: list[dict[str, Any]], *, source_type: str, title: str, text: str, company: dict[str, Any], path: str = "", url: str = "") -> None:
    text = _normalize_source_text(text)
    if len(text) < 25:
        return
    score, reasons = relevance(text, company, url=url, title=title)
    if source_type in {"dart_filing", "official_homepage", "ir", "patent", "local_tech_source"}:
        score += 4
        reasons.append(f"대/중출처 직접 수집: {source_type}")
    elif source_type == "company_yaml":
        return
    if score < 5:
        return
    docs.append({
        "doc_id": f"tech.doc.{len(docs) + 1:03d}",
        "source_type": source_type,
        "title": clean_text(title)[:180],
        "path": path,
        "url": url,
        "text": text[:50000],
        "relevance_score": round(score, 2),
        "relevance_reasons": reasons,
    })


def _fetch_dart_business_report(company: dict[str, Any], company_dir: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    if os.getenv("TECH_ENABLE_DART_FETCH", "1").lower() not in {"1", "true", "yes", "y"}:
        return docs
    stock_code = clean_text(company.get("stock_code"))
    if not stock_code:
        return docs
    try:
        client = OpenDartClient()
        if not client.api_key:
            return docs
        text = client.get_latest_business_text(stock_code)
        if text:
            cache = ensure_dir(tech_source_dir(company_dir))
            cp = cache / "dart_latest_business_report.txt"
            cp.write_text(text, encoding="utf-8")
            _add_doc(docs, source_type="dart_filing", title="DART 최신 사업/반기/분기보고서", text=text, company=company, path=str(cp.relative_to(ROOT_DIR)))
    except Exception as e:
        docs.append({"doc_id": "tech.dart.error", "source_type": "dart_filing_error", "title": "DART 수집 오류", "path": "", "url": "", "text": "", "relevance_score": 0, "relevance_reasons": [f"DART fetch failed: {type(e).__name__}"]})
    return docs


def _seed_urls(company: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for url in [company.get("homepage_url"), company.get("ir_url"), *_lst(company.get("extra_urls"))]:
        u = clean_text(url)
        if u.startswith("http"):
            out.append({"url": u, "title": "company.yaml 등록 URL", "snippet": "공식/추가 URL", "source_type": _source_kind_from_url(u, company)})
    return out


def _search_urls(company: dict[str, Any]) -> list[dict[str, str]]:
    if os.getenv("TECH_ENABLE_WEB_SEARCH", "1").lower() not in {"1", "true", "yes", "y"}:
        return []
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    if not serper_key:
        return []
    out: list[dict[str, str]] = []
    name = clean_text(company.get("corp_name") or company.get("name") or company.get("slug"))
    queries = [
        f"{name} 사업보고서 기술 제품 연구개발 양산",
        f"{name} IR 제품 포트폴리오 매출 비중 패키징",
        f"{name} 특허 고객사 양산 공급 기술",
    ]
    for q in queries:
        try:
            r = requests.post("https://google.serper.dev/search", headers={"X-API-KEY": serper_key, "Content-Type": "application/json"}, json={"q": q, "num": 8, "hl": "ko"}, timeout=min(REQUEST_TIMEOUT, 12))
            data = r.json()
            for row in data.get("organic") or []:
                link = clean_text(row.get("link"))
                if link.startswith("http"):
                    out.append({"url": link, "title": clean_text(row.get("title")), "snippet": clean_text(row.get("snippet")), "source_type": _source_kind_from_url(link, company)})
        except Exception:
            continue
    return out[:24]


def _crawl_official_urls(company: dict[str, Any], seeds: list[dict[str, str]]) -> list[dict[str, str]]:
    if os.getenv("TECH_CRAWL_OFFICIAL_LINKS", "1").lower() not in {"1", "true", "yes", "y"}:
        return []
    out: list[dict[str, str]] = []
    domains = official_domains(company)
    checked: set[str] = set()
    priority_terms = ["business", "semiconductor", "bumping", "wlp", "fowlp", "plp", "test", "product", "technology", "r&d", "rnd", "ir", "overview", "patent", "research"]
    for seed in seeds[:6]:
        url = clean_text(seed.get("url"))
        if not url.startswith("http") or url in checked:
            continue
        checked.add(url)
        title, text, status, links = _safe_get(url)
        if status != "OK":
            continue
        for link in links:
            try:
                net = urlparse(link).netloc.lower().replace("www.", "")
            except Exception:
                continue
            if not any(net.endswith(d) for d in domains):
                continue
            low = link.lower()
            if not any(t in low for t in priority_terms):
                continue
            if link not in checked:
                checked.add(link)
                out.append({"url": link, "title": "official same-domain candidate", "snippet": "공식 사이트 내부 기술/제품 후보 링크", "source_type": _source_kind_from_url(link, company)})
            if len(out) >= 20:
                return out
    return out


def _collect_actual_docs(company: dict[str, Any], company_dir: str, framework: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    docs: list[dict[str, Any]] = []
    accepted_urls: list[dict[str, Any]] = []
    rejected_urls: list[dict[str, Any]] = []

    for d in _fetch_dart_business_report(company, company_dir):
        if d.get("text"):
            docs.append(d)

    roots = [
        company_common_dir(company_dir),
        tech_source_dir(company_dir),
        field_common_dir("data") / "tech_sources",
    ]
    # v11: workspace/data 전체를 무차별 스캔하지 않는다.
    # 재무/주가/시장 파일까지 읽으면 속도가 느리고 Tech 근거에 잡음이 섞이므로
    # 회사명/종목코드/tech/dart/ir/patent/사업보고서가 걸리는 파일만 보조적으로 확인한다.
    roots.append(field_common_dir("data"))
    url_candidates = _seed_urls(company)
    company_file_terms = [company_dir.lower()] + [clean_text(company.get(k)).lower() for k in ["corp_name", "name", "corp_name_en", "stock_code"] if clean_text(company.get(k))]
    source_name_terms = ["tech", "technology", "dart", "ir", "patent", "kipris", "사업보고서", "분기보고서", "반기보고서", "특허", "제품", "연구개발"]
    scanned_files = 0
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or _should_skip_file(path):
                continue
            rel_lower = str(path.relative_to(ROOT_DIR)).lower() if str(path).startswith(str(ROOT_DIR)) else str(path).lower()
            # workspace/data 일반 영역에서는 관련 파일만 선별
            if (field_common_dir("data")) in path.parents and "tech_sources" not in rel_lower:
                if not any(t and t in rel_lower for t in company_file_terms + source_name_terms):
                    continue
            scanned_files += 1
            if scanned_files > 160:
                break
            text = _read_file(path)
            if not text:
                continue
            rel = str(path.relative_to(ROOT_DIR)) if str(path).startswith(str(ROOT_DIR)) else str(path)
            source_type = _source_kind_from_file(path)
            if source_type == "company_yaml":
                continue
            _add_doc(docs, source_type=source_type, title=path.name, text=text, company=company, path=rel)
            for url, context in _url_contexts(text):
                url_candidates.append({"url": url, "title": path.name, "snippet": context, "source_type": "file_url"})
        if scanned_files > 160:
            break

    url_candidates += _search_urls(company)
    url_candidates += _crawl_official_urls(company, url_candidates)

    seen_urls: set[str] = set()
    for item in url_candidates:
        url = clean_text(item.get("url"))
        if not url.startswith("http") or url in seen_urls:
            continue
        seen_urls.add(url)
        title, fetched_text, status, _ = _safe_get(url)
        source_type = clean_text(item.get("source_type")) or _source_kind_from_url(url, company)
        combined = "\n".join([clean_text(item.get("title")), clean_text(item.get("snippet")), fetched_text])
        score, reasons = relevance(combined, company, url=url, title=title or item.get("title", ""))
        record = {"url": url, "title": title or clean_text(item.get("title")) or url, "snippet": clean_text(item.get("snippet")) or clean_text(fetched_text)[:350], "source_type": source_type, "status": status, "relevance_score": round(score, 2), "relevance_reasons": reasons}
        official = any("공식 도메인" in r for r in reasons)
        identity = any("회사 식별어" in r for r in reasons)
        if status != "OK" or not fetched_text:
            rejected_urls.append(record)
            continue
        if not official and not identity and score < 8:
            record["status"] = "REJECTED_LOW_RELEVANCE"
            rejected_urls.append(record)
            continue
        accepted_urls.append(record)
        _add_doc(docs, source_type=_source_kind_from_url(url, company), title=record["title"], text=combined, company=company, url=url)

    dedup: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for doc in sorted(docs, key=lambda x: (clean_text(x.get("source_type")) in {"dart_filing", "ir", "patent", "official_homepage"}, float(x.get("relevance_score") or 0)), reverse=True):
        key = clean_text(doc.get("url") or doc.get("path") or doc.get("title"))[:250]
        if key in seen_keys or not key:
            continue
        seen_keys.add(key)
        doc["doc_id"] = f"tech.doc.{len(dedup)+1:03d}"
        dedup.append(doc)
    return dedup, accepted_urls[:50], rejected_urls[:80]


def _sentences(text: str) -> list[str]:
    if not text:
        return []
    # 줄 단위 먼저, 긴 줄은 문장부호로 추가 분리
    candidates: list[str] = []
    for line in str(text).split("\n"):
        line = _line_clean(line)
        if _is_noise_line(line):
            continue
        parts = re.split(r"(?<=[.!?。])\s+|(?<=다)\s+|(?<=니다)\s+|(?<=음)\s+", line)
        for p in parts:
            s = _line_clean(p)
            if _is_noise_line(s):
                continue
            if 18 <= len(s) <= 420:
                candidates.append(s)
    # duplicate / near duplicate 제거
    out: list[str] = []
    seen: set[str] = set()
    for s in candidates:
        key = re.sub(r"\d+", "#", s.lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _keyword_hits(text: str, kws: list[str]) -> list[str]:
    low = clean_text(text).lower()
    hits = []
    for kw in kws:
        kw = clean_text(kw)
        if kw and kw.lower() in low and kw not in hits:
            hits.append(kw)
    return hits


def _item_keywords(company: dict[str, Any], section: dict[str, Any], item: dict[str, Any]) -> list[str]:
    cat = clean_text(section.get("category"))
    item_name = clean_text(item.get("item_name"))
    kws: list[str] = []
    for x in ITEM_TERMS.get(item_name, []) + CATEGORY_TERMS.get(cat, []):
        if x not in kws:
            kws.append(x)
    # 기업 등록 기술/제품은 근거 후보 확장용으로만 추가
    for k in ["core_keywords", "tech_keywords", "products"]:
        for v in _lst(company.get(k)):
            v = clean_text(v)
            if v and v not in kws:
                kws.append(v)
    return kws[:35]


def _source_matches_plan(doc: dict[str, Any], item: dict[str, Any]) -> bool:
    source_type = clean_text(doc.get("source_type"))
    plan = clean_text(" ".join([item.get("major_source", ""), item.get("middle_source", "")])).lower()
    if "사업" in plan and source_type == "dart_filing":
        return True
    if "홈페이지" in plan and source_type == "official_homepage":
        return True
    if "ir" in plan and source_type == "ir":
        return True
    if "특허" in plan and source_type == "patent":
        return True
    if "기사" in plan and source_type in {"web", "search", "naver_news"}:
        return True
    return source_type in {"dart_filing", "official_homepage", "ir", "patent", "local_tech_source"}


def _sentence_quality(sent: str, hits: list[str], company: dict[str, Any], doc: dict[str, Any]) -> float:
    if _is_noise_line(sent):
        return -100
    score = len(set(hits)) * 2.0
    st = clean_text(doc.get("source_type"))
    if st in {"dart_filing", "ir", "patent"}:
        score += 5
    elif st == "official_homepage":
        score += 3
    elif st == "local_tech_source":
        score += 2
    if any(x.lower() in sent.lower() for x in identity_terms(company) if x):
        score += 2
    if re.search(r"\d", sent):
        score += 1.5
    if any(t.lower() in sent.lower() for t in ["양산", "고객", "공급", "매출", "특허", "연구개발", "수율", "공정"]):
        score += 2
    if len(sent) > 320:
        score -= 1
    return score


def _pick_item_evidence(company: dict[str, Any], docs: list[dict[str, Any]], section: dict[str, Any], item: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    kws = _item_keywords(company, section, item)
    picked: list[dict[str, Any]] = []
    candidates: list[tuple[float, dict[str, Any], str, list[str]]] = []
    ids = [x for x in identity_terms(company) if x]
    for doc in docs:
        stype = clean_text(doc.get("source_type"))
        if stype == "company_yaml":
            continue
        for sent in _sentences(doc.get("text", ""))[:500]:
            hits = _keyword_hits(sent, kws)
            if not hits:
                continue
            if stype in {"local_data", "web", "search", "naver_news", "file_url"} and not any(x.lower() in sent.lower() for x in ids):
                continue
            if any(noise in sent for noise in FINANCE_NOISE):
                continue
            q = _sentence_quality(sent, hits, company, doc) + (2 if _source_matches_plan(doc, item) else 0)
            if q <= 0:
                continue
            candidates.append((q, doc, sent, hits))
    candidates.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    used_sources: set[str] = set()
    for _, doc, sent, hits in candidates:
        key = re.sub(r"\d+", "#", sent.lower())[:130]
        src_key = clean_text(doc.get("url") or doc.get("path") or doc.get("title"))[:180]
        if key in seen:
            continue
        # 같은 공식 홈페이지 첫 문장만 반복되는 문제 방지
        if src_key in used_sources and len(picked) >= 1:
            if not re.search(r"\d|특허|양산|고객|공급|매출|연구개발|수율", sent):
                continue
        seen.add(key)
        used_sources.add(src_key)
        picked.append({
            "snippet": sent[:420],
            "source_type": doc.get("source_type"),
            "source_title": doc.get("title"),
            "source_url": doc.get("url"),
            "source_path": doc.get("path"),
            "source_plan_matched": _source_matches_plan(doc, item),
            "hits": hits[:10],
        })
        if len(picked) >= limit:
            break
    return picked


def _numbers_from_text(text: str, max_n: int = 8) -> list[dict[str, str]]:
    nums: list[dict[str, str]] = []
    if any(noise in text for noise in FINANCE_NOISE):
        return nums
    for m in TECH_NUM_RE.finditer(text[:900]):
        val = clean_text(m.group("value"))
        unit = clean_text(m.group("unit"))
        if not unit and len(nums) > 0:
            continue
        context = _line_clean(text[max(0, m.start() - 45) : min(len(text), m.end() + 75)])
        if _is_noise_line(context):
            continue
        nums.append({"value": val, "unit": unit, "context": context})
        if len(nums) >= max_n:
            break
    return nums


def _unique_terms_found(text: str, candidates: list[str]) -> list[str]:
    low = clean_text(text).lower()
    out: list[str] = []
    for kw in candidates:
        kw = clean_text(kw)
        if len(kw) >= 2 and kw.lower() in low and kw not in out:
            out.append(kw)
    return out


def _frequency_counts(text: str, terms: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    low = clean_text(text).lower()
    for term in terms:
        term = clean_text(term)
        if len(term) < 2:
            continue
        cnt = len(re.findall(re.escape(term.lower()), low))
        if cnt > 0:
            out[term] = cnt
    return dict(sorted(out.items(), key=lambda x: x[1], reverse=True)[:15])


def _section_text(docs: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> str:
    chunks = [e.get("snippet", "") for e in evidence]
    if not chunks:
        chunks = []
        for d in docs[:10]:
            chunks.extend(_sentences(d.get("text", ""))[:8])
    return "\n".join(chunks)


def _metric(name: str, value: Any, unit: str, formula: str, detail: Any = None) -> dict[str, Any]:
    return {"metric_name": name, "value": value, "unit": unit, "formula": formula, "detail": detail if detail is not None else []}


def _quantify_item(company: dict[str, Any], docs: list[dict[str, Any]], section: dict[str, Any], item: dict[str, Any], evidence: list[dict[str, Any]], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _section_text(docs, evidence)
    all_doc_text = "\n".join(d.get("text", "")[:30000] for d in docs[:12])
    cat = clean_text(section.get("category"))
    item_name = clean_text(item.get("item_name"))
    company_kw = [clean_text(x) for x in _lst(company.get("core_keywords")) + _lst(company.get("tech_keywords")) + _lst(company.get("products")) if clean_text(x)] or SEMICONDUCTOR_TERMS
    metrics: list[dict[str, Any]] = []

    if cat == "대표 기술" and item_name == "핵심 기술 키워드":
        freq = _frequency_counts(all_doc_text, company_kw)
        metrics.append(_metric("기술 키워드 등장 빈도", sum(freq.values()), "회", "DART/IR/공식/특허/로컬 기술 원천에서 핵심 기술 키워드 출현 횟수 합산", freq))
        metrics.append(_metric("확인 핵심 기술 수", len(freq), "개", "등장 빈도 1회 이상인 핵심 기술 후보 고유 개수", list(freq.keys())))
    if cat == "대표 기술" and item_name in {"적용 방식", "핵심 성능 요소"}:
        apps = _unique_terms_found(text, PROCESS_PRODUCT_TERMS)
        nums = _numbers_from_text(text)
        metrics.append(_metric("적용 제품/공정 수", len(apps), "개", "근거 문장 내 적용 제품·공정·Application 고유 키워드 수", apps))
        if nums:
            metrics.append(_metric("성능/공정 정량 수치", len(nums), "건", "성능·수율·공정·양산 문맥에서 숫자가 포함된 문장 수", nums[:4]))

    if cat == "핵심 제품/서비스":
        products = _unique_terms_found(text, company_kw + PROCESS_PRODUCT_TERMS + ["제품", "서비스", "소재", "패키징"])
        metrics.append(_metric("제품/서비스 축 수", len(products), "개", "제품·서비스 후보 고유 키워드 수", products[:20]))
        revenue_nums = [n for n in _numbers_from_text(text, 12) if "%" in n.get("unit", "") or any(k in n.get("context", "") for k in ["매출", "비중", "성장", "증가", "억원", "백만원"])]
        if revenue_nums:
            metrics.append(_metric("매출/성장 정량 신호", len(revenue_nums), "건", "매출·비중·성장률 문맥 내 숫자 포함 문장 수", revenue_nums[:4]))

    if cat == "고객 구매 이유":
        benefits = _unique_terms_found(text, BENEFIT_TERMS)
        nums = _numbers_from_text(text, 8)
        metrics.append(_metric("고객 효익 키워드 수", len(benefits), "개", "성능·원가·품질·수율 등 고객 효익 표현 고유 개수", benefits))
        if nums:
            metrics.append(_metric("효익 관련 정량 수치", len(nums), "건", "성능·원가·수율·처리속도 문맥 숫자 포함 문장 수", nums[:4]))

    if cat in {"경쟁 우위/대체가능성", "진입 부담/장벽"}:
        barriers = _unique_terms_found(text, BARRIER_TERMS)
        patent_docs = [d for d in docs if clean_text(d.get("source_type")) == "patent"]
        nums = _numbers_from_text(text, 10)
        metrics.append(_metric("진입장벽/대체난이도 신호 수", len(barriers), "개", "특허·승인·양산·노하우·대체재 문맥 신호 수", barriers))
        if item_name == "등록 특허" or cat == "경쟁 우위/대체가능성":
            metrics.append(_metric("특허/산업재산권 근거 문서 수", len(patent_docs), "건", "source_type=patent로 분류된 로컬/KIPRIS/웹 근거 문서 수", [d.get("title") for d in patent_docs[:10]]))
        if nums:
            metrics.append(_metric("장벽 관련 정량 수치", len(nums), "건", "특허/승인/기간/수치 문맥 숫자 포함 문장 수", nums[:4]))

    if cat == "활용 및 확장 산업":
        industries = _unique_terms_found(text, INDUSTRY_TERMS)
        metrics.append(_metric("활용/확장 산업 수", len(industries), "개", "근거 문장 내 전방산업/Application 고유 개수", industries))

    if cat == "R&D 강도":
        rd_terms = _unique_terms_found(text, RD_TERMS)
        nums = _numbers_from_text(text, 10)
        metrics.append(_metric("R&D/투자 신호 수", len(rd_terms), "개", "연구개발·설비투자·과제·인력 문맥 신호 수", rd_terms))
        if nums:
            metrics.append(_metric("R&D 관련 정량 수치", len(nums), "건", "연구개발·투자 문맥 숫자 포함 문장 수", nums[:4]))

    # 엑셀 수식 시트는 '산식 적용 가능성'만 기록한다. 원문 문장을 metric value로 붙이지 않는다.
    formula_hits = extract_quantitative_signals(text, rules, max_signals=6)
    good_formula_hits = [h for h in formula_hits if not _is_noise_line(clean_text(h.get("snippet"))) and h.get("numbers")]
    if good_formula_hits:
        names = []
        for h in good_formula_hits[:4]:
            nm = clean_text(h.get("metric_name")) or "수식 지표"
            if nm not in names:
                names.append(nm)
        metrics.append(_metric("수식 시트 매칭 지표 수", len(names), "개", "tech_template.xlsx 수식/정량화 시트와 원문 수치 문맥의 매칭 개수", names))

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in metrics:
        key = clean_text(m.get("metric_name")) + "|" + clean_text(m.get("value"))[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    return unique[:5]


def _build_section_items(company: dict[str, Any], docs: list[dict[str, Any]], framework: dict[str, Any], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections_out: list[dict[str, Any]] = []
    rule_by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in rules:
        rule_by_cat.setdefault(clean_text(r.get("category")), []).append(r)
    for sec in framework.get("sections", []):
        section_items: list[dict[str, Any]] = []
        section_ev_count = 0
        section_quant_count = 0
        for item in sec.get("items", []):
            evidence = _pick_item_evidence(company, docs, sec, item, limit=3)
            metrics = _quantify_item(company, docs, sec, item, evidence, rule_by_cat.get(clean_text(sec.get("category")), []))
            section_ev_count += len(evidence)
            section_quant_count += len(metrics)
            section_items.append({
                "item_name": item.get("item_name"),
                "category": sec.get("category"),
                "axis": sec.get("axis"),
                "major_source_plan": item.get("major_source") or sec.get("major_source"),
                "middle_source_plan": item.get("middle_source") or sec.get("middle_source"),
                "quantifiable_plan": item.get("quantifiable") or sec.get("quantifiable"),
                "evidence": evidence,
                "quant_metrics": metrics,
            })
        sections_out.append({
            "category": sec.get("category"),
            "axis": sec.get("axis"),
            "major_source_plan": sec.get("major_source"),
            "middle_source_plan": sec.get("middle_source"),
            "quantifiable_plan": sec.get("quantifiable"),
            "items": section_items,
            "evidence_count": section_ev_count,
            "quant_metric_count": section_quant_count,
        })
    return sections_out


def harvest_all_tech_evidence(company: dict[str, Any], company_dir: str, template_path: str | Path = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    rules = load_formula_rules(template_path)
    framework = load_template_framework(template_path)
    docs, accepted_urls, rejected_urls = _collect_actual_docs(company, company_dir, framework)
    section_items = _build_section_items(company, docs, framework, rules)

    all_metrics: list[dict[str, Any]] = []
    for sec in section_items:
        for item in sec.get("items", []):
            for m in item.get("quant_metrics", []):
                x = dict(m)
                x.update({"category": sec.get("category"), "item_name": item.get("item_name")})
                all_metrics.append(x)

    flags: list[str] = []
    if not any(d.get("source_type") == "dart_filing" for d in docs):
        flags.append("DART 사업보고서 본문 미수집: DART_API_KEY 또는 stock_code 확인 필요")
    if not any(d.get("source_type") in {"official_homepage", "ir"} for d in docs):
        flags.append("공식 홈페이지/IR 본문 미수집: company.yaml URL 또는 네트워크 접근 확인 필요")
    if rejected_urls:
        flags.append(f"저관련 URL {len(rejected_urls)}건 제외")
    if len(all_metrics) < 10:
        flags.append("정량 신호가 적음: DART/IR/제품 페이지 또는 KIPRIS CSV 추가 수집 권장")

    return {
        "company_dir": company_dir,
        "company_name": clean_text(company.get("corp_name") or company.get("name") or company_dir),
        "harvest_version": "v11_excel_frame_actual_source_concise_quantification",
        "template_usage": "framework_only: base/formula sheet source plan, no company-example content copied as evidence",
        "formula_rule_count": len(rules),
        "document_count": len([d for d in docs if d.get("text")]),
        "accepted_url_count": len(accepted_urls),
        "rejected_url_count": len(rejected_urls),
        "docs": [d for d in docs if d.get("text")],
        "accepted_urls": accepted_urls,
        "rejected_urls": rejected_urls,
        "framework": framework,
        "section_items": section_items,
        "quantitative_signals": all_metrics[:200],
        "quality_flags": flags,
    }


def _metric_line(m: dict[str, Any]) -> str:
    name = clean_text(m.get("metric_name"))
    value = clean_text(m.get("value"))
    unit = clean_text(m.get("unit"))
    detail = m.get("detail")
    detail_text = ""
    if isinstance(detail, dict):
        detail_text = ", ".join([f"{k} {v}회" for k, v in list(detail.items())[:5]])
    elif isinstance(detail, list):
        vals = []
        for x in detail[:5]:
            if isinstance(x, dict):
                vals.append(clean_text(x.get("context") or x.get("value") or x.get("metric_name")))
            else:
                vals.append(clean_text(x))
        detail_text = ", ".join([v for v in vals if v])
    return f"{name}: {value}{unit}" + (f" [{detail_text}]" if detail_text else "")


def write_evidence_harvest(company_dir: str, harvest: dict[str, Any], output_dir: str | Path = OUTPUT_DIR) -> dict[str, str]:
    out = ensure_dir(Path(output_dir))
    jp = out / f"{company_dir}_tech_evidence_harvest.json"
    mp = out / f"{company_dir}_tech_evidence_harvest.md"
    jp.write_text(json.dumps(harvest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {harvest.get('company_name')} Tech Evidence Harvest v11",
        "",
        f"- 문서: {harvest.get('document_count')}",
        f"- 통과 URL: {harvest.get('accepted_url_count')}",
        f"- 제외 URL: {harvest.get('rejected_url_count')}",
        f"- 정량 신호: {len(harvest.get('quantitative_signals') or [])}",
        f"- 템플릿 사용: {harvest.get('template_usage')}",
        "",
        "## 품질 플래그",
    ]
    for flag in harvest.get("quality_flags") or []:
        lines.append(f"- {flag}")
    lines += ["", "## 엑셀 틀 기반 대분류/항목별 직접 추출 요약"]
    for sec in harvest.get("section_items") or []:
        lines += ["", f"### {sec.get('category')} ({sec.get('axis')})"]
        lines.append(f"- 대 출처 기준: {sec.get('major_source_plan')}")
        lines.append(f"- 중 출처 기준: {sec.get('middle_source_plan')}")
        lines.append(f"- 정량화 기준: {sec.get('quantifiable_plan')}")
        for item in sec.get("items") or []:
            q = item.get("quant_metrics") or []
            evs = item.get("evidence") or []
            lines += ["", f"#### {item.get('item_name')}"]
            lines.append("- 정량화: " + (" / ".join(_metric_line(m) for m in q[:3]) if q else "직접 확인 가능한 수치 부족"))
            for ev in evs[:1]:
                src = ev.get("source_url") or ev.get("source_path") or ev.get("source_title")
                lines.append(f"- 핵심 근거: {ev.get('snippet')}")
                lines.append(f"  - 출처: {ev.get('source_type')}: {src}")
    mp.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(jp), "md": str(mp)}

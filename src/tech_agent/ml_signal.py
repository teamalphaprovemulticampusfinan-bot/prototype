from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any

from common.output_paths import agent_output_dir, output_candidates, read_json_first, read_text_first

try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    SKLEARN_AVAILABLE = True
except Exception:
    KMeans = None
    TfidfVectorizer = None
    SKLEARN_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = field_agent_dir("tech")


COMPANY_ALIASES: dict[str, dict[str, Any]] = {
    "nepes": {
        "company": "네패스",
        "aliases": ["네패스", "주식회사 네패스", "(주)네패스", "NEPES", "Nepes"],
        "tech_keywords": ["WLP", "FOWLP", "PLP", "Bumping", "반도체 패키징", "후공정", "첨단 패키징"],
    },
    "hanmi": {
        "company": "한미반도체",
        "aliases": ["한미반도체", "주식회사 한미반도체", "(주)한미반도체", "HANMI", "Hanmi Semiconductor"],
        "tech_keywords": ["TC Bonder", "bonding", "반도체 장비", "후공정", "패키징", "HBM", "본더"],
    },
    "hansol": {
        "company": "한솔케미칼",
        "aliases": ["한솔케미칼", "주식회사 한솔케미칼", "(주)한솔케미칼", "HANSOL", "Hansol Chemical"],
        "tech_keywords": ["과산화수소", "전자재료", "프리커서", "반도체 소재", "디스플레이 소재", "이차전지 소재"],
    },
    "duksan": {
        "company": "덕산테코피아",
        "aliases": ["덕산테코피아", "주식회사 덕산테코피아", "(주)덕산테코피아", "DUKSAN TECHOPIA", "DS Techopia"],
        "tech_keywords": ["OLED", "전자재료", "반도체 소재", "전구체", "이차전지", "첨가제"],
    },
    "ltc": {
        "company": "LTC",
        "aliases": ["LTC", "엘티씨", "주식회사 엘티씨", "(주)엘티씨", "LTC Co., Ltd."],
        "tech_keywords": ["박리액", "세정액", "디스플레이 소재", "반도체 소재", "친환경", "전자재료"],
    },
}


REGISTERED_WORDS = [
    "등록",
    "Registered",
    "registration",
]

DEAD_WORDS = [
    "소멸",
    "취하",
    "포기",
    "거절",
    "무효",
    "만료",
    "취소",
    "abandoned",
    "rejected",
    "expired",
    "invalid",
]

COMMERCIAL_KEYWORDS = [
    "고객",
    "채택",
    "양산",
    "수주",
    "공급",
    "매출",
    "실적",
    "영업이익",
    "FCF",
    "현금흐름",
    "mass production",
    "customer",
    "revenue",
    "cash flow",
    "supply",
    "contract",
]

TECH_KEYWORDS_FALLBACK = [
    "반도체",
    "패키징",
    "소재",
    "공정",
    "장비",
    "전자재료",
    "디스플레이",
    "AI",
    "HBM",
    "WLP",
    "Bumping",
    "OLED",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last_error: Exception | None = None

    for enc in encodings:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                return [{k: clean_text(v) for k, v in row.items()} for row in reader]
        except Exception as exc:
            last_error = exc

    print(f"[Tech ML] CSV 읽기 실패: {path} / {last_error}")
    return []


def discover_patent_csv(company_dir: str, root: Path = ROOT) -> Path | None:
    source_dir = tech_source_dir(company_dir)
    candidates = [
        source_dir / f"kipris_{company_dir}_patents.csv",
        source_dir / f"{company_dir}_kipris_patents.csv",
        source_dir / "kipris_patents.csv",
    ]

    for path in candidates:
        if path.exists():
            return path

    csv_files = sorted(source_dir.glob("*patent*.csv"))
    if csv_files:
        return csv_files[0]

    csv_files = sorted(source_dir.glob("*kipris*.csv"))
    if csv_files:
        return csv_files[0]

    return None


def dedupe_patents(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for row in rows:
        app_no = first_value(row, ["application_number", "applicationNumber", "출원번호"])
        reg_no = first_value(row, ["register_number", "registerNumber", "등록번호"])
        title = first_value(row, ["invention_title", "inventionTitle", "발명의명칭", "title"])
        applicant = first_value(row, ["applicant_name", "applicantName", "출원인", "권리자"])

        key = (app_no, reg_no, title, applicant)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return deduped


def first_value(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key in row and clean_text(row.get(key)):
            return clean_text(row.get(key))
    return ""


def parse_year(value: str) -> int | None:
    text = clean_text(value)
    if not text:
        return None

    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None

    try:
        return int(match.group(0))
    except Exception:
        return None


def is_registered(row: dict[str, str]) -> bool:
    status = first_value(row, ["register_status", "registerStatus", "상태", "등록상태"])
    reg_no = first_value(row, ["register_number", "registerNumber", "등록번호"])
    text = f"{status} {reg_no}"

    if reg_no:
        return True

    return any(word.lower() in text.lower() for word in REGISTERED_WORDS)


def is_alive(row: dict[str, str]) -> bool:
    status = first_value(row, ["register_status", "registerStatus", "상태", "등록상태"])
    text = status.lower()

    if any(word.lower() in text for word in DEAD_WORDS):
        return False

    # 등록번호가 있으면 기본적으로 존속 가능 후보로 본다.
    return is_registered(row)


def patent_text(row: dict[str, str]) -> str:
    title = first_value(row, ["invention_title", "inventionTitle", "발명의명칭", "title"])
    abstract = first_value(row, ["abstract", "astrtCont", "초록", "요약"])
    ipc = first_value(row, ["ipc_number", "ipcNumber", "IPC", "ipc"])
    cpc = first_value(row, ["cpc_number", "cpcNumber", "CPC", "cpc"])
    applicant = first_value(row, ["applicant_name", "applicantName", "출원인", "권리자"])

    return clean_text(f"{title} {abstract} {ipc} {cpc} {applicant}")


def patent_title(row: dict[str, str]) -> str:
    return first_value(row, ["invention_title", "inventionTitle", "발명의명칭", "title"]) or "제목 미확인"


def patent_date(row: dict[str, str]) -> str:
    return (
        first_value(row, ["application_date", "applicationDate", "출원일"])
        or first_value(row, ["register_date", "registerDate", "등록일"])
        or first_value(row, ["open_date", "openDate", "공개일"])
    )


def extract_ipc_codes(row: dict[str, str]) -> list[str]:
    text = " ".join(
        [
            first_value(row, ["ipc_number", "ipcNumber", "IPC", "ipc"]),
            first_value(row, ["cpc_number", "cpcNumber", "CPC", "cpc"]),
        ]
    )

    if not text:
        return []

    # 예: H01L, C07D, G06F 등 대분류 중심으로 추출
    codes = re.findall(r"\b[A-HY]\d{2}[A-Z]\b", text.upper())
    if codes:
        return sorted(set(codes))

    rough = re.split(r"[,;/\s]+", text.upper())
    rough = [x.strip() for x in rough if re.match(r"^[A-HY]\d{2}", x.strip())]
    return sorted(set(rough))


def keyword_hits(texts: list[str], keywords: list[str]) -> dict[str, int]:
    counter: dict[str, int] = {}
    joined = "\n".join(texts).lower()

    for keyword in keywords:
        keyword_clean = clean_text(keyword)
        if not keyword_clean:
            continue
        counter[keyword_clean] = joined.count(keyword_clean.lower())

    return {k: v for k, v in counter.items() if v > 0}


def calculate_hhi(counts: list[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    return sum((count / total) ** 2 for count in counts)


def choose_cluster_count(n_samples: int) -> int:
    if n_samples < 5:
        return 1
    if n_samples < 20:
        return 2
    if n_samples < 50:
        return 3
    if n_samples < 100:
        return 4
    return min(8, max(4, int(math.sqrt(n_samples))))


def fallback_keyword_clusters(texts: list[str], keywords: list[str]) -> dict[str, Any]:
    effective_keywords = keywords or TECH_KEYWORDS_FALLBACK
    clusters: list[dict[str, Any]] = []

    for keyword in effective_keywords:
        matched = [text for text in texts if keyword.lower() in text.lower()]
        if matched:
            clusters.append(
                {
                    "cluster_id": len(clusters),
                    "size": len(matched),
                    "top_terms": [keyword],
                    "sample_titles": [],
                }
            )

    if not clusters:
        clusters.append(
            {
                "cluster_id": 0,
                "size": len(texts),
                "top_terms": ["기술 키워드 미확인"],
                "sample_titles": [],
            }
        )

    sizes = [int(c["size"]) for c in clusters]
    return {
        "method": "keyword_fallback",
        "sklearn_available": False,
        "cluster_count": len(clusters),
        "clusters": clusters,
        "technology_concentration_index": round(calculate_hhi(sizes), 4),
        "feature_count": 0,
    }


def run_tfidf_kmeans(rows: list[dict[str, str]], texts: list[str], keywords: list[str]) -> dict[str, Any]:
    if not SKLEARN_AVAILABLE or len(texts) < 5:
        return fallback_keyword_clusters(texts, keywords)

    n_clusters = choose_cluster_count(len(texts))

    if n_clusters <= 1:
        return fallback_keyword_clusters(texts, keywords)

    vectorizer = TfidfVectorizer(
        max_features=1500,
        ngram_range=(1, 2),
        min_df=1,
        token_pattern=r"(?u)\b[\w가-힣][\w가-힣\-\+/\.]{1,}\b",
    )

    try:
        matrix = vectorizer.fit_transform(texts)
    except Exception:
        return fallback_keyword_clusters(texts, keywords)

    if matrix.shape[0] < n_clusters or matrix.shape[1] == 0:
        return fallback_keyword_clusters(texts, keywords)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(matrix)

    terms = vectorizer.get_feature_names_out()
    clusters: list[dict[str, Any]] = []

    for cluster_id in range(n_clusters):
        indices = [idx for idx, label in enumerate(labels) if int(label) == cluster_id]
        center = model.cluster_centers_[cluster_id]
        top_indices = center.argsort()[::-1][:8]
        top_terms = [str(terms[i]) for i in top_indices if center[i] > 0]

        sample_titles = []
        for idx in indices[:5]:
            sample_titles.append(patent_title(rows[idx]))

        clusters.append(
            {
                "cluster_id": int(cluster_id),
                "size": len(indices),
                "top_terms": top_terms,
                "sample_titles": sample_titles,
            }
        )

    clusters.sort(key=lambda x: x["size"], reverse=True)
    sizes = [int(c["size"]) for c in clusters]

    return {
        "method": "tfidf_kmeans",
        "sklearn_available": True,
        "cluster_count": n_clusters,
        "clusters": clusters,
        "technology_concentration_index": round(calculate_hhi(sizes), 4),
        "feature_count": int(matrix.shape[1]),
    }


def load_bridge_data(company_dir: str, root: Path = ROOT) -> dict[str, Any]:
    candidates = [company_agent_dir(company_dir, "tech") / "tech.json"]
    candidates.extend(output_candidates(company_dir, "tech", f"{company_dir}_tech_to_value_bridge.json", root=root))
    candidates.extend(output_candidates(company_dir, "tech", f"{company_dir}_tech_bridge.json", root=root))
    data = read_json_first(candidates)
    return data if isinstance(data, dict) else {}


def load_report_text(company_dir: str, root: Path = ROOT) -> str:
    candidates: list[Path] = []
    for filename in [
        f"{company_dir}_tech_high_quality_report.md",
        f"{company_dir}_tech_report.md",
        f"{company_dir}_tech_patent_evidence.md",
    ]:
        candidates.extend(output_candidates(company_dir, "tech", filename, root=root))

    parts: list[str] = []
    for path in candidates:
        text = read_text_first([path])
        if text:
            parts.append(text)

    return "\n".join(parts)


def extract_bridge_score(bridge: dict[str, Any]) -> float:
    possible_keys = [
        "tech_to_value_bridge_score",
        "bridge_score",
        "score",
        "Tech-to-Value Bridge Score",
    ]

    for key in possible_keys:
        if key in bridge:
            return safe_float(bridge.get(key))

    # packet 안쪽 구조 대응
    for key in ["tech_to_value_bridge", "bridge", "tech_bridge"]:
        nested = bridge.get(key)
        if isinstance(nested, dict):
            nested_score = extract_bridge_score(nested)
            if nested_score:
                return nested_score

    return 0.0


def extract_bridge_label(bridge: dict[str, Any]) -> str:
    possible_keys = [
        "label",
        "verdict",
        "grade",
        "judgement",
        "judgment",
        "판정",
    ]

    for key in possible_keys:
        value = clean_text(bridge.get(key))
        if value:
            return value

    for key in ["tech_to_value_bridge", "bridge", "tech_bridge"]:
        nested = bridge.get(key)
        if isinstance(nested, dict):
            nested_label = extract_bridge_label(nested)
            if nested_label:
                return nested_label

    return ""


def commercialization_score(report_text: str, bridge: dict[str, Any]) -> dict[str, Any]:
    text = report_text.lower()
    keyword_counts = {}
    total_hits = 0

    for keyword in COMMERCIAL_KEYWORDS:
        count = text.count(keyword.lower())
        if count > 0:
            keyword_counts[keyword] = count
            total_hits += count

    # bridge 안에 사업화 관련 evidence count가 있으면 보조 반영
    bridge_text = json.dumps(bridge, ensure_ascii=False).lower()
    bridge_hits = 0
    for keyword in COMMERCIAL_KEYWORDS:
        bridge_hits += bridge_text.count(keyword.lower())

    total_hits += bridge_hits

    if total_hits >= 20:
        score = 80.0
        level = "STRONG"
    elif total_hits >= 8:
        score = 60.0
        level = "MODERATE"
    elif total_hits >= 3:
        score = 40.0
        level = "WEAK"
    else:
        score = 20.0
        level = "INSUFFICIENT"

    return {
        "commercialization_score": score,
        "commercialization_level": level,
        "commercialization_keyword_hits": total_hits,
        "commercialization_keywords": keyword_counts,
    }


def calculate_patent_ml_score(
    total: int,
    registered: int,
    alive: int,
    recent: int,
    ipc_count: int,
    cluster_count: int,
    keyword_hit_total: int,
) -> float:
    if total <= 0:
        return 0.0

    count_score = min(total / 300.0, 1.0) * 20.0
    recent_score = min((recent / total) / 0.30, 1.0) * 20.0
    registered_score = min((registered / total) / 0.70, 1.0) * 15.0
    alive_score = min((alive / total) / 0.60, 1.0) * 15.0
    ipc_score = min(ipc_count / 80.0, 1.0) * 10.0
    cluster_score = min(cluster_count / 8.0, 1.0) * 10.0
    keyword_score = min(keyword_hit_total / 100.0, 1.0) * 10.0

    return round(
        count_score
        + recent_score
        + registered_score
        + alive_score
        + ipc_score
        + cluster_score
        + keyword_score,
        2,
    )


def determine_ml_label(
    patent_ml_score: float,
    commerce_score: float,
    bridge_score: float,
    bridge_label: str,
) -> tuple[str, str]:
    label_upper = bridge_label.upper()

    # 기존 Tech-to-Value Bridge 판정이 있으면 존중하되, ML 근거로 설명을 보강한다.
    if "TECH_FINANCE_GAP" in label_upper:
        return (
            "TECH_FINANCE_GAP",
            "특허·기술 신호는 존재하지만 매출·FCF 등 재무 전환 근거가 약해 기술-재무 괴리형으로 해석합니다.",
        )

    if "COMMERCIALIZATION_WATCH" in label_upper:
        return (
            "COMMERCIALIZATION_WATCH",
            "기술성과 특허 포트폴리오는 확인되지만 고객 채택·양산·매출 전환은 계속 추적해야 하는 사업화 추적형입니다.",
        )

    if patent_ml_score >= 75 and commerce_score >= 60 and bridge_score >= 70:
        return (
            "VALUE_CONVERSION_CONFIRMED",
            "기술 포트폴리오와 사업화 연결 신호가 함께 확인되어 가치 전환 확인형으로 해석합니다.",
        )

    if patent_ml_score >= 65 and commerce_score < 40:
        return (
            "TECH_FINANCE_GAP",
            "특허·기술 축은 강하지만 매출·현금흐름 전환 근거가 부족하여 기술-재무 괴리형으로 해석합니다.",
        )

    if patent_ml_score >= 50:
        return (
            "COMMERCIALIZATION_WATCH",
            "기술 포트폴리오는 확인되지만 사업화 연결 근거는 추가 확인이 필요한 사업화 추적형입니다.",
        )

    return (
        "TECH_EVIDENCE_WEAK",
        "특허·기술 정량 신호가 충분하지 않아 근거 보강 필요형으로 해석합니다.",
    )


def representative_patents(rows: list[dict[str, str]], limit: int = 5) -> list[dict[str, str]]:
    def sort_key(row: dict[str, str]) -> tuple[int, int]:
        year = parse_year(patent_date(row)) or 0
        reg = 1 if is_registered(row) else 0
        return (reg, year)

    selected = sorted(rows, key=sort_key, reverse=True)[:limit]
    reps = []

    for row in selected:
        reps.append(
            {
                "title": patent_title(row),
                "application_date": first_value(row, ["application_date", "applicationDate", "출원일"]),
                "register_date": first_value(row, ["register_date", "registerDate", "등록일"]),
                "register_status": first_value(row, ["register_status", "registerStatus", "상태", "등록상태"]),
                "ipc": first_value(row, ["ipc_number", "ipcNumber", "IPC", "ipc"]),
                "applicant": first_value(row, ["applicant_name", "applicantName", "출원인", "권리자"]),
            }
        )

    return reps


def build_markdown(signal: dict[str, Any]) -> str:
    company = signal.get("company", "")
    label = signal.get("tech_ml_label", "")
    label_desc = signal.get("tech_ml_label_description", "")

    lines: list[str] = []
    lines.append(f"# {company} Tech ML Signal Report")
    lines.append("")
    lines.append("## 1. Tech ML 요약")
    lines.append(f"- ML 판정: **{label}**")
    lines.append(f"- 판정 설명: {label_desc}")
    lines.append(f"- Patent ML Score: **{signal.get('patent_ml_score', 0)} / 100**")
    lines.append(f"- Commercialization Score: **{signal.get('commercialization_score', 0)} / 100**")
    lines.append(f"- 기존 Tech-to-Value Bridge Score: **{signal.get('bridge_score', 0)} / 100**")
    lines.append(f"- 기존 Bridge 판정: **{signal.get('bridge_label') or '미확인'}**")
    lines.append("")

    lines.append("## 2. KIPRIS/IP 정량 신호")
    lines.append(f"- 정규화 특허 레코드: **{signal.get('normalized_patent_records', 0)}건**")
    lines.append(f"- 회사 출원인/권리자 매칭: **{signal.get('company_matched_patents', 0)}건**")
    lines.append(f"- 등록 특허: **{signal.get('registered_patents', 0)}건**")
    lines.append(f"- 존속 가능 특허: **{signal.get('alive_patents', 0)}건**")
    lines.append(f"- 최근 5년 특허: **{signal.get('recent_5y_patents', 0)}건**")
    lines.append(f"- IPC/CPC 기술분류 수: **{signal.get('ipc_cpc_count', 0)}개**")
    lines.append(f"- H01L 반도체 핵심 IPC 특허: **{signal.get('h01l_patents', 0)}건**")
    lines.append("")

    lines.append("## 3. 특허 클러스터링")
    clustering = signal.get("clustering", {})
    lines.append(f"- 사용 방식: **{clustering.get('method', 'unknown')}**")
    lines.append(f"- 클러스터 수: **{clustering.get('cluster_count', 0)}개**")
    lines.append(f"- 기술 집중도 HHI: **{clustering.get('technology_concentration_index', 0)}**")
    lines.append(f"- TF-IDF 피처 수: **{clustering.get('feature_count', 0)}개**")
    lines.append("")

    lines.append("| 클러스터 | 규모 | 핵심 용어 | 대표 특허 예시 |")
    lines.append("|---:|---:|---|---|")
    for cluster in clustering.get("clusters", [])[:8]:
        terms = ", ".join(cluster.get("top_terms", [])[:6])
        samples = "<br>".join(cluster.get("sample_titles", [])[:3])
        lines.append(f"| {cluster.get('cluster_id')} | {cluster.get('size')} | {terms} | {samples} |")
    lines.append("")

    lines.append("## 4. 대표 특허 예시")
    reps = signal.get("representative_patents", [])
    if not reps:
        lines.append("- 대표 특허를 확인하지 못했습니다.")
    else:
        for idx, patent in enumerate(reps, start=1):
            title = patent.get("title", "제목 미확인")
            app_date = patent.get("application_date", "")
            reg_date = patent.get("register_date", "")
            status = patent.get("register_status", "")
            ipc = patent.get("ipc", "")
            lines.append(f"{idx}. **{title}**")
            lines.append(f"   - 출원일: {app_date or '미확인'} / 등록일: {reg_date or '미확인'} / 상태: {status or '미확인'}")
            lines.append(f"   - IPC/CPC: {ipc or '미확인'}")
    lines.append("")

    lines.append("## 5. Chair 반영 포인트")
    for point in signal.get("chair_reflection_points", []):
        lines.append(f"- {point}")
    lines.append("")

    lines.append("## 6. 비고")
    for note in signal.get("notes", []):
        lines.append(f"- {note}")

    return "\n".join(lines).strip() + "\n"


def build_tech_ml_signal(
    company_dir: str,
    company: str | None = None,
    root: Path = ROOT,
    save: bool = True,
) -> dict[str, Any]:
    company_dir = company_dir.strip()
    meta = COMPANY_ALIASES.get(company_dir, {})
    company_name = company or meta.get("company") or company_dir
    aliases = meta.get("aliases", [company_name])
    tech_keywords = meta.get("tech_keywords", TECH_KEYWORDS_FALLBACK)

    patent_csv = discover_patent_csv(company_dir, root=root)
    rows_raw = read_csv_rows(patent_csv) if patent_csv else []
    rows = dedupe_patents(rows_raw)

    texts = [patent_text(row) for row in rows]
    texts = [text for text in texts if text]

    now_year = datetime.now().year
    cutoff_year = now_year - 5

    total = len(rows)
    registered = sum(1 for row in rows if is_registered(row))
    alive = sum(1 for row in rows if is_alive(row))

    recent = 0
    years: list[int] = []
    for row in rows:
        year = parse_year(patent_date(row))
        if year:
            years.append(year)
            if year >= cutoff_year:
                recent += 1

    ipc_codes: list[str] = []
    h01l_patents = 0
    for row in rows:
        codes = extract_ipc_codes(row)
        ipc_codes.extend(codes)
        if any(code.startswith("H01L") for code in codes):
            h01l_patents += 1

    ipc_unique = sorted(set(ipc_codes))

    matched = 0
    lower_aliases = [alias.lower() for alias in aliases]
    for row in rows:
        applicant = first_value(row, ["applicant_name", "applicantName", "출원인", "권리자"]).lower()
        if any(alias in applicant for alias in lower_aliases):
            matched += 1

    # applicant_name이 비어있는 CSV도 있으므로, 매칭값이 0이면 전체 rows를 회사 관련 수집 결과로 간주한다.
    company_matched = matched if matched > 0 else total

    keyword_counter = keyword_hits(texts, tech_keywords)
    keyword_total = sum(keyword_counter.values())

    clustering = run_tfidf_kmeans(rows, texts, tech_keywords)

    bridge = load_bridge_data(company_dir, root=root)
    bridge_score = extract_bridge_score(bridge)
    bridge_label = extract_bridge_label(bridge)

    report_text = load_report_text(company_dir, root=root)
    commerce = commercialization_score(report_text, bridge)

    patent_ml_score = calculate_patent_ml_score(
        total=total,
        registered=registered,
        alive=alive,
        recent=recent,
        ipc_count=len(ipc_unique),
        cluster_count=int(clustering.get("cluster_count", 0)),
        keyword_hit_total=keyword_total,
    )

    tech_ml_label, label_desc = determine_ml_label(
        patent_ml_score=patent_ml_score,
        commerce_score=safe_float(commerce.get("commercialization_score")),
        bridge_score=bridge_score,
        bridge_label=bridge_label,
    )

    if total == 0:
        notes = [
            "KIPRIS 특허 CSV에서 유효한 특허 레코드를 확인하지 못했습니다.",
            "기업별 KIPRIS applicant 검색 파일을 먼저 실행한 뒤 다시 실행해야 합니다.",
            "자료 부족 상태에서는 Tech ML 신호를 Chair의 강한 판단 근거로 사용하지 않습니다.",
        ]
    else:
        notes = [
            "Tech ML은 특허 텍스트, 초록, IPC/CPC, 등록상태, 최근 출원 흐름을 기반으로 기술 포트폴리오를 구조화합니다.",
            "특허 수와 클러스터 수는 기술 지속성의 보조 근거이며, 단독으로 매출 성장이나 주가 상승을 의미하지 않습니다.",
            "사업화 판단은 고객 채택, 양산, 매출 전환, FCF 개선 근거와 함께 해석해야 합니다.",
        ]

    chair_points = [
        f"Tech ML 판정은 {tech_ml_label}이며, 기존 Tech-to-Value Bridge 판정과 함께 기술 섹션의 보조 신호로 사용합니다.",
        "특허 클러스터링 결과는 핵심 기술 축과 기술 포트폴리오 집중도를 설명하는 근거로 반영합니다.",
        "최근 5년 특허와 등록·존속 가능 특허는 기술 지속성 및 진입장벽의 보조 지표로 활용합니다.",
        "고객 채택, 양산, 매출 전환, FCF 개선 근거가 약하면 기술 점수만으로 매수 의견을 강화하지 않습니다.",
    ]

    if tech_ml_label == "TECH_FINANCE_GAP":
        chair_points.append("기술 신호가 존재하더라도 재무·현금흐름 전환 근거가 약하면 Chair는 보수적으로 반영해야 합니다.")
    elif tech_ml_label == "COMMERCIALIZATION_WATCH":
        chair_points.append("기술성은 확인되지만 사업화 연결 근거를 계속 확인해야 하므로 Chair는 관찰형 보조 신호로 반영해야 합니다.")
    elif tech_ml_label == "VALUE_CONVERSION_CONFIRMED":
        chair_points.append("기술성과 사업화 연결 신호가 함께 확인된 경우에만 가치평가 가산 요인으로 반영할 수 있습니다.")

    year_range = ""
    if years:
        year_range = f"{min(years)}~{max(years)}"

    signal: dict[str, Any] = {
        "company_dir": company_dir,
        "company": company_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_patent_csv": str(patent_csv) if patent_csv else "",
        "model_info": {
            "module": "Tech ML Signal Builder",
            "algorithm": "TF-IDF + KMeans" if SKLEARN_AVAILABLE else "keyword fallback",
            "sklearn_available": SKLEARN_AVAILABLE,
            "purpose": "KIPRIS patent portfolio clustering, patent momentum scoring, commercialization watch signal generation",
        },
        "tech_ml_label": tech_ml_label,
        "tech_ml_label_description": label_desc,
        "patent_ml_score": patent_ml_score,
        "bridge_score": bridge_score,
        "bridge_label": bridge_label,
        "normalized_patent_records": total,
        "company_matched_patents": company_matched,
        "registered_patents": registered,
        "alive_patents": alive,
        "recent_5y_patents": recent,
        "recent_5y_ratio": round(recent / total, 4) if total else 0.0,
        "ipc_cpc_count": len(ipc_unique),
        "ipc_cpc_examples": ipc_unique[:20],
        "h01l_patents": h01l_patents,
        "patent_year_range": year_range,
        "technology_keyword_hits": keyword_counter,
        "technology_keyword_hit_total": keyword_total,
        "clustering": clustering,
        "representative_patents": representative_patents(rows, limit=5),
        "commercialization_score": commerce.get("commercialization_score"),
        "commercialization_level": commerce.get("commercialization_level"),
        "commercialization_keyword_hits": commerce.get("commercialization_keyword_hits"),
        "commercialization_keywords": commerce.get("commercialization_keywords"),
        "chair_reflection_points": chair_points,
        "notes": notes,
    }

    if save:
        output_dir = agent_output_dir(company_dir, "tech", root=root)
        packet_dir = company_agent_dir(company_dir, "tech")

        json_path = output_dir / f"{company_dir}_tech_ml_signal.json"
        md_path = output_dir / f"{company_dir}_tech_ml_signal.md"
        packet_path = packet_dir / "tech_ml_signal.json"

        write_json(json_path, signal)
        write_text(md_path, build_markdown(signal))
        write_json(packet_path, signal)

        print(f"[Tech ML] 저장 완료: {json_path}")
        print(f"[Tech ML] 저장 완료: {md_path}")
        print(f"[Tech ML] 저장 완료: {packet_path}")

    return signal


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Tech ML signal from KIPRIS patent CSV.")
    parser.add_argument("--company-dir", required=True, help="company slug, e.g. nepes")
    parser.add_argument("--company", default="", help="display company name")
    args = parser.parse_args()

    build_tech_ml_signal(company_dir=args.company_dir, company=args.company or None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
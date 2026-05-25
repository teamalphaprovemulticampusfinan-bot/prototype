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

from common.output_paths import output_candidates, read_json_first, read_text_first, shared_output_dir

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    SKLEARN_AVAILABLE = True
except Exception:
    TfidfVectorizer = None
    cosine_similarity = None
    SKLEARN_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = shared_output_dir("tech", root=ROOT)

TECH_STOPWORDS = {
    "상기", "관한", "관련", "포함", "포함하는", "구비", "구비하는", "이용", "이용한", "이를", "통해",
    "발명", "발명은", "것이다", "제공", "제공하는", "형성", "형성하는", "방법", "장치", "시스템",
    "주식회사", "소자", "기판", "모듈", "부재", "구성", "처리", "제어", "사용", "가능", "기술",
    "및", "또는", "하는", "대한", "후보", "기반", "기업", "선택", "분석", "확인", "제조",
    "the", "and", "for", "with", "from", "this", "that", "method", "device", "system", "using", "company", "selected",
    "reference", "peer", "value", "true", "false", "apparatus", "including", "include", "provided", "thereof", "comprising",
}


def is_noise_term(term: Any) -> bool:
    text = re.sub(r"\s+", " ", str(term or "")).strip().lower()
    if not text or len(text) <= 1:
        return True
    if text in {x.lower() for x in TECH_STOPWORDS}:
        return True
    if re.fullmatch(r"[0-9\.\-_/]+", text):
        return True
    return False


def clean_top_terms(values: list[Any], limit: int = 12) -> list[Any]:
    out = []
    for item in values:
        term = item.get("term") if isinstance(item, dict) else str(item)
        if is_noise_term(term):
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


DEFAULT_COMPANIES: dict[str, str] = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "LTC",
}

CSV_TEXT_KEYS = [
    "invention_title",
    "inventionTitle",
    "title",
    "발명의명칭",
    "abstract",
    "astrtCont",
    "초록",
    "요약",
    "ipc_number",
    "ipcNumber",
    "IPC",
    "ipc",
    "cpc_number",
    "cpcNumber",
    "CPC",
    "cpc",
    "applicant_name",
    "applicantName",
    "출원인",
    "권리자",
]

CSV_KEY_KEYS = [
    "application_number",
    "applicationNumber",
    "출원번호",
    "register_number",
    "registerNumber",
    "등록번호",
    "invention_title",
    "inventionTitle",
    "발명의명칭",
    "title",
]

DOMAIN_HINTS: list[tuple[str, list[str]]] = [
    ("반도체 후공정/패키징", ["wlp", "fowlp", "plp", "bumping", "package", "packaging", "패키징", "후공정", "재배선", "rdl", "bump"]),
    ("반도체 장비/본딩", ["bonder", "bonding", "본더", "본딩", "vision", "placement", "장비", "hbm", "die", "attach"]),
    ("반도체·디스플레이 소재", ["소재", "전자재료", "precursor", "전구체", "과산화수소", "etch", "식각", "cleaner", "세정", "박리", "oled"]),
    ("이차전지/배터리 소재", ["battery", "배터리", "전지", "전해액", "양극", "음극", "첨가제", "lithium", "리튬"]),
    ("검사/테스트·공정 모니터링", ["test", "testing", "검사", "테스트", "monitor", "모니터링", "측정", "inspection", "sensor"]),
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    for enc in ["utf-8", "utf-8-sig", "cp949"]:
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    for enc in ["utf-8", "utf-8-sig", "cp949", "euc-kr"]:
        try:
            return path.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    return ""


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                return [{str(k): clean_text(v) for k, v in row.items()} for row in reader]
        except Exception:
            continue
    return []


def first_value(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = clean_text(row.get(key))
        if value:
            return value
    return ""


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

    for pattern in ["*patent*.csv", "*kipris*.csv", "*.csv"]:
        found = sorted(source_dir.glob(pattern))
        if found:
            return found[0]
    return None


def row_key(row: dict[str, str]) -> tuple[str, ...]:
    values = [first_value(row, [key]) for key in CSV_KEY_KEYS]
    return tuple(values)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = row_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def patent_row_text(row: dict[str, str]) -> str:
    parts = []
    for key in CSV_TEXT_KEYS:
        value = clean_text(row.get(key))
        if value:
            parts.append(value)
    return " ".join(parts)


def build_company_document_from_csv(company_dir: str, root: Path = ROOT) -> tuple[str, dict[str, Any]]:
    csv_path = discover_patent_csv(company_dir, root=root)
    rows = dedupe_rows(read_csv_rows(csv_path)) if csv_path else []
    row_texts = [patent_row_text(row) for row in rows]
    row_texts = [text for text in row_texts if text]
    document = "\n".join(row_texts)
    meta = {
        "input_patent_csv": str(csv_path) if csv_path else "",
        "patent_rows": len(rows),
        "text_rows": len(row_texts),
        "source_type": "kipris_csv" if row_texts else "fallback",
    }
    return document, meta


def build_company_document_fallback(company_dir: str, root: Path = ROOT) -> tuple[str, dict[str, Any]]:
    pieces: list[str] = []

    signal = read_json_first(output_candidates(company_dir, "tech", f"{company_dir}_tech_ml_signal.json", root=root))
    if signal:
        for cluster in signal.get("clustering", {}).get("clusters", []) or []:
            if isinstance(cluster, dict):
                pieces.extend(clean_text(x) for x in cluster.get("top_terms", []) or [])
                pieces.extend(clean_text(x) for x in cluster.get("sample_titles", []) or [])
        for patent in signal.get("representative_patents", []) or []:
            if isinstance(patent, dict):
                pieces.append(clean_text(patent.get("title")))
                pieces.append(clean_text(patent.get("ipc")))
        pieces.append(json.dumps(signal.get("technology_keyword_hits", {}), ensure_ascii=False))

    for filename in [
        f"{company_dir}_tech_high_quality_report.md",
        f"{company_dir}_tech_patent_evidence.md",
        f"{company_dir}_tech_to_value_bridge.md",
    ]:
        text = read_text_first(output_candidates(company_dir, "tech", filename, root=root))
        if text:
            pieces.append(text[:20000])

    document = "\n".join(p for p in pieces if p)
    meta = {
        "input_patent_csv": "",
        "patent_rows": 0,
        "text_rows": len(pieces),
        "source_type": "tech_outputs_fallback" if document else "missing",
    }
    return document, meta


def build_company_documents(companies: dict[str, str], root: Path = ROOT) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    company_dirs: list[str] = []
    documents: list[str] = []
    metadata: dict[str, dict[str, Any]] = {}

    for company_dir, company_name in companies.items():
        document, meta = build_company_document_from_csv(company_dir, root=root)
        if not document.strip():
            document, fallback_meta = build_company_document_fallback(company_dir, root=root)
            meta.update(fallback_meta)
        meta["company_dir"] = company_dir
        meta["company"] = company_name
        meta["document_chars"] = len(document)
        company_dirs.append(company_dir)
        documents.append(document)
        metadata[company_dir] = meta

    return company_dirs, documents, metadata


def tokenize_simple(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z0-9가-힣][a-zA-Z0-9가-힣\-\+/\.]{1,}", text)
    return [tok for tok in tokens if not is_noise_term(tok)]


def fallback_vectorize(documents: list[str]) -> tuple[list[list[float]], list[str], list[list[tuple[str, float]]]]:
    counters = [Counter(tokenize_simple(doc)) for doc in documents]
    vocab = sorted({term for c in counters for term, count in c.items() if count > 0})
    if not vocab:
        return [[0.0] for _ in documents], ["empty"], [[] for _ in documents]
    index = {term: i for i, term in enumerate(vocab)}
    vectors: list[list[float]] = []
    top_terms: list[list[tuple[str, float]]] = []
    n_docs = len(documents)
    df = Counter()
    for c in counters:
        for term in c:
            df[term] += 1
    idf = {term: math.log((1 + n_docs) / (1 + df[term])) + 1 for term in vocab}
    for c in counters:
        vec = [0.0] * len(vocab)
        for term, count in c.items():
            if term in index:
                vec[index[term]] = float(count) * idf[term]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        vec = [x / norm for x in vec]
        vectors.append(vec)
        ranked = sorted(((term, vec[index[term]]) for term in c if term in index), key=lambda x: x[1], reverse=True)[:12]
        top_terms.append(ranked)
    return vectors, vocab, top_terms


def cosine_dense(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def infer_domain(top_terms: list[str], document: str) -> str:
    haystack = " ".join(top_terms).lower() + " " + document[:5000].lower()
    scores: list[tuple[int, str]] = []
    for label, hints in DOMAIN_HINTS:
        score = sum(haystack.count(h.lower()) for h in hints)
        scores.append((score, label))
    scores.sort(reverse=True)
    if scores and scores[0][0] > 0:
        return scores[0][1]
    return "기술군 자동판정 제한"


def build_similarity(companies: dict[str, str], root: Path = ROOT, save: bool = True) -> dict[str, Any]:
    company_dirs, documents, metadata = build_company_documents(companies, root=root)
    usable_count = sum(1 for doc in documents if doc.strip())

    if usable_count < 2:
        result = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "method": "insufficient_data",
            "companies": [{"company_dir": cd, "company": companies[cd], **metadata[cd]} for cd in company_dirs],
            "similarity_matrix": [],
            "nearest_peers": [],
            "notes": ["회사 단위 유사도 계산에 필요한 특허/기술 텍스트가 2개 기업 이상에서 확인되지 않았습니다."],
        }
        if save:
            write_json(OUT_DIR / "tech_peer_similarity.json", result)
            write_text(OUT_DIR / "tech_peer_similarity.md", build_markdown(result))
        return result

    top_terms_by_company: dict[str, list[dict[str, Any]]] = {}

    if SKLEARN_AVAILABLE:
        vectorizer = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            min_df=1,
            token_pattern=r"(?u)\b[\w가-힣][\w가-힣\-\+/\.]{1,}\b",
            stop_words=list(TECH_STOPWORDS),
            max_df=0.90,
        )
        matrix = vectorizer.fit_transform(documents)
        sim_matrix = cosine_similarity(matrix)
        terms = vectorizer.get_feature_names_out()
        for row_idx, company_dir in enumerate(company_dirs):
            row = matrix.getrow(row_idx).toarray()[0]
            ranked_idx = row.argsort()[::-1][:15]
            top_terms_by_company[company_dir] = clean_top_terms([
                {"term": str(terms[i]), "weight": round(float(row[i]), 4)}
                for i in ranked_idx
                if row[i] > 0
            ], limit=15)
        method = "TF-IDF + Cosine Similarity"
        feature_count = int(matrix.shape[1])
    else:
        vectors, vocab, simple_top_terms = fallback_vectorize(documents)
        sim_matrix = [[cosine_dense(v1, v2) for v2 in vectors] for v1 in vectors]
        for company_dir, tops in zip(company_dirs, simple_top_terms):
            top_terms_by_company[company_dir] = clean_top_terms([
                {"term": term, "weight": round(float(weight), 4)} for term, weight in tops
            ], limit=15)
        method = "Simple TF-IDF fallback + Cosine Similarity"
        feature_count = len(vocab)

    matrix_rows: list[dict[str, Any]] = []
    for i, row_company in enumerate(company_dirs):
        row: dict[str, Any] = {"company_dir": row_company, "company": companies[row_company]}
        for j, col_company in enumerate(company_dirs):
            row[col_company] = round(float(sim_matrix[i][j]), 4)
        matrix_rows.append(row)

    nearest: list[dict[str, Any]] = []
    for i, company_dir in enumerate(company_dirs):
        candidates = []
        for j, peer_dir in enumerate(company_dirs):
            if i == j:
                continue
            candidates.append((float(sim_matrix[i][j]), peer_dir))
        candidates.sort(reverse=True)
        best_score, best_peer = candidates[0] if candidates else (0.0, "")
        top_terms = [x["term"] for x in top_terms_by_company.get(company_dir, [])[:8]]
        peer_terms = [x["term"] for x in top_terms_by_company.get(best_peer, [])[:8]] if best_peer else []
        shared_terms = sorted(set(t.lower() for t in top_terms) & set(t.lower() for t in peer_terms))[:8]
        nearest.append(
            {
                "company_dir": company_dir,
                "company": companies[company_dir],
                "nearest_peer_dir": best_peer,
                "nearest_peer": companies.get(best_peer, best_peer),
                "similarity": round(best_score, 4),
                "similarity_percent": round(best_score * 100, 2),
                "domain_inference": infer_domain(top_terms, documents[i]),
                "top_terms": top_terms,
                "shared_terms_with_nearest_peer": shared_terms,
                "interpretation": interpret_similarity(best_score),
            }
        )

    result = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "method": method,
        "sklearn_available": SKLEARN_AVAILABLE,
        "feature_count": feature_count,
        "companies": [{"company_dir": cd, "company": companies[cd], **metadata[cd]} for cd in company_dirs],
        "top_terms_by_company": top_terms_by_company,
        "similarity_matrix": matrix_rows,
        "nearest_peers": nearest,
        "notes": [
            "Cosine similarity는 특허 제목·초록·IPC/CPC 등 기술 텍스트 유사도를 나타내며, 재무적 유사도나 주가 상관을 의미하지 않습니다.",
            "5개 기업 MVP에서는 peer map의 방향성 확인용으로 사용하고, 30개 이상 확장 시 분야별 reference universe 기반 상대평가로 고도화합니다.",
        ],
    }

    if save:
        write_json(OUT_DIR / "tech_peer_similarity.json", result)
        write_text(OUT_DIR / "tech_peer_similarity.md", build_markdown(result))
        for item in nearest:
            company_dir = item["company_dir"]
            write_json(company_agent_dir(company_dir, "tech") / "tech_peer_similarity.json", {
                "created_at": result["created_at"],
                "method": method,
                "company": item,
                "similarity_matrix": matrix_rows,
                "notes": result["notes"],
            })
        print(f"[Tech Peer Similarity] 저장 완료: {OUT_DIR / 'tech_peer_similarity.json'}")
        print(f"[Tech Peer Similarity] 저장 완료: {OUT_DIR / 'tech_peer_similarity.md'}")

    return result


def interpret_similarity(score: float) -> str:
    if score >= 0.75:
        return "매우 유사한 기술 포트폴리오"
    if score >= 0.55:
        return "상당히 유사한 기술 포트폴리오"
    if score >= 0.35:
        return "일부 기술축이 겹치는 포트폴리오"
    if score >= 0.15:
        return "기술축 차이가 큰 편"
    return "기술 텍스트 기준 유사도 낮음"


def build_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 5개 기업 Tech Peer Cosine Similarity Report")
    lines.append("")
    lines.append("## 1. 분석 개요")
    lines.append(f"- 생성 시각: {result.get('created_at', '')}")
    lines.append(f"- 방법: **{result.get('method', '미확인')}**")
    lines.append(f"- TF-IDF 피처 수: **{result.get('feature_count', 0)}개**")
    lines.append("- 해석: 가까울수록 특허 제목·초록·IPC/CPC 기준 기술 포트폴리오가 유사합니다.")
    lines.append("")

    companies = result.get("companies", [])
    if companies:
        lines.append("## 2. 입력 데이터")
        lines.append("| 기업 | slug | 원천 | 특허 행 수 | 문서 길이 |")
        lines.append("|---|---|---|---:|---:|")
        for c in companies:
            lines.append(
                f"| {c.get('company', '')} | {c.get('company_dir', '')} | {c.get('source_type', '')} | {c.get('patent_rows', 0)} | {c.get('document_chars', 0)} |"
            )
        lines.append("")

    matrix = result.get("similarity_matrix", [])
    dirs = [c.get("company_dir") for c in companies]
    name_map = {c.get("company_dir"): c.get("company") for c in companies}
    if matrix and dirs:
        lines.append("## 3. Cosine Similarity Matrix")
        header = "| 기업 | " + " | ".join(str(name_map.get(d, d)) for d in dirs) + " |"
        sep = "|---|" + "---:|" * len(dirs)
        lines.append(header)
        lines.append(sep)
        for row in matrix:
            cells = [str(row.get("company", row.get("company_dir", "")))]
            for d in dirs:
                cells.append(f"{float(row.get(d, 0.0)):.4f}")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    nearest = result.get("nearest_peers", [])
    if nearest:
        lines.append("## 4. Nearest Peer")
        lines.append("| 기업 | 가장 가까운 peer | 유사도 | 자동 기술군 해석 | 공통 핵심 용어 | 해석 |")
        lines.append("|---|---|---:|---|---|---|")
        for item in nearest:
            shared = ", ".join(item.get("shared_terms_with_nearest_peer", [])[:6]) or "공통 상위 용어 제한"
            lines.append(
                f"| {item.get('company')} | {item.get('nearest_peer')} | {item.get('similarity_percent')}% | {item.get('domain_inference')} | {shared} | {item.get('interpretation')} |"
            )
        lines.append("")

    top_terms = result.get("top_terms_by_company", {})
    if top_terms:
        lines.append("## 5. 기업별 TF-IDF 상위 기술 용어")
        lines.append("| 기업 | 상위 기술 용어 |")
        lines.append("|---|---|")
        for c in companies:
            company_dir = c.get("company_dir")
            terms = ", ".join(x.get("term", "") for x in top_terms.get(company_dir, [])[:10])
            lines.append(f"| {c.get('company')} | {terms or '확인 제한'} |")
        lines.append("")

    notes = result.get("notes", [])
    if notes:
        lines.append("## 6. 해석상 주의점")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines).strip() + "\n"


def parse_company_args(values: list[str]) -> dict[str, str]:
    if not values:
        return dict(DEFAULT_COMPANIES)
    companies: dict[str, str] = {}
    for value in values:
        if ":" in value:
            slug, name = value.split(":", 1)
            companies[slug.strip()] = name.strip() or slug.strip()
        else:
            slug = value.strip()
            companies[slug] = DEFAULT_COMPANIES.get(slug, slug)
    return companies


def main() -> int:
    parser = argparse.ArgumentParser(description="Build company-level tech cosine similarity from KIPRIS patent text.")
    parser.add_argument("--companies", nargs="*", help="slug or slug:display_name list. default = 5 MVP companies")
    args = parser.parse_args()
    companies = parse_company_args(args.companies or [])
    build_similarity(companies=companies)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

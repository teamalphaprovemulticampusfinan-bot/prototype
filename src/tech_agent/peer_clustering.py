from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from importlib import import_module
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any

from common.output_paths import output_candidates, read_json_first, read_text_first


ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_DIR = ml_universe_dir()
OUTPUT_DIR = UNIVERSE_DIR

DEFAULT_UNIVERSE_PATH = UNIVERSE_DIR / "deeptech_reference_universe.csv"

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


FOCAL_TICKER_TO_DIR = {
    "033640": "nepes",
    "042700": "hanmi",
    "014680": "hansol",
    "317330": "duksan",
    "170920": "ltc",
}

FOCAL_NAME_TO_DIR = {
    "네패스": "nepes",
    "한미반도체": "hanmi",
    "한솔케미칼": "hansol",
    "덕산테코피아": "duksan",
    "LTC": "ltc",
    "엘티씨": "ltc",
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

UNIVERSE_TEXT_KEYS = [
    "company_name",
    "sector_theme",
    "sector_label",
    "peer_group",
    "semiconductor_tag",
    "selection_reason",
    "valuation_proxy_label",
    "credit_proxy_label",
    "valuation_pred_label",
    "credit_pred_label",
    "valuation_confidence_bucket",
    "credit_confidence_bucket",
    "data_quality_status",
    "manual_review_priority",
    "review_flag",
    "notes",
]

CLUSTER_NAME_RULES = [
    (
        "반도체 후공정/패키징 cluster",
        ["패키징", "후공정", "wlp", "fowlp", "plp", "bumping", "osat", "package", "packaging"],
    ),
    (
        "반도체 장비/본딩·검사 cluster",
        ["장비", "본더", "본딩", "bonder", "bonding", "검사", "테스트", "hbm", "레이저", "증착"],
    ),
    (
        "반도체 소재/전자재료 cluster",
        ["소재", "전자재료", "전구체", "과산화수소", "식각", "세정", "특수가스", "photoresist"],
    ),
    (
        "디스플레이/OLED·전자재료 cluster",
        ["oled", "디스플레이", "유기재료", "박리", "필름"],
    ),
    (
        "이차전지 소재 cluster",
        ["이차전지", "배터리", "양극재", "음극재", "전해액", "첨가제", "리튬", "cnt"],
    ),
    (
        "바이오 CMO/CDMO cluster",
        ["바이오", "cdmo", "cmo", "위탁생산", "의약품", "항체"],
    ),
    (
        "로봇/자동화 cluster",
        ["로봇", "자동화", "협동로봇", "감속기", "제어", "스마트팩토리"],
    ),
]


def load_sklearn_components() -> dict[str, Any]:
    """
    sklearn을 정적 import하지 않고 동적 import한다.
    VS Code/Pylance의 노란 import 경고를 줄이고,
    scikit-learn이 없으면 fallback 클러스터링으로 전환하기 위한 구조다.
    """
    result: dict[str, Any] = {
        "available": False,
        "error": "",
        "TfidfVectorizer": None,
        "TruncatedSVD": None,
        "Normalizer": None,
        "KMeans": None,
        "silhouette_score": None,
        "cosine_similarity": None,
    }
    try:
        result["TfidfVectorizer"] = getattr(import_module("sklearn.feature_extraction.text"), "TfidfVectorizer")
        result["TruncatedSVD"] = getattr(import_module("sklearn.decomposition"), "TruncatedSVD")
        result["Normalizer"] = getattr(import_module("sklearn.preprocessing"), "Normalizer")
        result["KMeans"] = getattr(import_module("sklearn.cluster"), "KMeans")
        result["silhouette_score"] = getattr(import_module("sklearn.metrics"), "silhouette_score")
        result["cosine_similarity"] = getattr(import_module("sklearn.metrics.pairwise"), "cosine_similarity")
        result["available"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


SK = load_sklearn_components()


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_ticker(value: Any) -> str:
    text = clean_text(value)
    text = re.sub(r"[^0-9]", "", text)
    return text.zfill(6) if text else ""


def slugify(value: str) -> str:
    text = clean_text(value).lower()
    text = text.replace("/", "_").replace("·", "_").replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^0-9a-zA-Z가-힣_]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unclassified"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"universe CSV를 찾지 못했습니다: {path}")

    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [{str(k): clean_text(v) for k, v in row.items()} for row in csv.DictReader(f)]
        except Exception:
            continue

    raise RuntimeError(f"CSV 인코딩을 읽지 못했습니다: {path}")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    keys.append(key)
                    seen.add(key)
        fieldnames = keys

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return path.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    return ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


def row_company(row: dict[str, str]) -> str:
    return clean_text(row.get("company_name") or row.get("corp_name") or row.get("name") or row.get("기업명"))


def row_ticker(row: dict[str, str]) -> str:
    return normalize_ticker(row.get("ticker") or row.get("ticker6") or row.get("stock_code") or row.get("종목코드"))


def company_dir_from_row(row: dict[str, str]) -> str:
    ticker = row_ticker(row)
    name = row_company(row)
    if ticker in FOCAL_TICKER_TO_DIR:
        return FOCAL_TICKER_TO_DIR[ticker]
    if name in FOCAL_NAME_TO_DIR:
        return FOCAL_NAME_TO_DIR[name]
    return slugify(name)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        text = clean_text(value)
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def discover_patent_csv(company_dir: str, company_name: str, ticker: str) -> Path | None:
    candidates: list[Path] = []

    source_dir = tech_source_dir(company_dir)
    candidates.extend(
        [
            source_dir / f"kipris_{company_dir}_patents.csv",
            source_dir / f"{company_dir}_kipris_patents.csv",
            source_dir / "kipris_patents.csv",
        ]
    )

    patent_universe_dir = ml_universe_dir() / "patents"
    if ticker:
        candidates.extend(sorted(patent_universe_dir.glob(f"*{ticker}*.csv")))
    if company_name:
        candidates.extend(sorted(patent_universe_dir.glob(f"*{company_name}*.csv")))

    for path in candidates:
        if path.exists():
            return path

    for pattern in ["*patent*.csv", "*kipris*.csv", "*.csv"]:
        found = sorted(source_dir.glob(pattern)) if source_dir.exists() else []
        if found:
            return found[0]

    return None


def read_patent_text_from_csv(path: Path | None) -> tuple[str, int]:
    if path is None or not path.exists():
        return "", 0

    rows = []
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                rows = [{str(k): clean_text(v) for k, v in row.items()} for row in csv.DictReader(f)]
            break
        except Exception:
            continue

    if not rows:
        return "", 0

    texts: list[str] = []
    for row in rows:
        parts = [clean_text(row.get(key)) for key in CSV_TEXT_KEYS if clean_text(row.get(key))]
        if parts:
            texts.append(" ".join(parts))

    return "\n".join(texts), len(rows)


def load_focal_enrichment(company_dir: str) -> str:
    pieces: list[str] = []

    ml = read_json_first(output_candidates(company_dir, "tech", f"{company_dir}_tech_ml_signal.json", root=ROOT))
    if ml:
        for cluster in (ml.get("clustering") or {}).get("clusters", []) or []:
            if isinstance(cluster, dict):
                pieces.extend([clean_text(x) for x in cluster.get("top_terms", []) or []])
                pieces.extend([clean_text(x) for x in cluster.get("sample_titles", []) or []])
        for pat in ml.get("representative_patents", []) or []:
            if isinstance(pat, dict):
                pieces.append(clean_text(pat.get("title") or pat.get("invention_title")))
                pieces.append(clean_text(pat.get("ipc")))
        pieces.append(json.dumps(ml, ensure_ascii=False))

    for filename in [
        f"{company_dir}_tech_high_quality_report.md",
        f"{company_dir}_tech_patent_evidence.md",
        f"{company_dir}_tech_to_value_bridge.md",
    ]:
        text = read_text_first(output_candidates(company_dir, "tech", filename, root=ROOT))
        if text:
            pieces.append(text[:25000])

    return "\n".join(x for x in pieces if x)


def build_company_document(row: dict[str, str]) -> tuple[str, dict[str, Any]]:
    company = row_company(row)
    ticker = row_ticker(row)
    company_dir = company_dir_from_row(row)

    base_parts: list[str] = []
    for key in UNIVERSE_TEXT_KEYS:
        value = clean_text(row.get(key))
        if value:
            # 중요한 분야 필드는 반복해 가중치를 조금 준다.
            repeat = 3 if key in {"sector_label", "peer_group", "semiconductor_tag"} else 1
            base_parts.extend([value] * repeat)

    for key in [
        "valuation_proxy_score",
        "credit_risk_score",
        "valuation_confidence",
        "credit_confidence",
        "selection_score",
    ]:
        value = clean_text(row.get(key))
        if value:
            base_parts.append(f"{key}_{value}")

    patent_csv = discover_patent_csv(company_dir, company, ticker)
    patent_text, patent_rows = read_patent_text_from_csv(patent_csv)

    focal_text = ""
    if company_dir in FOCAL_TICKER_TO_DIR.values():
        focal_text = load_focal_enrichment(company_dir)

    doc = "\n".join([x for x in base_parts + [patent_text, focal_text] if x])

    meta = {
        "company_dir": company_dir,
        "company_name": company,
        "ticker": ticker,
        "sector_label": clean_text(row.get("sector_label")),
        "peer_group": clean_text(row.get("peer_group")),
        "semiconductor_tag": clean_text(row.get("semiconductor_tag")),
        "reference_role": clean_text(row.get("reference_role")),
        "include_in_chair": clean_text(row.get("include_in_chair")),
        "selected_for_30": clean_text(row.get("selected_for_30")),
        "patent_csv": str(patent_csv) if patent_csv else "",
        "patent_rows": patent_rows,
        "document_chars": len(doc),
        "document_source": "universe_csv+kipris_or_outputs" if (patent_text or focal_text) else "universe_csv_only",
    }
    return doc, meta


def tokenize_simple(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z0-9가-힣][a-zA-Z0-9가-힣\-\+/\.]{1,}", text)
    return [t for t in tokens if not is_noise_term(t)]


def fallback_tfidf_vectors(documents: list[str]) -> tuple[list[list[float]], list[str], list[list[tuple[str, float]]]]:
    counters = [Counter(tokenize_simple(doc)) for doc in documents]
    vocab = sorted({term for c in counters for term in c})
    if not vocab:
        return [[0.0] for _ in documents], ["empty"], [[] for _ in documents]

    n = len(documents)
    df = Counter()
    for c in counters:
        for term in c:
            df[term] += 1

    idf = {term: math.log((1 + n) / (1 + df[term])) + 1 for term in vocab}
    idx = {term: i for i, term in enumerate(vocab)}

    vectors: list[list[float]] = []
    top_terms: list[list[tuple[str, float]]] = []

    for c in counters:
        v = [0.0] * len(vocab)
        for term, count in c.items():
            v[idx[term]] = count * idf[term]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        v = [x / norm for x in v]
        vectors.append(v)
        ranked = sorted(((term, v[idx[term]]) for term in c), key=lambda x: x[1], reverse=True)[:12]
        top_terms.append(ranked)

    return vectors, vocab, top_terms


def cosine_dense(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def kmeans_fallback(
    documents: list[str],
    requested_k: int | None,
) -> tuple[list[int], list[list[float]], list[list[float]], list[list[tuple[str, float]]], dict[str, Any]]:
    vectors, vocab, top_terms = fallback_tfidf_vectors(documents)
    n = len(vectors)
    if n == 0:
        return [], [], [], [], {"method": "fallback_empty", "feature_count": 0, "k": 0}

    k = requested_k or max(2, min(6, int(math.sqrt(n)) or 2))
    k = max(1, min(k, n))

    # 간단 fallback: sector/document token dominant term 기준으로 deterministic bucket 생성
    labels: list[int] = []
    buckets: dict[str, int] = {}
    for doc in documents:
        toks = tokenize_simple(doc)
        key = toks[0] if toks else "empty"
        if key not in buckets:
            buckets[key] = len(buckets) % k
        labels.append(buckets[key])

    centers: list[list[float]] = []
    for cluster_id in range(k):
        members = [vectors[i] for i, label in enumerate(labels) if label == cluster_id]
        if not members:
            centers.append([0.0] * len(vectors[0]))
            continue
        centers.append([sum(vals) / len(vals) for vals in zip(*members)])

    meta = {
        "method": "fallback simple TF-IDF bucket clustering",
        "feature_count": len(vocab),
        "k": k,
        "silhouette_score": None,
        "selected_k_strategy": "fallback_no_sklearn",
        "sklearn_available": False,
        "sklearn_error": SK.get("error", ""),
    }

    return labels, centers, vectors, top_terms, meta


def matrix_row_to_list(row: Any) -> list[float]:
    try:
        if hasattr(row, "toarray"):
            return [float(x) for x in row.toarray()[0]]
        return [float(x) for x in row]
    except Exception:
        return []


def choose_best_k(embeddings: Any, n_samples: int, requested_k: int | None, random_state: int) -> tuple[int, list[dict[str, Any]]]:
    if requested_k is not None and requested_k > 0:
        return max(2, min(requested_k, n_samples - 1)), []

    KMeans = SK["KMeans"]
    silhouette_score = SK["silhouette_score"]
    max_k = min(8, n_samples - 1)
    min_k = 2
    diagnostics: list[dict[str, Any]] = []

    best_k = min(4, max_k)
    best_score = -999.0

    for k in range(min_k, max_k + 1):
        try:
            model = KMeans(n_clusters=k, random_state=random_state, n_init=20)
            labels = model.fit_predict(embeddings)
            if len(set(labels)) < 2:
                score = -1.0
            else:
                score = float(silhouette_score(embeddings, labels))
            diagnostics.append({"k": k, "silhouette_score": round(score, 6)})
            if score > best_score:
                best_score = score
                best_k = k
        except Exception as exc:
            diagnostics.append({"k": k, "error": str(exc)})

    return best_k, diagnostics


def run_sklearn_clustering(
    documents: list[str],
    requested_k: int | None,
    random_state: int,
) -> tuple[list[int], Any, Any, list[list[dict[str, Any]]], dict[str, Any]]:
    if not SK["available"]:
        raise RuntimeError(SK["error"] or "scikit-learn is not available")

    TfidfVectorizer = SK["TfidfVectorizer"]
    TruncatedSVD = SK["TruncatedSVD"]
    Normalizer = SK["Normalizer"]
    KMeans = SK["KMeans"]
    silhouette_score = SK["silhouette_score"]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1,
        token_pattern=r"(?u)\b[\w가-힣][\w가-힣\-\+/\.]{1,}\b",
        stop_words=list(TECH_STOPWORDS),
        max_df=0.90,
    )
    tfidf = vectorizer.fit_transform(documents)
    terms = vectorizer.get_feature_names_out()

    n_samples, n_features = tfidf.shape
    if n_samples < 2:
        raise RuntimeError("클러스터링에는 최소 2개 기업 문서가 필요합니다.")

    if n_features >= 8 and n_samples >= 4:
        n_components = max(2, min(20, n_samples - 1, n_features - 1))
        svd = TruncatedSVD(n_components=n_components, random_state=random_state)
        normalizer = Normalizer(copy=False)
        embeddings = normalizer.fit_transform(svd.fit_transform(tfidf))
        embedding_method = f"TF-IDF + TruncatedSVD({n_components}) + Normalizer"
        explained_variance = float(getattr(svd, "explained_variance_ratio_", []).sum())
    else:
        embeddings = tfidf
        embedding_method = "TF-IDF sparse"
        explained_variance = None

    k, k_diagnostics = choose_best_k(embeddings, n_samples=n_samples, requested_k=requested_k, random_state=random_state)

    model = KMeans(n_clusters=k, random_state=random_state, n_init=50)
    labels = [int(x) for x in model.fit_predict(embeddings)]

    sil = None
    try:
        if len(set(labels)) > 1 and len(set(labels)) < n_samples:
            sil = float(silhouette_score(embeddings, labels))
    except Exception:
        sil = None

    top_terms: list[list[dict[str, Any]]] = []
    for i in range(n_samples):
        vec = tfidf.getrow(i).toarray()[0]
        ranked_idx = vec.argsort()[::-1][:15]
        top_terms.append(
            clean_top_terms([
                {"term": str(terms[j]), "weight": round(float(vec[j]), 5)}
                for j in ranked_idx
                if float(vec[j]) > 0
            ], limit=15)
        )

    meta = {
        "method": "Company-level TF-IDF/LSA + KMeans",
        "embedding_method": embedding_method,
        "feature_count": int(n_features),
        "k": int(k),
        "silhouette_score": round(sil, 6) if sil is not None else None,
        "k_diagnostics": k_diagnostics,
        "explained_variance_ratio_sum": round(explained_variance, 6) if explained_variance is not None else None,
        "sklearn_available": True,
        "sklearn_error": "",
    }

    return labels, model.cluster_centers_, embeddings, top_terms, meta


def get_embedding_row(embeddings: Any, idx: int) -> list[float]:
    try:
        row = embeddings[idx]
        return matrix_row_to_list(row)
    except Exception:
        try:
            return [float(x) for x in embeddings[idx]]
        except Exception:
            return []


def pairwise_cosine(embeddings: Any, n: int) -> list[list[float]]:
    if SK["available"] and SK.get("cosine_similarity") is not None:
        try:
            mat = SK["cosine_similarity"](embeddings)
            return [[float(mat[i][j]) for j in range(n)] for i in range(n)]
        except Exception:
            pass

    rows = [get_embedding_row(embeddings, i) for i in range(n)]
    return [[cosine_dense(rows[i], rows[j]) for j in range(n)] for i in range(n)]


def compute_centroid_distances(embeddings: Any, labels: list[int]) -> list[float]:
    rows = [get_embedding_row(embeddings, i) for i in range(len(labels))]
    if not rows or not rows[0]:
        return [0.0 for _ in labels]

    centroids: dict[int, list[float]] = {}
    for cluster_id in sorted(set(labels)):
        members = [rows[i] for i, label in enumerate(labels) if label == cluster_id]
        centroids[cluster_id] = [sum(vals) / len(vals) for vals in zip(*members)]

    dists: list[float] = []
    for row, label in zip(rows, labels):
        center = centroids[label]
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(row, center)))
        dists.append(dist)
    return dists


def infer_cluster_name(top_terms: list[str], sector_labels: list[str]) -> str:
    text = " ".join(top_terms + sector_labels).lower()
    best_label = "기술 포트폴리오 혼합 cluster"
    best_score = 0
    for label, keys in CLUSTER_NAME_RULES:
        score = sum(text.count(k.lower()) for k in keys)
        if score > best_score:
            best_score = score
            best_label = label
    return best_label


def build_cluster_summary(
    assignments: list[dict[str, Any]],
    top_terms_by_company: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    cluster_members: dict[int, list[dict[str, Any]]] = defaultdict(list)
    cluster_term_counter: dict[int, Counter[str]] = defaultdict(Counter)
    cluster_sector_counter: dict[int, Counter[str]] = defaultdict(Counter)

    for row, terms in zip(assignments, top_terms_by_company):
        cluster_id = int(row["cluster_id"])
        cluster_members[cluster_id].append(row)
        cluster_sector_counter[cluster_id][clean_text(row.get("sector_label"))] += 1
        for term in terms[:10]:
            cluster_term_counter[cluster_id][clean_text(term.get("term"))] += 1

    summary: list[dict[str, Any]] = []
    for cluster_id in sorted(cluster_members):
        members = cluster_members[cluster_id]
        top_terms = [term for term, _ in cluster_term_counter[cluster_id].most_common(12)]
        top_sectors = [sector for sector, _ in cluster_sector_counter[cluster_id].most_common(5)]
        cluster_name = infer_cluster_name(top_terms, top_sectors)

        focal_members = [m for m in members if int(m.get("is_focal", 0) or 0) == 1]
        ref_members = [m for m in members if int(m.get("is_focal", 0) or 0) == 0]

        avg_selection = sum(as_float(m.get("selection_score")) for m in members) / max(len(members), 1)

        summary.append(
            {
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "member_count": len(members),
                "focal_count": len(focal_members),
                "reference_count": len(ref_members),
                "top_terms": top_terms,
                "top_sector_labels": top_sectors,
                "companies": [
                    {
                        "company_name": m.get("company_name"),
                        "ticker": m.get("ticker"),
                        "is_focal": m.get("is_focal"),
                        "sector_label": m.get("sector_label"),
                        "selection_score": m.get("selection_score"),
                    }
                    for m in members
                ],
                "avg_selection_score": round(avg_selection, 4),
                "interpretation": interpret_cluster(cluster_name, len(members), len(focal_members)),
            }
        )

    return summary


def interpret_cluster(cluster_name: str, count: int, focal_count: int) -> str:
    base = f"{cluster_name}로 분류된 {count}개 기업의 특허/기술 텍스트 기반 peer group입니다."
    if focal_count:
        base += f" 현재 focal 기업 {focal_count}개가 포함되어 Chair 기술 판단의 비교 기준으로 활용할 수 있습니다."
    else:
        base += " 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다."
    return base


def nearest_peers_by_cluster(
    assignments: list[dict[str, Any]],
    sim_matrix: list[list[float]],
    top_n: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}

    for i, row in enumerate(assignments):
        same_cluster = []
        for j, other in enumerate(assignments):
            if i == j:
                continue
            if int(row["cluster_id"]) != int(other["cluster_id"]):
                continue
            same_cluster.append(
                {
                    "company_name": other["company_name"],
                    "ticker": other["ticker"],
                    "sector_label": other["sector_label"],
                    "similarity": round(float(sim_matrix[i][j]), 6),
                    "similarity_percent": round(float(sim_matrix[i][j]) * 100, 2),
                    "is_focal": other["is_focal"],
                }
            )
        same_cluster.sort(key=lambda x: x["similarity"], reverse=True)
        out[str(row["universe_id"])] = same_cluster[:top_n]

    return out


def build_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    meta = result.get("meta", {})

    lines.append("# Company-level KMeans Tech Peer Group Report")
    lines.append("")
    lines.append("## 1. 분석 개요")
    lines.append(f"- 생성 시각: {result.get('created_at')}")
    lines.append(f"- 입력 universe: `{result.get('universe_csv')}`")
    lines.append(f"- 분석 기업 수: **{meta.get('n_companies', 0)}개**")
    lines.append(f"- 방법: **{meta.get('method')}**")
    lines.append(f"- 임베딩: **{meta.get('embedding_method')}**")
    lines.append(f"- 선택 K: **{meta.get('k')}개**")
    lines.append(f"- Silhouette Score: **{meta.get('silhouette_score')}**")
    lines.append(f"- TF-IDF 피처 수: **{meta.get('feature_count')}개**")
    lines.append("- 해석: 이 cluster는 재무/주가 cluster가 아니라 특허·기술 텍스트와 reference universe 메타데이터 기반 기술 peer group입니다.")
    lines.append("")

    if meta.get("k_diagnostics"):
        lines.append("## 2. K 후보별 Silhouette 진단")
        lines.append("| K | Silhouette Score | 비고 |")
        lines.append("|---:|---:|---|")
        for item in meta.get("k_diagnostics", []):
            if "error" in item:
                lines.append(f"| {item.get('k')} | - | {item.get('error')} |")
            else:
                lines.append(f"| {item.get('k')} | {item.get('silhouette_score')} | - |")
        lines.append("")

    lines.append("## 3. Cluster Summary")
    lines.append("| Cluster | 이름 | 기업 수 | Focal | Reference | 주요 분야 | 핵심 용어 | 해석 |")
    lines.append("|---:|---|---:|---:|---:|---|---|---|")
    for c in result.get("clusters", []):
        lines.append(
            f"| {c.get('cluster_id')} | "
            f"{c.get('cluster_name')} | "
            f"{c.get('member_count')} | "
            f"{c.get('focal_count')} | "
            f"{c.get('reference_count')} | "
            f"{', '.join(c.get('top_sector_labels', [])[:4])} | "
            f"{', '.join(c.get('top_terms', [])[:8])} | "
            f"{c.get('interpretation')} |"
        )
    lines.append("")

    lines.append("## 4. Company Assignments")
    lines.append("| 기업 | 티커 | 분야 | Cluster | Cluster 이름 | 중심거리 | 선택점수 | 역할 |")
    lines.append("|---|---|---|---:|---|---:|---:|---|")
    cluster_name_map = {c["cluster_id"]: c["cluster_name"] for c in result.get("clusters", [])}
    for a in result.get("assignments", []):
        lines.append(
            f"| {a.get('company_name')} | "
            f"{a.get('ticker')} | "
            f"{a.get('sector_label')} | "
            f"{a.get('cluster_id')} | "
            f"{cluster_name_map.get(a.get('cluster_id'), '')} | "
            f"{a.get('distance_to_centroid')} | "
            f"{a.get('selection_score')} | "
            f"{a.get('reference_role')} |"
        )
    lines.append("")

    lines.append("## 5. Focal 기업별 같은 Cluster 내 nearest peer")
    lines.append("| Focal 기업 | Cluster | 가까운 peer |")
    lines.append("|---|---|---|")
    nearest = result.get("nearest_peers_by_universe_id", {})
    for a in result.get("assignments", []):
        if int(a.get("is_focal", 0) or 0) != 1:
            continue
        peers = nearest.get(str(a.get("universe_id")), [])
        peer_text = "; ".join(f"{p['company_name']}({p['similarity_percent']}%)" for p in peers[:5]) or "같은 cluster 내 peer 제한"
        lines.append(f"| {a.get('company_name')} | {a.get('cluster_id')} | {peer_text} |")
    lines.append("")

    lines.append("## 6. 활용 원칙")
    lines.append("- 이 결과는 30개 reference universe를 기술 텍스트 기준으로 재분류한 peer group입니다.")
    lines.append("- Chair에서는 같은 cluster 내 peer를 기술 비교 기준으로 사용하되, 재무·시장·현금흐름 판단과 혼동하지 않습니다.")
    lines.append("- 개별 company 폴더가 없는 reference 기업은 universe CSV 메타데이터만 사용하므로, KIPRIS 원천 특허가 추가될수록 cluster 품질이 개선됩니다.")
    lines.append("- 5단계에서는 이 결과를 UMAP 2D peer map으로 시각화하면 발표자료에서 ML 활용도가 더 잘 보입니다.")

    return "\n".join(lines).strip() + "\n"


def save_packet_for_focal(assignments: list[dict[str, Any]], result: dict[str, Any]) -> None:
    nearest = result.get("nearest_peers_by_universe_id", {})
    clusters = {c["cluster_id"]: c for c in result.get("clusters", [])}

    for row in assignments:
        ticker = row.get("ticker")
        company_dir = FOCAL_TICKER_TO_DIR.get(str(ticker), "")
        if not company_dir:
            continue

        packet = {
            "created_at": result.get("created_at"),
            "method": result.get("meta", {}).get("method"),
            "embedding_method": result.get("meta", {}).get("embedding_method"),
            "k": result.get("meta", {}).get("k"),
            "silhouette_score": result.get("meta", {}).get("silhouette_score"),
            "company_assignment": row,
            "cluster_summary": clusters.get(row.get("cluster_id"), {}),
            "nearest_peers_same_cluster": nearest.get(str(row.get("universe_id")), []),
            "chair_reflection": (
                "동일 cluster 내 reference peer를 기술 비교 기준으로 사용하되, "
                "최종 투자 판단에서는 고객 채택·양산·매출 전환·FCF 연결 근거를 별도 확인합니다."
            ),
        }
        write_json(company_agent_dir(company_dir, "tech") / "tech_peer_cluster.json", packet)


def run_peer_clustering(
    universe_csv: Path = DEFAULT_UNIVERSE_PATH,
    k: int | None = None,
    random_state: int = 42,
    save: bool = True,
) -> dict[str, Any]:
    rows = read_csv_rows(universe_csv)
    if not rows:
        raise RuntimeError("reference universe CSV에 행이 없습니다.")

    documents: list[str] = []
    metas: list[dict[str, Any]] = []

    for row in rows:
        doc, meta = build_company_document(row)
        if not doc.strip():
            doc = row_company(row) or row_ticker(row)
        documents.append(doc)
        meta.update(
            {
                "universe_id": clean_text(row.get("universe_id")) or f"{slugify(row_company(row))}_{row_ticker(row)}",
                "selection_score": as_float(row.get("selection_score")),
                "reference_role": clean_text(row.get("reference_role")),
                "is_focal": int(as_float(row.get("is_focal"), 0.0)),
                "include_in_chair": int(as_float(row.get("include_in_chair"), 0.0)),
                "selected_for_30": int(as_float(row.get("selected_for_30"), 0.0)),
                "valuation_proxy_label": clean_text(row.get("valuation_proxy_label") or row.get("valuation_pred_label")),
                "credit_proxy_label": clean_text(row.get("credit_proxy_label") or row.get("credit_pred_label")),
                "review_flag": clean_text(row.get("review_flag")),
            }
        )
        metas.append(meta)

    try:
        labels, centers, embeddings, top_terms_by_company, meta = run_sklearn_clustering(
            documents=documents,
            requested_k=k,
            random_state=random_state,
        )
    except Exception as exc:
        labels, centers, embeddings, fallback_terms, meta = kmeans_fallback(documents, requested_k=k)
        top_terms_by_company = [
            [{"term": term, "weight": round(weight, 5)} for term, weight in terms]
            for terms in fallback_terms
        ]
        meta["sklearn_runtime_error"] = str(exc)

    distances = compute_centroid_distances(embeddings, labels)
    sim_matrix = pairwise_cosine(embeddings, len(metas))

    assignments: list[dict[str, Any]] = []
    for idx, m in enumerate(metas):
        top_terms = [x["term"] for x in top_terms_by_company[idx][:10]]
        assignments.append(
            {
                **m,
                "cluster_id": int(labels[idx]),
                "distance_to_centroid": round(float(distances[idx]), 6),
                "top_terms": "|".join(top_terms),
            }
        )

    cluster_summary = build_cluster_summary(assignments, top_terms_by_company)
    nearest = nearest_peers_by_cluster(assignments, sim_matrix, top_n=5)

    result = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "universe_csv": str(universe_csv),
        "meta": {
            **meta,
            "n_companies": len(assignments),
            "random_state": random_state,
            "requested_k": k,
        },
        "assignments": assignments,
        "clusters": cluster_summary,
        "nearest_peers_by_universe_id": nearest,
        "notes": [
            "Company-level KMeans는 기업별 특허/기술 텍스트와 reference universe 메타데이터를 결합해 기술 peer group을 배정합니다.",
            "reference 기업은 개별 폴더 없이 universe CSV 정보만으로도 clustering에 참여할 수 있습니다.",
            "KIPRIS 특허 CSV가 추가되면 해당 기업의 document가 자동으로 풍부해져 cluster 품질이 개선됩니다.",
        ],
    }

    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "tech_peer_clusters.json"
        md_path = OUTPUT_DIR / "tech_peer_clusters.md"
        assignment_csv = OUTPUT_DIR / "company_tech_cluster_assignments.csv"

        write_json(json_path, result)
        md_path.write_text(build_markdown(result), encoding="utf-8")
        write_csv(
            assignment_csv,
            assignments,
            fieldnames=[
                "universe_id",
                "company_dir",
                "company_name",
                "ticker",
                "market",
                "sector_label",
                "peer_group",
                "semiconductor_tag",
                "reference_role",
                "is_focal",
                "include_in_chair",
                "selected_for_30",
                "selection_score",
                "cluster_id",
                "distance_to_centroid",
                "top_terms",
                "valuation_proxy_label",
                "credit_proxy_label",
                "review_flag",
                "document_source",
                "patent_csv",
                "patent_rows",
                "document_chars",
            ],
        )
        save_packet_for_focal(assignments, result)

        print(f"[Tech Peer Clustering] JSON 저장 완료: {json_path}")
        print(f"[Tech Peer Clustering] Markdown 저장 완료: {md_path}")
        print(f"[Tech Peer Clustering] Assignment CSV 저장 완료: {assignment_csv}")
        print(f"[Tech Peer Clustering] method={result['meta'].get('method')}")
        print(f"[Tech Peer Clustering] embedding={result['meta'].get('embedding_method')}")
        print(f"[Tech Peer Clustering] k={result['meta'].get('k')}")
        print(f"[Tech Peer Clustering] silhouette={result['meta'].get('silhouette_score')}")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run company-level KMeans peer clustering from deeptech_reference_universe.csv.")
    parser.add_argument(
        "--universe-csv",
        default=str(DEFAULT_UNIVERSE_PATH),
        help="path to data/<분야>/common/ml_universe/deeptech_reference_universe.csv",
    )
    parser.add_argument("--k", type=int, default=0, help="fixed K. 0 means auto-select by silhouette")
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    k = args.k if args.k > 0 else None
    run_peer_clustering(
        universe_csv=Path(args.universe_csv),
        k=k,
        random_state=args.random_state,
        save=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

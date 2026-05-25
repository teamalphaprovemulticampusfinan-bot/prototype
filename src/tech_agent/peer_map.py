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

from common.output_paths import agent_output_path, output_candidates, read_json_first, read_text_first

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_DIR = ml_universe_dir()
DEFAULT_UNIVERSE_PATH = UNIVERSE_DIR / "deeptech_reference_universe.csv"
DEFAULT_CLUSTER_PATH = UNIVERSE_DIR / "tech_peer_clusters.json"

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
    "invention_title", "inventionTitle", "title", "발명의명칭",
    "abstract", "astrtCont", "초록", "요약",
    "ipc_number", "ipcNumber", "IPC", "ipc",
    "cpc_number", "cpcNumber", "CPC", "cpc",
    "applicant_name", "applicantName", "출원인", "권리자",
]

UNIVERSE_TEXT_KEYS = [
    "company_name", "sector_theme", "sector_label", "peer_group", "semiconductor_tag",
    "selection_reason", "valuation_proxy_label", "credit_proxy_label",
    "valuation_pred_label", "credit_pred_label", "valuation_confidence_bucket",
    "credit_confidence_bucket", "data_quality_status", "manual_review_priority",
    "review_flag", "notes",
]


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


def normalize_ticker(value: Any) -> str:
    text = re.sub(r"[^0-9]", "", clean_text(value))
    return text.zfill(6) if text else ""


def slugify(value: str) -> str:
    text = clean_text(value).lower()
    text = text.replace("/", "_").replace("·", "_").replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^0-9a-zA-Z가-힣_]+", "", text)
    return re.sub(r"_+", "_", text).strip("_") or "unclassified"


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        text = clean_text(value)
        return float(text) if text else default
    except Exception:
        return default


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV를 찾지 못했습니다: {path}")
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
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    fieldnames.append(key)
                    seen.add(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def discover_patent_csv(company_dir: str, company_name: str, ticker: str) -> Path | None:
    candidates: list[Path] = []
    source_dir = tech_source_dir(company_dir)
    candidates.extend([
        source_dir / f"kipris_{company_dir}_patents.csv",
        source_dir / f"{company_dir}_kipris_patents.csv",
        source_dir / "kipris_patents.csv",
    ])
    patent_universe_dir = ml_universe_dir() / "patents"
    if ticker:
        candidates.extend(sorted(patent_universe_dir.glob(f"*{ticker}*.csv")))
    if company_name:
        candidates.extend(sorted(patent_universe_dir.glob(f"*{company_name}*.csv")))
    for path in candidates:
        if path.exists():
            return path
    if source_dir.exists():
        for pattern in ["*patent*.csv", "*kipris*.csv", "*.csv"]:
            found = sorted(source_dir.glob(pattern))
            if found:
                return found[0]
    return None


def read_patent_text_from_csv(path: Path | None) -> tuple[str, int]:
    if path is None or not path.exists():
        return "", 0
    rows: list[dict[str, str]] = []
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                rows = [{str(k): clean_text(v) for k, v in row.items()} for row in csv.DictReader(f)]
            break
        except Exception:
            continue
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
            repeat = 3 if key in {"sector_label", "peer_group", "semiconductor_tag"} else 1
            base_parts.extend([value] * repeat)
    for key in ["valuation_proxy_score", "credit_risk_score", "valuation_confidence", "credit_confidence", "selection_score"]:
        value = clean_text(row.get(key))
        if value:
            base_parts.append(f"{key}_{value}")
    patent_csv = discover_patent_csv(company_dir, company, ticker)
    patent_text, patent_rows = read_patent_text_from_csv(patent_csv)
    focal_text = load_focal_enrichment(company_dir) if company_dir in FOCAL_TICKER_TO_DIR.values() else ""
    doc = "\n".join([x for x in base_parts + [patent_text, focal_text] if x]).strip() or company or ticker
    meta = {
        "company_dir": company_dir,
        "company_name": company,
        "ticker": ticker,
        "market": clean_text(row.get("market")),
        "sector_label": clean_text(row.get("sector_label")),
        "peer_group": clean_text(row.get("peer_group")),
        "semiconductor_tag": clean_text(row.get("semiconductor_tag")),
        "reference_role": clean_text(row.get("reference_role")),
        "include_in_chair": int(as_float(row.get("include_in_chair"), 0.0)),
        "is_focal": int(as_float(row.get("is_focal"), 0.0)),
        "selected_for_30": int(as_float(row.get("selected_for_30"), 0.0)),
        "selection_score": as_float(row.get("selection_score")),
        "review_flag": clean_text(row.get("review_flag")),
        "patent_csv": str(patent_csv) if patent_csv else "",
        "patent_rows": patent_rows,
        "document_chars": len(doc),
        "document_source": "universe_csv+kipris_or_outputs" if (patent_text or focal_text) else "universe_csv_only",
        "universe_id": clean_text(row.get("universe_id")) or f"{slugify(company)}_{ticker}",
    }
    return doc, meta


def load_cluster_assignments(cluster_path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(cluster_path)
    assignments = data.get("assignments", []) if isinstance(data, dict) else []
    clusters = {str(c.get("cluster_id")): c for c in data.get("clusters", [])} if isinstance(data, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for row in assignments:
        if not isinstance(row, dict):
            continue
        key = normalize_ticker(row.get("ticker")) or clean_text(row.get("company_name")).lower()
        if key:
            cluster = clusters.get(str(row.get("cluster_id")), {})
            merged = dict(row)
            merged["cluster_name"] = cluster.get("cluster_name", "")
            out[key] = merged
    return out


def import_optional(name: str, attr: str | None = None) -> Any:
    module = import_module(name)
    return getattr(module, attr) if attr else module


def load_components() -> dict[str, Any]:
    out: dict[str, Any] = {"sklearn_available": False, "umap_available": False, "matplotlib_available": False, "errors": []}
    try:
        out["TfidfVectorizer"] = import_optional("sklearn.feature_extraction.text", "TfidfVectorizer")
        out["TruncatedSVD"] = import_optional("sklearn.decomposition", "TruncatedSVD")
        out["Normalizer"] = import_optional("sklearn.preprocessing", "Normalizer")
        out["PCA"] = import_optional("sklearn.decomposition", "PCA")
        out["sklearn_available"] = True
    except Exception as exc:
        out["errors"].append(f"sklearn import failed: {exc}")
    try:
        out["UMAP"] = import_optional("umap", "UMAP")
        out["umap_available"] = True
    except Exception:
        try:
            out["UMAP"] = import_optional("umap.umap_", "UMAP")
            out["umap_available"] = True
        except Exception as exc:
            out["errors"].append(f"umap import failed: {exc}")
    try:
        out["plt"] = import_optional("matplotlib.pyplot")
        out["matplotlib_available"] = True
    except Exception as exc:
        out["errors"].append(f"matplotlib import failed: {exc}")
    return out


COMP = load_components()


def configure_korean_matplotlib_font(plt: Any) -> dict[str, Any]:
    """Configure a Korean-capable font for matplotlib PNG outputs.

    This prevents glyph-missing warnings and broken Korean labels in UMAP/PCA
    peer-map images. The function is intentionally local to peer_map.py so that
    other agents are not affected.
    """
    info: dict[str, Any] = {"configured": False, "font_name": "", "font_path": "", "reason": ""}
    try:
        import os
        import platform
        from matplotlib import font_manager, rcParams

        env_candidates = [
            os.environ.get("TECH_KOREAN_FONT_PATH", ""),
            os.environ.get("KOREAN_FONT_PATH", ""),
        ]
        system = platform.system().lower()
        path_candidates: list[str] = []
        path_candidates.extend([x for x in env_candidates if x])

        if "windows" in system:
            path_candidates.extend([
                r"C:\Windows\Fonts\malgun.ttf",
                r"C:\Windows\Fonts\malgunbd.ttf",
                r"C:\Windows\Fonts\NanumGothic.ttf",
                r"C:\Windows\Fonts\NanumGothicBold.ttf",
            ])
        elif "darwin" in system:
            path_candidates.extend([
                "/System/Library/Fonts/AppleGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
                "/Library/Fonts/NanumGothic.ttf",
            ])
        else:
            path_candidates.extend([
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ])

        selected_path = ""
        for candidate in path_candidates:
            if candidate and Path(candidate).exists():
                selected_path = candidate
                break

        # Fallback: scan installed fonts for common Korean-capable families.
        selected_name = ""
        if selected_path:
            font_manager.fontManager.addfont(selected_path)
            selected_name = font_manager.FontProperties(fname=selected_path).get_name()
        else:
            preferred_names = [
                "Malgun Gothic",
                "맑은 고딕",
                "NanumGothic",
                "Nanum Gothic",
                "Noto Sans CJK KR",
                "Noto Sans KR",
                "AppleGothic",
            ]
            installed = {f.name: f.fname for f in font_manager.fontManager.ttflist}
            for name in preferred_names:
                if name in installed:
                    selected_name = name
                    selected_path = installed[name]
                    break

        if selected_name:
            rcParams["font.family"] = [selected_name, "DejaVu Sans"]
            rcParams["axes.unicode_minus"] = False
            try:
                plt.rcParams["font.family"] = [selected_name, "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
            except Exception:
                pass
            info.update({"configured": True, "font_name": selected_name, "font_path": selected_path})
            return info

        rcParams["axes.unicode_minus"] = False
        info["reason"] = "Korean-capable font not found. Set TECH_KOREAN_FONT_PATH to a .ttf/.ttc font file."
        return info
    except Exception as exc:
        info["reason"] = f"font configuration failed: {exc}"
        return info



def tokenize_simple(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z0-9가-힣][a-zA-Z0-9가-힣\-\+/\.]{1,}", text)
    stopwords = {"the", "and", "for", "with", "from", "method", "device", "system", "using", "company", "selected", "reference", "peer", "value", "true", "false", "및", "또는", "하는", "대한", "포함", "제조", "방법", "기업", "후보", "기반"}
    return [t for t in tokens if len(t) >= 2 and t not in stopwords]


def fallback_vectors(documents: list[str]) -> tuple[list[list[float]], list[list[str]], dict[str, Any]]:
    counters = [Counter(tokenize_simple(doc)) for doc in documents]
    vocab = sorted({term for c in counters for term in c}) or ["empty"]
    n = len(documents)
    df = Counter()
    for c in counters:
        for term in c:
            df[term] += 1
    idf = {term: math.log((1 + n) / (1 + df[term])) + 1 for term in vocab}
    idx = {term: i for i, term in enumerate(vocab)}
    vectors: list[list[float]] = []
    top_terms: list[list[str]] = []
    for c in counters:
        v = [0.0] * len(vocab)
        for term, count in c.items():
            v[idx[term]] = count * idf[term]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        vectors.append([x / norm for x in v])
        top_terms.append([term for term, _ in c.most_common(10)])
    return vectors, top_terms, {"vectorizer": "fallback_simple_tfidf", "feature_count": len(vocab)}


def get_row(matrix: Any, idx: int) -> list[float]:
    try:
        row = matrix[idx]
        if hasattr(row, "toarray"):
            return [float(x) for x in row.toarray()[0]]
        return [float(x) for x in row]
    except Exception:
        return []


def build_embeddings(documents: list[str], random_state: int) -> tuple[Any, list[list[str]], dict[str, Any]]:
    if not COMP.get("sklearn_available"):
        return fallback_vectors(documents)
    TfidfVectorizer = COMP["TfidfVectorizer"]
    TruncatedSVD = COMP["TruncatedSVD"]
    Normalizer = COMP["Normalizer"]
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1, token_pattern=r"(?u)\b[\w가-힣][\w가-힣\-\+/\.]{1,}\b")
    tfidf = vectorizer.fit_transform(documents)
    terms = vectorizer.get_feature_names_out()
    n_samples, n_features = tfidf.shape
    if n_features >= 8 and n_samples >= 4:
        n_components = max(2, min(20, n_samples - 1, n_features - 1))
        svd = TruncatedSVD(n_components=n_components, random_state=random_state)
        normalizer = Normalizer(copy=False)
        embeddings = normalizer.fit_transform(svd.fit_transform(tfidf))
        vectorizer_name = f"TF-IDF + TruncatedSVD({n_components}) + Normalizer"
        explained = float(getattr(svd, "explained_variance_ratio_", []).sum())
    else:
        embeddings = tfidf
        vectorizer_name = "TF-IDF sparse"
        explained = None
    top_terms: list[list[str]] = []
    for i in range(n_samples):
        vec = tfidf.getrow(i).toarray()[0]
        ranked_idx = vec.argsort()[::-1][:12]
        top_terms.append([str(terms[j]) for j in ranked_idx if float(vec[j]) > 0])
    return embeddings, top_terms, {"vectorizer": vectorizer_name, "feature_count": int(n_features), "explained_variance_ratio_sum": round(explained, 6) if explained is not None else None}


def reduce_to_2d(embeddings: Any, random_state: int, n_neighbors: int, min_dist: float) -> tuple[list[list[float]], dict[str, Any]]:
    n = len(embeddings)
    if COMP.get("umap_available"):
        UMAP = COMP["UMAP"]
        safe_neighbors = max(2, min(n_neighbors, n - 1))
        reducer = UMAP(n_components=2, n_neighbors=safe_neighbors, min_dist=min_dist, metric="cosine", random_state=random_state)
        coords = reducer.fit_transform(embeddings)
        return [[float(x), float(y)] for x, y in coords], {"method": "UMAP", "umap_used": True, "n_neighbors": safe_neighbors, "min_dist": min_dist, "metric": "cosine"}
    if COMP.get("sklearn_available"):
        PCA = COMP["PCA"]
        dense = [get_row(embeddings, i) for i in range(n)]
        reducer = PCA(n_components=2, random_state=random_state)
        coords = reducer.fit_transform(dense)
        explained = getattr(reducer, "explained_variance_ratio_", [])
        return [[float(x), float(y)] for x, y in coords], {"method": "PCA fallback because umap-learn is not installed", "umap_used": False, "explained_variance_ratio_sum": round(float(sum(explained)), 6) if len(explained) else None, "install_hint": "python -m pip install umap-learn"}
    rows = [get_row(embeddings, i) for i in range(n)]
    return [[float(r[0] if len(r) > 0 else 0.0), float(r[1] if len(r) > 1 else 0.0)] for r in rows], {"method": "first_two_dimensions fallback", "umap_used": False, "install_hint": "python -m pip install umap-learn scikit-learn"}


def build_points(universe_rows: list[dict[str, str]], coords: list[list[float]], top_terms: list[list[str]], cluster_assignments: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for row, xy, terms in zip(universe_rows, coords, top_terms):
        company = row_company(row)
        ticker = row_ticker(row)
        key = ticker or company.lower()
        cluster = cluster_assignments.get(key, {})
        cluster_id = cluster.get("cluster_id", row.get("cluster_id", ""))
        points.append({
            "universe_id": clean_text(row.get("universe_id")) or f"{slugify(company)}_{ticker}",
            "company_name": company,
            "ticker": ticker,
            "market": clean_text(row.get("market")),
            "sector_label": clean_text(row.get("sector_label")),
            "peer_group": clean_text(row.get("peer_group")),
            "semiconductor_tag": clean_text(row.get("semiconductor_tag")),
            "reference_role": clean_text(row.get("reference_role")),
            "is_focal": int(as_float(row.get("is_focal"), 0.0)),
            "include_in_chair": int(as_float(row.get("include_in_chair"), 0.0)),
            "selected_for_30": int(as_float(row.get("selected_for_30"), 0.0)),
            "selection_score": as_float(row.get("selection_score")),
            "cluster_id": int(cluster_id) if str(cluster_id).strip() not in {"", "None"} else "",
            "cluster_name": clean_text(cluster.get("cluster_name")),
            "distance_to_centroid": cluster.get("distance_to_centroid", ""),
            "umap_x": round(float(xy[0]), 8),
            "umap_y": round(float(xy[1]), 8),
            "top_terms": "|".join(terms[:10]),
            "valuation_proxy_label": clean_text(row.get("valuation_proxy_label") or row.get("valuation_pred_label")),
            "credit_proxy_label": clean_text(row.get("credit_proxy_label") or row.get("credit_pred_label")),
            "review_flag": clean_text(row.get("review_flag")),
        })
    return points


def build_cluster_summary(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in points:
        grouped[str(p.get("cluster_id"))].append(p)
    summary: list[dict[str, Any]] = []
    for cid, members in sorted(grouped.items(), key=lambda x: str(x[0])):
        sector_counter = Counter(clean_text(m.get("sector_label")) for m in members)
        term_counter: Counter[str] = Counter()
        for m in members:
            for term in str(m.get("top_terms", "")).split("|"):
                if term:
                    term_counter[term] += 1
        focal = [m for m in members if int(m.get("is_focal", 0) or 0) == 1]
        ref = [m for m in members if int(m.get("is_focal", 0) or 0) == 0]
        xs = [float(m.get("umap_x", 0.0)) for m in members]
        ys = [float(m.get("umap_y", 0.0)) for m in members]
        summary.append({
            "cluster_id": cid,
            "member_count": len(members),
            "focal_count": len(focal),
            "reference_count": len(ref),
            "top_sector_labels": [x for x, _ in sector_counter.most_common(5)],
            "top_terms": [x for x, _ in term_counter.most_common(10)],
            "centroid_x": round(sum(xs) / max(len(xs), 1), 8),
            "centroid_y": round(sum(ys) / max(len(ys), 1), 8),
            "companies": [{"company_name": m.get("company_name"), "ticker": m.get("ticker"), "is_focal": m.get("is_focal")} for m in members],
        })
    return summary


def save_plot(points: list[dict[str, Any]], path: Path, use_umap_label: bool) -> bool:
    if not COMP.get("matplotlib_available"):
        return False
    plt = COMP["plt"]
    font_info = configure_korean_matplotlib_font(plt)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 8))
    cluster_ids = sorted({str(p.get("cluster_id")) for p in points})
    for cid in cluster_ids:
        group = [p for p in points if str(p.get("cluster_id")) == cid]
        ax.scatter([float(p["umap_x"]) for p in group], [float(p["umap_y"]) for p in group], label=f"Cluster {cid}", alpha=0.75, s=70)
    focal_points = [p for p in points if int(p.get("is_focal", 0) or 0) == 1]
    if focal_points:
        ax.scatter([float(p["umap_x"]) for p in focal_points], [float(p["umap_y"]) for p in focal_points], marker="*", s=220, label="Focal companies", edgecolors="black", linewidths=0.8)
    for p in focal_points:
        ax.annotate(p["company_name"], (float(p["umap_x"]), float(p["umap_y"])), xytext=(5, 5), textcoords="offset points", fontsize=10, fontweight="bold")
    ax.set_title("DeepTech Reference Universe - 2D Tech Peer Map")
    ax.set_xlabel("UMAP-1" if use_umap_label else "PCA-1")
    ax.set_ylabel("UMAP-2" if use_umap_label else "PCA-2")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return True


def build_markdown(result: dict[str, Any]) -> str:
    meta = result.get("meta", {})
    lines: list[str] = []
    lines.append("# UMAP 2D Tech Peer Map")
    lines.append("")
    lines.append("## 1. 생성 요약")
    lines.append(f"- 생성 시각: {result.get('created_at')}")
    lines.append(f"- 입력 universe: `{result.get('universe_csv')}`")
    lines.append(f"- 입력 cluster: `{result.get('cluster_json')}`")
    lines.append(f"- 분석 기업 수: **{meta.get('n_companies')}개**")
    lines.append(f"- 차원축소 방법: **{meta.get('reducer_method')}**")
    lines.append(f"- UMAP 사용 여부: **{meta.get('umap_used')}**")
    lines.append(f"- 벡터화/임베딩: **{meta.get('vectorizer')}**")
    lines.append(f"- TF-IDF 피처 수: **{meta.get('feature_count')}개**")
    lines.append(f"- PNG 저장: `{result.get('png_path')}`")
    if not meta.get("umap_used"):
        lines.append("- 비고: `umap-learn`이 설치되지 않으면 PCA fallback으로 저장됩니다. 진짜 UMAP 결과가 필요하면 `python -m pip install umap-learn` 후 재실행하세요.")
    lines.append("")
    lines.append("## 2. Cluster별 2D Map 요약")
    lines.append("| Cluster | 기업 수 | Focal | Reference | 중심 X | 중심 Y | 주요 분야 | 핵심 용어 |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---|")
    for c in result.get("clusters", []):
        lines.append(f"| {c.get('cluster_id')} | {c.get('member_count')} | {c.get('focal_count')} | {c.get('reference_count')} | {c.get('centroid_x')} | {c.get('centroid_y')} | {', '.join(c.get('top_sector_labels', [])[:4])} | {', '.join(c.get('top_terms', [])[:8])} |")
    lines.append("")
    lines.append("## 3. Focal 기업 좌표")
    lines.append("| 기업 | 티커 | Cluster | X | Y | 같은 기술군 해석 |")
    lines.append("|---|---|---|---:|---:|---|")
    for p in result.get("points", []):
        if int(p.get("is_focal", 0) or 0) != 1:
            continue
        lines.append(f"| {p.get('company_name')} | {p.get('ticker')} | {p.get('cluster_id')} | {p.get('umap_x')} | {p.get('umap_y')} | {p.get('sector_label')} / {p.get('peer_group')} |")
    lines.append("")
    lines.append("## 4. 활용 원칙")
    lines.append("- 이 지도는 투자 추천 지도가 아니라 특허/기술 텍스트 기반 peer map입니다.")
    lines.append("- 가까울수록 기술 텍스트 포트폴리오가 유사하다는 의미이며, 재무 안정성이나 주가 방향을 직접 의미하지 않습니다.")
    lines.append("- 발표에서는 focal 기업이 reference universe 안에서 어느 기술군에 놓이는지 보여주는 ML 시각화 근거로 사용합니다.")
    lines.append("- Chair 보고서에는 이 결과를 기술 peer 위치 근거로만 반영하고, 최종 추천은 재무·시장·현금흐름 근거와 함께 판단합니다.")
    return "\n".join(lines).strip() + "\n"


def save_focal_packets(result: dict[str, Any]) -> None:
    clusters = {str(c.get("cluster_id")): c for c in result.get("clusters", [])}
    for p in result.get("points", []):
        ticker = normalize_ticker(p.get("ticker"))
        company_dir = FOCAL_TICKER_TO_DIR.get(ticker)
        if not company_dir:
            continue
        packet = {
            "created_at": result.get("created_at"),
            "method": result.get("meta", {}).get("reducer_method"),
            "umap_used": result.get("meta", {}).get("umap_used"),
            "vectorizer": result.get("meta", {}).get("vectorizer"),
            "company_point": p,
            "cluster_map_summary": clusters.get(str(p.get("cluster_id")), {}),
            "png_path": result.get("png_path"),
            "csv_path": result.get("csv_path"),
            "chair_reflection": "2D peer map은 reference universe 내 기술 포트폴리오 위치를 시각화한 ML 근거입니다. 최종 투자판단에서는 재무·시장·사업화 근거와 분리해 보조적으로 반영합니다.",
        }
        write_json(company_agent_dir(company_dir, "tech") / "tech_peer_map.json", packet)
        write_json(agent_output_path(company_dir, "tech", f"{company_dir}_tech_peer_map.json", root=ROOT), packet)


def run_peer_map(universe_csv: Path = DEFAULT_UNIVERSE_PATH, cluster_json: Path = DEFAULT_CLUSTER_PATH, random_state: int = 42, n_neighbors: int = 8, min_dist: float = 0.15, save: bool = True) -> dict[str, Any]:
    universe_rows = read_csv_rows(universe_csv)
    if not universe_rows:
        raise RuntimeError("reference universe CSV에 행이 없습니다.")
    documents: list[str] = []
    for row in universe_rows:
        doc, _ = build_company_document(row)
        documents.append(doc)
    embeddings, top_terms, vector_meta = build_embeddings(documents, random_state=random_state)
    coords, reducer_meta = reduce_to_2d(embeddings, random_state=random_state, n_neighbors=n_neighbors, min_dist=min_dist)
    cluster_assignments = load_cluster_assignments(cluster_json)
    points = build_points(universe_rows, coords, top_terms, cluster_assignments)
    clusters = build_cluster_summary(points)
    csv_path = UNIVERSE_DIR / "tech_peer_map_points.csv"
    json_path = UNIVERSE_DIR / "tech_peer_map.json"
    md_path = UNIVERSE_DIR / "tech_peer_map.md"
    png_path = UNIVERSE_DIR / "tech_peer_map.png"
    result = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "universe_csv": str(universe_csv),
        "cluster_json": str(cluster_json),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "png_path": str(png_path),
        "meta": {
            "n_companies": len(points),
            "vectorizer": vector_meta.get("vectorizer"),
            "feature_count": vector_meta.get("feature_count"),
            "explained_variance_ratio_sum": vector_meta.get("explained_variance_ratio_sum"),
            "reducer_method": reducer_meta.get("method"),
            "umap_used": reducer_meta.get("umap_used", False),
            "n_neighbors": reducer_meta.get("n_neighbors"),
            "min_dist": reducer_meta.get("min_dist"),
            "metric": reducer_meta.get("metric"),
            "install_hint": reducer_meta.get("install_hint", ""),
            "component_errors": COMP.get("errors", []),
        },
        "clusters": clusters,
        "points": points,
        "notes": [
            "이 2D map은 기술 텍스트 기반 peer map이며 재무/주가 방향을 직접 의미하지 않습니다.",
            "UMAP이 설치되어 있으면 UMAP으로 저장하고, 없으면 PCA fallback으로 저장합니다.",
            "진짜 UMAP 결과가 필요하면 requirements.txt에 umap-learn을 추가하고 재실행하세요.",
        ],
    }
    if save:
        write_json(json_path, result)
        write_csv(csv_path, points)
        md_path.write_text(build_markdown(result), encoding="utf-8")
        png_saved = save_plot(points, png_path, use_umap_label=bool(result["meta"].get("umap_used")))
        result["png_saved"] = png_saved
        write_json(json_path, result)
        save_focal_packets(result)
        print(f"[Tech Peer Map] JSON 저장 완료: {json_path}")
        print(f"[Tech Peer Map] CSV 저장 완료: {csv_path}")
        print(f"[Tech Peer Map] Markdown 저장 완료: {md_path}")
        if png_saved:
            print(f"[Tech Peer Map] PNG 저장 완료: {png_path}")
        else:
            print("[Tech Peer Map] PNG 저장 실패: matplotlib 설치 여부 확인 필요")
        print(f"[Tech Peer Map] reducer={result['meta'].get('reducer_method')}")
        print(f"[Tech Peer Map] umap_used={result['meta'].get('umap_used')}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save UMAP 2D tech peer map from reference universe.")
    parser.add_argument("--universe-csv", default=str(DEFAULT_UNIVERSE_PATH))
    parser.add_argument("--cluster-json", default=str(DEFAULT_CLUSTER_PATH))
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--n-neighbors", type=int, default=8)
    parser.add_argument("--min-dist", type=float, default=0.15)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_peer_map(
        universe_csv=Path(args.universe_csv),
        cluster_json=Path(args.cluster_json),
        random_state=args.random_state,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        save=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

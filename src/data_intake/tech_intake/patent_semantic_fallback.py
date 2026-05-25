from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
except Exception:  # pragma: no cover
    TfidfVectorizer = None  # type: ignore
    cosine_similarity = None  # type: ignore


TEXT_COLUMNS = [
    "title",
    "invention_title",
    "발명의명칭",
    "명칭",
    "abstract",
    "summary",
    "요약",
    "claim_text",
    "claims",
    "청구항",
    "ipc",
    "ipc_code",
    "ipc_all",
    "cpc",
    "cpc_code",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]
        except Exception:
            continue
    return []


def _text_from_row(row: dict[str, str]) -> str:
    parts: list[str] = []
    lower_map = {k.lower(): k for k in row.keys()}
    for col in TEXT_COLUMNS:
        key = lower_map.get(col.lower())
        if key and row.get(key):
            parts.append(str(row.get(key, "")))
    if not parts:
        for v in row.values():
            if isinstance(v, str) and len(v) > 3:
                parts.append(v)
    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _simple_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9가-힣]{2,}", text.lower())


def _simple_similarity(texts: list[str], top_k: int = 20) -> tuple[list[dict[str, Any]], float]:
    vectors = [Counter(_simple_tokens(t)) for t in texts]
    pairs: list[dict[str, Any]] = []
    scores: list[float] = []
    for i in range(len(vectors)):
        vi = vectors[i]
        ni = math.sqrt(sum(v * v for v in vi.values())) or 1.0
        for j in range(i + 1, len(vectors)):
            vj = vectors[j]
            nj = math.sqrt(sum(v * v for v in vj.values())) or 1.0
            common = set(vi) & set(vj)
            score = sum(vi[t] * vj[t] for t in common) / (ni * nj)
            scores.append(score)
            if len(pairs) < top_k or score > min(p["similarity"] for p in pairs):
                pairs.append({"left_index": i, "right_index": j, "similarity": round(float(score), 4)})
                pairs = sorted(pairs, key=lambda x: x["similarity"], reverse=True)[:top_k]
    return pairs, round(float(sum(scores) / len(scores)), 4) if scores else 0.0


def _tfidf_similarity(texts: list[str], top_k: int = 20) -> tuple[list[dict[str, Any]], float]:
    if TfidfVectorizer is None or cosine_similarity is None:
        return _simple_similarity(texts, top_k=top_k)

    try:
        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1)
        mat = vectorizer.fit_transform(texts)
        sim = cosine_similarity(mat)
        pairs: list[dict[str, Any]] = []
        values: list[float] = []
        n = sim.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                score = float(sim[i, j])
                values.append(score)
                if len(pairs) < top_k or score > min(p["similarity"] for p in pairs):
                    pairs.append({"left_index": i, "right_index": j, "similarity": round(score, 4)})
                    pairs = sorted(pairs, key=lambda x: x["similarity"], reverse=True)[:top_k]
        return pairs, round(float(sum(values) / len(values)), 4) if values else 0.0
    except Exception:
        return _simple_similarity(texts, top_k=top_k)


def build_patent_semantic_features(
    *,
    source_csv: Path,
    output_dir: Path,
    company_slug: str,
    company_name: str,
    max_rows: int = 1000,
) -> dict[str, Any]:
    rows = _read_csv(source_csv)
    texts = [_text_from_row(r) for r in rows]
    filtered: list[tuple[int, str]] = [(i, t) for i, t in enumerate(texts) if len(t) >= 5]
    if max_rows and len(filtered) > max_rows:
        filtered = filtered[:max_rows]

    if not filtered:
        result = {
            "status": "NO_TEXT_AVAILABLE",
            "company_slug": company_slug,
            "company_name": company_name,
            "source_csv": str(source_csv),
            "patent_text_count": 0,
            "semantic_similarity_avg": 0.0,
            "top_pairs": [],
        }
    else:
        indices = [x[0] for x in filtered]
        usable_texts = [x[1] for x in filtered]
        pairs, avg = _tfidf_similarity(usable_texts)
        for p in pairs:
            p["left_source_index"] = indices[p["left_index"]]
            p["right_source_index"] = indices[p["right_index"]]
        result = {
            "status": "OK",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "company_slug": company_slug,
            "company_name": company_name,
            "source_csv": str(source_csv),
            "method": "TFIDF_COSINE_FALLBACK",
            "patent_text_count": len(usable_texts),
            "semantic_similarity_avg": avg,
            "top_pairs": pairs,
            "usage_note": (
                "This is an offline fallback inspired by PatentSBERTa-style semantic patent distance. "
                "If sentence-transformers and AI-Growth-Lab/PatentSBERTa are installed later, this layer can be upgraded."
            ),
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("tech_patent_semantic_features.json", f"{company_slug}_tech_patent_semantic_features.json"):
        (output_dir / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# Patent Semantic Features - {company_name} ({company_slug})",
        "",
        f"- status: {result.get('status')}",
        f"- method: {result.get('method', 'N/A')}",
        f"- patent_text_count: {result.get('patent_text_count')}",
        f"- semantic_similarity_avg: {result.get('semantic_similarity_avg')}",
        "",
        "## Top Similar Patent Pairs",
    ]
    for p in result.get("top_pairs", [])[:10]:
        md.append(f"- source_index {p.get('left_source_index')} ↔ {p.get('right_source_index')}: {p.get('similarity')}")
    for name in ("tech_patent_semantic_features.md", f"{company_slug}_tech_patent_semantic_features.md"):
        (output_dir / name).write_text("\n".join(md) + "\n", encoding="utf-8")

    csv_path = output_dir / "tech_patent_similarity_top_pairs.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["left_source_index", "right_source_index", "similarity"])
        w.writeheader()
        for p in result.get("top_pairs", []):
            w.writerow(
                {
                    "left_source_index": p.get("left_source_index"),
                    "right_source_index": p.get("right_source_index"),
                    "similarity": p.get("similarity"),
                }
            )
    return result

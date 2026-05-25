from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from common.output_paths import agent_output_path, shared_output_dir

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

try:
    from tech_agent.tech_ip_ml import (
        COMPANY_ALIASES,
        DEFAULT_COMPANIES,
        STOPWORDS,
        CompanyPatentSignal,
        collect_company_patent_signal,
        ensure_dir,
        find_project_root,
        fit_nmf,
        load_company_list,
        percentile_rank,
        read_csv_rows,
        write_json,
        write_text,
    )
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "tech_agent.tech_ip_ml 모듈을 먼저 유지해야 합니다. "
        "Step 10은 Step 9의 KIPRIS/NMF 유틸을 재사용합니다."
    ) from exc


DEFAULT_FOCAL_COMPANIES: Dict[str, str] = dict(DEFAULT_COMPANIES)


@dataclass
class TechnologyDifferentiationResult:
    company_dir: str
    company_name: str
    technology_differentiation_score: float
    technology_differentiation_percentile: float
    technology_differentiation_grade: str
    component_scores: Dict[str, float]
    nearest_peer: Dict[str, Any]
    peer_similarity_top: List[Dict[str, Any]]
    dominant_topic: Dict[str, Any]
    unique_terms: List[str]
    raw_metrics: Dict[str, Any]
    interpretation: str
    limitations: List[str]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def _ratio(num: float, den: float) -> float:
    den = max(float(den), 1.0)
    return max(0.0, float(num) / den)


def _clip100(x: float) -> float:
    return round(max(0.0, min(100.0, float(x))), 2)


def _company_doc(signal: CompanyPatentSignal) -> str:
    parts: List[str] = []
    if signal.patent_text:
        parts.append(signal.patent_text[:250_000])
    if signal.representative_patents:
        parts.append(" ".join(signal.representative_patents))
    parts.append(signal.company_name)
    parts.extend(COMPANY_ALIASES.get(signal.company_dir, []))
    return " ".join(p for p in parts if p).strip() or signal.company_name or signal.company_dir


def _grade(score: float) -> str:
    if score >= 75:
        return "DISTINCTIVE_TECH_LEADER"
    if score >= 60:
        return "DIFFERENTIATED_TECH_POSITION"
    if score >= 45:
        return "MODERATE_DIFFERENTIATION"
    if score >= 30:
        return "LOW_DIFFERENTIATION"
    return "COMMODITIZED_OR_UNCLEAR"


def _grade_kr(grade: str) -> str:
    return {
        "DISTINCTIVE_TECH_LEADER": "차별화 우위형",
        "DIFFERENTIATED_TECH_POSITION": "차별화 확인형",
        "MODERATE_DIFFERENTIATION": "보통 차별화형",
        "LOW_DIFFERENTIATION": "차별화 약화형",
        "COMMODITIZED_OR_UNCLEAR": "범용/확인 제한형",
    }.get(grade, grade)


# 특허 문서에서 자주 등장하지만 기술 차별성 신호로 보기 어려운 상투어/법률 문구.
# TF-IDF 자체에는 남아 있을 수 있으므로, 최종 top_terms/unique_terms 표시 직전에 한 번 더 제거한다.
GENERIC_PATENT_TERMS = {
    "발명", "본 발명", "본발명", "청구항", "도면", "실시예", "일 실시예", "실시 형태", "형태",
    "기술적", "기술적 사상", "사상", "사상은", "발명의", "발명의 기술적",
    "제공", "제공한다", "제공하는", "포함", "포함한다", "포함하는", "구비", "구비한다",
    "따른", "따라", "의한", "위한", "있다", "된다", "한다", "하도록", "가능하게",
    "이의", "이를", "이러한", "해당", "상기", "상기한", "상기와", "통해", "이용", "이용하여", "사용", "사용하여",
    "방법", "장치", "시스템", "구성", "구조", "단계", "부분", "영역", "측면", "일부",
    "제1", "제2", "제3", "제4", "제5", "복수", "하나", "이상", "이하", "전술한",
}

GENERIC_PATENT_PHRASES = (
    "필름 이를", "필름이를", "패키지를 제공", "패키지를 제공한다", "제공한다", "제공하는",
    "기술적 사상", "사상은", "발명의 기술적", "본 발명", "발명의",
    "따른 패키지는", "패키지 이의", "패키지 발명", "이의 패키지",
    "상기", "청구항", "일 실시예", "실시예", "도면", "구성된다",
)

KOREAN_JOSA_ENDINGS = ("은", "는", "이", "가", "을", "를", "의", "에", "에서", "으로", "로", "와", "과")


def _normalize_display_term(term: Any) -> str:
    s = str(term or "").strip()
    s = " ".join(s.split())
    # 특허 문장형 표현을 발표용 기술어로 약하게 정규화
    replacements = {
        "전기적으로 연결된": "전기적 연결",
        "패키지를": "패키지",
        "패키지는": "패키지",
        "재배선을": "재배선",
        "재배선의": "재배선",
        "도전성의": "도전성",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    # 단독 조사/문장 어미 제거
    parts = []
    for part in s.split():
        p = part.strip()
        for ending in KOREAN_JOSA_ENDINGS:
            if len(p) > len(ending) + 1 and p.endswith(ending):
                p = p[: -len(ending)]
                break
        parts.append(p)
    s = " ".join(parts).strip(" ,.;:()[]{}")
    return s


def _is_informative_display_term(term: Any) -> bool:
    s = _normalize_display_term(term)
    if not s or len(s) < 2:
        return False
    compact = s.replace(" ", "")
    # 너무 일반적인 특허 문구 제거
    if compact in {x.replace(" ", "") for x in GENERIC_PATENT_TERMS}:
        return False
    if any(phrase.replace(" ", "") in compact for phrase in GENERIC_PATENT_PHRASES):
        return False
    # 조사/대명사 조각이 붙은 특허 문장 찌꺼기 제거
    if compact.endswith("이를") and len(compact) <= 6:
        return False
    # 숫자/순번 중심 표현 제거. 단, 재배선·전극 등 기술어와 같이 쓰이면 아래에서 허용될 수 있음.
    if compact in {"제1", "제2", "제3", "제4", "제5"}:
        return False
    if re.fullmatch(r"[0-9]+", compact):
        return False
    # 기술적 의미가 거의 없는 일반 단어만으로 구성된 경우 제거
    generic_tokens = {x.replace(" ", "") for x in GENERIC_PATENT_TERMS}
    token_compacts = [t.replace(" ", "") for t in s.split()]
    if token_compacts and all(t in generic_tokens for t in token_compacts):
        return False
    return True


def _clean_display_terms(terms: Iterable[Any], limit: int = 15) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for term in terms:
        s = _normalize_display_term(term)
        if not _is_informative_display_term(s):
            continue
        key = s.replace(" ", "").lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(s)
        if len(cleaned) >= limit:
            break
    return cleaned


def _build_vectorizer():
    if TfidfVectorizer is None:
        return None
    return TfidfVectorizer(
        max_features=2500,
        min_df=1,
        max_df=0.92,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[\w가-힣A-Za-z0-9\-\+]{2,}\b",
        stop_words=list(set(STOPWORDS) | GENERIC_PATENT_TERMS),
        sublinear_tf=True,
    )


def _tfidf_similarity(signals: Sequence[CompanyPatentSignal]) -> Dict[str, Any]:
    docs = [_company_doc(s) for s in signals]
    slugs = [s.company_dir for s in signals]
    if TfidfVectorizer is None or cosine_similarity is None:
        return {
            "available": False,
            "reason": "scikit-learn 미설치 또는 import 실패",
            "similarity_matrix": {},
            "top_terms": {},
            "unique_terms": {},
            "doc_freq": {},
        }
    if len(docs) < 2:
        return {
            "available": False,
            "reason": "Technology Differentiation Score에는 최소 2개 회사 텍스트가 필요합니다.",
            "similarity_matrix": {},
            "top_terms": {},
            "unique_terms": {},
            "doc_freq": {},
        }
    vectorizer = _build_vectorizer()
    if vectorizer is None:
        return {"available": False, "reason": "vectorizer 생성 실패"}
    try:
        X = vectorizer.fit_transform(docs)
    except Exception as exc:
        return {"available": False, "reason": f"TF-IDF 생성 실패: {exc}"}
    if X.shape[1] < 2:
        return {"available": False, "reason": "유효 TF-IDF token 수 부족"}

    sim = cosine_similarity(X)
    terms = np.array(vectorizer.get_feature_names_out())
    df = np.asarray((X > 0).sum(axis=0)).ravel()

    sim_dict: Dict[str, Dict[str, float]] = {}
    top_terms: Dict[str, List[str]] = {}
    unique_terms: Dict[str, List[str]] = {}
    unique_weights: Dict[str, float] = {}

    for i, slug in enumerate(slugs):
        row = X[i].toarray().ravel()
        order = row.argsort()[::-1]
        raw_top = [str(terms[j]) for j in order[:80] if row[j] > 0]
        raw_uniq = [str(terms[j]) for j in order if row[j] > 0 and df[j] == 1]
        top = _clean_display_terms(raw_top, limit=30)
        uniq = _clean_display_terms(raw_uniq, limit=15)
        uniq_weight_sum = float(sum(row[j] for j in order if row[j] > 0 and df[j] == 1))
        all_weight_sum = float(row.sum()) or 1.0
        top_terms[slug] = top
        unique_terms[slug] = uniq
        unique_weights[slug] = 100.0 * uniq_weight_sum / all_weight_sum
        sim_dict[slug] = {slugs[j]: round(float(sim[i, j]), 4) for j in range(len(slugs))}

    return {
        "available": True,
        "similarity_matrix": sim_dict,
        "top_terms": top_terms,
        "unique_terms": unique_terms,
        "unique_weight_ratio": unique_weights,
        "feature_count": int(X.shape[1]),
    }


def _topic_features(signals: Sequence[CompanyPatentSignal]) -> Dict[str, Any]:
    try:
        nmf = fit_nmf(list(signals), max_topics=5)
    except Exception as exc:
        return {"available": False, "reason": f"NMF 실행 실패: {exc}", "company_topics": {}}
    company_topics = nmf.get("company_topics", {}) if isinstance(nmf, dict) else {}
    dominant_ids: Dict[str, Any] = {}
    for slug, topics in company_topics.items():
        if topics:
            dominant_ids[slug] = topics[0].get("topic_id")
    counts: Dict[Any, int] = {}
    for tid in dominant_ids.values():
        counts[tid] = counts.get(tid, 0) + 1
    return {
        "available": True,
        "method": nmf.get("method") if isinstance(nmf, dict) else "TF-IDF + NMF",
        "topics": nmf.get("topics", []) if isinstance(nmf, dict) else [],
        "company_topics": company_topics,
        "dominant_topic_counts": counts,
        "limitations": nmf.get("limitations", []) if isinstance(nmf, dict) else [],
    }


def _nearest_peers(slug: str, sim_matrix: Dict[str, Dict[str, float]], name_map: Dict[str, str], topn: int = 5) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    row = sim_matrix.get(slug, {})
    peers = []
    for peer_slug, score in row.items():
        if peer_slug == slug:
            continue
        peers.append({
            "company_dir": peer_slug,
            "company_name": name_map.get(peer_slug, peer_slug),
            "cosine_similarity": round(float(score), 4),
            "technology_distance": round(1.0 - float(score), 4),
        })
    peers.sort(key=lambda x: x["cosine_similarity"], reverse=True)
    nearest = peers[0] if peers else {"company_dir": None, "company_name": None, "cosine_similarity": None, "technology_distance": None}
    return nearest, peers[:topn]


def _topic_score(slug: str, topic_pack: Dict[str, Any], total_companies: int) -> Tuple[float, Dict[str, Any]]:
    topics = topic_pack.get("company_topics", {}).get(slug, []) if topic_pack.get("available") else []
    if not topics:
        return 50.0, {"topic_id": None, "topic_label": "확인 제한", "weight": None, "margin": None, "rarity": None}
    first = topics[0]
    second = topics[1] if len(topics) > 1 else {}
    w1 = _safe_float(first.get("weight"), 0.0)
    w2 = _safe_float(second.get("weight"), 0.0)
    margin = max(0.0, w1 - w2)
    topic_id = first.get("topic_id")
    same_count = int(topic_pack.get("dominant_topic_counts", {}).get(topic_id, 1))
    if total_companies <= 1:
        rarity = 50.0
    else:
        rarity = 100.0 * (1.0 - max(0, same_count - 1) / max(1, total_companies - 1))
    score = _clip100(100.0 * (0.45 * w1 + 0.35 * margin) + 0.20 * rarity)
    return score, {
        "topic_id": topic_id,
        "topic_label": first.get("topic_label") or first.get("label") or "확인 제한",
        "weight": round(w1, 4),
        "margin": round(margin, 4),
        "rarity": round(rarity, 2),
    }


def _collect_signals(root: Path, company_dirs: Optional[List[str]], include_empty: bool, all_companies: bool) -> Tuple[List[CompanyPatentSignal], Dict[str, str], List[str]]:
    if company_dirs:
        companies = load_company_list(root, company_dirs)
    elif all_companies:
        companies = load_company_list(root, None)
    else:
        companies = dict(DEFAULT_FOCAL_COMPANIES)

    signals: List[CompanyPatentSignal] = []
    excluded: List[str] = []
    for slug, name in companies.items():
        signal = collect_company_patent_signal(root, slug, name)
        has_data = bool(signal.normalized_patent_records or signal.company_matched_patents or signal.patent_text or signal.representative_patents)
        if has_data or include_empty:
            signals.append(signal)
        else:
            excluded.append(f"{name}({slug}): 특허/KIPRIS 원천 데이터 없음")
    return signals, companies, excluded


def compute_technology_differentiation(signals: Sequence[CompanyPatentSignal], excluded: Optional[List[str]] = None) -> Dict[str, Any]:
    if not signals:
        raise RuntimeError("Technology Differentiation Score를 계산할 회사 데이터가 없습니다.")

    name_map = {s.company_dir: s.company_name for s in signals}
    sim_pack = _tfidf_similarity(signals)
    topic_pack = _topic_features(signals)

    slugs = [s.company_dir for s in signals]
    n = len(signals)

    # Raw peer distance values for percentile scoring
    nearest_distance_raw: Dict[str, float] = {}
    keyword_raw: Dict[str, float] = {}
    ipc_div_raw: Dict[str, float] = {}
    core_ipc_raw: Dict[str, float] = {}
    recent_raw: Dict[str, float] = {}

    for s in signals:
        if sim_pack.get("available"):
            nearest, _ = _nearest_peers(s.company_dir, sim_pack.get("similarity_matrix", {}), name_map)
            dist = _safe_float(nearest.get("technology_distance"), 0.5)
            nearest_distance_raw[s.company_dir] = dist
            keyword_raw[s.company_dir] = _safe_float(sim_pack.get("unique_weight_ratio", {}).get(s.company_dir), 0.0)
        else:
            nearest_distance_raw[s.company_dir] = 0.5
            keyword_raw[s.company_dir] = 50.0
        matched = max(int(s.company_matched_patents or 0), 1)
        ipc_div_raw[s.company_dir] = float(s.ipc_cpc_classes or 0)
        core_ipc_raw[s.company_dir] = _ratio(float(s.core_ipc_h01l_patents or 0), matched)
        recent_raw[s.company_dir] = _ratio(float(s.recent_5y_patents or 0), matched)

    distance_vals = list(nearest_distance_raw.values())
    keyword_vals = list(keyword_raw.values())
    ipc_vals = list(ipc_div_raw.values())
    core_vals = list(core_ipc_raw.values())
    recent_vals = list(recent_raw.values())

    prelim: Dict[str, Dict[str, Any]] = {}
    score_values: List[float] = []

    for s in signals:
        slug = s.company_dir
        nearest, peer_top = _nearest_peers(slug, sim_pack.get("similarity_matrix", {}), name_map) if sim_pack.get("available") else ({"company_dir": None, "company_name": None, "cosine_similarity": None, "technology_distance": None}, [])
        uniqueness_score = percentile_rank(distance_vals, nearest_distance_raw[slug]) if n >= 3 else _clip100(100.0 * nearest_distance_raw[slug])
        keyword_score = percentile_rank(keyword_vals, keyword_raw[slug]) if n >= 3 else _clip100(keyword_raw[slug])
        topic_score, dominant_topic = _topic_score(slug, topic_pack, n)
        ipc_score = _clip100(
            0.50 * (percentile_rank(ipc_vals, ipc_div_raw[slug]) if n >= 3 else min(100.0, ipc_div_raw[slug]))
            + 0.35 * (percentile_rank(core_vals, core_ipc_raw[slug]) if n >= 3 else 100.0 * core_ipc_raw[slug])
            + 0.15 * (percentile_rank(recent_vals, recent_raw[slug]) if n >= 3 else 100.0 * recent_raw[slug])
        )
        final_score = _clip100(0.35 * uniqueness_score + 0.25 * topic_score + 0.20 * ipc_score + 0.20 * keyword_score)
        score_values.append(final_score)
        prelim[slug] = {
            "company_dir": slug,
            "company_name": s.company_name,
            "technology_differentiation_score": final_score,
            "component_scores": {
                "peer_uniqueness_score": round(uniqueness_score, 2),
                "topic_distinctiveness_score": round(topic_score, 2),
                "ipc_specialization_score": round(ipc_score, 2),
                "keyword_uniqueness_score": round(keyword_score, 2),
            },
            "nearest_peer": nearest,
            "peer_similarity_top": peer_top,
            "dominant_topic": dominant_topic,
            "unique_terms": sim_pack.get("unique_terms", {}).get(slug, [])[:12] if sim_pack.get("available") else [],
            "raw_metrics": {
                "normalized_patent_records": s.normalized_patent_records,
                "company_matched_patents": s.company_matched_patents,
                "registered_patents": s.registered_patents,
                "alive_patents": s.alive_patents,
                "recent_5y_patents": s.recent_5y_patents,
                "ipc_cpc_classes": s.ipc_cpc_classes,
                "core_ipc_h01l_patents": s.core_ipc_h01l_patents,
                "patent_keyword_matches": s.patent_keyword_matches,
                "patent_year_min": s.patent_year_min,
                "patent_year_max": s.patent_year_max,
                "source_files": s.source_files,
            },
            "limitations": list(s.limitations),
        }

    results: Dict[str, Any] = {}
    for slug, item in prelim.items():
        pct = percentile_rank(score_values, item["technology_differentiation_score"]) if len(score_values) >= 2 else 50.0
        grade = _grade(item["technology_differentiation_score"])
        peer_name = item["nearest_peer"].get("company_name") or "확인 제한"
        sim_val = item["nearest_peer"].get("cosine_similarity")
        topic_label = item["dominant_topic"].get("topic_label") or "확인 제한"
        item["technology_differentiation_percentile"] = pct
        item["technology_differentiation_grade"] = grade
        item["interpretation"] = (
            f"{item['company_name']}의 Technology Differentiation Score는 "
            f"{item['technology_differentiation_score']}/100, percentile {pct}로 산출되어 "
            f"{_grade_kr(grade)}으로 해석됩니다. 가장 유사한 peer는 {peer_name}"
            f"(cosine similarity={sim_val})이며, 주된 NMF 기술 주제는 '{topic_label}'입니다. "
            "이 점수는 특허/IP 포트폴리오의 차별성 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다."
        )
        results[slug] = item

    return {
        "method": "Technology Differentiation Score = TF-IDF peer distance + NMF topic distinctiveness + IPC specialization + unique-term signal",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "companies": results,
        "universe": {
            "company_count_used": len(signals),
            "company_dirs_used": [s.company_dir for s in signals],
            "excluded": excluded or [],
            "tfidf_available": bool(sim_pack.get("available")),
            "tfidf_feature_count": sim_pack.get("feature_count"),
            "nmf_method": topic_pack.get("method"),
        },
        "score_weights": {
            "peer_uniqueness_score": 0.35,
            "topic_distinctiveness_score": 0.25,
            "ipc_specialization_score": 0.20,
            "keyword_uniqueness_score": 0.20,
        },
        "notes": [
            "미래 수익률 예측이 아니라 특허/IP 포트폴리오가 peer 대비 얼마나 다른지를 설명하는 비지도 ML 기반 차별화 점수입니다.",
            "표본이 5개일 때는 percentile 해석이 거칠 수 있으므로, 30개 reference universe 확장 시 더 안정적으로 사용합니다.",
        ],
    }


def render_markdown(all_result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Technology Differentiation Score")
    lines.append("")
    lines.append(f"- 생성 시각: {all_result.get('created_at', '')}")
    lines.append(f"- 방법론: {all_result.get('method', '')}")
    lines.append("- 해석 원칙: 미래 수익률 예측이 아니라 특허/IP 포트폴리오의 peer-relative 차별성을 설명하는 비지도 ML 신호입니다.")
    lines.append("")
    lines.append("## 1. 회사별 Technology Differentiation Score")
    lines.append("")
    lines.append("| 기업 | Differentiation Score | Percentile | Grade | Nearest peer | Similarity | Dominant topic |")
    lines.append("|---|---:|---:|---|---|---:|---|")
    rows = sorted(all_result.get("companies", {}).items(), key=lambda kv: kv[1].get("technology_differentiation_score", 0), reverse=True)
    for _, r in rows:
        nearest = r.get("nearest_peer", {}) or {}
        topic = r.get("dominant_topic", {}) or {}
        lines.append(
            f"| {r.get('company_name')} | {r.get('technology_differentiation_score')} | "
            f"{r.get('technology_differentiation_percentile')} | {r.get('technology_differentiation_grade')} | "
            f"{nearest.get('company_name') or '확인 제한'} | {nearest.get('cosine_similarity')} | "
            f"{topic.get('topic_label') or '확인 제한'} |"
        )
    lines.append("")
    lines.append("## 2. Component Scores")
    lines.append("")
    lines.append("| 기업 | Peer uniqueness | Topic distinctiveness | IPC specialization | Keyword uniqueness |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in rows:
        c = r.get("component_scores", {}) or {}
        lines.append(
            f"| {r.get('company_name')} | {c.get('peer_uniqueness_score')} | {c.get('topic_distinctiveness_score')} | "
            f"{c.get('ipc_specialization_score')} | {c.get('keyword_uniqueness_score')} |"
        )
    lines.append("")
    lines.append("## 3. 해석상 주의")
    lines.append("")
    lines.append("- Technology Differentiation Score는 '좋은 기업' 점수가 아니라, peer 대비 기술/IP 포트폴리오가 얼마나 구별되는지 보는 점수입니다.")
    lines.append("- 점수가 높더라도 양산, 고객 채택, 매출 전환, FCF 개선 근거가 약하면 Chair는 보수적으로 반영해야 합니다.")
    lines.append("- 5개 기업 기준 결과는 데모/파일럿이며, 30개 reference universe로 확장할수록 percentile 해석력이 좋아집니다.")
    excluded = all_result.get("universe", {}).get("excluded") or []
    if excluded:
        lines.append("")
        lines.append("## 4. 제외/확인 제한")
        for e in excluded[:30]:
            lines.append(f"- {e}")
    return "\n".join(lines) + "\n"


def save_company_packets(root: Path, all_result: Dict[str, Any]) -> None:
    for slug, result in all_result.get("companies", {}).items():
        packet_dir = company_agent_dir(slug, "tech")
        ensure_dir(packet_dir)
        write_json(packet_dir / "tech_differentiation.json", result)
        write_json(agent_output_path(slug, "tech", f"{slug}_tech_differentiation.json", root=root), result)


def run_technology_differentiation(
    root: Optional[Path] = None,
    company_dirs: Optional[List[str]] = None,
    all_companies: bool = False,
    include_empty: bool = False,
    save: bool = True,
) -> Dict[str, Any]:
    root = find_project_root(root)
    signals, _, excluded = _collect_signals(root, company_dirs, include_empty=include_empty, all_companies=all_companies)
    if len(signals) < 2:
        raise RuntimeError("Technology Differentiation Score에는 최소 2개 회사의 특허/IP 데이터가 필요합니다.")
    result = compute_technology_differentiation(signals, excluded=excluded)
    if save:
        out = shared_output_dir("tech", root=root)
        ensure_dir(out)
        write_json(out / "tech_differentiation_all.json", result)
        write_text(out / "tech_differentiation.md", render_markdown(result))
        save_company_packets(root, result)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Technology Differentiation Score")
    parser.add_argument("--root", default=None)
    parser.add_argument("--company-dir", action="append", default=None, help="분석할 회사 slug. 여러 번 사용 가능")
    parser.add_argument("--all", action="store_true", help="reference universe 후보까지 읽되 특허 원천 데이터 없는 기업은 기본 제외")
    parser.add_argument("--include-empty", action="store_true", help="특허 원천 데이터가 없는 기업도 포함")
    args = parser.parse_args(argv)

    root = find_project_root(Path(args.root)) if args.root else find_project_root()
    result = run_technology_differentiation(
        root=root,
        company_dirs=args.company_dir,
        all_companies=args.all,
        include_empty=args.include_empty,
        save=True,
    )
    print(f"[Tech Differentiation] 저장 완료: {shared_output_dir('tech', root=root) / 'tech_differentiation_all.json'}")
    print(f"[Tech Differentiation] 저장 완료: {shared_output_dir('tech', root=root) / 'tech_differentiation.md'}")
    print(f"[Tech Differentiation] companies={len(result.get('companies', {}))}")
    for slug, item in result.get("companies", {}).items():
        print(
            f"  - {item.get('company_name')}({slug}): "
            f"diff={item.get('technology_differentiation_score')}/100, "
            f"percentile={item.get('technology_differentiation_percentile')}, "
            f"grade={item.get('technology_differentiation_grade')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

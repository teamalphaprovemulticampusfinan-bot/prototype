from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any, Dict, List, Optional, Sequence

from common.output_paths import agent_output_dir, agent_output_path, shared_output_dir

import numpy as np

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:  # pragma: no cover
    NMF = None
    TfidfVectorizer = None

DEFAULT_COMPANIES: Dict[str, str] = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}

COMPANY_ALIASES: Dict[str, List[str]] = {
    "nepes": ["네패스", "nepes", "nepes corporation"],
    "hanmi": ["한미반도체", "hanmi semiconductor", "hanmi"],
    "hansol": ["한솔케미칼", "hansol chemical", "hansol"],
    "duksan": ["덕산테코피아", "duksan techopia", "duksan"],
    "ltc": ["엘티씨", "ltc"],
}

STOPWORDS = sorted({
    "상기", "포함", "포함하는", "이용", "이용한", "방법", "장치", "시스템", "제조", "제조방법",
    "제공", "관련", "구성", "형성", "기판", "반도체", "소자", "있다", "위한", "하는", "및",
    "또는", "통해", "기술", "발명", "본", "실시", "예", "단계", "부분", "주식회사",
    "있으며", "가능", "다수", "대상", "경우", "것을", "등을", "으로", "에서", "대한",
    "the", "and", "or", "of", "for", "with", "using", "method", "device", "system",
    "apparatus", "semiconductor", "substrate", "forming", "manufacturing",
    "provided", "includes", "including", "thereof", "therein", "present",
    "invention", "example", "embodiment", "plurality", "portion", "unit",
    "configured", "comprising", "based", "related", "technology", "company",
})

TEXT_HINTS = ["title", "invention", "발명의 명칭", "명칭", "제목", "abstract", "요약", "요약서", "대표청구항", "청구항", "claim", "description", "초록", "키워드", "keyword"]
APPLICANT_HINTS = ["applicant", "출원인", "권리자", "assignee", "owner", "applicants", "출원인명"]
STATUS_HINTS = ["status", "상태", "등록상태", "법적상태", "registration", "등록", "권리상태"]
DATE_HINTS = ["application_date", "출원일", "출원일자", "apply_date", "filing_date", "date", "publication_date", "공개일", "등록일"]
IPC_HINTS = ["ipc", "cpc", "ipc/cpc", "ipc_cpc", "국제특허분류", "분류", "classification"]


@dataclass
class CompanyPatentSignal:
    company_dir: str
    company_name: str
    source_files: List[str]
    normalized_patent_records: int
    company_matched_patents: int
    registered_patents: int
    alive_patents: int
    recent_5y_patents: int
    ipc_cpc_classes: int
    core_ipc_h01l_patents: int
    patent_keyword_matches: int
    patent_year_min: Optional[int]
    patent_year_max: Optional[int]
    representative_patents: List[str]
    patent_text: str
    limitations: List[str]


@dataclass
class TechIPMLResult:
    company_dir: str
    company_name: str
    tech_ip_strength_index: float
    tech_ip_strength_percentile: float
    tech_ip_grade: str
    feature_scores: Dict[str, float]
    raw_metrics: Dict[str, Any]
    dominant_topics: List[Dict[str, Any]]
    patent_momentum_score: float
    interpretation: str
    limitations: List[str]


def find_project_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "main.py").exists() and (path / "src").exists():
            return path
    return cur


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def norm_text(x: Any) -> str:
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x).strip())


def is_mojibake(text: str) -> bool:
    return any(m in text for m in ["�", "媛", "泥", "ㅽ", "뙣", "떒", "諛", "덉"])


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)):
            return None
        return float(value)
    s = str(value).replace(",", "").replace("%", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_year(value: Any) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", str(value or ""))
    if not m:
        return None
    y = int(m.group(0))
    return y if 1900 <= y <= datetime.now().year + 1 else None


def read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [dict(r) for r in csv.DictReader(f)]
        except Exception:
            pass
    if pd is not None:
        for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                return pd.read_csv(path, encoding=enc).fillna("").to_dict(orient="records")
            except Exception:
                pass
    return []


def read_xlsx_rows(path: Path) -> List[Dict[str, Any]]:
    if pd is None:
        return []
    try:
        return pd.read_excel(path).fillna("").to_dict(orient="records")
    except Exception:
        return []


def find_columns(row: Dict[str, Any], hints: Sequence[str]) -> List[str]:
    found: List[str] = []
    for key in row.keys():
        lk = str(key).lower()
        if any(h.lower() in lk for h in hints):
            found.append(key)
    return found


def value_from_columns(row: Dict[str, Any], columns: Sequence[str]) -> str:
    vals = [norm_text(row.get(c)) for c in columns if norm_text(row.get(c))]
    vals = [v for v in vals if not is_mojibake(v)]
    return " ".join(vals)


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def discover_patent_source_files(root: Path, company_dir: str) -> List[Path]:
    search_dirs = [
        tech_source_dir(company_dir),
        agent_output_dir(company_dir, "tech", root=root),
        field_agent_dir("tech"),
        company_agent_dir(company_dir, "tech"),
    ]
    patterns = [
        "**/*patent*.csv", "**/*patent*.xlsx", "**/*kipris*.csv", "**/*kipris*.xlsx",
        f"**/{company_dir}*patent*.json", f"**/{company_dir}*kipris*.json",
        f"{company_dir}_tech_patent_evidence.json",
    ]
    out: List[Path] = []
    seen = set()
    for d in search_dirs:
        if not d.exists():
            continue
        for pat in patterns:
            for p in d.glob(pat):
                rp = p.resolve()
                if p.is_file() and rp not in seen:
                    seen.add(rp)
                    out.append(p)
    return out


def extract_metrics_from_json(data: Any) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    if not isinstance(data, dict):
        return metrics
    items = list(data.items())
    for key in ["metrics", "summary", "patent_summary", "signals", "result"]:
        if isinstance(data.get(key), dict):
            items.extend(data[key].items())
    key_map = {
        "normalized_patent_records": ["normalized", "record"],
        "company_matched_patents": ["company", "match"],
        "registered_patents": ["registered"],
        "alive_patents": ["alive"],
        "recent_5y_patents": ["recent", "5"],
        "ipc_cpc_classes": ["ipc"],
        "core_ipc_h01l_patents": ["h01l"],
        "patent_keyword_matches": ["keyword", "match"],
        "patent_year_min": ["year", "min"],
        "patent_year_max": ["year", "max"],
    }
    for target, hints in key_map.items():
        for k, v in items:
            lk = str(k).lower()
            if all(h in lk for h in hints):
                num = to_float(v)
                if num is not None:
                    metrics[target] = int(num)
                break
    reps = data.get("representative_patents") or data.get("examples") or data.get("대표특허")
    if isinstance(reps, list):
        metrics["representative_patents"] = [norm_text(x) for x in reps if norm_text(x)][:5]
    return metrics


def collect_company_patent_signal(root: Path, company_dir: str, company_name: str) -> CompanyPatentSignal:
    aliases = [a.lower() for a in COMPANY_ALIASES.get(company_dir, [company_name, company_dir])]
    files = discover_patent_source_files(root, company_dir)
    all_rows: List[Dict[str, Any]] = []
    json_metrics: Dict[str, Any] = {}
    source_files: List[str] = []
    limitations: List[str] = []

    for path in files:
        source_files.append(relpath(path, root))
        if path.suffix.lower() == ".json":
            try:
                json_metrics.update(extract_metrics_from_json(read_json(path)))
            except Exception as exc:
                limitations.append(f"{path.name} JSON 읽기 실패: {exc}")
        elif path.suffix.lower() == ".csv":
            all_rows.extend(read_csv_rows(path))
        elif path.suffix.lower() in [".xlsx", ".xls"]:
            all_rows.extend(read_xlsx_rows(path))

    if not files:
        limitations.append("특허/KIPRIS 원천 파일을 찾지 못했습니다.")

    company_rows: List[Dict[str, Any]] = []
    years: List[int] = []
    ipc_classes: set[str] = set()
    reps: List[str] = []
    texts: List[str] = []
    registered = alive = recent = h01l = 0
    current_year = datetime.now().year
    recent_cutoff = current_year - 4

    for row in all_rows:
        app_cols = find_columns(row, APPLICANT_HINTS)
        status_cols = find_columns(row, STATUS_HINTS)
        date_cols = find_columns(row, DATE_HINTS)
        ipc_cols = find_columns(row, IPC_HINTS)
        text_cols = find_columns(row, TEXT_HINTS)
        row_all = " ".join(norm_text(v) for v in row.values())
        applicant = value_from_columns(row, app_cols) if app_cols else row_all
        matched = any(alias and alias in applicant.lower() for alias in aliases) if app_cols else True
        if not matched:
            continue
        company_rows.append(row)

        status = value_from_columns(row, status_cols) if status_cols else row_all
        if "등록" in status or "registered" in status.lower():
            registered += 1
        if not any(x in status.lower() for x in ["소멸", "만료", "거절", "취하", "포기", "abandon", "reject", "expire", "withdraw"]):
            alive += 1
        year = None
        for c in date_cols:
            year = parse_year(row.get(c))
            if year:
                break
        if year:
            years.append(year)
            if year >= recent_cutoff:
                recent += 1
        ipc_text = value_from_columns(row, ipc_cols) if ipc_cols else row_all
        for code in re.findall(r"[A-HY]\d{2}[A-Z]?", ipc_text.upper()):
            ipc_classes.add(code)
        if "H01L" in ipc_text.upper():
            h01l += 1
        text = value_from_columns(row, text_cols) if text_cols else row_all
        if text and not is_mojibake(text):
            texts.append(text)
        title_cols = [c for c in text_cols if any(h in str(c).lower() for h in ["title", "명칭", "제목", "invention"])]
        title = value_from_columns(row, title_cols) if title_cols else ""
        if title and title not in reps:
            reps.append(title[:120])

    patent_text = " ".join(texts)
    keyword_matches = 0
    for kw in ["WLP", "FOWLP", "PLP", "Bumping", "패키징", "후공정", "HBM", "TSV", "반도체", "소재", "전구체", "세정", "식각"]:
        keyword_matches += len(re.findall(re.escape(kw), patent_text, flags=re.IGNORECASE))

    def fill(name: str, parsed: int) -> int:
        return int(parsed) if parsed > 0 else int(json_metrics.get(name, 0) or 0)

    normalized = fill("normalized_patent_records", len(all_rows))
    matched = fill("company_matched_patents", len(company_rows))
    registered = fill("registered_patents", registered)
    alive = fill("alive_patents", alive)
    recent = fill("recent_5y_patents", recent)
    ipc_count = fill("ipc_cpc_classes", len(ipc_classes))
    h01l = fill("core_ipc_h01l_patents", h01l)
    keyword_matches = fill("patent_keyword_matches", keyword_matches)
    year_min = min(years) if years else json_metrics.get("patent_year_min")
    year_max = max(years) if years else json_metrics.get("patent_year_max")
    reps = reps[:5] or json_metrics.get("representative_patents", [])[:5]

    if matched == 0 and normalized > 0:
        limitations.append("출원인/권리자 매칭 컬럼이 부족하여 회사 매칭 정확도 확인이 필요합니다.")
    if not patent_text:
        limitations.append("NMF topic modeling에 사용할 특허 텍스트가 부족합니다.")

    return CompanyPatentSignal(company_dir, company_name, source_files, normalized, matched, registered, alive, recent, ipc_count, h01l, keyword_matches, int(year_min) if year_min else None, int(year_max) if year_max else None, reps, patent_text[:200000], limitations)


def ratio(n: float, d: float) -> float:
    return 0.0 if d <= 0 else float(n) / float(d)


def percentile_rank(values: List[float], value: float) -> float:
    if not values:
        return 50.0
    arr = np.array(values, dtype=float)
    if len(arr) == 1:
        return 50.0
    less = float(np.sum(arr < value))
    equal = float(np.sum(arr == value))
    return round(100.0 * (less + 0.5 * equal) / len(arr), 2)


def patent_momentum(signal: CompanyPatentSignal) -> float:
    recent_ratio = ratio(signal.recent_5y_patents, max(signal.company_matched_patents, 1))
    recency_bonus = 0.0
    if signal.patent_year_max:
        age = max(0, datetime.now().year - signal.patent_year_max)
        recency_bonus = max(0.0, 1.0 - age / 10.0)
    return round(max(0.0, min(100.0, 100.0 * (0.75 * recent_ratio + 0.25 * recency_bonus))), 2)


def build_features(signals: List[CompanyPatentSignal]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for s in signals:
        matched = max(s.company_matched_patents, 1)
        out[s.company_dir] = {
            "patent_scale": math.log1p(max(s.company_matched_patents, 0)),
            "registered_ratio": ratio(s.registered_patents, matched),
            "alive_ratio": ratio(s.alive_patents, matched),
            "recent_ratio": ratio(s.recent_5y_patents, matched),
            "ipc_diversity": math.log1p(max(s.ipc_cpc_classes, 0)),
            "keyword_density": ratio(s.patent_keyword_matches, matched),
            "core_ipc_ratio": ratio(s.core_ipc_h01l_patents, matched),
            "patent_momentum": patent_momentum(s) / 100.0,
        }
    return out


def compute_strength(signals: List[CompanyPatentSignal]) -> Dict[str, Dict[str, Any]]:
    features = build_features(signals)
    weights = {"patent_scale": 0.12, "registered_ratio": 0.14, "alive_ratio": 0.12, "recent_ratio": 0.16, "ipc_diversity": 0.18, "keyword_density": 0.12, "core_ipc_ratio": 0.08, "patent_momentum": 0.08}
    norm: Dict[str, Dict[str, float]] = defaultdict(dict)
    for fname in weights:
        vals = [features[s.company_dir][fname] for s in signals]
        cap = max(max(vals), 1.0)
        for s in signals:
            v = features[s.company_dir][fname]
            norm[s.company_dir][fname] = percentile_rank(vals, v) if len(signals) >= 3 else round(max(0.0, min(100.0, 100.0 * v / cap)), 2)
    scores: Dict[str, Dict[str, Any]] = {}
    all_scores: List[float] = []
    for s in signals:
        score = round(sum(norm[s.company_dir][k] * w for k, w in weights.items()), 2)
        all_scores.append(score)
        scores[s.company_dir] = {"tech_ip_strength_index": score, "feature_scores": {k: round(v, 2) for k, v in norm[s.company_dir].items()}, "patent_momentum_score": patent_momentum(s)}
    for s in signals:
        score = scores[s.company_dir]["tech_ip_strength_index"]
        pct = percentile_rank(all_scores, score)
        grade = "STRONG_IP_POSITION" if score >= 80 else "ABOVE_AVERAGE_IP_POSITION" if score >= 65 else "MID_IP_POSITION" if score >= 50 else "WEAK_OR_INSUFFICIENT_IP_EVIDENCE"
        scores[s.company_dir]["tech_ip_strength_percentile"] = pct
        scores[s.company_dir]["tech_ip_grade"] = grade
    return scores


def fit_nmf(signals: List[CompanyPatentSignal], max_topics: int = 5) -> Dict[str, Any]:
    docs, dirs = [], []
    for s in signals:
        text = s.patent_text or " ".join(s.representative_patents)
        if len(text) >= 5:
            docs.append(text)
            dirs.append(s.company_dir)
    if TfidfVectorizer is None or NMF is None:
        return {"method": "NMF unavailable", "topics": [], "company_topics": {}, "limitations": ["scikit-learn 미설치로 NMF를 실행하지 못했습니다."]}
    if len(docs) < 2:
        return {"method": "TF-IDF + NMF", "topics": [], "company_topics": {}, "limitations": ["NMF에는 최소 2개 회사 텍스트가 필요합니다."]}
    vectorizer = TfidfVectorizer(max_features=1200, min_df=1, max_df=0.95, ngram_range=(1, 2), token_pattern=r"(?u)\b[\w가-힣A-Za-z0-9\-\+]{2,}\b", stop_words=STOPWORDS)
    X = vectorizer.fit_transform(docs)
    if X.shape[1] < 2:
        return {"method": "TF-IDF + NMF", "topics": [], "company_topics": {}, "limitations": ["유효 토큰 부족으로 NMF를 수행하지 못했습니다."]}
    n_components = max(2, min(max_topics, len(docs), X.shape[1] - 1))
    model = NMF(n_components=n_components, init="nndsvda", random_state=42, max_iter=600, alpha_W=0.0005, alpha_H=0.0005, l1_ratio=0.0)
    W = model.fit_transform(X)
    H = model.components_
    terms = np.array(vectorizer.get_feature_names_out())
    topics = []
    for idx, comp in enumerate(H):
        top_idx = comp.argsort()[::-1][:10]
        top_terms = [terms[i] for i in top_idx if terms[i].strip()]
        topics.append({"topic_id": int(idx), "label": " / ".join(top_terms[:4]) if top_terms else f"Topic {idx}", "top_terms": top_terms})
    company_topics: Dict[str, List[Dict[str, Any]]] = {}
    for row_idx, slug in enumerate(dirs):
        weights = W[row_idx]
        total = float(weights.sum()) or 1.0
        order = weights.argsort()[::-1]
        company_topics[slug] = [{"topic_id": int(i), "topic_label": topics[int(i)]["label"], "weight": round(float(weights[i] / total), 4)} for i in order[:3]]
    return {"method": "TF-IDF + NMF", "topics": topics, "company_topics": company_topics, "limitations": []}


def build_interpretation(base: Dict[str, Any], signal: CompanyPatentSignal, topics: List[Dict[str, Any]]) -> str:
    score = base["tech_ip_strength_index"]
    pct = base["tech_ip_strength_percentile"]
    grade = base["tech_ip_grade"]
    topic = topics[0]["topic_label"] if topics else "주요 topic 확인 제한"
    level = {"STRONG_IP_POSITION": "강한 IP 포지션", "ABOVE_AVERAGE_IP_POSITION": "평균 이상 IP 포지션", "MID_IP_POSITION": "중간 수준 IP 포지션"}.get(grade, "근거 보강 필요 IP 포지션")
    return f"{signal.company_name}의 Tech/IP Strength Index는 {score}/100, percentile {pct}로 산출되어 {level}으로 해석됩니다. NMF 기준 주된 기술 주제는 '{topic}'입니다. 단, 이 지표는 기술/IP 포트폴리오 상대 강도 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다."


def create_results(signals: List[CompanyPatentSignal]) -> Dict[str, Any]:
    strength = compute_strength(signals)
    nmf = fit_nmf(signals)
    results: Dict[str, Any] = {}
    for s in signals:
        topics = nmf.get("company_topics", {}).get(s.company_dir, [])
        raw = asdict(s)
        raw.pop("patent_text", None)
        base = strength[s.company_dir]
        result = TechIPMLResult(s.company_dir, s.company_name, base["tech_ip_strength_index"], base["tech_ip_strength_percentile"], base["tech_ip_grade"], base["feature_scores"], raw, topics, base["patent_momentum_score"], build_interpretation(base, s, topics), list(s.limitations) + list(nmf.get("limitations", [])))
        results[s.company_dir] = asdict(result)
    return {"method": "Tech/IP Strength Index + TF-IDF NMF Topic Modeling", "created_at": datetime.now().isoformat(timespec="seconds"), "companies": results, "topics": nmf.get("topics", []), "notes": ["미래 수익률 예측이 아니라 특허/IP 포트폴리오 기반 설명가능 기술 ML 신호입니다.", "Tech/IP Strength Index는 reference universe 내부 상대 점수입니다."]}


def load_company_list(root: Path, company_dirs: Optional[List[str]] = None) -> Dict[str, str]:
    if company_dirs:
        return {slug: DEFAULT_COMPANIES.get(slug, slug) for slug in company_dirs}
    companies = dict(DEFAULT_COMPANIES)
    csv_path = ml_universe_dir() / "deeptech_reference_universe.csv"
    if csv_path.exists():
        for r in read_csv_rows(csv_path):
            slug = norm_text(r.get("company_dir") or r.get("slug") or r.get("company_slug"))
            name = norm_text(r.get("company_name") or r.get("corp_name") or r.get("name"))
            if slug:
                companies.setdefault(slug, name or slug)
    return companies


def render_markdown(all_result: Dict[str, Any]) -> str:
    lines = ["# Tech/IP Strength Index + NMF Topic Modeling", "", f"- 생성 시각: {all_result.get('created_at', '')}", f"- 방법론: {all_result.get('method', '')}", "- 해석 원칙: 미래 수익률 예측이 아니라 딥테크 특허/IP 포트폴리오의 상대 강도와 기술 주제 집중도를 설명하는 ML 신호입니다.", "", "## 1. 회사별 Tech/IP Strength Index", "", "| 기업 | Tech/IP Strength | Percentile | Grade | Patent Momentum | Dominant NMF Topic |", "|---|---:|---:|---|---:|---|"]
    for _, r in sorted(all_result.get("companies", {}).items(), key=lambda kv: kv[1].get("tech_ip_strength_index", 0), reverse=True):
        topic = (r.get("dominant_topics") or [{}])[0].get("topic_label", "확인 제한")
        lines.append(f"| {r.get('company_name')} | {r.get('tech_ip_strength_index')} | {r.get('tech_ip_strength_percentile')} | {r.get('tech_ip_grade')} | {r.get('patent_momentum_score')} | {topic} |")
    lines += ["", "## 2. NMF Topic Dictionary", ""]
    topics = all_result.get("topics", [])
    if topics:
        lines += ["| Topic | Label | Top terms |", "|---:|---|---|"]
        for t in topics:
            lines.append(f"| {t.get('topic_id')} | {t.get('label')} | {', '.join(t.get('top_terms', [])[:10])} |")
    else:
        lines.append("- NMF topic dictionary를 생성하지 못했습니다. 특허 텍스트 또는 scikit-learn 설치 상태를 확인하세요.")
    lines += ["", "## 3. 해석상 주의", "", "- 특허 수, topic weight, IP strength는 기술/IP 포트폴리오의 상대 신호입니다.", "- 고객 채택, 양산, 매출 전환, FCF 개선 근거가 확인되지 않으면 가치평가 가산 요인으로 과대해석하지 않습니다."]
    return "\n".join(lines) + "\n"


def save_company_packets(root: Path, all_result: Dict[str, Any]) -> None:
    for slug, result in all_result.get("companies", {}).items():
        packet_dir = company_agent_dir(slug, "tech")
        ensure_dir(packet_dir)
        write_json(packet_dir / "tech_ip_ml.json", result)
        write_json(agent_output_path(slug, "tech", f"{slug}_tech_ip_ml.json", root=root), result)


def run_tech_ip_ml(root: Optional[Path] = None, company_dirs: Optional[List[str]] = None, save: bool = True) -> Dict[str, Any]:
    root = find_project_root(root)
    companies = load_company_list(root, company_dirs)
    signals = [collect_company_patent_signal(root, slug, name) for slug, name in companies.items()]
    if not signals:
        raise RuntimeError("분석할 회사가 없습니다.")
    result = create_results(signals)
    if save:
        out = shared_output_dir("tech", root=root)
        write_json(out / "tech_ip_strength_all.json", result)
        write_text(out / "tech_ip_strength.md", render_markdown(result))
        save_company_packets(root, result)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Tech/IP Strength Index + NMF Topic Modeling")
    parser.add_argument("--root", default=None)
    parser.add_argument("--company-dir", action="append", default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    root = find_project_root(Path(args.root)) if args.root else find_project_root()
    result = run_tech_ip_ml(root=root, company_dirs=args.company_dir, save=True)
    print(f"[Tech/IP ML] 저장 완료: {shared_output_dir('tech', root=root) / 'tech_ip_strength_all.json'}")
    print(f"[Tech/IP ML] 저장 완료: {shared_output_dir('tech', root=root) / 'tech_ip_strength.md'}")
    print(f"[Tech/IP ML] companies={len(result.get('companies', {}))}")
    for slug, item in result.get("companies", {}).items():
        print(f"  - {item.get('company_name')}({slug}): strength={item.get('tech_ip_strength_index')}/100, percentile={item.get('tech_ip_strength_percentile')}, grade={item.get('tech_ip_grade')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

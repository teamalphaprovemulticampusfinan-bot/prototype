from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml


MOJIBAKE_CHARS = ["â", "ã", "ì", "ë", "ê", "Â", "Ã", "�"]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def try_fix_mojibake(text: str) -> str:
    if not text:
        return ""
    raw = str(text)

    if not looks_mojibake(raw):
        return raw

    # 가장 흔한 latin1 -> utf8 깨짐 복구
    try:
        fixed = raw.encode("latin1").decode("utf-8")
        if score_readability(fixed) >= score_readability(raw):
            return fixed
    except Exception:
        pass

    # cp1252 -> utf8 계열
    try:
        fixed = raw.encode("cp1252", errors="ignore").decode("utf-8", errors="ignore")
        if fixed and score_readability(fixed) >= score_readability(raw):
            return fixed
    except Exception:
        pass

    return raw


def score_readability(text: str) -> int:
    if not text:
        return 0
    score = 0
    score += len(re.findall(r"[가-힣]", text)) * 3
    score += len(re.findall(r"[A-Za-z0-9]", text))
    score -= sum(text.count(ch) for ch in MOJIBAKE_CHARS) * 5
    return score


def clean_text(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    s = try_fix_mojibake(s)
    s = s.replace("\u00a0", " ")
    s = s.replace("\u200b", " ")
    s = s.replace("\ufeff", " ")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def best_effort_decode(content: bytes, preferred: str | None = None) -> str:
    encodings = []
    if preferred:
        encodings.append(preferred)
    encodings.extend(["utf-8", "utf-8-sig", "cp949", "euc-kr", "latin1"])

    for enc in encodings:
        try:
            return content.decode(enc)
        except Exception:
            continue

    return content.decode("utf-8", errors="ignore")


def looks_mojibake(text: str) -> bool:
    if not text:
        return False
    s = str(text)
    hits = sum(s.count(ch) for ch in MOJIBAKE_CHARS)
    if hits >= 8:
        return True
    weird_ratio = hits / max(len(s), 1)
    return weird_ratio > 0.02


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    s = clean_text(text)
    # 한국어/영문 혼합 문장 분리
    parts = re.split(r"(?<=[\.\?\!。])\s+|(?<=다\.)\s+|(?<=요\.)\s+", s)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def keyword_score(text: str, keywords: list[str]) -> int:
    if not text:
        return 0
    lowered = text.lower()
    score = 0
    for kw in keywords:
        kw = clean_text(kw)
        if not kw:
            continue
        score += lowered.count(kw.lower())
    return score


def pick_sentences(text: str, keywords: list[str], top_k: int = 4) -> list[str]:
    sents = split_sentences(text)
    scored = []
    for sent in sents:
        score = keyword_score(sent, keywords)
        if score > 0:
            scored.append((score, sent))
    scored.sort(key=lambda x: (x[0], len(x[1])), reverse=True)

    picked = []
    seen = set()
    for _, sent in scored:
        key = sent[:120]
        if key in seen:
            continue
        seen.add(key)
        picked.append(sent)
        if len(picked) >= top_k:
            break
    return picked


def extract_first_json(text: str) -> dict | None:
    if not text:
        return None

    raw = text.strip()

    # ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)

    # 그냥 첫 JSON object 찾기
    if not raw.startswith("{"):
        obj_match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if obj_match:
            raw = obj_match.group(1)

    try:
        return json.loads(raw)
    except Exception:
        pass

    # trailing comma 등 아주 약한 정리
    try:
        raw2 = re.sub(r",\s*([}\]])", r"\1", raw)
        return json.loads(raw2)
    except Exception:
        return None


def trim(text: Any, max_len: int = 200) -> str:
    s = clean_text(text)
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def has_meaningful_text(text: str) -> bool:
    s = clean_text(text)
    if not s:
        return False
    bad_tokens = [
        "공시상 미제시",
        "직접 확인 제한",
        "확인 제한",
        "정보 없음",
        "미상",
    ]
    return s not in bad_tokens and len(s) >= 3


def contains_number(text: str) -> bool:
    return bool(re.search(r"\d", clean_text(text)))


def safe_filename(name: str) -> str:
    s = clean_text(name).lower()
    s = re.sub(r"[^a-z0-9가-힣_-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "company"


def listify(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

def company_aliases(name: str) -> list[str]:
    s = clean_text(name)
    if not s:
        return []

    aliases = {
        s,
        s.replace("(주)", "").strip(),
        s.replace("주식회사", "").strip(),
        s.replace("㈜", "").strip(),
        s.replace(" ", ""),
    }

    cleaned = set()
    for a in aliases:
        a = clean_text(a)
        if a:
            cleaned.add(a)

    return sorted(cleaned)


def guess_doc_kind_from_url(url: str) -> str:
    u = clean_text(url).lower()
    if not u:
        return "unknown"

    if "dart" in u or "report" in u or "businessreport" in u:
        return "report"
    if "ir" in u or "investor" in u:
        return "ir"
    if "news" in u or "article" in u:
        return "news"
    if "recruit" in u or "career" in u:
        return "recruit"
    return "homepage"


def extract_json_block(text: str) -> dict | None:
    return extract_first_json(text)
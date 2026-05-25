from __future__ import annotations

import re
import unicodedata
from typing import Any


_HANGUL_RE = re.compile(r"[가-힣]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_REPLACEMENT_RE = re.compile(r"[�]")
_NOISE_RE = re.compile(
    r"(媛|쒕|덈|섎|뒿|毓|蹂|諛|泥|湲|怨|援|寃|곌|쑝|댁|뺤|쟾|룄|룞|뚯|묒|쭠)"
)


def _score_text(s: str) -> int:
    if not s:
        return -10_000

    hangul = len(_HANGUL_RE.findall(s))
    cjk = len(_CJK_RE.findall(s))
    repl = len(_REPLACEMENT_RE.findall(s))
    noise = len(_NOISE_RE.findall(s))
    ascii_letters = len(re.findall(r"[A-Za-z0-9]", s))

    # 한국어 문서에서는 한글 비중이 높고, 이상한 한자/깨짐 문자가 낮아야 한다.
    return hangul * 5 + ascii_letters - cjk * 2 - repl * 20 - noise * 12


def repair_mojibake_text(value: Any) -> Any:
    """
    UTF-8 한국어가 CP949/EUC-KR로 잘못 해석되어 생긴 깨짐을 복구한다.
    예: '諛섎룄泥?' -> '반도체'
    """
    if not isinstance(value, str):
        return value

    original = unicodedata.normalize("NFC", value).replace("\x00", "")
    if not original:
        return original

    candidates = {original}

    # UTF-8 bytes를 CP949/EUC-KR로 잘못 읽은 경우 복원
    for enc in ("cp949", "euc-kr"):
        try:
            candidates.add(original.encode(enc, errors="ignore").decode("utf-8", errors="ignore"))
        except Exception:
            pass

    # 2중 깨짐 방어
    for first in list(candidates):
        for enc in ("cp949", "euc-kr"):
            try:
                candidates.add(first.encode(enc, errors="ignore").decode("utf-8", errors="ignore"))
            except Exception:
                pass

    best = max(candidates, key=_score_text)

    # 공백/줄바꿈 정리
    best = re.sub(r"\s+", " ", best).strip()

    # 너무 짧게 깨져 복원된 경우 원문 유지
    if len(best) < max(3, len(original) * 0.15) and _score_text(original) > _score_text(best):
        best = original

    return best


def is_probably_mojibake(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if _REPLACEMENT_RE.search(value):
        return True
    if len(_NOISE_RE.findall(value)) >= 3:
        return True
    cjk = len(_CJK_RE.findall(value))
    hangul = len(_HANGUL_RE.findall(value))
    return cjk >= 8 and cjk > hangul


def normalize_spaces(value: Any, limit: int | None = None) -> Any:
    if not isinstance(value, str):
        return value
    text = repair_mojibake_text(value)
    text = re.sub(r"\s+", " ", text).strip()
    if limit is not None and len(text) > limit:
        text = text[:limit].rstrip()
    return text


def deep_clean(obj: Any) -> Any:
    """
    dict/list/string 전체를 재귀적으로 한글 깨짐 복구 + 공백 정리.
    JSON 저장 직전에 반드시 통과시킨다.
    """
    if isinstance(obj, dict):
        return {repair_mojibake_text(k): deep_clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_clean(v) for v in obj]
    if isinstance(obj, str):
        return normalize_spaces(obj)
    return obj
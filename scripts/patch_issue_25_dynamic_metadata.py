from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path.cwd()
CONFIG = ROOT / "src" / "issue_agent" / "config.py"

MARKER_START = "# === ALPHAPROVE_ISSUE25_DYNAMIC_METADATA_START ==="
MARKER_END = "# === ALPHAPROVE_ISSUE25_DYNAMIC_METADATA_END ==="

BLOCK = """
# === ALPHAPROVE_ISSUE25_DYNAMIC_METADATA_START ===
# Added by scripts/patch_issue_25_dynamic_metadata.py
# Purpose:
# - Extend Issue Agent RSS/search keywords from the locked Universe 30 CSV.
# - Avoid manually hardcoding 25 added companies into team member code.
# - Keep this block fail-safe so Issue Agent can still import even when metadata is unavailable.
try:
    from common.company_metadata import iter_company_metadata

    if "COMPANY_RSS_KEYWORDS" in globals():
        for _meta in iter_company_metadata():
            _keywords = [_meta.name]

            if _meta.peer_group:
                _keywords.append(_meta.peer_group)

                _pg = str(_meta.peer_group)
                if "후공정" in _pg or "패키징" in _pg:
                    _keywords.extend(["후공정", "패키징", "OSAT", "HBM"])
                if "테스트" in _pg or "소켓" in _pg:
                    _keywords.extend(["테스트", "검사", "소켓", "수율"])
                if "소재" in _pg:
                    _keywords.extend(["반도체 소재", "전구체", "식각", "증착", "고순도"])
                if "장비" in _pg:
                    _keywords.extend(["반도체 장비", "CAPEX", "공정장비"])
                if "팹리스" in _pg or "설계" in _pg:
                    _keywords.extend(["팹리스", "시스템반도체", "SoC", "MCU"])
                if "디자인" in _pg:
                    _keywords.extend(["디자인하우스", "디자인솔루션", "파운드리"])
                if "파운드리" in _pg:
                    _keywords.extend(["파운드리", "웨이퍼", "수율"])
                if "차량용" in _pg:
                    _keywords.extend(["차량용 반도체", "전장", "MCU"])

            _keywords.extend(["반도체", "semiconductor", "주가", "실적", "투자", "공시"])

            _deduped = []
            for _kw in _keywords:
                _kw = str(_kw).strip()
                if _kw and _kw not in _deduped:
                    _deduped.append(_kw)

            COMPANY_RSS_KEYWORDS[_meta.name] = _deduped
            COMPANY_RSS_KEYWORDS[_meta.slug] = _deduped

except Exception:
    # Issue Agent should still import even if optional universe metadata is unavailable.
    pass
# === ALPHAPROVE_ISSUE25_DYNAMIC_METADATA_END ===
""".strip()


def _read_text(path: Path) -> str:
    last_error: Exception | None = None

    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error

    return path.read_text()


def main() -> int:
    if not CONFIG.exists():
        raise FileNotFoundError(f"issue config not found: {CONFIG}")

    text = _read_text(CONFIG)

    if MARKER_START in text and MARKER_END in text:
        print(f"[SKIP] already patched: {CONFIG}")
        return 0

    backup = CONFIG.with_suffix(".py.bak_issue25")
    if not backup.exists():
        shutil.copy2(CONFIG, backup)
        print(f"[BACKUP] {backup}")

    if not text.endswith("\n"):
        text += "\n"

    CONFIG.write_text(text + "\n" + BLOCK + "\n", encoding="utf-8")
    print(f"[PATCHED] {CONFIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

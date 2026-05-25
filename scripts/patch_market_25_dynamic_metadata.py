from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path.cwd()
CONFIG = ROOT / "src" / "market_agent" / "config.py"

MARKER_START = "# === ALPHAPROVE_MARKET25_DYNAMIC_METADATA_START ==="
MARKER_END = "# === ALPHAPROVE_MARKET25_DYNAMIC_METADATA_END ==="

BLOCK = """
# === ALPHAPROVE_MARKET25_DYNAMIC_METADATA_START ===
# Added by scripts/patch_market_25_dynamic_metadata.py
# Purpose:
# - Extend Market Agent company/ticker mappings from the locked Universe 30 CSV.
# - Avoid manually hardcoding 25 additional companies into team member code.
# - Keep this block fail-safe so Market Agent can still import even when metadata is unavailable.
try:
    from common.company_metadata import iter_company_metadata

    for _meta in iter_company_metadata():
        if _meta.yf_ticker and "TICKERS" in globals():
            TICKERS[_meta.name] = _meta.yf_ticker
            TICKERS[_meta.slug] = _meta.yf_ticker

        if _meta.stock_code and "CORP_CODES" in globals():
            CORP_CODES[_meta.name] = _meta.stock_code
            CORP_CODES[_meta.slug] = _meta.stock_code

        if _meta.name and "DEFAULT_COMPANIES" in globals() and isinstance(DEFAULT_COMPANIES, list):
            if _meta.name not in DEFAULT_COMPANIES:
                DEFAULT_COMPANIES.append(_meta.name)

except Exception:
    # Market Agent should still import even if optional universe metadata is unavailable.
    pass
# === ALPHAPROVE_MARKET25_DYNAMIC_METADATA_END ===
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
        raise FileNotFoundError(f"market config not found: {CONFIG}")

    text = _read_text(CONFIG)

    if MARKER_START in text and MARKER_END in text:
        print(f"[SKIP] already patched: {CONFIG}")
        return 0

    backup = CONFIG.with_suffix(".py.bak_market25")
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

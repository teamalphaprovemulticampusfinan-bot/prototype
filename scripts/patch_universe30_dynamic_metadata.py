from __future__ import annotations

from pathlib import Path
import shutil
import textwrap


ROOT = Path.cwd()
SRC = ROOT / "src"


COMPANY_METADATA_CODE = r"""from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from common.data_paths import DATA_DIR, COMPANY_COMMON_NAME, DEFAULT_FIELD, safe_name
except Exception:  # pragma: no cover
    DATA_DIR = Path("data")
    COMPANY_COMMON_NAME = "_company_common"
    DEFAULT_FIELD = "반도체"

    def safe_name(value: str) -> str:
        return str(value).strip().replace(" ", "_")


DEFAULT_UNIVERSE_CSV = (
    DATA_DIR
    / DEFAULT_FIELD
    / "_sector_common"
    / "universe"
    / "universe_30_semiconductor_20260514.csv"
)


@dataclass(frozen=True)
class CompanyMetadata:
    slug: str
    name: str
    stock_code: str
    market: str
    field: str
    sector: str
    peer_group: str = ""
    yf_ticker: str = ""


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [dict(r) for r in csv.DictReader(f)]
        except Exception:
            continue
    return []


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}

    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            data = yaml.safe_load(path.read_text(encoding=enc)) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _market_to_yf_suffix(market: str) -> str:
    m = str(market or "").strip().upper()
    if m == "KOSPI":
        return ".KS"
    if m == "KOSDAQ":
        return ".KQ"
    return ""


def make_yf_ticker(stock_code: str, market: str) -> str:
    code = str(stock_code or "").strip().zfill(6)
    if not code or not code.isdigit() or code == "000000":
        return ""
    suffix = _market_to_yf_suffix(market)
    return f"{code}{suffix}" if suffix else code


def _row_to_meta(row: dict[str, Any]) -> CompanyMetadata | None:
    name = str(
        row.get("company_name")
        or row.get("display_name")
        or row.get("output_name")
        or row.get("corp_name")
        or row.get("name")
        or ""
    ).strip()
    slug = str(row.get("company_dir") or row.get("slug") or "").strip()
    stock_code_raw = str(row.get("stock_code") or row.get("ticker6") or "").strip()
    stock_code = stock_code_raw.zfill(6) if stock_code_raw else ""
    market = str(row.get("market") or "").strip().upper()
    field = str(row.get("field") or row.get("industry_field") or row.get("sector") or DEFAULT_FIELD).strip() or DEFAULT_FIELD
    sector = str(row.get("sector") or field).strip() or field
    peer_group = str(row.get("peer_group") or row.get("selection_bucket") or "").strip()
    yf_ticker = str(row.get("ticker") or row.get("yf_ticker") or "").strip()

    if not yf_ticker:
        yf_ticker = make_yf_ticker(stock_code, market)

    if not name and slug:
        name = slug
    if not slug and name:
        slug = safe_name(name)

    if not slug or not name:
        return None

    return CompanyMetadata(
        slug=slug,
        name=name,
        stock_code=stock_code,
        market=market,
        field=field,
        sector=sector,
        peer_group=peer_group,
        yf_ticker=yf_ticker,
    )


def _iter_company_yaml_meta() -> Iterable[CompanyMetadata]:
    if not DATA_DIR.exists():
        return []

    metas: list[CompanyMetadata] = []
    for path in DATA_DIR.glob(f"*/*/{COMPANY_COMMON_NAME}/company.yaml"):
        data = _read_yaml(path)
        if not data:
            continue
        row = {
            "company_name": data.get("display_name") or data.get("output_name") or data.get("corp_name"),
            "company_dir": data.get("company_dir") or data.get("slug"),
            "stock_code": data.get("stock_code"),
            "market": data.get("market"),
            "field": data.get("field") or data.get("industry_field"),
            "sector": data.get("sector"),
            "peer_group": data.get("peer_group"),
            "ticker": data.get("ticker") or data.get("yf_ticker"),
        }
        meta = _row_to_meta(row)
        if meta:
            metas.append(meta)
    return metas


def iter_company_metadata(csv_path: str | Path | None = None) -> list[CompanyMetadata]:
    \"\"\"Return fixed universe metadata from CSV plus generated company.yaml files.

    CSV is treated as the evaluation lock source. company.yaml is fallback.
    \"\"\"
    path = Path(csv_path) if csv_path else DEFAULT_UNIVERSE_CSV

    out: list[CompanyMetadata] = []
    seen: set[str] = set()

    for row in _read_csv_rows(path):
        include = str(row.get("include_in_evaluation", "1")).strip().lower()
        if include not in {"1", "true", "yes", "y"}:
            continue
        meta = _row_to_meta(row)
        if meta and meta.slug not in seen:
            out.append(meta)
            seen.add(meta.slug)

    for meta in _iter_company_yaml_meta():
        if meta.slug not in seen:
            out.append(meta)
            seen.add(meta.slug)

    return out


def get_company_metadata(value: str, fallback_name: str | None = None) -> CompanyMetadata | None:
    raw = str(value or "").strip()
    fallback = str(fallback_name or "").strip()
    lowered = raw.lower()

    for meta in iter_company_metadata():
        aliases = {
            meta.slug,
            meta.slug.lower(),
            meta.name,
            meta.name.lower(),
            meta.stock_code,
            meta.yf_ticker,
            meta.yf_ticker.lower(),
        }
        if fallback:
            aliases.add(fallback)
            aliases.add(fallback.lower())

        if raw in aliases or lowered in aliases:
            return meta

    return None


def ticker_for_company(value: str, fallback_name: str | None = None) -> str:
    meta = get_company_metadata(value, fallback_name)
    return meta.yf_ticker if meta else ""


def display_name_for_company(value: str, fallback_name: str | None = None) -> str:
    meta = get_company_metadata(value, fallback_name)
    if meta:
        return meta.name
    return fallback_name or value
"""


VALUATION_DYNAMIC_BLOCK = r"""
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_START ===
# Added by scripts/patch_universe30_dynamic_metadata.py
# Purpose: keep Valuation Agent code generic. New companies are resolved from
# data/반도체/_sector_common/universe/*.csv or data/반도체/<회사>/_company_common/company.yaml.
try:
    from common.company_metadata import get_company_metadata

    _alphaprove_static_resolve_company = resolve_company

    def resolve_company(company_dir: str, company: str | None = None) -> ListedCompany:  # type: ignore[no-redef]
        meta = get_company_metadata(company_dir or company or "", company)
        if meta and meta.stock_code:
            return ListedCompany(
                slug=meta.slug,
                name=meta.name,
                stock_code=meta.stock_code,
                market=meta.market or "KOSDAQ",
                yf_ticker=meta.yf_ticker,
            )
        return _alphaprove_static_resolve_company(company_dir, company)

except Exception:
    pass
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_END ===
"""


MARKET_DYNAMIC_BLOCK = r"""
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_START ===
# Added by scripts/patch_universe30_dynamic_metadata.py
# Extend market ticker/default-company mappings from the fixed universe CSV/company.yaml.
try:
    from common.company_metadata import iter_company_metadata

    if "TICKERS" in globals():
        for _meta in iter_company_metadata():
            if _meta.yf_ticker:
                TICKERS[_meta.name] = _meta.yf_ticker
                TICKERS[_meta.slug] = _meta.yf_ticker

    if "DEFAULT_COMPANIES" in globals():
        for _meta in iter_company_metadata():
            if _meta.name and _meta.name not in DEFAULT_COMPANIES:
                DEFAULT_COMPANIES.append(_meta.name)

except Exception:
    pass
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_END ===
"""


ISSUE_DYNAMIC_BLOCK = r"""
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_START ===
# Added by scripts/patch_universe30_dynamic_metadata.py
# Add generic RSS keywords for universe companies without hardcoding each one by hand.
try:
    from common.company_metadata import iter_company_metadata

    if "COMPANY_RSS_KEYWORDS" in globals():
        for _meta in iter_company_metadata():
            _keywords = [_meta.name]
            if _meta.peer_group:
                _keywords.append(_meta.peer_group)
            _keywords.extend(["반도체", "semiconductor"])
            COMPANY_RSS_KEYWORDS.setdefault(_meta.name, _keywords)

except Exception:
    pass
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_END ===
"""


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_universe30_dynamic")
        if not bak.exists():
            shutil.copy2(path, bak)
    path.write_text(text, encoding="utf-8")


def append_block_once(path: Path, block: str) -> bool:
    if not path.exists():
        raise FileNotFoundError(path)

    text = path.read_text(encoding="utf-8")
    marker = "ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_START"

    if marker in text:
        print(f"[SKIP] already patched: {path}")
        return False

    bak = path.with_suffix(path.suffix + ".bak_universe30_dynamic")
    if not bak.exists():
        shutil.copy2(path, bak)

    if not text.endswith("\n"):
        text += "\n"

    path.write_text(text + "\n" + block.strip() + "\n", encoding="utf-8")
    print(f"[PATCHED] {path}")
    return True


def main() -> int:
    common_path = SRC / "common" / "company_metadata.py"
    write_file(common_path, COMPANY_METADATA_CODE)
    print(f"[WRITE] {common_path}")

    append_block_once(SRC / "data_intake" / "valuation_intake" / "sources.py", VALUATION_DYNAMIC_BLOCK)
    append_block_once(SRC / "market_agent" / "config.py", MARKET_DYNAMIC_BLOCK)
    append_block_once(SRC / "issue_agent" / "config.py", ISSUE_DYNAMIC_BLOCK)

    print("[DONE] Dynamic universe metadata patch applied.")
    print("Next:")
    print("  python -c \"from common.company_metadata import get_company_metadata; print(get_company_metadata('dbhitek', 'DB하이텍'))\"")
    print("  python main.py valuation-intake --company-dir dbhitek --company \"DB하이텍\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

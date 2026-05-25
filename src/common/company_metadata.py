from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
                rows = list(csv.DictReader(f))
            if rows:
                return [dict(r) for r in rows]
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
    market_upper = str(market or "").strip().upper()

    if market_upper == "KOSPI":
        return ".KS"

    if market_upper == "KOSDAQ":
        return ".KQ"

    return ""


def make_yf_ticker(stock_code: str, market: str) -> str:
    code = str(stock_code or "").strip()

    if not code:
        return ""

    code = code.zfill(6)

    if not code.isdigit() or code == "000000":
        return ""

    suffix = _market_to_yf_suffix(market)

    if suffix:
        return f"{code}{suffix}"

    return code


def _as_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _norm(value: Any) -> str:
    """Normalize company lookup keys.

    The project often receives Korean company names from CLI arguments with
    spaces or punctuation variants, e.g. ``SFA 반도체`` vs ``SFA반도체``.
    Keep matching permissive here while preserving original names in outputs.
    """
    text = _as_text(value).lower()
    text = text.replace("㈜", "").replace("(주)", "").replace("주식회사", "")
    return "".join(ch for ch in text if ch.isalnum())


def _alias_values_from_yaml(data: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    for key in (
        "aliases",
        "alias",
        "corp_name",
        "display_name",
        "output_name",
        "name",
        "company_name",
        "company_dir",
        "slug",
        "ticker",
        "yf_ticker",
        "stock_code",
    ):
        value = data.get(key)
        if isinstance(value, (list, tuple, set)):
            aliases.extend(_as_text(x) for x in value if _as_text(x))
        elif _as_text(value):
            aliases.append(_as_text(value))
    return aliases


def _row_to_meta(row: dict[str, Any]) -> CompanyMetadata | None:
    name = _as_text(
        row.get("company_name")
        or row.get("display_name")
        or row.get("output_name")
        or row.get("corp_name")
        or row.get("name")
    )
    slug = _as_text(row.get("company_dir") or row.get("slug"))

    stock_code_raw = _as_text(row.get("stock_code") or row.get("ticker6"))
    stock_code = stock_code_raw.zfill(6) if stock_code_raw else ""

    market = _as_text(row.get("market")).upper()
    field = _as_text(row.get("field") or row.get("industry_field") or row.get("sector") or DEFAULT_FIELD) or DEFAULT_FIELD
    sector = _as_text(row.get("sector") or field) or field
    peer_group = _as_text(row.get("peer_group") or row.get("selection_bucket"))
    yf_ticker = _as_text(row.get("ticker") or row.get("yf_ticker"))

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


def _iter_company_yaml_meta() -> list[CompanyMetadata]:
    if not DATA_DIR.exists():
        return []

    metas: list[CompanyMetadata] = []
    pattern = f"*/*/{COMPANY_COMMON_NAME}/company.yaml"

    for path in DATA_DIR.glob(pattern):
        data = _read_yaml(path)

        if not data:
            continue

        row = {
            "company_name": data.get("display_name") or data.get("output_name") or data.get("corp_name") or data.get("name"),
            "company_dir": data.get("company_dir") or data.get("slug") or path.parent.parent.name,
            "stock_code": data.get("stock_code") or data.get("ticker6"),
            "market": data.get("market"),
            "field": data.get("field") or data.get("industry_field") or data.get("output_category"),
            "sector": data.get("sector"),
            "peer_group": data.get("peer_group") or data.get("selection_bucket"),
            "ticker": data.get("ticker") or data.get("yf_ticker"),
        }
        meta = _row_to_meta(row)

        if meta:
            metas.append(meta)

    return metas


def iter_company_metadata(csv_path: str | Path | None = None) -> list[CompanyMetadata]:
    """Return fixed universe metadata from CSV plus generated company.yaml files.

    CSV rows are returned first and have priority over generated YAML files.
    """
    path = Path(csv_path) if csv_path else DEFAULT_UNIVERSE_CSV

    out: list[CompanyMetadata] = []
    seen: set[str] = set()

    for row in _read_csv_rows(path):
        include = _as_text(row.get("include_in_evaluation") or "1").lower()

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
    """Find company metadata by exact priority order.

    This strict resolver prevents English-uppercase companies such as GST and ISC
    from being resolved as the first universe company.
    """
    raw = _as_text(value)
    fallback = _as_text(fallback_name)

    exact_queries = [q for q in [raw, fallback] if q]
    norm_queries = {_norm(q) for q in exact_queries if q}

    metas = iter_company_metadata()

    for q in exact_queries:
        for meta in metas:
            if q == meta.slug:
                return meta

    for nq in norm_queries:
        for meta in metas:
            if nq and nq == _norm(meta.slug):
                return meta

    for q in exact_queries:
        q6 = q.zfill(6) if q.isdigit() else q
        for meta in metas:
            if q6 and q6 == meta.stock_code:
                return meta

    for q in exact_queries:
        for meta in metas:
            if q and q == meta.yf_ticker:
                return meta

    for nq in norm_queries:
        for meta in metas:
            if nq and nq == _norm(meta.yf_ticker):
                return meta

    for q in exact_queries:
        for meta in metas:
            if q and q == meta.name:
                return meta

    for nq in norm_queries:
        for meta in metas:
            if nq and nq == _norm(meta.name):
                return meta

    # Last pass: whitespace/punctuation-insensitive containment for CLI names
    # such as "SFA 반도체" when the universe stores "SFA반도체".
    for nq in norm_queries:
        if not nq:
            continue
        for meta in metas:
            candidates = {_norm(meta.slug), _norm(meta.name), _norm(meta.stock_code), _norm(meta.yf_ticker)}
            if nq in candidates or any(nq and c and (nq in c or c in nq) for c in candidates):
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

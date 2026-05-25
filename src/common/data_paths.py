from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
LEGACY_WORKSPACE_DIR = ROOT_DIR / "workspace"

def normalize_field_name(value: Any = None, default: str = "반도체") -> str:
    """Return a canonical field folder name.

    Some Windows/PowerShell entrypoints can pass UTF-8 Korean text after it has
    been decoded as CP949, e.g. ``반도체`` becomes ``諛섎룄泥?``.  Keep the
    repair close to path construction so CLI env glitches do not create a
    parallel broken field directory.
    """
    text = str(value or "").strip()
    fallback = str(default or "반도체").strip() or "반도체"
    if not text:
        return fallback

    normalized = text.replace("\ufffd", "?")
    if normalized in {"諛섎룄泥?", "諛섎룄泥�", "諛섎룄泥"}:
        return "반도체"
    if "諛섎룄" in normalized and "泥" in normalized:
        return "반도체"

    try:
        repaired = text.encode("cp949").decode("utf-8").strip()
    except Exception:
        repaired = ""
    if repaired and "\ufffd" not in repaired and "?" not in repaired:
        return repaired

    return text


DEFAULT_FIELD = normalize_field_name(os.getenv("ALPHAPROVE_DATA_FIELD", "반도체"), "반도체")

GLOBAL_COMMON_NAME = "_global_common"
FIELD_COMMON_NAME = "_sector_common"
COMPANY_COMMON_NAME = "_company_common"
FIELD_SOURCE_DATA_NAME = "source_data"

# Backward compatibility aliases
COMMON_NAME = COMPANY_COMMON_NAME
LEGACY_COMMON_NAME = "common"

KNOWN_COMPANY_DIRS = [
    "nepes", "hanmi", "hansol", "duksan", "ltc",
    "dbhitek", "mico", "lxsemicon", "jeju_semicon", "abov",
    "telechips", "coasia", "gaochips", "wonik_ips", "eugene_tech",
    "psk", "tes", "gst", "sti", "nextin",
    "soulbrain", "dongjin_semichem", "wonik_materials", "enf_tech", "tck",
    "woldex", "isc", "sfa_semicon", "doosan_tesna", "leeno",
]

KNOWN_COMPANY_DIR_TO_NAME = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
    "dbhitek": "DB하이텍",
    "mico": "미코",
    "lxsemicon": "LX세미콘",
    "jeju_semicon": "제주반도체",
    "abov": "어보브반도체",
    "telechips": "텔레칩스",
    "coasia": "코아시아",
    "gaochips": "가온칩스",
    "wonik_ips": "원익IPS",
    "eugene_tech": "유진테크",
    "psk": "피에스케이",
    "tes": "테스",
    "gst": "GST",
    "sti": "에스티아이",
    "nextin": "넥스틴",
    "soulbrain": "솔브레인",
    "dongjin_semichem": "동진쎄미켐",
    "wonik_materials": "원익머트리얼즈",
    "enf_tech": "이엔에프테크놀로지",
    "tck": "티씨케이",
    "woldex": "월덱스",
    "isc": "ISC",
    "sfa_semicon": "SFA반도체",
    "doosan_tesna": "두산테스나",
    "leeno": "리노공업",
}

KNOWN_COMPANY_NAME_TO_DIR = {
    "네패스": "nepes", "nepes": "nepes", "033640": "nepes",
    "한미반도체": "hanmi", "hanmi": "hanmi", "042700": "hanmi",
    "한솔케미칼": "hansol", "hansol": "hansol", "014680": "hansol",
    "덕산테코피아": "duksan", "duksan": "duksan", "317330": "duksan",
    "엘티씨": "ltc", "LTC": "ltc", "ltc": "ltc", "170920": "ltc",
    "DB하이텍": "dbhitek", "dbhitek": "dbhitek", "000990": "dbhitek",
    "미코": "mico", "mico": "mico", "059090": "mico",
    "LX세미콘": "lxsemicon", "lxsemicon": "lxsemicon", "108320": "lxsemicon",
    "제주반도체": "jeju_semicon", "jeju_semicon": "jeju_semicon", "080220": "jeju_semicon",
    "어보브반도체": "abov", "abov": "abov", "102120": "abov",
    "텔레칩스": "telechips", "telechips": "telechips", "054450": "telechips",
    "코아시아": "coasia", "coasia": "coasia", "045970": "coasia",
    "가온칩스": "gaochips", "gaochips": "gaochips", "399720": "gaochips",
    "원익IPS": "wonik_ips", "wonik_ips": "wonik_ips", "240810": "wonik_ips",
    "유진테크": "eugene_tech", "eugene_tech": "eugene_tech", "084370": "eugene_tech",
    "피에스케이": "psk", "psk": "psk", "319660": "psk",
    "테스": "tes", "tes": "tes", "095610": "tes",
    "GST": "gst", "gst": "gst", "083450": "gst",
    "에스티아이": "sti", "sti": "sti", "039440": "sti",
    "넥스틴": "nextin", "nextin": "nextin", "348210": "nextin",
    "솔브레인": "soulbrain", "soulbrain": "soulbrain", "357780": "soulbrain",
    "동진쎄미켐": "dongjin_semichem", "dongjin_semichem": "dongjin_semichem", "005290": "dongjin_semichem",
    "원익머트리얼즈": "wonik_materials", "wonik_materials": "wonik_materials", "104830": "wonik_materials",
    "이엔에프테크놀로지": "enf_tech", "enf_tech": "enf_tech", "102710": "enf_tech",
    "티씨케이": "tck", "tck": "tck", "064760": "tck",
    "월덱스": "woldex", "woldex": "woldex", "101160": "woldex",
    "ISC": "isc", "isc": "isc", "095340": "isc",
    "SFA반도체": "sfa_semicon", "sfa_semicon": "sfa_semicon", "036540": "sfa_semicon",
    "두산테스나": "doosan_tesna", "doosan_tesna": "doosan_tesna", "131970": "doosan_tesna",
    "리노공업": "leeno", "leeno": "leeno", "058470": "leeno",
}

AGENT_NAMES = {"finance", "market", "issue", "macro", "tech", "chair", "auditor", "valuation"}


def decode_escaped_unicode(text: Any) -> str:
    """Decode zip-extracted names like '#Ubc18#Ub3c4#Uccb4' into Korean."""
    s = str(text or "")
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)


def safe_name(value: Any, default: str = "output") -> str:
    text = decode_escaped_unicode(value).strip().strip('"').strip("'")
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text).strip("._ ")
    return text or default


def _company_lookup_key(value: Any) -> str:
    text = decode_escaped_unicode(value).strip().strip('"').strip("'").lower()
    return re.sub(r"[\s_\-./()]+", "", text)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except UnicodeDecodeError:
        return yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except Exception:
        return {}


def _iter_company_yaml_paths() -> Iterable[Path]:
    """Yield company.yaml paths from new layout first, then old fallback paths."""
    if DATA_DIR.exists():
        patterns = [
            f"*/ */{COMPANY_COMMON_NAME}/company.yaml".replace(" ", ""),
            f"*/ */{LEGACY_COMMON_NAME}/company.yaml".replace(" ", ""),
            f"*/{FIELD_COMMON_NAME}/companies/*/company.yaml",
            f"*/{LEGACY_COMMON_NAME}/companies/*/company.yaml",
            "companies/*/company.yaml",
        ]
        seen: set[str] = set()
        for pattern in patterns:
            for path in DATA_DIR.glob(pattern):
                key = str(path.resolve())
                if key not in seen:
                    seen.add(key)
                    yield path

    if LEGACY_WORKSPACE_DIR.exists():
        for path in (LEGACY_WORKSPACE_DIR / "companies").glob("*/company.yaml"):
            yield path


def _unique_company_slug_by_prefix(compact: str) -> str | None:
    if len(compact) < 3:
        return None

    matches: set[str] = set()

    for alias, slug in KNOWN_COMPANY_NAME_TO_DIR.items():
        key = _company_lookup_key(alias)
        if key and key.startswith(compact):
            matches.add(slug)

    for yp in _iter_company_yaml_paths():
        data = _read_yaml(yp)
        folder_name = decode_escaped_unicode(
            yp.parent.parent.name if yp.parent.name in {COMPANY_COMMON_NAME, LEGACY_COMMON_NAME} else yp.parent.name
        )
        slug = str(data.get("slug") or KNOWN_COMPANY_NAME_TO_DIR.get(folder_name) or safe_name(folder_name))
        aliases = {
            yp.parent.name,
            folder_name,
            slug,
            str(data.get("corp_name") or ""),
            str(data.get("display_name") or ""),
            str(data.get("output_name") or ""),
            str(data.get("name") or ""),
            str(data.get("corp_name_en") or ""),
            str(data.get("stock_code") or ""),
            *[str(x) for x in (data.get("aliases") or [])],
        }
        for alias in aliases:
            key = _company_lookup_key(alias)
            if key and key.startswith(compact):
                matches.add(slug)

    return next(iter(matches)) if len(matches) == 1 else None


def company_slug(value: Any, default: str | None = None) -> str:
    raw = decode_escaped_unicode(value).strip().strip('"').strip("'")
    if not raw:
        return safe_name(default or "unknown_company")

    if raw in KNOWN_COMPANY_NAME_TO_DIR:
        return KNOWN_COMPANY_NAME_TO_DIR[raw]

    lowered = raw.lower()
    if lowered in KNOWN_COMPANY_NAME_TO_DIR:
        return KNOWN_COMPANY_NAME_TO_DIR[lowered]

    compact = _company_lookup_key(raw)
    for alias, slug in KNOWN_COMPANY_NAME_TO_DIR.items():
        if compact and compact == _company_lookup_key(alias):
            return slug

    p = Path(raw.replace("\\", "/"))
    if p.name.lower() == "company.yaml" and len(p.parts) >= 2:
        if len(p.parts) >= 3 and p.parts[-2] in {COMPANY_COMMON_NAME, LEGACY_COMMON_NAME}:
            parent = decode_escaped_unicode(p.parts[-3])
        else:
            parent = decode_escaped_unicode(p.parts[-2])

        if parent in KNOWN_COMPANY_NAME_TO_DIR:
            return KNOWN_COMPANY_NAME_TO_DIR[parent]
        return safe_name(parent)

    for yp in _iter_company_yaml_paths():
        data = _read_yaml(yp)
        folder_name = decode_escaped_unicode(
            yp.parent.parent.name if yp.parent.name in {COMPANY_COMMON_NAME, LEGACY_COMMON_NAME} else yp.parent.name
        )
        aliases = {
            yp.parent.name,
            folder_name,
            str(data.get("slug") or ""),
            str(data.get("corp_name") or ""),
            str(data.get("display_name") or ""),
            str(data.get("output_name") or ""),
            str(data.get("name") or ""),
            str(data.get("corp_name_en") or ""),
            str(data.get("stock_code") or ""),
            *[str(x) for x in (data.get("aliases") or [])],
        }
        aliases = {decode_escaped_unicode(x).strip() for x in aliases if x and str(x).strip()}
        if raw in aliases or lowered in {x.lower() for x in aliases} or compact in {_company_lookup_key(x) for x in aliases}:
            return str(data.get("slug") or KNOWN_COMPANY_NAME_TO_DIR.get(folder_name) or safe_name(folder_name))

    prefix_match = _unique_company_slug_by_prefix(compact)
    if prefix_match:
        return prefix_match

    return safe_name(default or raw, "unknown_company")


def company_name(value: Any) -> str:
    slug = company_slug(value)

    if slug in KNOWN_COMPANY_DIR_TO_NAME:
        return safe_name(KNOWN_COMPANY_DIR_TO_NAME[slug], slug)

    for yp in _iter_company_yaml_paths():
        data = _read_yaml(yp)
        if str(data.get("slug") or "").strip() == slug:
            return safe_name(
                data.get("output_name")
                or data.get("display_name")
                or data.get("corp_name")
                or yp.parent.parent.name,
                slug,
            )

    return safe_name(value or slug, slug)


def company_field(value: Any = None, default: str | None = None) -> str:
    slug = company_slug(value or "") if value else ""

    for yp in _iter_company_yaml_paths():
        data = _read_yaml(yp)
        if slug and str(data.get("slug") or "").strip() != slug:
            continue

        for key in (
            "output_category",
            "industry_field",
            "field",
            "sector",
            "category",
            "analysis_group",
            "industry_theme",
            "theme",
        ):
            v = str(data.get(key) or "").strip()
            if v:
                return safe_name(normalize_field_name(v, default or DEFAULT_FIELD), default or DEFAULT_FIELD)

        if slug:
            break

    if slug in KNOWN_COMPANY_DIRS:
        return safe_name(normalize_field_name(default or DEFAULT_FIELD, DEFAULT_FIELD), DEFAULT_FIELD)

    return safe_name(normalize_field_name(default or os.getenv("ALPHAPROVE_DATA_FIELD", DEFAULT_FIELD), DEFAULT_FIELD), DEFAULT_FIELD)


def field_dir(field: str | None = None, *, create: bool = True) -> Path:
    path = DATA_DIR / safe_name(normalize_field_name(field or DEFAULT_FIELD, DEFAULT_FIELD), DEFAULT_FIELD)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def global_common_dir(subdir: str | None = None, *, create: bool = True) -> Path:
    """Project-wide shared files.

    Canonical:
        data/common/
        data/common/macro/
    """
    path = DATA_DIR / GLOBAL_COMMON_NAME
    if subdir:
        path = path / safe_name(subdir, subdir)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def field_common_dir(subdir: str | None = None, *, field: str | None = None, create: bool = True) -> Path:
    """Field-level shared files.

    Canonical:
        data/<field>/field_common/
        data/<field>/field_common/source_data/
    """
    path = field_dir(field, create=create) / FIELD_COMMON_NAME
    if subdir:
        path = path / safe_name(subdir, subdir)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def company_root(value: Any, *, field: str | None = None, create: bool = True) -> Path:
    path = field_dir(field or company_field(value), create=create) / company_name(value)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def company_common_dir(value: Any, *, create: bool = True) -> Path:
    """Company-level shared metadata.

    Canonical:
        data/<field>/<company>/company_common/company.yaml
    """
    path = company_root(value, create=create) / COMPANY_COMMON_NAME
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def company_agent_dir(value: Any, agent: str, *, create: bool = True) -> Path:
    agent_name = safe_name(str(agent).lower().replace("_agent", ""), "agent")
    path = company_root(value, create=create) / agent_name
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def field_agent_dir(agent: str, *, field: str | None = None, create: bool = True) -> Path:
    agent_name = safe_name(str(agent).lower().replace("_agent", ""), "agent")
    path = field_common_dir(agent_name, field=field, create=create)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def company_config_path(value: Any, *, create_parent: bool = False) -> Path:
    slug = company_slug(value)

    canonical = company_common_dir(slug, create=create_parent) / "company.yaml"
    if canonical.exists():
        return canonical

    old_company_common = company_root(slug, create=False) / LEGACY_COMMON_NAME / "company.yaml"
    if old_company_common.exists():
        return old_company_common

    legacy_candidates = [
        field_dir(company_field(slug), create=False) / FIELD_COMMON_NAME / "companies" / slug / "company.yaml",
        field_dir(company_field(slug), create=False) / LEGACY_COMMON_NAME / "companies" / slug / "company.yaml",
        DATA_DIR / "companies" / slug / "company.yaml",
        LEGACY_WORKSPACE_DIR / "companies" / slug / "company.yaml",
    ]

    for legacy in legacy_candidates:
        if legacy.exists():
            return legacy

    return canonical


def finance_csv_path(value: Any, filename: str | None = None) -> Path:
    slug = company_slug(value)
    cfg = _read_yaml(company_config_path(slug))
    name = filename or str(cfg.get("finance_file") or f"{company_name(slug)}_재무.csv")

    candidates = [
        company_agent_dir(slug, "finance", create=True) / name,
        company_common_dir(slug, create=True) / name,
        LEGACY_WORKSPACE_DIR / "companies" / slug / name,
    ]

    for path in candidates:
        if path.exists():
            return path

    return candidates[0]


def stock_csv_path(value: Any, filename: str | None = None) -> Path:
    """Stock CSV is now treated as finance-side input."""
    slug = company_slug(value)
    cfg = _read_yaml(company_config_path(slug))
    name = filename or str(cfg.get("stock_file") or f"{company_name(slug)}_주식.csv")

    candidates = [
        company_agent_dir(slug, "finance", create=True) / name,
        company_common_dir(slug, create=True) / name,
        company_agent_dir(slug, "market", create=True) / name,
        LEGACY_WORKSPACE_DIR / "companies" / slug / name,
    ]

    for path in candidates:
        if path.exists():
            return path

    return candidates[0]


def warning_csv_path() -> Path:
    candidates = [
        global_common_dir(create=True) / "투자경고종목.csv",
        DATA_DIR / "투자경고종목.csv",
        LEGACY_WORKSPACE_DIR / "투자경고종목.csv",
        LEGACY_WORKSPACE_DIR / "data" / "투자경고종목.csv",
    ]

    for path in candidates:
        if path.exists():
            return path

    return candidates[0]


def field_data_file(filename: str, *, create_parent: bool = True) -> Path:
    """Field-level shared source data.

    Canonical:
        data/<field>/field_common/source_data/<filename>
    """
    name = decode_escaped_unicode(filename)

    candidates = [
        # 현재 표준: data/<field>/_sector_common/source_data/<filename>
        field_common_dir(FIELD_SOURCE_DATA_NAME, create=create_parent) / name,
        field_dir(DEFAULT_FIELD, create=create_parent) / FIELD_SOURCE_DATA_NAME / name,
        # 사용자가 이미 보유한 호환 구조: data/<field>/common/data/<filename>
        field_dir(DEFAULT_FIELD, create=False) / LEGACY_COMMON_NAME / "data" / name,
        field_dir(DEFAULT_FIELD, create=False) / "common" / "data" / name,
        field_dir(DEFAULT_FIELD, create=False) / "data" / name,
        DATA_DIR / name,
        # 읽기 전용 legacy fallback. 새 산출물은 workspace로 쓰지 않는다.
        LEGACY_WORKSPACE_DIR / "data" / name,
        LEGACY_WORKSPACE_DIR / name,
    ]

    for path in candidates:
        if path.exists():
            return path

    return candidates[0]


def templates_dir(*, field: str | None = None, create: bool = True) -> Path:
    """Return sector template directory.

    Canonical:
        data/<field>/_sector_common/templates

    The old workspace fallback is intentionally removed from write paths.
    A few read-only compatibility candidates are still checked inside data/.
    """
    use_field = field or DEFAULT_FIELD
    candidates = [
        field_common_dir("templates", field=use_field, create=create),
        field_dir(use_field, create=False) / LEGACY_COMMON_NAME / "templates",
        field_dir(use_field, create=False) / "common" / "templates",
        field_dir(use_field, create=False) / "templates",
    ]

    for path in candidates:
        if path.exists() and any(path.iterdir()):
            return path

    return candidates[0]


def ml_universe_dir(*, field: str | None = None, create: bool = True) -> Path:
    """Return sector ML/reference-universe directory."""
    use_field = field or DEFAULT_FIELD
    candidates = [
        field_common_dir("ml_universe", field=use_field, create=create),
        field_dir(use_field, create=False) / LEGACY_COMMON_NAME / "ml_universe",
        field_dir(use_field, create=False) / "common" / "ml_universe",
        field_dir(use_field, create=False) / "ml_universe",
    ]

    for path in candidates:
        if path.exists() and any(path.iterdir()):
            return path

    return candidates[0]


def tech_source_dir(value: Any, *, create: bool = True) -> Path:
    """Return canonical company tech source directory.

    Canonical:
        data/<field>/<company>/tech/source

    Workspace fallback is intentionally removed in the no-workspace structure.
    """
    path = company_agent_dir(value, "tech", create=create) / "source"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def auditor_dir(value: Any, *, create: bool = True) -> Path:
    path = company_agent_dir(value, "auditor", create=create)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def first_auditor_dir(value: Any, *, create: bool = True) -> Path:
    path = auditor_dir(value, create=create) / "first_auditor"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def chair_quality_dir(value: Any, *, create: bool = True) -> Path:
    path = company_agent_dir(value, "chair", create=create) / "quality"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def macro_common_dir(*, create: bool = True) -> Path:
    """Macro raw CSV/JSON artifact dir.

    Canonical:
        data/common/macro/
    """
    return global_common_dir("macro", create=create)


def rel_project_path(value: Any, *, root: Path | None = None) -> str:
    if value is None:
        return ""

    base = root or ROOT_DIR
    raw = str(value).strip().replace("\\", "/")
    if not raw:
        return ""

    try:
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve().relative_to(base.resolve())).replace("\\", "/")
    except Exception:
        pass

    for prefix in ("data", "workspace", "src", "scripts"):
        m = re.search(rf"(?:^|.*?)({prefix}[\/].*)$", raw)
        if m:
            return m.group(1).replace("\\", "/")

    return raw


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def ensure_standard_tree(
    companies: Iterable[str] | None = None,
    agents: Iterable[str] | None = None,
    *,
    field: str | None = None,
) -> list[Path]:
    """Create canonical AlphaProve data tree."""
    made: list[Path] = []
    f = safe_name(field or DEFAULT_FIELD, DEFAULT_FIELD)

    made.append(global_common_dir(create=True))
    made.append(global_common_dir("macro", create=True))

    for sub in (
        FIELD_SOURCE_DATA_NAME,
        "ml_universe",
        "templates",
        "migration",
        "scripts",
        "tech",
        "tech_intake",
        "tech_lifecycle",
        "tech_certifications",
        "tech_value_evidence",
        "market",
        "issue",
        "macro",
        "finance",
        "chair",
        "auditor",
    ):
        made.append(field_common_dir(sub, field=f, create=True))

    for company in companies or KNOWN_COMPANY_DIRS:
        made.append(company_common_dir(company, create=True))
        for agent in agents or sorted(AGENT_NAMES):
            made.append(company_agent_dir(company, agent, create=True))
        made.append(company_agent_dir(company, "tech", create=True) / "source")

    return made



# ---------------------------------------------------------------------------
# Tech-sector shared-data helpers.
# ---------------------------------------------------------------------------

def tech_sector_common_dir(subdir: str | None = None, *, field: str | None = None, create: bool = True) -> Path:
    """Return the canonical sector-level Tech data directory.

    Canonical examples:
        data/반도체/_sector_common/tech
        data/반도체/_sector_common/tech_intake
        data/반도체/_sector_common/tech_lifecycle
        data/반도체/_sector_common/tech_certifications
        data/반도체/_sector_common/ml_universe
        data/반도체/_sector_common/templates

    This helper exists so migrated Agent_6.8 Tech assets are resolved from the
    no-workspace Agent_6.9 layout without falling back to old absolute paths.
    """
    name = safe_name(subdir or "tech", subdir or "tech")
    path = field_common_dir(name, field=field or DEFAULT_FIELD, create=create)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def tech_intake_common_dir(*, field: str | None = None, create: bool = True) -> Path:
    return tech_sector_common_dir("tech_intake", field=field, create=create)


def tech_lifecycle_common_dir(*, field: str | None = None, create: bool = True) -> Path:
    return tech_sector_common_dir("tech_lifecycle", field=field, create=create)


def tech_certifications_common_dir(*, field: str | None = None, create: bool = True) -> Path:
    return tech_sector_common_dir("tech_certifications", field=field, create=create)


def tech_value_evidence_common_dir(*, field: str | None = None, create: bool = True) -> Path:
    return tech_sector_common_dir("tech_value_evidence", field=field, create=create)

# ---------------------------------------------------------------------------
# Compatibility helpers used by Tech Intake and Issue Agent.
# ---------------------------------------------------------------------------

def canonical_company_name(value: Any) -> str:
    """Return display/canonical company name for slug or company name."""
    return company_name(value)


def company_config_file(value: Any, *, create: bool = True) -> Path:
    return company_config_path(value, create_parent=create)


def tech_template_dir(*, field: str | None = None, create: bool = True) -> Path:
    return templates_dir(field=field or DEFAULT_FIELD, create=create)


def tech_ml_universe_dir(*, field: str | None = None, create: bool = True) -> Path:
    return ml_universe_dir(field=field or DEFAULT_FIELD, create=create)

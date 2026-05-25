from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from common.data_paths import company_agent_dir, field_common_dir, normalize_field_name, rel_project_path, templates_dir
from data_intake.tech_intake.template_bridge import prepare_template_references


ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable

DEFAULT_FIELD = "반도체"
DEFAULT_COMPANIES: dict[str, str] = {
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

TECH_COMPANY_ALIASES: dict[str, set[str]] = {
    "nepes": {"네패스", "nepes", "NEPES", "033640"},
    "hanmi": {"한미반도체", "hanmi", "Hanmi", "Hanmi Semiconductor", "HANMI", "042700"},
    "hansol": {"한솔케미칼", "한솔", "hansol", "Hansol", "Hansol Chemical", "HANSOL", "014680"},
    "duksan": {"덕산테코피아", "덕산", "duksan", "Duksan", "DS Techopia", "DUKSAN TECHOPIA", "317330"},
    "ltc": {"엘티씨", "LTC", "ltc", "170920"},
    "dbhitek": {"DB하이텍", "디비하이텍", "dbhitek", "DB HiTek", "000990"},
    "mico": {"미코", "mico", "MiCo", "059090"},
    "lxsemicon": {"LX세미콘", "엘엑스세미콘", "lxsemicon", "LX Semicon", "108320"},
    "jeju_semicon": {"제주반도체", "jeju_semicon", "jeju semicon", "Jeju Semiconductor", "080220"},
    "abov": {"어보브반도체", "abov", "ABOV", "ABOV Semiconductor", "102120"},
    "telechips": {"텔레칩스", "telechips", "Telechips", "054450"},
    "coasia": {"코아시아", "coasia", "CoAsia", "045970"},
    "gaochips": {"가온칩스", "gaochips", "gaonchips", "Gaonchips", "399720"},
    "wonik_ips": {"원익IPS", "원익아이피에스", "wonik_ips", "wonik ips", "Wonik IPS", "240810"},
    "eugene_tech": {"유진테크", "eugene_tech", "eugene tech", "Eugene Technology", "084370"},
    "psk": {"피에스케이", "psk", "PSK", "319660"},
    "tes": {"테스", "tes", "TES", "095610"},
    "gst": {"GST", "지에스티", "gst", "Global Standard Technology", "083450"},
    "sti": {"에스티아이", "sti", "STI", "039440"},
    "nextin": {"넥스틴", "nextin", "NEXTIN", "348210"},
    "soulbrain": {"솔브레인", "soulbrain", "Soulbrain", "357780"},
    "dongjin_semichem": {"동진쎄미켐", "dongjin_semichem", "dongjin semichem", "Dongjin Semichem", "005290"},
    "wonik_materials": {"원익머트리얼즈", "wonik_materials", "wonik materials", "Wonik Materials", "104830"},
    "enf_tech": {"이엔에프테크놀로지", "ENF테크놀로지", "enf", "enf_tech", "ENF Technology", "102710"},
    "tck": {"티씨케이", "TCK", "tck", "064760"},
    "woldex": {"월덱스", "woldex", "Woldex", "101160"},
    "isc": {"ISC", "아이에스시", "isc", "095340"},
    "sfa_semicon": {"SFA반도체", "SFA 반도체", "에스에프에이반도체", "sfa", "sfa_semicon", "SFA Semicon", "036540"},
    "doosan_tesna": {"두산테스나", "doosan_tesna", "doosan tesna", "Doosan Tesna", "131970"},
    "leeno": {"리노공업", "leeno", "Leeno", "Leeno Industrial", "058470"},
}

REQUIRED_AFTER_AGENT = [
    "tech_chair_summary.json",
    "tech_chair_summary.md",
    "tech_ip_evidence_composite.json",
    "tech_to_value_bridge_ip_evidence_adjusted.json",
]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, default)).strip())
    except Exception:
        return default


def _parse_components(value: str | Sequence[str] | None) -> set[str]:
    """Parse KIPRIS Plus component selection.

    Accepted component names: bibliographic/biblio, claims, citation/citations, family.
    Empty value means all components. This keeps the old default behavior while
    allowing safe call-budget splitting such as bibliographic first, claims/citation
    second, and family later.
    """
    allowed = {"bibliographic", "claims", "citation", "family"}
    if value is None:
        raw = os.getenv("TECH_INTAKE_KIPRIS_PLUS_COMPONENTS", "all")
    elif isinstance(value, str):
        raw = value
    else:
        raw = ",".join(str(x) for x in value)

    raw = (raw or "all").strip().lower()
    if raw in {"", "all", "*", "plus", "kipris"}:
        return set(allowed)

    aliases = {
        "biblio": "bibliographic",
        "bibliographic": "bibliographic",
        "bibliography": "bibliographic",
        "patent_search": "bibliographic",
        "public": "bibliographic",
        "publication": "bibliographic",
        "register": "bibliographic",
        "registered": "bibliographic",
        "claim": "claims",
        "claims": "claims",
        "citation": "citation",
        "citations": "citation",
        "citing": "citation",
        "cited": "citation",
        "family": "family",
        "families": "family",
        "patfam": "family",
    }
    result: set[str] = set()
    unknown: list[str] = []
    for token in raw.replace(";", ",").replace("|", ",").split(","):
        key = token.strip().lower()
        if not key:
            continue
        mapped = aliases.get(key)
        if mapped:
            result.add(mapped)
        else:
            unknown.append(key)
    if unknown:
        raise ValueError(
            "Unknown --kipris-plus-components value(s): "
            + ", ".join(unknown)
            + ". Use bibliographic,claims,citation,family or all."
        )
    return result or set(allowed)


def _norm_alias(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def _canonical_tech_slug(value: Any) -> str:
    raw = str(value or "").strip()
    raw_norm = _norm_alias(raw)
    for slug, aliases in TECH_COMPANY_ALIASES.items():
        if raw == slug or raw_norm in {_norm_alias(slug), *{_norm_alias(alias) for alias in aliases}}:
            return slug
    return raw


def _script(name: str) -> Path:
    return ROOT / "scripts" / name


def _mask_cmd(cmd: Sequence[str]) -> str:
    text = " ".join(str(x) for x in cmd)
    for key_name in (
        "KIPRIS_PLUS_API_KEY",
        "KIPRIS_PLUS_BIBLIO_API_KEY",
        "KIPRIS_PLUS_CLAIMS_API_KEY",
        "KIPRIS_PLUS_CITATION_API_KEY",
        "KIPRIS_PLUS_FAMILY_API_KEY",
        "KIPRIS_API_KEY",
        "KIPRIS_ACCESS_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        key = os.getenv(key_name)
        if key:
            text = text.replace(key, "***KEY***")
    return text


def _run_step(
    *,
    name: str,
    cmd: list[str],
    continue_on_error: bool = True,
    timeout: int | None = None,
) -> dict[str, Any]:
    print(f"\n[Tech Intake] STEP: {name}")
    print(f"[Tech Intake] CMD : {_mask_cmd(cmd)}")
    started = datetime.now()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        status = "DONE" if proc.returncode == 0 else "FAILED"
        rec = {
            "step": name,
            "status": status,
            "returncode": proc.returncode,
            "started_at": started.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "cmd": _mask_cmd(cmd),
        }
        if proc.returncode != 0:
            print(f"[Tech Intake] WARN: {name} returncode={proc.returncode}")
            if not continue_on_error:
                raise RuntimeError(f"{name} failed with returncode={proc.returncode}")
        return rec
    except Exception as exc:
        rec = {
            "step": name,
            "status": "FAILED_EXCEPTION",
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "started_at": started.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "cmd": _mask_cmd(cmd),
        }
        print(f"[Tech Intake] ERROR: {name}: {exc}")
        print(rec["traceback"])
        if not continue_on_error:
            raise
        return rec


def _append_if_exists(steps: list[tuple[str, list[str]]], name: str, args: list[str]) -> None:
    path = _script(name)
    if path.exists():
        steps.append((name.replace(".py", ""), [PYTHON, str(path)] + args))
    else:
        print(f"[Tech Intake] SKIP missing script: {path}")


def _find_source_csv(tech_dir: Path, slug: str) -> Path | None:
    candidates = [
        tech_dir / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / f"{slug}_kipris_patents_normalized.csv",
        tech_dir / f"{slug}_tech_patent_normalized.csv",
        tech_dir / "kipris_bibliographic_normalized.csv",
        tech_dir / "kipris_patents_normalized.csv",
        tech_dir / "tech_patent_normalized.csv",
        tech_dir / "source" / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / "source" / f"{slug}_kipris_patents_normalized.csv",
        tech_dir / "source" / "kipris_bibliographic_normalized.csv",
        tech_dir / "source" / "kipris_patents_normalized.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    found = sorted(tech_dir.glob("*kipris*bibliographic*normalized*.csv"))
    return found[0] if found else None


def _copy_if_missing(src: Path, dst: Path) -> bool:
    if dst.exists() or not src.exists():
        return False
    try:
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False


def _existing_kipris_data_status(*, tech_dir: Path, slug: str, field: str) -> dict[str, Any]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path | None) -> None:
        if not path or not path.exists() or not path.is_file():
            return
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        paths.append(path)

    add(_find_source_csv(tech_dir, slug))
    for root in [tech_dir, tech_dir / "source"]:
        if not root.exists():
            continue
        for pattern in [
            "*kipris*normalized*.csv",
            "*kipris*features*.json",
            "tech_ip_*features.json",
        ]:
            for path in root.glob(pattern):
                name = path.name.lower()
                if any(skip in name for skip in ["request_log", "request_targets"]):
                    continue
                add(path)

    common_tech = field_common_dir("tech", field=field, create=False)
    if common_tech.exists():
        for pattern in [
            "*kipris*.csv",
            "*kipris*.json",
            "daily/tech_patent_quality*.csv",
            "monthly/tech_patent_quality*.csv",
        ]:
            for path in common_tech.glob(pattern):
                add(path)

    return {
        "exists": bool(paths),
        "sample_paths": [rel_project_path(path) for path in paths[:12]],
        "count": len(paths),
    }


def _ensure_alias_files(tech_dir: Path, slug: str) -> list[str]:
    """Create common-name aliases from slug-name files.

    The Tech Agent historically saved some markdown files as
    <slug>_tech_chair_summary.md.  Chair/check scripts prefer common names.
    """
    made: list[str] = []
    alias_pairs = [
        (tech_dir / f"{slug}_tech_chair_summary.md", tech_dir / "tech_chair_summary.md"),
        (tech_dir / f"{slug}_tech_full_appendix.md", tech_dir / "tech_full_appendix.md"),
        (tech_dir / f"{slug}_tech_patent_semantic_features.json", tech_dir / "tech_patent_semantic_features.json"),
        (tech_dir / f"{slug}_tech_patent_semantic_features.md", tech_dir / "tech_patent_semantic_features.md"),
    ]
    for src, dst in alias_pairs:
        if _copy_if_missing(src, dst):
            made.append(rel_project_path(dst))

    # If only JSON summary exists, create a small markdown summary so Chair/check never misses it.
    md = tech_dir / "tech_chair_summary.md"
    js = tech_dir / "tech_chair_summary.json"
    if not md.exists() and js.exists():
        try:
            obj = json.loads(js.read_text(encoding="utf-8"))
            lines = [
                f"# Tech Chair Summary - {obj.get('company_name') or obj.get('company') or slug}",
                "",
                f"- opinion: {obj.get('opinion', obj.get('recommendation', 'N/A'))}",
                f"- confidence: {obj.get('confidence', 'N/A')}",
                "",
                "## Summary",
                str(obj.get("summary") or obj.get("tech_summary") or obj.get("one_line_summary") or "")[:3000],
                "",
            ]
            md.write_text("\n".join(lines), encoding="utf-8")
            made.append(rel_project_path(md))
        except Exception:
            pass
    return made


def _copy_reference_from_nepes_if_requested(tech_dir: Path, slug: str) -> list[str]:
    copied: list[str] = []
    if slug == "nepes":
        return copied
    if not _env_bool("TECH_INTAKE_COPY_NEPES_REFERENCE_SCHEMA", True):
        return copied
    nepes_dir = company_agent_dir("nepes", "tech", create=False)
    if not nepes_dir.exists():
        return copied

    ref_dir = tech_dir / "_nepes_reference_schema"
    ref_dir.mkdir(parents=True, exist_ok=True)
    for pattern in [
        "tech_template_inventory.*",
        "tech_chair_summary.md",
        "*_tech_chair_summary.md",
        "tech_full_appendix.json",
        "*_tech_full_appendix.md",
        "tech_ip_evidence_composite.json",
        "tech_to_value_bridge_ip_evidence_adjusted.json",
    ]:
        for src in nepes_dir.glob(pattern):
            if src.is_file():
                dst = ref_dir / src.name
                try:
                    shutil.copy2(src, dst)
                    copied.append(rel_project_path(dst))
                except Exception:
                    pass
    return copied


def _artifact_status(tech_dir: Path, slug: str, skip_agent: bool) -> dict[str, Any]:
    _ensure_alias_files(tech_dir, slug)
    files = sorted(p.name for p in tech_dir.glob("*") if p.is_file())
    required = [] if skip_agent else REQUIRED_AFTER_AGENT
    missing = [name for name in required if not (tech_dir / name).exists()]
    optional = {
        "source_csv": _find_source_csv(tech_dir, slug),
        "template_inventory": tech_dir / "tech_template_inventory.json",
        "kipris_tech_ml": tech_dir / f"{slug}_kipris_tech_ml_features.json",
        "legal": tech_dir / "tech_ip_legal_features.json",
        "claim": tech_dir / "tech_ip_claim_features.json",
        "citation": tech_dir / "tech_ip_citation_features.json",
        "family": tech_dir / "tech_ip_family_features.json",
        "composite": tech_dir / "tech_ip_evidence_composite.json",
        "semantic": tech_dir / "tech_patent_semantic_features.json",
        "chair_summary_json": tech_dir / "tech_chair_summary.json",
        "chair_summary_md": tech_dir / "tech_chair_summary.md",
    }
    return {
        "file_count": len(files),
        "required_missing": missing,
        "optional_exists": {k: bool(v and Path(v).exists()) for k, v in optional.items()},
        "files_sample": files[:100],
    }


def run_tech_intake(
    *,
    company_dir: str,
    company: str | None = None,
    field: str = DEFAULT_FIELD,
    max_patents: int | None = None,
    sleep_sec: float | None = None,
    timeout: int | None = None,
    force_fetch: bool | None = None,
    skip_network: bool | None = None,
    skip_agent: bool | None = None,
    kipris_plus_components: str | Sequence[str] | None = None,
    continue_on_error: bool = True,
) -> dict[str, Any]:
    field = normalize_field_name(field)
    requested_company_dir = company_dir
    slug = _canonical_tech_slug(company_dir)
    display = DEFAULT_COMPANIES.get(slug) or company or slug
    max_patents = _env_int("TECH_INTAKE_MAX_PATENTS", 0) if max_patents is None else int(max_patents)
    sleep_sec = _env_float("TECH_INTAKE_SLEEP_SEC", 0.6) if sleep_sec is None else float(sleep_sec)
    timeout = _env_int("TECH_INTAKE_TIMEOUT", 60) if timeout is None else int(timeout)
    force_fetch = _env_bool("TECH_INTAKE_FORCE_FETCH", False) if force_fetch is None else bool(force_fetch)
    skip_network = _env_bool("TECH_INTAKE_SKIP_NETWORK", False) if skip_network is None else bool(skip_network)
    skip_agent = _env_bool("TECH_INTAKE_SKIP_AGENT", False) if skip_agent is None else bool(skip_agent)
    components = _parse_components(kipris_plus_components)

    print("=" * 88)
    print(f"Tech Data Intake: {display} / {slug}")
    print("=" * 88)
    print(f"field={field}")
    print(f"max_patents={max_patents} (0 means all normalized CSV patents)")
    print(f"sleep_sec={sleep_sec}, timeout={timeout}, force_fetch={force_fetch}")
    print(f"skip_network={skip_network}, skip_agent={skip_agent}")
    print(f"kipris_plus_components={','.join(sorted(components))}")
    if requested_company_dir != slug:
        print(f"[Tech Intake] company_dir alias resolved: {requested_company_dir} -> {slug}")

    tech_dir = company_agent_dir(slug, "tech", create=True)
    (tech_dir / "source").mkdir(parents=True, exist_ok=True)

    source_csv = _find_source_csv(tech_dir, slug)
    if not source_csv:
        print(f"[Tech Intake] INFO: normalized KIPRIS CSV not found yet. Local/free KIPRIS normalizer will run first: {tech_dir}")

    existing_kipris_data = _existing_kipris_data_status(tech_dir=tech_dir, slug=slug, field=field)
    skip_kipris_network_for_existing_data = bool(existing_kipris_data.get("exists")) and not force_fetch
    if skip_kipris_network_for_existing_data:
        print(
            "[Tech Intake] KIPRIS Plus network fetch skipped: existing tech/common KIPRIS data found "
            f"(count={existing_kipris_data.get('count')}, sample={existing_kipris_data.get('sample_paths')})"
        )

    try:
        tpl_dir = templates_dir(field=field, create=True)
    except TypeError:
        tpl_dir = templates_dir(create=True)

    template_inventory = prepare_template_references(
        template_dir=tpl_dir,
        tech_dir=tech_dir,
        company_slug=slug,
        company_name=display,
    )
    nepes_refs = _copy_reference_from_nepes_if_requested(tech_dir, slug)

    base_args = ["--field", field, "--company-name", display, "--company-slug", slug]
    steps: list[tuple[str, list[str]]] = []

    # Step 0-A. Excel-frame/template evidence extraction.
    # This is local-only, fast, and must run before Tech Agent so that
    # tech_chair_summary.json/MD can include investor-readable quantitative cards.
    _append_if_exists(steps, "build_tech_excel_quantified_metrics.py", ["--field", field, "--company-dir", slug])

    kipris_key_envs = [
        "KIPRIS_PLUS_BIBLIO_API_KEY",
        "KIPRIS_PLUS_API_KEY",
        "KIPRIS_PLUS_CLAIMS_API_KEY",
        "KIPRIS_PLUS_CITATION_API_KEY",
        "KIPRIS_PLUS_FAMILY_API_KEY",
        "KIPRIS_API_KEY",
        "KIPRIS_ACCESS_KEY",
    ]
    has_kipris_key = any(bool(os.getenv(name)) for name in kipris_key_envs)
    has_biblio_endpoint = bool(
        os.getenv("KIPRIS_PLUS_BIBLIO_ENDPOINTS")
        or os.getenv("KIPRIS_PLUS_BIBLIO_ENDPOINT")
        or os.getenv("KIPRIS_PLUS_PUBLIC_REGISTER_ENDPOINTS")
        or os.getenv("KIPRIS_PLUS_PUBLIC_REGISTER_ENDPOINT")
        or os.getenv("KIPRIS_PLUS_PATENT_SEARCH_ENDPOINTS")
        or os.getenv("KIPRIS_PLUS_PATENT_SEARCH_ENDPOINT")
        or _env_bool("KIPRIS_PLUS_BIBLIO_USE_DEFAULT_ENDPOINTS", True)
    )
    has_claims_endpoint = bool(os.getenv("KIPRIS_PLUS_CLAIMS_ENDPOINT"))
    has_citation_endpoint = bool(
        os.getenv("KIPRIS_PLUS_CITATION_ENDPOINT")
        or os.getenv("KIPRIS_CITATION_ENDPOINT")
        or os.getenv("KIPRIS_PLUS_CITING_ENDPOINT")
    )
    has_family_endpoint = bool(os.getenv("KIPRIS_PLUS_FAMILY_URL") or os.getenv("KIPRIS_FAMILY_URL"))

    # Step 0-B-0. KIPRIS Plus public/register bibliographic collector.
    # For the 25 expanded companies, there may be no manual/free KIPRIS CSV yet.
    # This step creates the same normalized CSV schema that the original 5 companies already use.
    if not skip_network and not skip_kipris_network_for_existing_data and has_kipris_key and "bibliographic" in components and has_biblio_endpoint:
        biblio_args = base_args + ["--max-patents", str(max_patents), "--sleep-sec", str(sleep_sec), "--timeout", str(timeout)]
        if force_fetch:
            biblio_args.append("--force")
        _append_if_exists(steps, "fetch_kipris_plus_bibliographic.py", biblio_args)
    elif "bibliographic" not in components:
        print("[Tech Intake] KIPRIS Plus bibliographic skipped: component not requested")
    elif skip_kipris_network_for_existing_data:
        print("[Tech Intake] KIPRIS Plus bibliographic skipped: existing tech/common KIPRIS data")
    elif skip_network:
        print("[Tech Intake] KIPRIS Plus bibliographic skipped: skip_network=True")
    elif not has_kipris_key:
        print("[Tech Intake] KIPRIS Plus bibliographic skipped: KIPRIS API key not set")
    else:
        print("[Tech Intake] KIPRIS Plus bibliographic skipped: endpoint env/default not available")

    # Step 0-B. KIPRIS free/manual fallback normalizer.
    # It scans data/<field>/<company>/tech/source for KIPRIS CSV/XLSX exports and
    # generates the normalized CSVs required by all IP feature scripts.
    # This also normalizes the paid KIPRIS Plus bibliographic raw CSV generated above.
    prepare_args = base_args + (["--force"] if force_fetch else [])
    _append_if_exists(steps, "prepare_kipris_bibliographic_normalized.py", prepare_args)

    _append_if_exists(steps, "build_kipris_tech_ml_features.py", base_args)
    _append_if_exists(steps, "build_tech_ip_legal_features.py", base_args)

    if not skip_network and not skip_kipris_network_for_existing_data and has_kipris_key and (has_biblio_endpoint or has_claims_endpoint or has_citation_endpoint or has_family_endpoint):
        claims_key_param = os.getenv("KIPRIS_PLUS_CLAIMS_KEY_PARAM", "accessKey") or "accessKey"
        claims_app_param = os.getenv("KIPRIS_PLUS_CLAIMS_APP_PARAM", "applicationNumber") or "applicationNumber"
        citation_key_param = os.getenv("KIPRIS_PLUS_CITATION_KEY_PARAM", "accessKey") or "accessKey"
        citation_app_param = os.getenv("KIPRIS_PLUS_CITATION_APP_PARAM", "applicationNumber") or "applicationNumber"
        family_key_param = os.getenv("KIPRIS_PLUS_FAMILY_KEY_PARAM", "ServiceKey") or "ServiceKey"
        family_app_param = (
            os.getenv("KIPRIS_PLUS_FAMILY_APP_PARAM")
            or os.getenv("KIPRIS_PLUS_APPNO_PARAM")
            or "applicationNumber"
        )

        network_args = base_args + ["--max-patents", str(max_patents), "--sleep-sec", str(sleep_sec), "--timeout", str(timeout)]
        if force_fetch:
            network_args.append("--force")

        if "claims" in components and has_claims_endpoint:
            _append_if_exists(steps, "fetch_kipris_plus_claims.py", network_args + ["--key-param", claims_key_param, "--app-param", claims_app_param])
        elif "claims" not in components:
            print("[Tech Intake] KIPRIS Plus claims skipped: component not requested")
        else:
            print("[Tech Intake] KIPRIS Plus claims skipped: KIPRIS_PLUS_CLAIMS_ENDPOINT not set")

        if "citation" in components and has_citation_endpoint:
            # Current citation fetcher already tries accessKey first and ServiceKey second.
            # Keep env-specific values in the manifest/printout for traceability.
            print(f"[Tech Intake] KIPRIS Plus citation param preference: key={citation_key_param}, app={citation_app_param}")
            _append_if_exists(steps, "fetch_kipris_plus_citations.py", network_args)
        elif "citation" not in components:
            print("[Tech Intake] KIPRIS Plus citations skipped: component not requested")
        else:
            print("[Tech Intake] KIPRIS Plus citations skipped: KIPRIS_PLUS_CITATION_ENDPOINT not set")

        if "family" in components and has_family_endpoint:
            _append_if_exists(
                steps,
                "fetch_kipris_plus_family.py",
                base_args
                + ["--max-patents", str(max_patents), "--sleep-sec", str(sleep_sec), "--timeout", str(timeout), "--key-param", family_key_param, "--app-param", family_app_param]
                + (["--force"] if force_fetch else []),
            )
        elif "family" not in components:
            print("[Tech Intake] KIPRIS Plus family skipped: component not requested")
        else:
            print("[Tech Intake] KIPRIS Plus family skipped: KIPRIS_PLUS_FAMILY_URL not set")
    else:
        if skip_kipris_network_for_existing_data:
            reason = "existing tech/common KIPRIS data"
        elif skip_network:
            reason = "skip_network=True"
        elif not has_kipris_key:
            reason = "KIPRIS API key not set"
        else:
            reason = "KIPRIS Plus endpoint env not set yet; using free/local KIPRIS fallback"
        print(f"[Tech Intake] KIPRIS Plus network collection skipped: {reason}")

    # Fallback builder is non-destructive by default: it fills only missing/bad
    # claim/citation/family feature files.  Do not force-overwrite richer KIPRIS
    # Plus outputs merely because approval/endpoint is temporarily unavailable.
    force_local_fallback = _env_bool("TECH_INTAKE_FORCE_LOCAL_FALLBACK", False)
    _append_if_exists(steps, "build_tech_ip_fallback_features.py", base_args + (["--force"] if force_local_fallback else []))
    _append_if_exists(steps, "build_tech_ip_evidence_composite.py", base_args)
    _append_if_exists(steps, "build_patent_semantic_fallback.py", ["--company-dir", slug, "--company", display])
    _append_if_exists(steps, "run_tech_ip_ml.py", ["--company-dir", slug])
    _append_if_exists(steps, "run_tech_ml_signal.py", ["--company-dir", slug, "--company", display])

    bridge_checker = _script("check_ip_evidence_bridge_one.py")
    if bridge_checker.exists():
        steps.append(("check_ip_evidence_bridge_one", [PYTHON, str(bridge_checker), "--tech", str(tech_dir), "--slug", slug, "--company-name", display]))

    records: list[dict[str, Any]] = []
    for name, cmd in steps:
        records.append(_run_step(name=name, cmd=cmd, continue_on_error=continue_on_error, timeout=max(timeout * 10, 120)))

    if not skip_agent:
        records.append(
            _run_step(
                name="main_py_tech_agent",
                cmd=[PYTHON, str(ROOT / "main.py"), "tech", "--company-dir", slug, "--company", display],
                continue_on_error=continue_on_error,
                timeout=max(timeout * 15, 180),
            )
        )
    else:
        print("[Tech Intake] main.py tech skipped by --tech-skip-agent / TECH_INTAKE_SKIP_AGENT=1")

    # Re-detect the source CSV after the local/free KIPRIS normalizer has run.
    source_csv = _find_source_csv(tech_dir, slug)
    if not source_csv:
        print(f"[Tech Intake] WARNING: normalized KIPRIS CSV still not found under {tech_dir}")

    aliases = _ensure_alias_files(tech_dir, slug)
    artifact = _artifact_status(tech_dir, slug, skip_agent=skip_agent)
    failed = [r for r in records if str(r.get("status", "")).startswith("FAILED")]
    if artifact["required_missing"]:
        status = "WARN_MISSING_REQUIRED_ARTIFACTS"
    elif failed:
        status = "WARN_STEP_FAILURE_WITH_FALLBACK"
    elif skip_agent:
        status = "READY_WITHOUT_AGENT"
    else:
        status = "OK"

    manifest = {
        "pipeline": "tech_intake",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "company_dir": slug,
        "company": display,
        "tech_dir": rel_project_path(tech_dir),
        "source_csv": rel_project_path(source_csv) if source_csv else None,
        "template_inventory_status": template_inventory.get("status"),
        "nepes_reference_files": nepes_refs,
        "alias_files_created": aliases,
        "kipris_plus_network_enabled": (
            not skip_network
            and not skip_kipris_network_for_existing_data
            and has_kipris_key
            and (has_biblio_endpoint or has_claims_endpoint or has_citation_endpoint or has_family_endpoint)
        ),
        "existing_kipris_data": existing_kipris_data,
        "kipris_plus_network_config": {
            "has_key": has_kipris_key,
            "has_biblio_endpoint": has_biblio_endpoint,
            "has_claims_endpoint": has_claims_endpoint,
            "has_citation_endpoint": has_citation_endpoint,
            "has_family_endpoint": has_family_endpoint,
            "mode": (
                "existing_local_or_common_data"
                if skip_kipris_network_for_existing_data
                else "plus_network"
                if (not skip_network and has_kipris_key and (has_biblio_endpoint or has_claims_endpoint or has_citation_endpoint or has_family_endpoint))
                else "free_local_fallback"
            ),
        },
        "max_patents": max_patents,
        "kipris_plus_components_requested": sorted(components),
        "steps": records,
        "artifacts": artifact,
        "reference_design": {
            "korean_patent_mcp": "Search/detail/citing functions are mirrored through local KIPRIS Plus scripts when API credentials are available.",
            "patent_sberta": "Offline TF-IDF cosine fallback is generated now; sentence-transformer PatentSBERTa can be added later without breaking intake.",
        },
    }

    manifest_path = tech_dir / "tech_intake_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (tech_dir / "tech_intake_manifest.md").write_text(
        "\n".join(
            [
                f"# Tech Intake Manifest - {display} ({slug})",
                "",
                f"- status: {status}",
                f"- source_csv: {manifest.get('source_csv')}",
                f"- kipris_plus_network_enabled: {manifest.get('kipris_plus_network_enabled')}",
                f"- kipris_mode: {(manifest.get('kipris_plus_network_config') or {}).get('mode')}",
                f"- required_missing: {artifact.get('required_missing')}",
                "",
                "## Steps",
                *[f"- {r.get('step')}: {r.get('status')} ({r.get('returncode', '')})" for r in records],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n[Tech Intake] manifest saved: {manifest_path}")
    print(f"[Tech Intake] status: {status}")
    if artifact["required_missing"]:
        print(f"[Tech Intake] missing: {artifact['required_missing']}")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AlphaProve Tech Data Intake.")
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", default="")
    parser.add_argument("--max-patents", type=int, default=None)
    parser.add_argument("--sleep-sec", type=float, default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument(
        "--kipris-plus-components",
        default=None,
        help="Comma-separated KIPRIS Plus collectors to run: bibliographic,claims,citation,family or all. Example: bibliographic,claims,citation",
    )
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--tech-force-fetch", action="store_true")
    parser.add_argument("--tech-skip-network", action="store_true")
    parser.add_argument("--tech-skip-agent", action="store_true")
    args = parser.parse_args(argv)

    run_tech_intake(
        company_dir=args.company_dir,
        company=args.company or None,
        field=args.field,
        max_patents=args.max_patents,
        sleep_sec=args.sleep_sec,
        timeout=args.timeout,
        force_fetch=args.force_fetch or args.tech_force_fetch,
        skip_network=args.skip_network or args.tech_skip_network,
        skip_agent=args.skip_agent or args.tech_skip_agent,
        kipris_plus_components=args.kipris_plus_components,
        continue_on_error=not args.stop_on_error,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from .data_paths import (
    AGENT_NAMES,
    COMPANY_COMMON_NAME,
    FIELD_COMMON_NAME,
    LEGACY_COMMON_NAME,
    DATA_DIR,
    DEFAULT_FIELD,
    KNOWN_COMPANY_DIRS,
    KNOWN_COMPANY_NAME_TO_DIR,
    ROOT_DIR,
    company_agent_dir,
    company_field,
    company_name,
    company_slug,
    decode_escaped_unicode,
    ensure_standard_tree,
    field_agent_dir,
    rel_project_path,
    safe_name,
    write_json,
    write_text,
)

# Backward-compatible names used by older modules.
WORKSPACE_DIR = DATA_DIR
OUTPUTS_DIR = DATA_DIR
PACKETS_DIR = DATA_DIR
COMPANIES_DIR = DATA_DIR
DEFAULT_OUTPUT_CATEGORY = DEFAULT_FIELD
COMMON_FOLDER_NAME = COMPANY_COMMON_NAME


def company_dir_from_name(company: Any, default: str | None = None) -> str:
    return company_slug(company, default=default)


def company_output_name(company: Any) -> str:
    return company_name(company)


def company_output_category(company: Any = None, *, default: str | None = None) -> str:
    return company_field(company, default=default)


def outputs_root(root: Path | None = None) -> Path:
    return (Path(root) if root else ROOT_DIR) / "data"


def category_output_dir(category: str | None = None, *, root: Path | None = None, create: bool = True) -> Path:
    base = outputs_root(root)
    path = base / safe_name(category or DEFAULT_FIELD, DEFAULT_FIELD)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def agent_output_dir(
    company_dir: str,
    agent_name: str,
    *,
    root: Path | None = None,
    create: bool = True,
    category: str | None = None,
) -> Path:
    return company_agent_dir(company_dir, agent_name, create=create)


def shared_output_dir(
    agent_name: str,
    *,
    root: Path | None = None,
    create: bool = True,
    category: str | None = None,
) -> Path:
    return field_agent_dir(agent_name, field=category or DEFAULT_FIELD, create=create)


def agent_output_path(
    company_dir: str,
    agent_name: str,
    filename: str,
    *,
    root: Path | None = None,
    create: bool = True,
    category: str | None = None,
) -> Path:
    return agent_output_dir(company_dir, agent_name, root=root, create=create, category=category) / filename


def packet_dir(company_dir: str, *, root: Path | None = None, create: bool = True) -> Path:
    path = company_agent_dir(company_dir, "common", create=create) / "packets"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_output_path(filename: str, *, root: Path | None = None) -> Path:
    return outputs_root(root) / filename


def _dedupe(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()

    for path in paths:
        key = str(path).replace("\\", "/")
        if key not in seen:
            result.append(path)
            seen.add(key)

    return result


def output_candidates(company_dir: str, agent_name: str, filename: str, *, root: Path | None = None) -> list[Path]:
    company_slug_value = company_dir_from_name(company_dir)
    field = company_output_category(company_slug_value)
    company_folder = company_output_name(company_slug_value)
    agent = safe_name(agent_name.lower().replace("_agent", ""), "agent")
    base = outputs_root(root)
    prefixed = filename if filename.startswith(f"{company_slug_value}_") else f"{company_slug_value}_{filename}"
    # Canonical output lookup is data-first. Legacy workspace lookup is disabled by default
    # so that running agents does not encourage or recreate the old workspace layout.
    # Set ALPHAPROVE_ENABLE_WORKSPACE_FALLBACK=1 only when migrating old local artifacts.
    enable_workspace_fallback = False
    try:
        import os
        enable_workspace_fallback = os.getenv("ALPHAPROVE_ENABLE_WORKSPACE_FALLBACK", "0") == "1"
    except Exception:
        enable_workspace_fallback = False
    legacy = (Path(root) if root else ROOT_DIR) / "workspace"

    paths = [
        base / field / company_folder / agent / filename,
        base / field / company_folder / agent / prefixed,
        base / field / company_folder / agent / filename.replace(f"{company_slug_value}_", ""),
        base / field / company_folder / COMPANY_COMMON_NAME / "packets" / filename,
        base / field / company_folder / COMPANY_COMMON_NAME / "packets" / prefixed,
        base / field / company_folder / LEGACY_COMMON_NAME / "packets" / filename,
        base / field / company_folder / LEGACY_COMMON_NAME / "packets" / prefixed,
        base / field / FIELD_COMMON_NAME / agent / filename,
        base / field / FIELD_COMMON_NAME / agent / prefixed,
        base / field / LEGACY_COMMON_NAME / agent / filename,
        base / field / LEGACY_COMMON_NAME / agent / prefixed,
    ]

    if enable_workspace_fallback and legacy.exists():
        paths.extend([
            legacy / "outputs" / field / company_folder / agent / filename,
            legacy / "outputs" / field / company_folder / agent / prefixed,
            legacy / "outputs" / company_slug_value / agent / filename,
            legacy / "outputs" / company_slug_value / agent / prefixed,
            legacy / "outputs" / filename,
            legacy / "outputs" / prefixed,
            legacy / "packets" / company_slug_value / filename,
            legacy / "packets" / company_slug_value / prefixed,
        ])

    return _dedupe(paths)


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        try:
            if path.exists():
                return path
        except Exception:
            continue
    return None


def read_json_first(paths: Iterable[Path]) -> Any | None:
    path = first_existing(paths)
    if not path:
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def read_text_first(paths: Iterable[Path]) -> str:
    path = first_existing(paths)
    if not path:
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def ensure_company_agent_tree(
    company_dirs: Iterable[str] | None = None,
    agent_names: Iterable[str] | None = None,
    *,
    category: str | None = None,
) -> list[Path]:
    return ensure_standard_tree(company_dirs or KNOWN_COMPANY_DIRS, agent_names or AGENT_NAMES, field=category or DEFAULT_FIELD)


def infer_agent_from_filename(filename: str) -> str:
    name = decode_escaped_unicode(filename).lower()

    if "tech" in name or "kipris" in name or "patent" in name or "특허" in name:
        return "tech"
    if "finance" in name or "재무" in name or "주식" in name:
        return "finance"
    if "market" in name:
        return "market"
    if "issue" in name or "이슈" in name:
        return "issue"
    if "macro" in name or "거시" in name:
        return "macro"
    if "audit" in name or "auditor" in name or "검증" in name:
        return "auditor"
    if "chair" in name or "report" in name or "보고서" in name:
        return "chair"
    if "migration" in name:
        return "migration"

    return "misc"


def infer_company_from_filename(filename: str) -> str:
    name = decode_escaped_unicode(filename).lower()

    for slug in KNOWN_COMPANY_DIRS:
        if name == slug or name.startswith(f"{slug}_") or f"_{slug}_" in name:
            return slug

    for cname, slug in KNOWN_COMPANY_NAME_TO_DIR.items():
        if cname and cname.lower() in name:
            return slug

    return ""


def canonical_output_path_for_existing(src: Path, *, root: Path | None = None, category: str | None = None) -> Path:
    name = decode_escaped_unicode(src.name)
    agent = infer_agent_from_filename(name)
    company = infer_company_from_filename(name)

    if company:
        return agent_output_path(company, agent, name, root=root, category=category)

    return shared_output_dir(agent, root=root, category=category, create=True) / name


def migrate_flat_outputs(
    *,
    root: Path | None = None,
    move: bool = False,
    overwrite: bool = False,
    cleanup_empty_dirs: bool = False,
    category: str | None = None,
) -> list[dict[str, str]]:
    legacy_base = (Path(root) if root else ROOT_DIR) / "workspace" / "outputs"
    # Do not recreate workspace during data-first operation. This helper is now migration-only.
    if not legacy_base.exists():
        return []

    ensure_company_agent_tree(category=category)

    changes: list[dict[str, str]] = []

    for src in sorted([p for p in legacy_base.rglob("*") if p.is_file()]):
        dst = canonical_output_path_for_existing(src, root=root, category=category)

        if dst.exists() and not overwrite:
            action = "skip_exists"
            if move:
                try:
                    src.unlink()
                    action = "removed_duplicate"
                except Exception:
                    pass
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if move:
                shutil.move(str(src), str(dst))
                action = "moved"
            else:
                shutil.copy2(src, dst)
                action = "copied"

        changes.append(
            {
                "action": action,
                "source": rel_project_path(src),
                "target": rel_project_path(dst),
            }
        )

    if cleanup_empty_dirs:
        for directory in sorted(
            [p for p in legacy_base.rglob("*") if p.is_dir()],
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            try:
                if not any(directory.iterdir()):
                    directory.rmdir()
            except Exception:
                pass

    return changes
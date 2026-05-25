from __future__ import annotations

"""
Migrate AlphaProve legacy workspace/* files into the canonical data/* layout.

Canonical layout:
  data/common/<global common files>
  data/<field>/common/<field-level common folders>
  data/<field>/<company-korean>/common/company.yaml
  data/<field>/<company-korean>/<agent>/<agent outputs and inputs>

This script is intentionally conservative:
- It copies by default.
- Use --move to move files after verification.
- It keeps existing src folder structure untouched.
"""

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"
DATA = ROOT / "data"
DEFAULT_FIELD = "반도체"
COMMON = "common"

SLUG_TO_NAME = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}
NAME_TO_SLUG = {v: k for k, v in SLUG_TO_NAME.items()}
NAME_TO_SLUG.update({k: k for k in SLUG_TO_NAME})
NAME_TO_SLUG.update({"LTC": "ltc", "ltc": "ltc"})


def decode_escaped_unicode(text: Any) -> str:
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text or ""))


def safe_name(value: Any, default: str = "output") -> str:
    text = decode_escaped_unicode(value).strip().strip('"').strip("'")
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text).strip("._ ")
    return text or default


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def company_meta(slug: str) -> tuple[str, str]:
    yml = WORKSPACE / "companies" / slug / "company.yaml"
    data = read_yaml(yml)
    field = safe_name(data.get("output_category") or DEFAULT_FIELD, DEFAULT_FIELD)
    name = safe_name(SLUG_TO_NAME.get(slug) or data.get("corp_name") or slug, SLUG_TO_NAME.get(slug, slug))
    return field, name


def infer_slug(text: str) -> str | None:
    name = decode_escaped_unicode(text).lower()
    for slug in SLUG_TO_NAME:
        if name == slug or name.startswith(f"{slug}_") or f"_{slug}_" in name or f"/{slug}/" in name:
            return slug
    for korean, slug in NAME_TO_SLUG.items():
        if korean and korean.lower() in name:
            return slug
    return None


def infer_agent(filename: str) -> str:
    name = decode_escaped_unicode(filename).lower()
    # Local stock-price CSV belongs to finance, not market. Market Agent
    # handles market environment/workbook/API outputs; Finance Agent consumes
    # *_주식.csv for annual return, MDD, and stock-risk metrics.
    if "주식" in name and name.endswith(".csv"):
        return "finance"
    if "first_auditor" in name or "audit" in name or "auditor" in name or "valuation_credit" in name:
        return "auditor"
    if "chair" in name or "report_quality" in name:
        return "chair"
    if "tech" in name or "kipris" in name or "patent" in name or "특허" in name:
        return "tech"
    if "finance" in name or "재무" in name:
        return "finance"
    if "market" in name:
        return "market"
    if "issue" in name or "이슈" in name:
        return "issue"
    if "macro" in name or "거시" in name:
        return "macro"
    return "misc"


def copy_or_move(src: Path, dst: Path, *, move: bool, overwrite: bool, log: list[dict[str, str]]) -> None:
    dst = Path(*[decode_escaped_unicode(p) for p in dst.parts])
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not overwrite:
        action = "skip_exists"
    else:
        if move:
            shutil.move(str(src), str(dst))
            action = "moved"
        else:
            shutil.copy2(src, dst)
            action = "copied"
    log.append({"action": action, "source": rel(src), "target": rel(dst)})


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def map_workspace_file(src: Path) -> Path:
    relp = src.relative_to(WORKSPACE)
    parts = [decode_escaped_unicode(p) for p in relp.parts]

    if len(parts) == 1 and parts[0] == "투자경고종목.csv":
        return DATA / COMMON / parts[0]

    if parts[0] == "data":
        if len(parts) >= 3 and parts[1] == "tech_sources":
            slug = parts[2]
            field, cname = company_meta(slug)
            return DATA / field / cname / "tech" / "source" / Path(*parts[3:])
        return DATA / DEFAULT_FIELD / COMMON / "data" / Path(*parts[1:])

    if parts[0] == "ml_universe":
        return DATA / DEFAULT_FIELD / COMMON / "ml_universe" / Path(*parts[1:])

    if parts[0] == "templates":
        return DATA / DEFAULT_FIELD / COMMON / "templates" / Path(*parts[1:])

    if parts[0] == "companies" and len(parts) >= 3:
        slug = parts[1]
        field, cname = company_meta(slug)
        filename = parts[-1]
        if filename == "company.yaml":
            return DATA / field / cname / COMMON / filename
        if "재무" in filename:
            return DATA / field / cname / "finance" / filename
        if "주식" in filename:
            return DATA / field / cname / "finance" / filename
        return DATA / field / cname / COMMON / Path(*parts[2:])

    if parts[0] == "packets" and len(parts) >= 3:
        slug = parts[1]
        field, cname = company_meta(slug)
        agent = infer_agent(parts[-1])
        return DATA / field / cname / agent / Path(*parts[2:])

    if parts[0] == "audit" and len(parts) >= 3:
        slug = parts[1]
        field, cname = company_meta(slug)
        return DATA / field / cname / "auditor" / Path(*parts[2:])

    if parts[0] == "quality" and len(parts) >= 2:
        slug = parts[1]
        field, cname = company_meta(slug)
        return DATA / field / cname / "chair" / "quality" / Path(*parts[2:])

    if parts[0] == "outputs":
        rest = parts[1:]
        if len(rest) >= 3 and rest[1] == COMMON:
            field = safe_name(rest[0], DEFAULT_FIELD)
            agent = safe_name(rest[2], "misc")
            return DATA / field / COMMON / agent / Path(*rest[3:])
        if len(rest) >= 3:
            # workspace/outputs/<field>/<company>/<agent>/file OR outputs/<slug>/<agent>/file
            maybe_field, maybe_company, maybe_agent = rest[0], rest[1], rest[2]
            slug = infer_slug(maybe_company) or infer_slug(rest[-1])
            if slug:
                field, cname = company_meta(slug)
                # if rest[0] looks like a field, keep it
                field = safe_name(maybe_field, field) if maybe_field not in SLUG_TO_NAME else field
                return DATA / field / cname / safe_name(maybe_agent, infer_agent(rest[-1])) / Path(*rest[3:])
            return DATA / safe_name(maybe_field, DEFAULT_FIELD) / COMMON / safe_name(maybe_agent, "misc") / Path(*rest[3:])
        if rest:
            slug = infer_slug(rest[-1])
            agent = infer_agent(rest[-1])
            if slug:
                field, cname = company_meta(slug)
                return DATA / field / cname / agent / rest[-1]
            return DATA / DEFAULT_FIELD / COMMON / agent / rest[-1]

    # fallback: preserve under data/common/legacy_workspace
    return DATA / COMMON / "legacy_workspace" / Path(*parts)


def migrate(*, move: bool = False, overwrite: bool = False) -> list[dict[str, str]]:
    if not WORKSPACE.exists():
        raise FileNotFoundError(f"workspace 폴더가 없습니다: {WORKSPACE}")

    log: list[dict[str, str]] = []
    for src in sorted([p for p in WORKSPACE.rglob("*") if p.is_file()]):
        # never migrate secrets/cache-like junk
        if any(part in {".venv", "__pycache__"} for part in src.parts):
            continue
        dst = map_workspace_file(src)
        copy_or_move(src, dst, move=move, overwrite=overwrite, log=log)

    # Create expected empty agent folders so future outputs have a clean target.
    for slug in SLUG_TO_NAME:
        field, cname = company_meta(slug)
        for agent in ["common", "finance", "market", "issue", "macro", "tech", "chair", "auditor"]:
            (DATA / field / cname / agent).mkdir(parents=True, exist_ok=True)
        (DATA / field / cname / "tech" / "source").mkdir(parents=True, exist_ok=True)
    for sub in ["data", "ml_universe", "templates", "migration", "finance", "market", "issue", "macro", "tech", "chair", "auditor"]:
        (DATA / DEFAULT_FIELD / COMMON / sub).mkdir(parents=True, exist_ok=True)
    (DATA / COMMON).mkdir(parents=True, exist_ok=True)

    summary_path = DATA / DEFAULT_FIELD / COMMON / "migration" / "workspace_to_data_migration_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy workspace/* to canonical data/* layout")
    parser.add_argument("--move", action="store_true", help="Move files instead of copying them")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing target files")
    args = parser.parse_args()
    log = migrate(move=args.move, overwrite=args.overwrite)
    print(f"[OK] migrated files: {len(log)}")
    print(f"[OK] summary: {rel(DATA / DEFAULT_FIELD / COMMON / 'migration' / 'workspace_to_data_migration_summary.json')}")
    print("[NEXT] 실행 확인 후 기존 workspace는 workspace_legacy_backup 으로 이름을 바꾸거나 삭제하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from common.data_paths import rel_project_path
except Exception:  # pragma: no cover
    def rel_project_path(value):
        return str(value).replace("\\", "/")

try:
    from openpyxl import load_workbook  # type: ignore
except Exception:  # pragma: no cover
    load_workbook = None  # type: ignore


def _safe_read_workbook(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "filename": path.name,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "sheets": [],
    }
    if not path.exists() or load_workbook is None:
        info["read_status"] = "SKIPPED_OPENPYXL_NOT_AVAILABLE" if load_workbook is None else "MISSING"
        return info

    try:
        wb = load_workbook(path, read_only=True, data_only=False)
        sheets = []
        for ws in wb.worksheets:
            sample_rows = []
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 8), values_only=True):
                sample_rows.append([str(v).strip() if v is not None else "" for v in row[:12]])
            sheets.append(
                {
                    "sheet_name": ws.title,
                    "max_row": ws.max_row,
                    "max_column": ws.max_column,
                    "sample_rows": sample_rows,
                }
            )
        info["sheets"] = sheets
        info["read_status"] = "OK"
    except Exception as exc:
        info["read_status"] = "FAILED"
        info["error"] = str(exc)
    return info


def prepare_template_references(
    *,
    template_dir: Path,
    tech_dir: Path,
    company_slug: str,
    company_name: str,
) -> dict[str, Any]:
    """Copy sector template files into the company tech folder as read-only references.

    This does not alter the source templates.  It only creates:
        data/반도체/<company>/tech/_template_refs/
        data/반도체/<company>/tech/tech_template_inventory.json
    """

    ref_dir = tech_dir / "_template_refs"
    ref_dir.mkdir(parents=True, exist_ok=True)

    template_files = sorted([p for p in template_dir.glob("*") if p.is_file()])
    copied: list[dict[str, Any]] = []
    inventory: dict[str, Any] = {
        "status": "OK" if template_files else "NO_TEMPLATE_FILES",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_slug": company_slug,
        "company_name": company_name,
        "source_template_dir": rel_project_path(template_dir),
        "reference_dir": rel_project_path(ref_dir),
        "templates": [],
        "usage_rule": (
            "Templates are references for Tech Agent output structure. "
            "Never overwrite template values blindly; extract only the schema, sheet names, and calculation frame."
        ),
    }

    for src in template_files:
        dst = ref_dir / src.name
        try:
            shutil.copy2(src, dst)
            item = _safe_read_workbook(dst) if src.suffix.lower() in {".xlsx", ".xlsm"} else {
                "filename": src.name,
                "exists": True,
                "size_bytes": dst.stat().st_size,
                "read_status": "COPIED_NON_EXCEL",
                "sheets": [],
            }
            item["copied_to"] = rel_project_path(dst)
            copied.append(item)
        except Exception as exc:
            copied.append({"filename": src.name, "read_status": "COPY_FAILED", "error": str(exc)})

    inventory["templates"] = copied
    inventory["template_count"] = len(copied)
    out = tech_dir / "tech_template_inventory.json"
    out.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# Tech Template Inventory - {company_name} ({company_slug})",
        "",
        f"- source: `{rel_project_path(template_dir)}`",
        f"- reference: `{rel_project_path(ref_dir)}`",
        f"- template_count: {len(copied)}",
        "",
        "## Templates",
    ]
    for item in copied:
        md_lines.append(f"- {item.get('filename')} / status={item.get('read_status')} / sheets={len(item.get('sheets') or [])}")
        for sheet in item.get("sheets") or []:
            md_lines.append(f"  - {sheet.get('sheet_name')} ({sheet.get('max_row')} x {sheet.get('max_column')})")
    (tech_dir / "tech_template_inventory.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return inventory

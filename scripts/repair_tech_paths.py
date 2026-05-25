from __future__ import annotations

import json
import re
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any

ROOT = Path.cwd().resolve()

FILES = {
    "chair_summary": ROOT / "src" / "tech_agent" / "chair_summary.py",
    "chair_section": ROOT / "src" / "tech_agent" / "chair_section.py",
    "tech_full_report": ROOT / "src" / "tech_agent" / "tech_full_report.py",
    "runner": ROOT / "src" / "tech_agent" / "runner.py",
}

HELPER_MARKER = "def _rel_project_path"


def _read(path: Path) -> str:
    if not path.exists():
        print(f"[SKIP] file not found: {path}")
        return ""
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _backup(path: Path) -> None:
    if not path.exists():
        return
    bak = path.with_suffix(path.suffix + ".bak_pathfix")
    if not bak.exists():
        bak.write_text(_read(path), encoding="utf-8")


def _write(path: Path, text: str) -> bool:
    if not path.exists():
        return False
    old = _read(path)
    if old == text:
        return False
    _backup(path)
    path.write_text(text, encoding="utf-8")
    return True


def _ensure_imports(text: str) -> str:
    """Ensure target file can use Path, Any, and re without breaking existing imports."""
    if not text:
        return text
    if "from pathlib import Path" not in text:
        text = text.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nfrom pathlib import Path\n", 1)
    if "from typing import" in text:
        m = re.search(r"from typing import ([^\n]+)", text)
        if m and "Any" not in {x.strip() for x in m.group(1).split(",")}:
            text = text[:m.start(1)] + m.group(1).rstrip() + ", Any" + text[m.end(1):]
    else:
        text = text.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nfrom typing import Any\n", 1)
    if re.search(r"^import re\b", text, flags=re.MULTILINE) is None:
        # Insert after future/import block. Duplicate-safe enough for repo scripts.
        lines = text.splitlines()
        insert_at = 0
        if lines and lines[0].startswith("from __future__"):
            insert_at = 1
        while insert_at < len(lines) and (lines[insert_at].startswith("import ") or lines[insert_at].startswith("from ") or not lines[insert_at].strip()):
            insert_at += 1
        lines.insert(insert_at, "import re")
        text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return text


def _ensure_root(text: str) -> str:
    if not text:
        return text
    if re.search(r"^ROOT\s*=", text, flags=re.MULTILINE):
        return text
    # Add a stable project root just before helper insertion.
    root_line = "\nROOT = Path(__file__).resolve().parents[2]\n"
    lines = text.splitlines()
    insert_at = 0
    if lines and lines[0].startswith("from __future__"):
        insert_at = 1
    while insert_at < len(lines) and (lines[insert_at].startswith("import ") or lines[insert_at].startswith("from ") or not lines[insert_at].strip()):
        insert_at += 1
    lines.insert(insert_at, root_line.strip())
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _helper_code() -> str:
    return r'''


def _rel_project_path(value: Any) -> str:
    """Return a project-relative path string for repo portability."""
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    raw = raw.replace("\\", "/")
    try:
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass
    m = re.search(r"(?:^|.*?)(workspace[\/].*)$", raw)
    if m:
        return m.group(1).replace("\\", "/")
    m = re.search(r"(?:^|.*?)(src[\/].*)$", raw)
    if m:
        return m.group(1).replace("\\", "/")
    return raw.replace("\\", "/")


def _relativize_dict_paths(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _relativize_dict_paths(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_relativize_dict_paths(v) for v in data]
    if isinstance(data, (str, Path)):
        s = str(data)
        if "workspace" in s or ":\\" in s or ":/" in s or s.startswith("/"):
            return _rel_project_path(s)
    return data
'''


def _ensure_helper(text: str) -> str:
    if not text or HELPER_MARKER in text:
        return text
    text = _ensure_imports(_ensure_root(text))
    # Insert helper after ROOT assignment block.
    m = list(re.finditer(r"^ROOT\s*=.*$", text, flags=re.MULTILINE))
    if m:
        pos = m[-1].end()
        return text[:pos] + _helper_code() + text[pos:]
    return text + _helper_code()


def _replace_once(text: str, old: str, new: str) -> str:
    return text.replace(old, new, 1) if old in text else text


def patch_chair_summary() -> bool:
    path = FILES["chair_summary"]
    text = _read(path)
    if not text:
        return False
    text = _ensure_helper(text)
    original = text

    text = text.replace('"detail_files": output_files,', '"detail_files": _relativize_dict_paths(output_files),')
    text = text.replace('"detail_files": files,', '"detail_files": _relativize_dict_paths(files),')

    # Portable summary_files values.
    text = text.replace('"chair_summary_json": str(summary_json),', '"chair_summary_json": _rel_project_path(summary_json),')
    text = text.replace('"chair_summary_md": str(summary_md),', '"chair_summary_md": _rel_project_path(summary_md),')
    text = text.replace('"tech_deep_dive_md": str(deep_dive_md),', '"tech_deep_dive_md": _rel_project_path(deep_dive_md),')

    # Markdown path tables.
    text = text.replace('lines.append(f"| {k} | `{v}` |")', 'lines.append(f"| {k} | `{_rel_project_path(v)}` |")')
    text = text.replace('lines.append(f"| {key} | `{value}` |")', 'lines.append(f"| {key} | `{_rel_project_path(value)}` |")')

    return _write(path, text) if text != original else False


def patch_tech_full_report() -> bool:
    path = FILES["tech_full_report"]
    text = _read(path)
    if not text:
        return False
    text = _ensure_helper(text)
    original = text

    text = text.replace('lines.append(f"| {key} | `{value}` |")', 'lines.append(f"| {key} | `{_rel_project_path(value)}` |")')
    text = text.replace('lines.append(f"| {k} | `{v}` |")', 'lines.append(f"| {k} | `{_rel_project_path(v)}` |")')
    text = text.replace('"path": str(output_path),', '"path": _rel_project_path(output_path),')
    text = text.replace('"meta_path": str(meta_path),', '"meta_path": _rel_project_path(meta_path),')
    text = text.replace(
        'return {"markdown": report_md, "path": str(output_path), "meta_path": str(meta_path), "payload": payload}',
        'return {"markdown": report_md, "path": _rel_project_path(output_path), "meta_path": _rel_project_path(meta_path), "payload": payload}',
    )
    # If the meta_path field is still absent in payload, add it after path.
    if '"meta_path": _rel_project_path(meta_path),' not in text:
        text = text.replace(
            '"path": _rel_project_path(output_path),\n        "created_at":',
            '"path": _rel_project_path(output_path),\n        "meta_path": _rel_project_path(meta_path),\n        "created_at":',
        )

    return _write(path, text) if text != original else False


def patch_runner() -> bool:
    path = FILES["runner"]
    text = _read(path)
    if not text:
        return False
    text = _ensure_helper(text)
    original = text

    anchor = '''    files.update({
        "tech_full_appendix_md": full_appendix.get("path"),
        "tech_full_appendix_json": full_appendix.get("meta_path"),
    })'''
    addition = '''    files.update({
        "tech_full_appendix_md": full_appendix.get("path"),
        "tech_full_appendix_json": full_appendix.get("meta_path"),
    })
    # Rewrite Tech Chair summary after the full appendix is created so Chair
    # can show a relative appendix link instead of a local absolute path.
    try:
        summary_path = ROOT / "workspace" / "packets" / cdir / "tech_chair_summary.json"
        if summary_path.exists():
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            summary_payload.setdefault("summary_files", {})["tech_full_appendix_md"] = _rel_project_path(full_appendix.get("path"))
            summary_payload.setdefault("summary_files", {})["tech_full_appendix_json"] = _rel_project_path(full_appendix.get("meta_path"))
            summary_payload["detail_files"] = _relativize_dict_paths(files)
            summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            chair_summary = summary_payload
    except Exception as exc:
        print(f"[Tech Agent] chair summary path normalization skipped: {exc}")'''
    already_has_summary_rewrite = 'summary_payload.setdefault("summary_files", {})["tech_full_appendix_md"]' in text
    if anchor in text and not already_has_summary_rewrite:
        text = text.replace(anchor, addition, 1)

    text = text.replace('"output_files":files,', '"output_files":_relativize_dict_paths(files),')
    text = text.replace('"output_files": files,', '"output_files": _relativize_dict_paths(files),')
    text = text.replace('for k,v in files.items(): print(f"  - {k}: {v}")', 'for k,v in files.items(): print(f"  - {k}: {_rel_project_path(v)}")')
    text = text.replace('for k, v in files.items(): print(f"  - {k}: {v}")', 'for k, v in files.items(): print(f"  - {k}: {_rel_project_path(v)}")')

    return _write(path, text) if text != original else False


def patch_chair_section() -> bool:
    path = FILES["chair_section"]
    text = _read(path)
    if not text:
        return False
    text = _ensure_helper(text)
    original = text

    text = re.sub(
        r'detail_md\s*=\s*files\.get\("tech_deep_dive_md"\)\s*or\s*files\.get\("chair_summary_md"\)',
        'detail_md = files.get("tech_full_appendix_md") or files.get("tech_deep_dive_md") or files.get("chair_summary_md")',
        text,
    )
    text = re.sub(
        r'detail_md\s*=\s*files\.get\("chair_summary_md"\)',
        'detail_md = files.get("tech_full_appendix_md") or files.get("tech_deep_dive_md") or files.get("chair_summary_md")',
        text,
    )
    text = text.replace('lines.append(f"- **상세 부록:** `{detail_md}`")', 'lines.append(f"- **상세 부록:** `{_rel_project_path(detail_md)}`")')

    # Make regex replacement safe when markdown contains backslashes such as C:\\.
    text = text.replace('return pat.sub(new_section.rstrip() + "\\n\\n", report, count=1)', 'return pat.sub(lambda _m: new_section.rstrip() + "\\n\\n", report, count=1)')
    text = text.replace("return pat.sub(new_section.rstrip() + '\\n\\n', report, count=1)", "return pat.sub(lambda _m: new_section.rstrip() + '\\n\\n', report, count=1)")

    return _write(path, text) if text != original else False


def _rel_project_path(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip().replace("\\", "/")
    if not raw:
        return ""
    try:
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass
    m = re.search(r"(?:^|.*?)(workspace[\/].*)$", raw)
    if m:
        return m.group(1).replace("\\", "/")
    return raw.replace("\\", "/")


def _relativize_dict_paths(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _relativize_dict_paths(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_relativize_dict_paths(v) for v in data]
    if isinstance(data, str):
        if "workspace" in data or ":\\" in data or ":/" in data or data.startswith("/"):
            return _rel_project_path(data)
    return data


def normalize_existing_outputs() -> None:
    packets = ROOT / "workspace" / "packets"
    if not packets.exists():
        print("[SKIP] workspace/packets not found")
        return

    for path in packets.glob("*/tech_chair_summary.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data.get("detail_files"), dict):
                data["detail_files"] = _relativize_dict_paths(data["detail_files"])
            data.setdefault("summary_files", {})
            company_dir = path.parent.name
            full_md = field_agent_dir("tech") / f"{company_dir}_tech_full_appendix.md"
            full_json = ROOT / "workspace" / "packets" / company_dir / "tech_full_appendix.json"
            if full_md.exists():
                data["summary_files"]["tech_full_appendix_md"] = _rel_project_path(full_md)
            if full_json.exists():
                data["summary_files"]["tech_full_appendix_json"] = _rel_project_path(full_json)
            for k, v in list(data.get("summary_files", {}).items()):
                data["summary_files"][k] = _rel_project_path(v)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] normalized {path.relative_to(ROOT)}")
        except Exception as exc:
            print(f"[WARN] skip {path}: {exc}")

    for path in packets.glob("*/tech_full_appendix.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if "path" in data:
                data["path"] = _rel_project_path(data["path"])
            if "meta_path" in data:
                data["meta_path"] = _rel_project_path(data["meta_path"])
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] normalized {path.relative_to(ROOT)}")
        except Exception as exc:
            print(f"[WARN] skip {path}: {exc}")


def main() -> int:
    changed = {
        "chair_summary.py": patch_chair_summary(),
        "tech_full_report.py": patch_tech_full_report(),
        "runner.py": patch_runner(),
        "chair_section.py": patch_chair_section(),
    }
    normalize_existing_outputs()
    for name, ok in changed.items():
        print(f"[PATCH] {name}: {'updated' if ok else 'already ok or skipped'}")
    print("[DONE] Tech path repair finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

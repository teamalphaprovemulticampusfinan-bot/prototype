from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


def _safe_extract(zip_path: Path, tmp_dir: Path) -> Path:
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError(f"unsafe zip member: {info.filename}")
        zf.extractall(tmp_dir)
    children = [p for p in tmp_dir.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return tmp_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract a bt_*.zip seed into the v49 local backtest folder.")
    ap.add_argument("--zip", required=True, help="예: C:\\Agent_6.9\\bt_2025_2026_v49.zip")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--frequency", default="monthly", choices=["monthly", "daily"])
    ap.add_argument("--run-stamp", default="20260522_150418")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--replace", action="store_true", help="기존 대상 폴더가 있으면 삭제 후 교체")
    ns = ap.parse_args(argv)

    root = Path.cwd().resolve()
    zip_path = Path(ns.zip).expanduser().resolve()
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    run_id = ns.run_id or zip_path.stem
    dst = root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / ns.frequency / "backtest" / ns.run_stamp / run_id
    if dst.exists():
        if not ns.replace:
            raise FileExistsError(f"대상 폴더가 이미 있습니다. --replace를 붙이거나 run-id/run-stamp를 바꾸세요: {dst}")
        shutil.rmtree(dst)
    tmp = root / ".cache" / "bt_seed_extract" / f"{zip_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    extracted_root = _safe_extract(zip_path, tmp)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(extracted_root, dst)
    manifest = {
        "source_zip": str(zip_path),
        "destination": str(dst),
        "field": ns.field,
        "frequency": ns.frequency,
        "run_stamp": ns.run_stamp,
        "run_id": run_id,
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }
    (dst / "IMPORTED_SEED_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

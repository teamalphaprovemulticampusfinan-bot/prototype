from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in [ROOT / "src_eval", ROOT / "src"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.null_fill import postprocess_output_root  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill blank/null evaluation-output cells without modifying production src.")
    ap.add_argument("--output-root", required=True, help="Run output folder, e.g. data/.../history_sheets_exports/monthly/backtest/<run_id>")
    ap.add_argument("--report-json", default="", help="Optional path to write a JSON report.")
    ns = ap.parse_args()
    reports = postprocess_output_root(ns.output_root)
    ok = [r for r in reports if "error" not in r]
    err = [r for r in reports if "error" in r]
    print(f"[v42-null-fill] files={len(reports)} ok={len(ok)} error={len(err)}")
    for r in reports:
        print(json.dumps(r, ensure_ascii=False))
    if ns.report_json:
        out = Path(ns.report_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[v42-null-fill] report={out}")
    return 1 if err else 0


if __name__ == "__main__":
    raise SystemExit(main())

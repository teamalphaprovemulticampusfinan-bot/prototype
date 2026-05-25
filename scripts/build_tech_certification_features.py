from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.tech_intake.certification_standards import build_certification_standard_features


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Tech Intake certification and standards features.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", default="")
    args = parser.parse_args()

    result = build_certification_standard_features(
        field=args.field,
        company_dir=args.company_dir,
        company=args.company or None,
        write=True,
    )
    print(json.dumps({
        "status": result.get("status"),
        "company": result.get("company"),
        "certification_signal": result.get("certification_signal"),
        "certification_score": result.get("certification_score"),
        "quality_gate_stage": result.get("quality_gate_stage"),
        "evidence_count": result.get("evidence_count"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

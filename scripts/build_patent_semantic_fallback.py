from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import company_agent_dir  # noqa: E402
from data_intake.tech_intake.patent_semantic_fallback import build_patent_semantic_features  # noqa: E402


def _find_source_csv(tech_dir: Path, slug: str) -> Path | None:
    candidates = [
        tech_dir / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / "kipris_bibliographic_normalized.csv",
        tech_dir / "source" / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / "source" / "kipris_bibliographic_normalized.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    found = sorted(tech_dir.glob("*kipris*bibliographic*normalized*.csv"))
    return found[0] if found else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build offline patent semantic similarity features.")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--max-rows", type=int, default=1000)
    args = parser.parse_args(argv)

    tech_dir = company_agent_dir(args.company_dir, "tech", create=True)
    source_csv = _find_source_csv(tech_dir, args.company_dir)
    if not source_csv:
        print(f"[Patent Semantic] source CSV missing for {args.company_dir}: {tech_dir}")
        return 1

    result = build_patent_semantic_features(
        source_csv=source_csv,
        output_dir=tech_dir,
        company_slug=args.company_dir,
        company_name=args.company,
        max_rows=args.max_rows,
    )
    print(f"[Patent Semantic] status={result.get('status')} count={result.get('patent_text_count')}")
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())

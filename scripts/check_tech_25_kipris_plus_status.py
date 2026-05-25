from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE5 = {"nepes", "hanmi", "hansol", "duksan", "ltc"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return max(0, sum(1 for _ in csv.DictReader(f)))
    except Exception:
        return 0


def load_targets(universe_csv: Path, mode: str) -> list[dict[str, str]]:
    with universe_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out: list[dict[str, str]] = []
    for row in rows:
        include = str(row.get("include_in_evaluation", row.get("include", "1"))).strip().lower()
        if include not in {"1", "true", "y", "yes"}:
            continue
        slug = str(row.get("company_dir") or row.get("slug") or "").strip()
        company = str(row.get("company_name") or row.get("display_name") or row.get("corp_name") or row.get("company") or "").strip()
        if not slug or not company:
            continue
        if mode == "New25" and slug in BASE5:
            continue
        if mode == "Base5" and slug not in BASE5:
            continue
        out.append({"company_dir": slug, "company": company})
    return out


def status_for(company: str, slug: str) -> dict[str, Any]:
    tech_dir = ROOT / "data" / "반도체" / company / "tech"
    chair_dir = ROOT / "data" / "반도체" / company / "chair"
    manifest_path = tech_dir / "tech_intake_manifest.json"
    manifest = read_json(manifest_path)
    source_csv = tech_dir / f"{slug}_kipris_bibliographic_normalized.csv"
    if not source_csv.exists():
        source_csv = tech_dir / "kipris_bibliographic_normalized.csv"
    biblio_summary = read_json(tech_dir / f"{slug}_kipris_plus_bibliographic_summary.json")
    optional = ((manifest.get("artifacts") or {}).get("optional_exists") or {})
    steps = manifest.get("steps") or []
    step_map = {str(s.get("step")): str(s.get("status")) for s in steps if isinstance(s, dict)}
    return {
        "company": company,
        "company_dir": slug,
        "tech_dir_exists": tech_dir.exists(),
        "manifest_status": manifest.get("status"),
        "kipris_mode": ((manifest.get("kipris_plus_network_config") or {}).get("mode")),
        "network_enabled": manifest.get("kipris_plus_network_enabled"),
        "biblio_step": step_map.get("fetch_kipris_plus_bibliographic", "MISSING"),
        "claims_step": step_map.get("fetch_kipris_plus_claims", "MISSING"),
        "citation_step": step_map.get("fetch_kipris_plus_citations", "MISSING"),
        "family_step": step_map.get("fetch_kipris_plus_family", "MISSING"),
        "source_csv_exists": source_csv.exists(),
        "source_csv_rows": count_csv_rows(source_csv),
        "biblio_summary_status": biblio_summary.get("status"),
        "biblio_rows_after_dedupe": biblio_summary.get("rows_after_dedupe"),
        "legal_exists": bool(optional.get("legal")) or (tech_dir / "tech_ip_legal_features.json").exists(),
        "claim_exists": bool(optional.get("claim")) or (tech_dir / "tech_ip_claim_features.json").exists(),
        "citation_exists": bool(optional.get("citation")) or (tech_dir / "tech_ip_citation_features.json").exists(),
        "family_exists": bool(optional.get("family")) or (tech_dir / "tech_ip_family_features.json").exists(),
        "composite_exists": bool(optional.get("composite")) or (tech_dir / "tech_ip_evidence_composite.json").exists(),
        "tech_summary_exists": (tech_dir / "tech_chair_summary.json").exists(),
        "chair_report_exists": (chair_dir / f"{slug}_chair_report.md").exists(),
        "manifest_path": str(manifest_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Tech KIPRIS Plus status for 25/30 semiconductor companies.")
    parser.add_argument("--universe-csv", default=str(ROOT / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"))
    parser.add_argument("--mode", choices=["New25", "All30", "Base5"], default="New25")
    parser.add_argument("--out", default="")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    targets = load_targets(Path(args.universe_csv), args.mode)
    rows = [status_for(t["company"], t["company_dir"]) for t in targets]

    columns = list(rows[0].keys()) if rows else []
    out_path = Path(args.out) if args.out else ROOT / "data" / "반도체" / "_sector_common" / "tech_kipris_plus_run_logs" / f"tech_kipris_plus_status_{args.mode}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[status] targets={len(rows)} out={out_path}")
    problems: list[str] = []
    for row in rows:
        bad = []
        if not row["source_csv_exists"] or int(row["source_csv_rows"] or 0) <= 0:
            bad.append("NO_SOURCE_CSV_ROWS")
        for key in ("legal_exists", "claim_exists", "citation_exists", "family_exists", "composite_exists", "tech_summary_exists"):
            if not row[key]:
                bad.append(key.upper() + "_FALSE")
        if bad:
            problems.append(f"{row['company']}({row['company_dir']}): {', '.join(bad)}")

    if problems:
        print("[problems]")
        for p in problems[:100]:
            print("- " + p)
        return 1 if args.strict else 0
    print("[OK] 모든 대상의 Tech/IP 핵심 산출물 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

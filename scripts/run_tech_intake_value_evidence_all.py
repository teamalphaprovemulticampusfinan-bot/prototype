from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.tech_intake.value_evidence_bridge import generate_value_evidence_bridge


def _read_yaml_like(path: Path) -> Dict[str, Any]:
    """Minimal company.yaml reader without requiring PyYAML."""
    data: Dict[str, Any] = {}
    if not path.exists():
        return data
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return data

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val:
            data[key] = val
    return data


def _normalize_row(row: Dict[str, Any], fallback_field: str) -> Dict[str, str]:
    lower = {str(k or "").strip().lower(): str(v or "").strip() for k, v in row.items()}
    company_dir = (
        lower.get("company_dir")
        or lower.get("slug")
        or lower.get("company_slug")
        or lower.get("ticker_slug")
        or lower.get("기업슬러그")
        or ""
    )
    company = (
        lower.get("company")
        or lower.get("company_name")
        or lower.get("name")
        or lower.get("기업명")
        or lower.get("종목명")
        or ""
    )
    field = lower.get("field") or lower.get("sector") or lower.get("분야") or fallback_field
    return {"field": field, "company_dir": company_dir, "company": company}


def _load_companies_from_csv(path: Path, field: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, errors="replace", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    item = _normalize_row(row, field)
                    if item["company_dir"]:
                        rows.append(item)
            return rows
        except Exception:
            rows = []
            continue
    return rows


def _discover_companies_from_data(field: str) -> List[Dict[str, str]]:
    """
    Discover companies from data/<field>/*/_company_common/company.yaml.
    Also falls back to data/*/*/_company_common/company.yaml because zip-extracted
    Korean paths can appear as #Uxxxx escaped directory names.
    """
    rows: List[Dict[str, str]] = []
    seen: set[str] = set()
    data_root = ROOT / "data"
    if not data_root.exists():
        return rows

    yaml_paths: List[Path] = []
    yaml_paths.extend((data_root / field).glob("*/_company_common/company.yaml"))
    yaml_paths.extend(data_root.glob("*/*/_company_common/company.yaml"))

    for yp in yaml_paths:
        if not yp.exists():
            continue
        meta = _read_yaml_like(yp)
        company_dir = (
            meta.get("company_dir")
            or meta.get("slug")
            or meta.get("company_slug")
            or yp.parents[1].name
        )
        company = (
            meta.get("company")
            or meta.get("company_name")
            or meta.get("name")
            or yp.parents[1].name
        )
        row_field = meta.get("field") or meta.get("sector") or field
        key = str(company_dir).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append({"field": str(row_field), "company_dir": key, "company": str(company)})

    return rows


def _dedupe_companies(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        slug = str(row.get("company_dir") or "").strip()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(
            {
                "field": str(row.get("field") or "반도체").strip(),
                "company_dir": slug,
                "company": str(row.get("company") or slug).strip(),
            }
        )
    return out


def _default_universe_candidates(field: str) -> List[Path]:
    return [
        ROOT / "data" / field / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv",
        ROOT / "data" / field / "_sector_common" / "universe" / "selected_30_companies.csv",
        ROOT / "data" / field / "_sector_common" / "universe" / "selected_25_companies.csv",
    ]


def load_companies(args: argparse.Namespace) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    if args.company_dir:
        for i, slug in enumerate(args.company_dir):
            company = args.company[i] if args.company and i < len(args.company) else slug
            rows.append({"field": args.field, "company_dir": slug, "company": company})
        return _dedupe_companies(rows)

    if args.universe_csv:
        p = Path(args.universe_csv)
        if not p.is_absolute():
            p = ROOT / p
        rows = _load_companies_from_csv(p, args.field)
        return _dedupe_companies(rows)

    for p in _default_universe_candidates(args.field):
        if p.exists():
            rows = _load_companies_from_csv(p, args.field)
            if rows:
                return _dedupe_companies(rows)

    return _dedupe_companies(_discover_companies_from_data(args.field))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Tech Intake Value Evidence Bridge for one or many companies."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--universe-csv", default="", help="CSV with company_dir/slug and company/company_name columns.")
    parser.add_argument("--company-dir", action="append", default=[], help="Run only selected company_dir. Can be repeated.")
    parser.add_argument("--company", action="append", default=[], help="Company name paired with --company-dir. Can be repeated.")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of companies to process.")
    parser.add_argument("--no-merge-summary", action="store_true", help="Do not merge into tech_chair_summary.json.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true", default=True)
    args = parser.parse_args(argv)

    companies = load_companies(args)
    if args.limit and args.limit > 0:
        companies = companies[: args.limit]

    print("=" * 80)
    print("[Tech Intake Value Evidence Bridge - Batch]")
    print(f"root      : {ROOT}")
    print(f"field     : {args.field}")
    print(f"companies : {len(companies)}")
    print(f"merge     : {not args.no_merge_summary}")
    print("=" * 80)

    if not companies:
        print("[ERROR] No companies found. Provide --universe-csv or --company-dir.")
        return 2

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for idx, item in enumerate(companies, start=1):
        field = item.get("field") or args.field
        slug = item.get("company_dir") or ""
        company = item.get("company") or slug
        print(f"\n[{idx}/{len(companies)}] {company} / {slug} / {field}")

        if args.dry_run:
            print("  - dry-run: skipped")
            continue

        try:
            payload = generate_value_evidence_bridge(
                company_dir=slug,
                company=company,
                field=field,
                write=True,
                merge_summary=not args.no_merge_summary,
            )
            result = {
                "field": field,
                "company": company,
                "company_dir": slug,
                "score": payload.get("value_evidence_score"),
                "label": payload.get("value_evidence_label"),
                "source_document_count": payload.get("source_document_count"),
                "output_files": payload.get("output_files"),
                "merged_summary_files": payload.get("merged_summary_files"),
            }
            results.append(result)
            print(f"  - score: {result['score']} / label: {result['label']}")
            print(f"  - outputs: {result['output_files']}")
            print(f"  - merged : {result['merged_summary_files']}")
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            errors.append({"company": company, "company_dir": slug, "error": msg})
            print(f"  - [ERROR] {msg}")
            if not args.continue_on_error:
                break

    out_dir = ROOT / "data" / args.field / "_sector_common" / "tech_value_evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "tech_value_evidence_batch_summary.json"
    summary = {
        "field": args.field,
        "processed": len(results),
        "errors": errors,
        "results": results,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("[Batch Summary]")
    print(f"processed : {len(results)}")
    print(f"errors    : {len(errors)}")
    print(f"summary   : {summary_path}")
    print("=" * 80)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

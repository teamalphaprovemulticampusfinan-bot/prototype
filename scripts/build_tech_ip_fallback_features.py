from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import company_agent_dir  # noqa: E402


def _read_csv(path: Path) -> list[dict[str, str]]:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]
        except Exception:
            continue
    return []


def _pick(row: dict[str, str], keys: list[str]) -> str:
    lower = {k.lower(): k for k in row}
    for key in keys:
        real = lower.get(key.lower())
        if real and row.get(real):
            return str(row.get(real, "")).strip()
    return ""


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


def _status_bad(path: Path, metric_keys: list[str]) -> bool:
    if not path.exists():
        return True
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return True
    status = str(obj.get("status", "")).upper()
    if status in {"OK", "MERGED"}:
        for key in metric_keys:
            val = obj.get(key)
            if isinstance(val, (int, float)) and val > 0:
                return False
        # status OK but all important metrics are zero -> still use fallback
        return True
    if "NO_" in status or "FAILED" in status or "ERROR" in status or "NOT_AVAILABLE" in status:
        return True
    return False


def _write_json_md(tech_dir: Path, slug: str, base: str, obj: dict[str, Any]) -> None:
    for name in (f"tech_ip_{base}_features.json", f"{slug}_tech_ip_{base}_features.json"):
        (tech_dir / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        f"# Tech IP {base.title()} Fallback Features",
        "",
        f"- status: {obj.get('status')}",
        f"- score: {obj.get('score_estimated', obj.get(base + '_score_estimated', 'N/A'))}",
        f"- bridge_signal: {obj.get('bridge_signal')}",
        f"- bridge_adjustment_points: {obj.get('bridge_adjustment_points')}",
        "",
        obj.get("usage_rule", ""),
    ]
    (tech_dir / f"{slug}_tech_ip_{base}_features.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _build_claim(rows: list[dict[str, str]], slug: str, company: str, source_csv: Path) -> dict[str, Any]:
    texts = []
    for r in rows:
        texts.append(
            " ".join(
                [
                    _pick(r, ["claim_text", "claims", "청구항"]),
                    _pick(r, ["abstract", "요약"]),
                    _pick(r, ["title", "invention_title", "발명의명칭", "명칭"]),
                ]
            ).strip()
        )
    usable = [t for t in texts if len(t) >= 10]
    avg_len = sum(len(t) for t in usable) / len(usable) if usable else 0.0
    # conservative estimated score: enough title/abstract text is useful, but not equivalent to real claims.
    score = min(55.0, max(20.0, avg_len / 12.0)) if usable else 20.0
    return {
        "status": "FALLBACK_ESTIMATED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_slug": slug,
        "company_name": company,
        "source_csv": str(source_csv),
        "target_patent_count": len(rows),
        "success_response_count": 0,
        "patents_with_claims": 0,
        "claim_collection_coverage": 0.0,
        "claim_count": 0,
        "independent_claim_count_estimated": 0,
        "claim_defense_score_estimated": round(score, 2),
        "score_estimated": round(score, 2),
        "bridge_adjustment_points": 0.0 if score >= 35 else -0.5,
        "bridge_signal": "IP_CLAIM_FALLBACK_ESTIMATED",
        "usage_rule": "KIPRIS Plus claims were unavailable. This conservative fallback uses bibliographic text only and must not be treated as true claim-scope evidence.",
    }


def _build_citation(rows: list[dict[str, str]], slug: str, company: str, source_csv: Path) -> dict[str, Any]:
    recent = 0
    for r in rows:
        date = _pick(r, ["application_date", "출원일", "app_date", "date"])
        m = re.search(r"(20\d{2}|19\d{2})", date)
        if m and int(m.group(1)) >= datetime.now().year - 5:
            recent += 1
    recent_rate = recent / len(rows) if rows else 0.0
    score = round(25.0 + min(20.0, recent_rate * 40.0), 2)
    return {
        "status": "FALLBACK_ESTIMATED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_slug": slug,
        "company_name": company,
        "source_csv": str(source_csv),
        "target_patent_count": len(rows),
        "forward_citation_count": 0,
        "backward_citation_count": 0,
        "citation_collection_coverage": 0.0,
        "citation_influence_score_estimated": score,
        "score_estimated": score,
        "bridge_adjustment_points": 0.0 if score >= 30 else -0.5,
        "bridge_signal": "IP_CITATION_FALLBACK_ESTIMATED",
        "usage_rule": "KIPRIS Plus citation data were unavailable. This fallback uses portfolio recency only and is not true citation impact evidence.",
    }


def _build_family(rows: list[dict[str, str]], slug: str, company: str, source_csv: Path) -> dict[str, Any]:
    overseas_tokens = ("PCT", "WO", "US", "EP", "JP", "CN")
    overseas = 0
    pct = 0
    for r in rows:
        blob = " ".join(str(v) for v in r.values()).upper()
        if any(t in blob for t in overseas_tokens):
            overseas += 1
        if "PCT" in blob or "WO" in blob:
            pct += 1
    rate = overseas / len(rows) if rows else 0.0
    score = round(25.0 + min(30.0, rate * 100.0), 2)
    return {
        "status": "FALLBACK_ESTIMATED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_slug": slug,
        "company_name": company,
        "source_csv": str(source_csv),
        "target_patent_count": len(rows),
        "family_record_count": 0,
        "patents_with_family": 0,
        "overseas_family_patent_count": overseas,
        "pct_or_wo_hint_count": pct,
        "overseas_family_patent_rate": round(rate, 4),
        "global_extension_score": score,
        "score_estimated": score,
        "bridge_adjustment_points": 0.0 if score >= 30 else -0.5,
        "bridge_signal": "IP_FAMILY_FALLBACK_ESTIMATED",
        "usage_rule": "KIPRIS Plus family data were unavailable. This fallback searches bibliographic hints only and is not true family-record evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build conservative fallback IP features when KIPRIS Plus paid endpoints are unavailable.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-slug", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    tech_dir = company_agent_dir(args.company_slug, "tech", create=True)
    source_csv = _find_source_csv(tech_dir, args.company_slug)
    rows = _read_csv(source_csv) if source_csv else []

    if not source_csv or not rows:
        print(f"[FALLBACK] source csv missing or empty: {source_csv}")
        return 1

    jobs = [
        ("claim", ["claim_defense_score_estimated"], _build_claim),
        ("citation", ["citation_influence_score_estimated", "score_estimated"], _build_citation),
        ("family", ["global_extension_score", "score_estimated"], _build_family),
    ]
    for base, metrics, builder in jobs:
        path = tech_dir / f"tech_ip_{base}_features.json"
        if args.force or _status_bad(path, metrics):
            obj = builder(rows, args.company_slug, args.company_name, source_csv)
            _write_json_md(tech_dir, args.company_slug, base, obj)
            print(f"[FALLBACK] wrote {base} features -> {path}")
        else:
            print(f"[FALLBACK] keep existing OK {base} features -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

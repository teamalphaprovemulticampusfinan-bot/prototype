from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]

AGENT_FILE_CANDIDATES: dict[str, list[str]] = {
    "finance": [
        "finance/auditor_chair_packet.json",
        "finance/*_finance_agent_packet.json",
        "finance/*_finance.json",
    ],
    "market": [
        "market/auditor_chair_packet.json",
        "market/*_market_agent_packet.json",
        "market/*_market.json",
    ],
    "tech": [
        "tech/auditor_chair_packet.json",
        "tech/*_tech_agent_packet.json",
        "tech/*_tech_chair_summary.json",
        "tech/tech_chair_summary.json",
        "tech/*_tech.json",
    ],
    "valuation": [
        "valuation/auditor_chair_packet.json",
        "valuation/*_valuation_agent_packet.json",
        "valuation/*_valuation_metrics.json",
        "valuation/*_dashboard_payload.json",
    ],
    "issue": [
        "issue/auditor_chair_packet.json",
        "issue/*_issue_agent_packet.json",
        "issue/*_issue.json",
    ],
    "macro": [
        "macro/auditor_chair_packet.json",
        "macro/*_macro_agent_packet.json",
        "macro/*_macro.json",
        "macro/macro_signal_*.json",
    ],
    "chair": [
        "chair/*_chair_agent_packet.json",
        "chair/*_chair.json",
    ],
}


def read_universe_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_dir = (
                row.get("company_dir")
                or row.get("slug")
                or row.get("company_slug")
                or row.get("ticker_slug")
                or ""
            ).strip()
            company = (
                row.get("company")
                or row.get("company_name")
                or row.get("name")
                or row.get("기업명")
                or ""
            ).strip()
            if company_dir and company:
                rows.append({"company_dir": company_dir, "company": company})
    return rows


def company_root(field: str, company_dir: str, company: str) -> Path:
    base = PROJECT_ROOT / "data" / field
    for candidate in [base / company, base / company_dir]:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return base / company


def find_json(root: Path, agent: str) -> Path | None:
    candidates: list[Path] = []
    for pat in AGENT_FILE_CANDIDATES.get(agent, []):
        candidates.extend([p for p in root.glob(pat) if p.is_file()])
    if not candidates:
        return None
    candidates.sort(key=lambda p: (p.stat().st_mtime, len(str(p))), reverse=True)
    return candidates[0]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def deep_find(obj: Any, keys: set[str], max_depth: int = 8) -> Any:
    if max_depth < 0:
        return None
    if isinstance(obj, dict):
        for k, v in obj.items():
            if norm_key(k) in keys and v not in (None, "", [], {}):
                return v
        for v in obj.values():
            found = deep_find(v, keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(obj, list):
        for item in obj[:200]:
            found = deep_find(item, keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found
    return None


def sha256_json(payload: Any) -> tuple[str, int]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw = text.encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def main() -> int:
    ap = argparse.ArgumentParser(description="현재 로컬 data/<field>/<company>/<agent> JSON을 그대로 인식하는지 먼저 점검합니다.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--agents", nargs="*", default=AGENTS)
    args = ap.parse_args()

    targets = read_universe_csv(Path(args.universe_csv))
    if args.limit:
        targets = targets[: args.limit]

    out_dir = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_sheets_exports" / "checks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"local_agent_json_recognition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    fieldnames = [
        "field", "company", "company_dir", "agent", "status", "source_file", "payload_hash", "payload_bytes",
        "top_keys", "detected_recommendation", "detected_signal", "detected_created_at", "error",
    ]
    rows: list[dict[str, Any]] = []

    print("=" * 100)
    print("[Local Agent JSON Recognition Check]")
    print(f"field       : {args.field}")
    print(f"targets     : {len(targets)}")
    print(f"agents      : {args.agents}")
    print(f"output_csv  : {out_csv}")
    print("=" * 100)

    for t in targets:
        root = company_root(args.field, t["company_dir"], t["company"])
        for agent in args.agents:
            row = {
                "field": args.field,
                "company": t["company"],
                "company_dir": t["company_dir"],
                "agent": agent,
                "status": "MISSING",
                "source_file": "",
                "payload_hash": "",
                "payload_bytes": "",
                "top_keys": "",
                "detected_recommendation": "",
                "detected_signal": "",
                "detected_created_at": "",
                "error": "",
            }
            path = find_json(root, agent)
            if not path:
                row["error"] = f"JSON not found under {root}"
                rows.append(row)
                print(f"[MISSING] {t['company']} / {agent}")
                continue
            try:
                payload = read_json(path)
                h, n = sha256_json(payload)
                row.update({
                    "status": "OK",
                    "source_file": str(path.relative_to(PROJECT_ROOT)),
                    "payload_hash": h,
                    "payload_bytes": n,
                    "top_keys": ",".join(list(payload.keys())[:30]) if isinstance(payload, dict) else type(payload).__name__,
                    "detected_recommendation": deep_find(payload, {"auditor_recommendation", "recommendation", "opinion", "final_recommendation", "final_opinion"}) or "",
                    "detected_signal": deep_find(payload, {"auditor_signal", "weighted_signal", "signal", "directional_signal"}) or "",
                    "detected_created_at": deep_find(payload, {"created_at", "timestamp", "run_at"}) or "",
                })
                print(f"[OK] {t['company']} / {agent}: {row['source_file']} | {n} bytes")
            except Exception as exc:
                row["status"] = "ERROR"
                row["source_file"] = str(path.relative_to(PROJECT_ROOT))
                row["error"] = str(exc)
                print(f"[ERROR] {t['company']} / {agent}: {exc}")
            rows.append(row)

    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    ok = sum(1 for r in rows if r["status"] == "OK")
    missing = sum(1 for r in rows if r["status"] == "MISSING")
    err = sum(1 for r in rows if r["status"] == "ERROR")
    print("=" * 100)
    print(f"OK={ok} | MISSING={missing} | ERROR={err}")
    print(f"CSV={out_csv}")
    print("=" * 100)
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

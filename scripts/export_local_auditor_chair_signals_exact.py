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

AUDITOR_PACKET_CANDIDATES = [
    "auditor/first_auditor/compact_agent_packets/auditor_chair_packet.json",
    "auditor/first_auditor/auditor_chair_packet.json",
    "chair/auditor_chair_packet.json",
]
CHAIR_CANDIDATES = [
    "chair/*_chair_agent_packet.json",
    "chair/*_chair.json",
    "chair/chair_agent_packet.json",
    "chair/chair.json",
]


def read_universe_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_dir = (row.get("company_dir") or row.get("slug") or row.get("company_slug") or "").strip()
            company = (row.get("company") or row.get("company_name") or row.get("name") or row.get("기업명") or "").strip()
            if company_dir and company:
                rows.append({"company_dir": company_dir, "company": company})
    return rows


def company_root(field: str, company_dir: str, company: str) -> Path:
    base = PROJECT_ROOT / "data" / field
    for p in [base / company, base / company_dir]:
        if p.exists() and p.is_dir():
            return p
    return base / company


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest_glob(root: Path, patterns: list[str]) -> Path | None:
    matches: list[Path] = []
    for pat in patterns:
        matches.extend([p for p in root.glob(pat) if p.is_file()])
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def deep_find(obj: Any, keys: set[str], max_depth: int = 10) -> Any:
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
        for item in obj[:300]:
            found = deep_find(item, keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found
    return None


def to_json_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False)


def sha256_payload(payload: Any) -> tuple[str, int]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw = text.encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def normalize_packet_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidate_keys = [
        "compact_agent_packets",
        "auditor_compact_packets",
        "agent_packets",
        "packets",
        "chair_input_packets",
        "raw_packets",
        "opinions",
    ]
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, list):
            packets = [x for x in value if isinstance(x, dict)]
            if packets:
                return packets
        if isinstance(value, dict):
            packets = []
            for agent, packet in value.items():
                if isinstance(packet, dict):
                    p = dict(packet)
                    p.setdefault("agent", agent)
                    packets.append(p)
            if packets:
                return packets
    # Auditor receipt의 result.agent_results 구조 지원
    agent_results = deep_find(payload, {"agent_results"})
    if isinstance(agent_results, dict):
        packets = []
        for agent, packet in agent_results.items():
            if isinstance(packet, dict):
                p = dict(packet)
                p.setdefault("agent", agent)
                packets.append(p)
        if packets:
            return packets
    # 최상위 agent 키 구조 지원
    packets = []
    for agent in AGENTS:
        value = payload.get(agent)
        if isinstance(value, dict):
            p = dict(value)
            p.setdefault("agent", agent)
            packets.append(p)
    return packets


def packet_agent(packet: dict[str, Any], fallback: str) -> str:
    return str(packet.get("agent") or packet.get("agent_name") or packet.get("name") or fallback).strip()


def extract_signal(packet: dict[str, Any]) -> Any:
    value = deep_find(packet, {"auditor_signal", "weighted_signal", "signal", "directional_signal", "score_signal"})
    return value


def extract_recommendation(packet: dict[str, Any]) -> Any:
    return deep_find(packet, {"auditor_recommendation", "recommendation", "opinion", "final_recommendation", "final_opinion"})


def summarize_packets(packets: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    agents: list[str] = []
    signals: dict[str, Any] = {}
    recs: dict[str, Any] = {}
    for i, p in enumerate(packets):
        agent = packet_agent(p, f"packet_{i+1}")
        agents.append(agent)
        signal = extract_signal(p)
        rec = extract_recommendation(p)
        if signal not in (None, "", [], {}):
            signals[agent] = signal
        if rec not in (None, "", [], {}):
            recs[agent] = rec
    return agents, signals, recs


def main() -> int:
    ap = argparse.ArgumentParser(description="로컬 auditor_chair_packet/chair JSON에서 기존 형식 그대로 signal CSV를 추출합니다.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--as-of-date", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--run-id", default="local_existing_json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    targets = read_universe_csv(Path(args.universe_csv))
    if args.limit:
        targets = targets[: args.limit]

    out_dir = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_sheets_exports" / f"local_exact_{args.as_of_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"auditor_chair_packets_{args.as_of_date}_{args.run_id}.csv"

    fieldnames = [
        "run_id", "as_of_date", "field", "company", "company_dir",
        "packet_agent_count", "packet_agents", "packet_signals", "packet_recommendations",
        "auditor_final_recommendation", "auditor_weighted_signal", "auditor_passed", "failed_agents",
        "chair_final_recommendation", "chair_weighted_signal",
        "payload_hash", "payload_bytes", "created_at",
        "auditor_source_file", "chair_source_file",
    ] + [f"{a}_signal" for a in AGENTS] + [f"{a}_recommendation" for a in AGENTS]

    rows: list[dict[str, Any]] = []
    print("=" * 100)
    print("[Local Exact Auditor/Chair Signal Export]")
    print(f"field       : {args.field}")
    print(f"as_of_date  : {args.as_of_date}")
    print(f"targets     : {len(targets)}")
    print(f"output_csv  : {out_csv}")
    print("=" * 100)

    for t in targets:
        root = company_root(args.field, t["company_dir"], t["company"])
        auditor_path = latest_glob(root, AUDITOR_PACKET_CANDIDATES)
        chair_path = latest_glob(root, CHAIR_CANDIDATES)
        auditor_payload = read_json(auditor_path) if auditor_path else {}
        chair_payload = read_json(chair_path) if chair_path else {}
        packets = normalize_packet_list(auditor_payload)
        packet_agents, packet_signals, packet_recs = summarize_packets(packets)
        h, n = sha256_payload(auditor_payload)
        row: dict[str, Any] = {
            "run_id": args.run_id,
            "as_of_date": args.as_of_date,
            "field": args.field,
            "company": t["company"],
            "company_dir": t["company_dir"],
            "packet_agent_count": len(packet_agents),
            "packet_agents": ",".join(packet_agents),
            "packet_signals": to_json_text(packet_signals),
            "packet_recommendations": to_json_text(packet_recs),
            "auditor_final_recommendation": deep_find(auditor_payload, {"auditor_final_recommendation", "final_recommendation", "recommendation"}) or "",
            "auditor_weighted_signal": deep_find(auditor_payload, {"auditor_weighted_signal", "weighted_signal", "final_weighted_signal"}) or "",
            "auditor_passed": deep_find(auditor_payload, {"auditor_passed", "passed", "raw_passed"}) if deep_find(auditor_payload, {"auditor_passed", "passed", "raw_passed"}) is not None else "",
            "failed_agents": to_json_text(deep_find(auditor_payload, {"failed_agents", "failed_agent_names"})),
            "chair_final_recommendation": deep_find(chair_payload, {"final_recommendation", "recommendation", "opinion", "final_opinion"}) or "",
            "chair_weighted_signal": deep_find(chair_payload, {"weighted_signal", "chair_weighted_signal", "final_weighted_signal"}) or "",
            "payload_hash": h,
            "payload_bytes": n,
            "created_at": deep_find(auditor_payload, {"created_at", "timestamp", "run_at"}) or "",
            "auditor_source_file": str(auditor_path.relative_to(PROJECT_ROOT)) if auditor_path else "MISSING",
            "chair_source_file": str(chair_path.relative_to(PROJECT_ROOT)) if chair_path else "MISSING",
        }
        for a in AGENTS:
            row[f"{a}_signal"] = packet_signals.get(a, "")
            row[f"{a}_recommendation"] = packet_recs.get(a, "")
        rows.append(row)
        print(f"[ROW] {t['company']} | packets={len(packet_agents)} | auditor={row['auditor_source_file']} | chair={row['chair_source_file']}")

    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 100)
    print(f"rows={len(rows)}")
    print(f"output={out_csv}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

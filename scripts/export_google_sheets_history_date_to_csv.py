from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

os.environ.setdefault("ALPHAPROVE_HISTORY_BACKEND", "sheets")

from common.agent_history import list_run_results  # noqa: E402

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def to_json_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False)


def deep_find(obj: Any, target_keys: set[str], max_depth: int = 8) -> Any:
    if max_depth < 0:
        return None
    if isinstance(obj, dict):
        for k, v in obj.items():
            if norm_key(k) in target_keys and v not in (None, "", [], {}):
                return v
        for v in obj.values():
            found = deep_find(v, target_keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(obj, list):
        for item in obj[:120]:
            found = deep_find(item, target_keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found
    return None


def extract_packets(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ["compact_agent_packets", "auditor_compact_packets", "agent_packets", "packets", "auditor_chair_packet", "chair_input_packets"]:
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


def packet_summaries(packets: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    agents = []
    signals = {}
    recs = {}
    for i, p in enumerate(packets):
        agent = packet_agent(p, f"packet_{i + 1}")
        agents.append(agent)
        signal = deep_find(p, {"auditor_signal", "weighted_signal", "signal", "directional_signal"})
        rec = deep_find(p, {"auditor_recommendation", "recommendation", "opinion", "final_recommendation"})
        if signal not in (None, "", [], {}):
            signals[agent] = signal
        if rec not in (None, "", [], {}):
            recs[agent] = rec
    return agents, signals, recs


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def latest_by_company(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest = {}
    for row in rows:
        key = row.get("company_dir") or row.get("company")
        if not key:
            continue
        if key not in latest or str(row.get("created_at", "")) >= str(latest[key].get("created_at", "")):
            latest[key] = row
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(description="Google Sheets history에서 특정 날짜의 auditor/chair 결과 CSV만 로컬로 추출합니다.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--include-payload-json", action="store_true")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_sheets_exports" / f"{args.as_of_date}_{timestamp}"

    base_filters = {
        "field": args.field,
        "as_of_date": args.as_of_date,
        "run_id": args.run_id.strip() or None,
        "include_payload": True,
    }

    print("=" * 100)
    print("[Google Sheets History Export → Local CSV]")
    print(f"field      : {args.field}")
    print(f"as_of_date : {args.as_of_date}")
    print(f"run_id     : {args.run_id or '(all runs for date)'}")
    print(f"output_dir : {out_dir}")
    print("local files: auditor/chair CSV only")
    print("=" * 100)

    auditor_raw = list_run_results(agent="auditor", **base_filters)
    chair_raw = list_run_results(agent="chair", **base_filters)

    auditor_rows: list[dict[str, Any]] = []
    for item in auditor_raw:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        packets = extract_packets(payload)
        packet_agents, packet_signals, packet_recs = packet_summaries(packets)
        row = {
            "run_id": item.get("run_id", ""),
            "as_of_date": item.get("as_of_date", args.as_of_date),
            "field": item.get("field", args.field),
            "company": item.get("company_name", "") or deep_find(payload, {"company", "company_name", "corp_name"}) or "",
            "company_dir": item.get("company_dir", "") or deep_find(payload, {"company_dir", "slug", "company_slug"}) or "",
            "output_kind": item.get("output_kind", ""),
            "packet_agent_count": len(packet_agents),
            "packet_agents": ",".join(packet_agents),
            "packet_signals": to_json_text(packet_signals),
            "packet_recommendations": to_json_text(packet_recs),
            "auditor_final_recommendation": deep_find(payload, {"auditor_final_recommendation", "final_recommendation", "recommendation"}) or "",
            "auditor_weighted_signal": deep_find(payload, {"auditor_weighted_signal", "weighted_signal", "final_weighted_signal"}) or "",
            "auditor_passed": deep_find(payload, {"auditor_passed", "passed", "raw_passed"}) if deep_find(payload, {"auditor_passed", "passed", "raw_passed"}) is not None else "",
            "failed_agents": to_json_text(deep_find(payload, {"failed_agents", "failed_agent_names"})),
            "payload_hash": item.get("payload_hash", ""),
            "payload_bytes": item.get("payload_bytes", ""),
            "created_at": item.get("created_at", ""),
        }
        if args.include_payload_json:
            row["payload_json"] = to_json_text(payload)
        auditor_rows.append(row)

    chair_rows: list[dict[str, Any]] = []
    for item in chair_raw:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        row = {
            "run_id": item.get("run_id", ""),
            "as_of_date": item.get("as_of_date", args.as_of_date),
            "field": item.get("field", args.field),
            "company": item.get("company_name", "") or deep_find(payload, {"company", "company_name", "corp_name"}) or "",
            "company_dir": item.get("company_dir", "") or deep_find(payload, {"company_dir", "slug", "company_slug"}) or "",
            "output_kind": item.get("output_kind", ""),
            "final_recommendation": deep_find(payload, {"final_recommendation", "recommendation", "opinion", "final_opinion"}) or "",
            "weighted_signal": deep_find(payload, {"weighted_signal", "chair_weighted_signal", "final_weighted_signal"}) or "",
            "chair_report_chars": len(str(deep_find(payload, {"chair_report", "report", "markdown"}) or "")),
            "payload_hash": item.get("payload_hash", ""),
            "payload_bytes": item.get("payload_bytes", ""),
            "created_at": item.get("created_at", ""),
        }
        if args.include_payload_json:
            row["payload_json"] = to_json_text(payload)
        chair_rows.append(row)

    auditor_fields = [
        "run_id", "as_of_date", "field", "company", "company_dir", "output_kind",
        "packet_agent_count", "packet_agents", "packet_signals", "packet_recommendations",
        "auditor_final_recommendation", "auditor_weighted_signal", "auditor_passed", "failed_agents",
        "payload_hash", "payload_bytes", "created_at",
    ]
    chair_fields = [
        "run_id", "as_of_date", "field", "company", "company_dir", "output_kind",
        "final_recommendation", "weighted_signal", "chair_report_chars",
        "payload_hash", "payload_bytes", "created_at",
    ]
    if args.include_payload_json:
        auditor_fields.append("payload_json")
        chair_fields.append("payload_json")

    auditor_csv = out_dir / f"auditor_chair_packets_{args.as_of_date}.csv"
    chair_csv = out_dir / f"chair_results_{args.as_of_date}.csv"
    write_csv(auditor_csv, auditor_rows, auditor_fields)
    write_csv(chair_csv, chair_rows, chair_fields)

    latest_auditor = latest_by_company(auditor_rows)
    latest_chair = latest_by_company(chair_rows)
    keys = sorted(set(latest_auditor) | set(latest_chair))
    combined_rows = []
    for key in keys:
        a = latest_auditor.get(key, {})
        c = latest_chair.get(key, {})
        combined_rows.append({
            "as_of_date": args.as_of_date,
            "field": args.field,
            "company": c.get("company") or a.get("company") or "",
            "company_dir": c.get("company_dir") or a.get("company_dir") or key,
            "latest_run_id": c.get("run_id") or a.get("run_id") or "",
            "chair_final_recommendation": c.get("final_recommendation", ""),
            "chair_weighted_signal": c.get("weighted_signal", ""),
            "auditor_packet_agent_count": a.get("packet_agent_count", ""),
            "auditor_packet_agents": a.get("packet_agents", ""),
            "auditor_packet_signals": a.get("packet_signals", ""),
            "auditor_packet_recommendations": a.get("packet_recommendations", ""),
            "auditor_passed": a.get("auditor_passed", ""),
            "failed_agents": a.get("failed_agents", ""),
            "chair_created_at": c.get("created_at", ""),
            "auditor_created_at": a.get("created_at", ""),
        })
    combined_csv = out_dir / f"auditor_chair_dataset_{args.as_of_date}.csv"
    write_csv(combined_csv, combined_rows, [
        "as_of_date", "field", "company", "company_dir", "latest_run_id",
        "chair_final_recommendation", "chair_weighted_signal",
        "auditor_packet_agent_count", "auditor_packet_agents", "auditor_packet_signals",
        "auditor_packet_recommendations", "auditor_passed", "failed_agents",
        "chair_created_at", "auditor_created_at",
    ])

    print("=" * 100)
    print("[DONE]")
    print(f"auditor_rows : {len(auditor_rows)}")
    print(f"chair_rows   : {len(chair_rows)}")
    print(f"dataset_rows : {len(combined_rows)}")
    print(f"auditor_csv  : {auditor_csv}")
    print(f"chair_csv    : {chair_csv}")
    print(f"dataset_csv  : {combined_csv}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

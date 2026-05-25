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

from common.agent_history import list_run_results, history_source_label  # noqa: E402

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


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


def normalize_packet_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in [
        "compact_agent_packets",
        "auditor_compact_packets",
        "agent_packets",
        "packets",
        "chair_input_packets",
        "raw_packets",
        "opinions",
    ]:
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
    return deep_find(packet, {"auditor_signal", "weighted_signal", "signal", "directional_signal", "score_signal"})


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


def latest_by_company(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("company_dir") or row.get("company") or ""
        if not key:
            continue
        if key not in latest or str(row.get("created_at", "")) >= str(latest[key].get("created_at", "")):
            latest[key] = row
    return latest


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{k: r.get(k, "") for k in fieldnames} for r in rows])


def main() -> int:
    ap = argparse.ArgumentParser(description="Google Sheets history에서 auditor 각 agent signal과 Chair 매수/보유/매도를 기존 CSV 형식으로 추출합니다.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--as-of-date", required=True)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--include-all-runs", action="store_true")
    args = ap.parse_args()

    run_filter = None if args.include_all_runs or not args.run_id.strip() else args.run_id.strip()
    out_dir = PROJECT_ROOT / "data" / args.field / "_sector_common" / "history_sheets_exports" / f"signals_{args.as_of_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("[Google Sheets Exact Auditor/Chair Signal Export]")
    print(f"backend    : {history_source_label()}")
    print(f"field      : {args.field}")
    print(f"as_of_date : {args.as_of_date}")
    print(f"run_id     : {run_filter or '(all runs for date, latest per company in dataset)'}")
    print(f"output_dir : {out_dir}")
    print("=" * 100)

    auditor_items = list_run_results(
        run_id=run_filter,
        as_of_date=args.as_of_date,
        field=args.field,
        agent="auditor",
        output_kind="auditor_chair_packet_json",
        include_payload=True,
    )
    chair_items = list_run_results(
        run_id=run_filter,
        as_of_date=args.as_of_date,
        field=args.field,
        agent="chair",
        include_payload=True,
    )

    auditor_rows: list[dict[str, Any]] = []
    for item in auditor_items:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        packets = normalize_packet_list(payload)
        packet_agents, packet_signals, packet_recs = summarize_packets(packets)
        row: dict[str, Any] = {
            "run_id": item.get("run_id", ""),
            "as_of_date": item.get("as_of_date", args.as_of_date),
            "field": item.get("field", args.field),
            "company": item.get("company_name", "") or deep_find(payload, {"company", "company_name", "corp_name"}) or "",
            "company_dir": item.get("company_dir", "") or deep_find(payload, {"company_dir", "slug", "company_slug"}) or "",
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
        for a in AGENTS:
            row[f"{a}_signal"] = packet_signals.get(a, "")
            row[f"{a}_recommendation"] = packet_recs.get(a, "")
        auditor_rows.append(row)

    chair_rows: list[dict[str, Any]] = []
    for item in chair_items:
        if item.get("output_kind") not in {"chair_agent_packet_json", "chair_json", "chair_result_json"}:
            continue
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        chair_rows.append({
            "run_id": item.get("run_id", ""),
            "as_of_date": item.get("as_of_date", args.as_of_date),
            "field": item.get("field", args.field),
            "company": item.get("company_name", "") or deep_find(payload, {"company", "company_name", "corp_name"}) or "",
            "company_dir": item.get("company_dir", "") or deep_find(payload, {"company_dir", "slug", "company_slug"}) or "",
            "chair_final_recommendation": deep_find(payload, {"final_recommendation", "recommendation", "opinion", "final_opinion"}) or "",
            "chair_weighted_signal": deep_find(payload, {"weighted_signal", "chair_weighted_signal", "final_weighted_signal"}) or "",
            "chair_output_kind": item.get("output_kind", ""),
            "chair_payload_hash": item.get("payload_hash", ""),
            "chair_payload_bytes": item.get("payload_bytes", ""),
            "chair_created_at": item.get("created_at", ""),
        })

    latest_chair = latest_by_company(chair_rows)
    combined_rows: list[dict[str, Any]] = []
    for a in auditor_rows:
        c = latest_chair.get(a.get("company_dir", ""), {})
        row = dict(a)
        row["chair_final_recommendation"] = c.get("chair_final_recommendation", "")
        row["chair_weighted_signal"] = c.get("chair_weighted_signal", "")
        row["chair_created_at"] = c.get("chair_created_at", "")
        combined_rows.append(row)

    fieldnames = [
        "run_id", "as_of_date", "field", "company", "company_dir",
        "packet_agent_count", "packet_agents", "packet_signals", "packet_recommendations",
        "auditor_final_recommendation", "auditor_weighted_signal", "auditor_passed", "failed_agents",
        "chair_final_recommendation", "chair_weighted_signal",
        "payload_hash", "payload_bytes", "created_at", "chair_created_at",
    ] + [f"{a}_signal" for a in AGENTS] + [f"{a}_recommendation" for a in AGENTS]

    out_csv = out_dir / f"auditor_chair_packets_{args.as_of_date}_{run_filter or 'all_runs'}.csv"
    write_csv(out_csv, combined_rows, fieldnames)

    print("=" * 100)
    print("[DONE]")
    print(f"auditor_result_rows : {len(auditor_items)}")
    print(f"chair_result_rows   : {len(chair_rows)}")
    print(f"export_rows         : {len(combined_rows)}")
    print(f"output              : {out_csv}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

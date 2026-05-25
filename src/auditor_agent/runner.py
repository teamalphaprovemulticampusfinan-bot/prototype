from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from chair_agent.adapters import (
    run_finance_for_chair,
    run_issue_for_chair,
    run_macro_for_chair,
    run_market_for_chair,
    run_tech_for_chair,
    run_valuation_for_chair,
)
from auditor_agent.first_gate import run_first_auditor


AGENT_RUNNERS = {
    "finance": run_finance_for_chair,
    "market": run_market_for_chair,
    "tech": run_tech_for_chair,
    "valuation": run_valuation_for_chair,
    "issue": run_issue_for_chair,
    "macro": run_macro_for_chair,
}


def _split_agents(value: str | None) -> list[str]:
    if not value:
        return list(AGENT_RUNNERS)
    aliases = {"all": list(AGENT_RUNNERS), "6": list(AGENT_RUNNERS)}
    text = value.strip().lower()
    if text in aliases:
        return aliases[text]
    out: list[str] = []
    for part in value.replace(";", ",").split(","):
        name = part.strip().lower()
        if not name:
            continue
        if name not in AGENT_RUNNERS:
            raise ValueError(f"지원하지 않는 agent: {name}. 가능 목록: {', '.join(AGENT_RUNNERS)}")
        out.append(name)
    return out or list(AGENT_RUNNERS)


def collect_agent_packets(company_dir: str, company: str, agents: list[str]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for agent in agents:
        print(f"[Auditor CLI] {agent} agent packet 수집 중...")
        packet = AGENT_RUNNERS[agent](company_dir, company)
        if isinstance(packet, dict):
            packet.setdefault("agent", agent)
            packets.append(packet)
            print(f"[Auditor CLI] {agent} 완료 → packet_keys={len(packet.keys())}")
    return packets


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run First Auditor over the 6 AlphaProve agents without generating a Chair report."
    )
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--agents", default="finance,market,tech,valuation,issue,macro")
    parser.add_argument("--max-rounds", type=int, default=1, help="구버전 호환 인자입니다. 현재 Auditor는 재시도 라운드 없이 내부 3차 검증을 1회 수행합니다.")
    parser.add_argument("--fail-open", action="store_true", help="검증 미통과여도 프로세스 종료코드 0으로 반환")
    parser.add_argument("--json", action="store_true", help="Auditor 결과 JSON을 콘솔에 출력")
    args = parser.parse_args(argv)

    agents = _split_agents(args.agents)
    packets = collect_agent_packets(args.company_dir, args.company, agents)
    result = run_first_auditor(
        company_dir=args.company_dir,
        company=args.company,
        opinions=packets,
        max_rounds=args.max_rounds,
    )

    print(
        "[Auditor CLI] 완료: "
        f"mode=fixed_3stage "
        f"passed={result.get('passed')} "
        f"min_actual_match={result.get('min_actual_match')} "
        f"failed_agents={result.get('failed_agents')} "
        f"final_recommendation={result.get('final_recommendation')} "
        f"weighted_signal={result.get('weighted_signal')} "
        f"receipt={result.get('receipt_path') or result.get('receipt')}"
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("passed") and not args.fail_open:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


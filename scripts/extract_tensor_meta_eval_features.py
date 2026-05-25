from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


AGENTS = ["finance", "valuation", "tech", "market", "issue", "macro"]

def equal_prior_weights(agents: List[str]) -> Dict[str, float]:
    """Objective fallback when a DMA posterior is not available."""
    available = [a for a in agents if a]
    if not available:
        return {}
    w = 1.0 / len(available)
    return {a: w for a in available}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clip01(value: Any, default: float = 1.0) -> float:
    x = safe_float(value, default)
    return max(0.0, min(1.0, x))


def softmax(values: List[float]) -> List[float]:
    if not values:
        return []
    max_v = max(values)
    exps = [math.exp(v - max_v) for v in values]
    denom = sum(exps)
    if denom == 0:
        return [1.0 / len(values)] * len(values)
    return [v / denom for v in exps]


def signal_to_probabilities(signal: float, reliability: Optional[float] = None) -> Dict[str, float]:
    """
    signal(-1~+1)을 Buy/Hold/Sell 확률로 변환한다.
    reliability가 주어지면 낮은 신뢰도의 agent 확률은 균등분포에 가깝게 보정한다.
    """
    signal = max(-1.0, min(1.0, safe_float(signal)))

    buy_logit = 2.0 * signal
    hold_logit = 1.0 - abs(signal)
    sell_logit = -2.0 * signal

    raw_buy, raw_hold, raw_sell = softmax([buy_logit, hold_logit, sell_logit])

    if reliability is None:
        cal_buy, cal_hold, cal_sell = raw_buy, raw_hold, raw_sell
    else:
        r = clip01(reliability, 1.0)
        uniform = 1.0 / 3.0
        cal_buy = r * raw_buy + (1.0 - r) * uniform
        cal_hold = r * raw_hold + (1.0 - r) * uniform
        cal_sell = r * raw_sell + (1.0 - r) * uniform

    return {
        "raw_buy_prob": raw_buy,
        "raw_hold_prob": raw_hold,
        "raw_sell_prob": raw_sell,
        "cal_buy_prob": cal_buy,
        "cal_hold_prob": cal_hold,
        "cal_sell_prob": cal_sell,
    }


def recommendation_from_probabilities(probabilities: Dict[str, Any]) -> str:
    """Posterior decision without a fixed weighted_signal band.

    Hold is used as a reject/no-trade option when Buy and Sell posterior masses
    are exactly tied or unavailable; otherwise the larger directional posterior
    decides.  The tiny equality tolerance is floating-point protection only.
    """
    if not isinstance(probabilities, dict) or not probabilities:
        return "보유"
    p_buy = safe_float(probabilities.get("매수", probabilities.get("buy", probabilities.get("cal_buy_prob", 0.0))))
    p_sell = safe_float(probabilities.get("매도", probabilities.get("sell", probabilities.get("cal_sell_prob", 0.0))))
    if abs(p_buy - p_sell) <= 1e-12:
        return "보유"
    return "매수" if p_buy > p_sell else "매도"


def posterior_from_signal(signal: float, reliability: Optional[float] = None) -> Dict[str, float]:
    probs = signal_to_probabilities(signal, reliability=reliability)
    return {
        "매수": probs["cal_buy_prob"],
        "보유": probs["cal_hold_prob"],
        "매도": probs["cal_sell_prob"],
    }


def extract_qd_posterior(qd: Dict[str, Any]) -> Dict[str, Any]:
    for key in (
        "label_posterior",
        "current_label_posterior",
        "posterior_probabilities",
        "probabilities",
        "final_probabilities",
    ):
        value = qd.get(key)
        if isinstance(value, dict) and value:
            return value
    return {}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compact_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return ""


def parse_simple_company_yaml(company_dir: Path) -> Dict[str, str]:
    """
    PyYAML 의존성을 만들지 않기 위해 아주 단순한 key: value만 읽는다.
    없으면 빈 값으로 둔다.
    """
    yaml_path = company_dir / "_company_common" / "company.yaml"
    out = {
        "ticker": "",
        "slug": "",
        "sub_sector": "",
        "vc_role": "",
        "market": "",
    }

    if not yaml_path.exists():
        return out

    try:
        text = yaml_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = yaml_path.read_text(encoding="cp949", errors="ignore")

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key in out:
            out[key] = value

    return out


def infer_primary_market_benchmark(market: str) -> str:
    text = str(market or "").strip().lower()
    if "kosdaq" in text or "코스닥" in text:
        return "KOSDAQ_지수"
    if "kospi" in text or "코스피" in text or "유가증권" in text:
        return "KOSPI_지수"
    return ""


def infer_sector_benchmark(sector: str, sub_sector: str = "", vc_role: str = "") -> str:
    text = " ".join(str(x or "") for x in (sector, sub_sector, vc_role)).lower()
    if "반도체" in text or "semiconductor" in text:
        return "KRX_반도체_지수"
    return ""


def benchmark_selection_rule(primary_benchmark: str, sector_benchmark: str) -> str:
    rules = []
    if primary_benchmark:
        rules.append("KOSPI-listed uses KOSPI, KOSDAQ-listed uses KOSDAQ")
    if sector_benchmark:
        rules.append("semiconductor excess return uses KRX semiconductor sector benchmark when available")
    return "; ".join(rules)


def get_agent_packet_map(packet: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    packets = packet.get("packets", [])
    if not isinstance(packets, list):
        return {}

    out = {}
    for item in packets:
        if not isinstance(item, dict):
            continue
        agent = item.get("agent")
        if agent:
            out[str(agent)] = item
    return out


def extract_one_company(company_dir: Path, sector: str) -> Optional[Dict[str, Any]]:
    auditor_path = (
        company_dir
        / "auditor"
        / "first_auditor"
        / "compact_agent_packets"
        / "auditor_chair_packet.json"
    )

    if not auditor_path.exists():
        return None

    packet = read_json(auditor_path)
    qd = packet.get("quantitative_decision", {}) or {}
    weights = qd.get("weights", {}) or {}
    agent_decisions = qd.get("agent_decisions", {}) or {}
    agent_packet_map = get_agent_packet_map(packet)
    yaml_meta = parse_simple_company_yaml(company_dir)

    company_name = packet.get("company") or company_dir.name
    company_slug = packet.get("company_dir") or yaml_meta.get("slug") or company_dir.name

    row: Dict[str, Any] = {
        "sector": sector,
        "company": company_name,
        "company_folder": company_dir.name,
        "slug": company_slug,
        "ticker": yaml_meta.get("ticker", ""),
        "sub_sector": yaml_meta.get("sub_sector", ""),
        "vc_role": yaml_meta.get("vc_role", ""),
        "market": yaml_meta.get("market", ""),
        "auditor_packet_path": str(auditor_path).replace("\\", "/"),
        "packet_version": packet.get("packet_version", ""),
        "created_at": packet.get("created_at", ""),
        "weight_policy": qd.get("weight_policy", ""),
        "fixed_weighted_signal": safe_float(qd.get("weighted_signal")),
        "fixed_base_recommendation": qd.get("base_recommendation", ""),
        "fixed_final_recommendation": qd.get("final_recommendation", ""),
        "fixed_recommendation_recomputed": recommendation_from_probabilities(
            extract_qd_posterior(qd) or posterior_from_signal(safe_float(qd.get("weighted_signal")))
        ),
        "thresholds_json": compact_json({}),
        "core_pillar_summary_json": compact_json(qd.get("core_pillar_summary", {})),
    }

    # 혹시 packet 안의 weighted_signal이 없으면 직접 계산하기 위한 누적값.
    # 가중치는 packet의 DMA posterior를 우선하고, 없을 때만 사용 가능 agent 균등 prior를 쓴다.
    recomputed_fixed_signal = 0.0
    fallback_weights = equal_prior_weights(AGENTS)

    for agent in AGENTS:
        decision = agent_decisions.get(agent, {}) or {}
        auditor_agent_packet = agent_packet_map.get(agent, {}) or {}

        signal = safe_float(
            decision.get("signal", auditor_agent_packet.get("auditor_signal", 0.0))
        )

        fixed_weight = safe_float(
            decision.get("weight", weights.get(agent, fallback_weights.get(agent, 0.0))),
            fallback_weights.get(agent, 0.0),
        )

        weighted_contribution = safe_float(
            decision.get("weighted_contribution"),
            signal * fixed_weight,
        )

        actual_match = auditor_agent_packet.get("auditor_actual_match", "")
        actual_match_float = (
            safe_float(actual_match, 1.0) if actual_match != "" else 1.0
        )

        stage_scores = auditor_agent_packet.get("auditor_stage_scores", {}) or {}
        stage1 = safe_float(stage_scores.get("stage1_basic_consistency"), 0.0)
        stage2 = safe_float(stage_scores.get("stage2_framework"), 0.0)
        stage3 = safe_float(stage_scores.get("stage3_decision_readiness"), 0.0)

        # stage quality는 나중에 동적가중치 만들 때 바로 쓸 수 있게 저장
        stage_quality = 0.4 * stage1 + 0.3 * stage2 + 0.3 * stage3

        probs = signal_to_probabilities(signal, reliability=actual_match_float)

        recomputed_fixed_signal += signal * fixed_weight

        row[f"{agent}_signal"] = signal
        row[f"{agent}_recommendation"] = decision.get(
            "recommendation", auditor_agent_packet.get("auditor_recommendation", "")
        )
        row[f"{agent}_fixed_weight"] = fixed_weight
        row[f"{agent}_weighted_contribution"] = weighted_contribution

        row[f"{agent}_auditor_status"] = auditor_agent_packet.get("auditor_status", "")
        row[f"{agent}_auditor_actual_match"] = (
            safe_float(actual_match) if actual_match != "" else ""
        )
        row[f"{agent}_stage1_basic_consistency"] = stage1
        row[f"{agent}_stage2_framework"] = stage2
        row[f"{agent}_stage3_decision_readiness"] = stage3
        row[f"{agent}_stage_quality"] = stage_quality

        row[f"{agent}_basis_json"] = compact_json(decision.get("basis", []))
        row[f"{agent}_components_json"] = compact_json(decision.get("components", {}))
        row[f"{agent}_auditor_issues_json"] = compact_json(
            auditor_agent_packet.get("auditor_issues", [])
        )

        row[f"{agent}_raw_buy_prob"] = probs["raw_buy_prob"]
        row[f"{agent}_raw_hold_prob"] = probs["raw_hold_prob"]
        row[f"{agent}_raw_sell_prob"] = probs["raw_sell_prob"]
        row[f"{agent}_cal_buy_prob"] = probs["cal_buy_prob"]
        row[f"{agent}_cal_hold_prob"] = probs["cal_hold_prob"]
        row[f"{agent}_cal_sell_prob"] = probs["cal_sell_prob"]

    row["fixed_weighted_signal_recomputed"] = recomputed_fixed_signal
    row["fixed_recommendation_from_recomputed"] = recommendation_from_probabilities(
        posterior_from_signal(recomputed_fixed_signal)
    )

    # 향후 수익률 라벨을 붙일 자리
    primary_benchmark = infer_primary_market_benchmark(yaml_meta.get("market", ""))
    sector_benchmark = infer_sector_benchmark(
        sector,
        yaml_meta.get("sub_sector", ""),
        yaml_meta.get("vc_role", ""),
    )
    row["base_close"] = ""
    row["next_month_close"] = ""
    row["primary_market_benchmark"] = primary_benchmark
    row["sector_benchmark"] = sector_benchmark
    row["primary_benchmark_1m_return"] = ""
    row["sector_benchmark_1m_return"] = ""
    row["benchmark_selection_rule"] = benchmark_selection_rule(primary_benchmark, sector_benchmark)
    row["future_1m_return"] = ""
    row["sector_1m_return"] = ""
    row["future_1m_excess_return"] = ""
    row["future_label"] = ""

    return row


def get_fieldnames() -> List[str]:
    base_cols = [
        "sector",
        "company",
        "company_folder",
        "slug",
        "ticker",
        "sub_sector",
        "vc_role",
        "market",
        "auditor_packet_path",
        "packet_version",
        "created_at",
        "weight_policy",
        "fixed_weighted_signal",
        "fixed_weighted_signal_recomputed",
        "fixed_base_recommendation",
        "fixed_final_recommendation",
        "fixed_recommendation_recomputed",
        "fixed_recommendation_from_recomputed",
        "thresholds_json",
        "core_pillar_summary_json",
    ]

    agent_cols = []
    for agent in AGENTS:
        agent_cols.extend(
            [
                f"{agent}_signal",
                f"{agent}_recommendation",
                f"{agent}_fixed_weight",
                f"{agent}_weighted_contribution",
                f"{agent}_auditor_status",
                f"{agent}_auditor_actual_match",
                f"{agent}_stage1_basic_consistency",
                f"{agent}_stage2_framework",
                f"{agent}_stage3_decision_readiness",
                f"{agent}_stage_quality",
                f"{agent}_raw_buy_prob",
                f"{agent}_raw_hold_prob",
                f"{agent}_raw_sell_prob",
                f"{agent}_cal_buy_prob",
                f"{agent}_cal_hold_prob",
                f"{agent}_cal_sell_prob",
                f"{agent}_basis_json",
                f"{agent}_components_json",
                f"{agent}_auditor_issues_json",
            ]
        )

    label_cols = [
        "base_close",
        "next_month_close",
        "primary_market_benchmark",
        "sector_benchmark",
        "primary_benchmark_1m_return",
        "sector_benchmark_1m_return",
        "benchmark_selection_rule",
        "future_1m_return",
        "sector_1m_return",
        "future_1m_excess_return",
        "future_label",
    ]

    return base_cols + agent_cols + label_cols


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def build_probability_tensor(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Tensor Meta-Learner용 [company, agent, buy/hold/sell] 구조를 JSON으로 저장.
    """
    tensor = []

    for row in rows:
        item = {
            "company": row.get("company", ""),
            "slug": row.get("slug", ""),
            "company_folder": row.get("company_folder", ""),
            "agents": {},
        }

        for agent in AGENTS:
            item["agents"][agent] = {
                "signal": row.get(f"{agent}_signal", 0.0),
                "recommendation": row.get(f"{agent}_recommendation", ""),
                "fixed_weight": row.get(f"{agent}_fixed_weight", 0.0),
                "auditor_status": row.get(f"{agent}_auditor_status", ""),
                "auditor_actual_match": row.get(f"{agent}_auditor_actual_match", ""),
                "raw_probability": {
                    "buy": row.get(f"{agent}_raw_buy_prob", 0.0),
                    "hold": row.get(f"{agent}_raw_hold_prob", 0.0),
                    "sell": row.get(f"{agent}_raw_sell_prob", 0.0),
                },
                "calibrated_probability": {
                    "buy": row.get(f"{agent}_cal_buy_prob", 0.0),
                    "hold": row.get(f"{agent}_cal_hold_prob", 0.0),
                    "sell": row.get(f"{agent}_cal_sell_prob", 0.0),
                },
            }

        tensor.append(item)

    return tensor


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract auditor agent signals for Tensor Meta-Learner evaluation."
    )
    parser.add_argument("--root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--sector", default="반도체", help="Sector folder under data/.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory. Default: data/<sector>/_sector_common/evaluation/tensor_meta_learner",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    sector_dir = root / "data" / args.sector

    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = root / out_dir
    else:
        out_dir = sector_dir / "_sector_common" / "evaluation" / "tensor_meta_learner"

    if not sector_dir.exists():
        raise FileNotFoundError(f"sector directory not found: {sector_dir}")

    rows: List[Dict[str, Any]] = []
    missing: List[Dict[str, str]] = []

    company_dirs = [
        p for p in sector_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    ]

    for company_dir in sorted(company_dirs, key=lambda p: p.name):
        auditor_path = (
            company_dir
            / "auditor"
            / "first_auditor"
            / "compact_agent_packets"
            / "auditor_chair_packet.json"
        )

        if not auditor_path.exists():
            missing.append(
                {
                    "company_folder": company_dir.name,
                    "expected_auditor_packet": str(auditor_path).replace("\\", "/"),
                    "reason": "auditor_chair_packet.json not found",
                }
            )
            continue

        try:
            row = extract_one_company(company_dir, args.sector)
            if row:
                rows.append(row)
        except Exception as exc:
            missing.append(
                {
                    "company_folder": company_dir.name,
                    "expected_auditor_packet": str(auditor_path).replace("\\", "/"),
                    "reason": f"parse error: {exc}",
                }
            )

    fieldnames = get_fieldnames()

    signal_csv = out_dir / "auditor_agent_signal_table.csv"
    tensor_json = out_dir / "agent_probability_tensor.json"
    missing_csv = out_dir / "missing_auditor_packets.csv"
    summary_json = out_dir / "extract_summary.json"

    write_csv(signal_csv, rows, fieldnames)
    write_json(tensor_json, build_probability_tensor(rows))

    missing_fieldnames = ["company_folder", "expected_auditor_packet", "reason"]
    write_csv(missing_csv, missing, missing_fieldnames)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root).replace("\\", "/"),
        "sector": args.sector,
        "company_dir_count": len(company_dirs),
        "extracted_company_count": len(rows),
        "missing_or_failed_count": len(missing),
        "outputs": {
            "auditor_agent_signal_table_csv": str(signal_csv).replace("\\", "/"),
            "agent_probability_tensor_json": str(tensor_json).replace("\\", "/"),
            "missing_auditor_packets_csv": str(missing_csv).replace("\\", "/"),
            "extract_summary_json": str(summary_json).replace("\\", "/"),
        },
        "decision_policy": {
            "name": "dma_posterior_reject_option_v49",
            "buy_sell_rule": "larger Buy-vs-Sell posterior mass; no fixed weighted_signal band",
            "hold_rule": "reject/no-trade only when posterior direction is tied or unavailable",
        },
        "fallback_weight_policy": "equal prior over available agents only when packet DMA posterior is absent",
        "agents": AGENTS,
    }

    write_json(summary_json, summary)

    print("=" * 80)
    print("[Tensor Meta-Learner Feature Extraction]")
    print(f"sector_dir              : {sector_dir}")
    print(f"company_dir_count       : {len(company_dirs)}")
    print(f"extracted_company_count : {len(rows)}")
    print(f"missing_or_failed_count : {len(missing)}")
    print()
    print(f"signal_csv              : {signal_csv}")
    print(f"tensor_json             : {tensor_json}")
    print(f"missing_csv             : {missing_csv}")
    print(f"summary_json            : {summary_json}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

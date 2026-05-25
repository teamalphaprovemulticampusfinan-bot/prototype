from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


RECOMMENDATION_ORDER = ["매수", "보유", "매도"]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def normalize_recommendation(value: Any) -> str:
    text = str(value or "").strip().lower()

    if text in {"매수", "buy", "strong buy", "limited_buy", "limited buy"}:
        return "매수"

    if text in {"매도", "sell", "strong sell"}:
        return "매도"

    if text in {"보유", "hold", "neutral", "관망"}:
        return "보유"

    if "매수" in text or "buy" in text:
        return "매수"

    if "매도" in text or "sell" in text:
        return "매도"

    if "보유" in text or "hold" in text or "neutral" in text:
        return "보유"

    return "기타/공백"


def classify_existing_threshold(weighted_signal: float) -> str:
    """Backward-compatible no-threshold directional fallback.

    This diagnostic script no longer recreates the old weighted_signal band.
    When only a scalar diagnostic signal is available, the sign supplies
    directional evidence; exact zero remains Hold as reject/no-trade.
    """
    x = safe_float(weighted_signal)
    if x > 0:
        return "매수"
    if x < 0:
        return "매도"
    return "보유"


def read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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


def pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total * 100, 4)


def build_distribution_rows(
    rows: List[Dict[str, Any]],
    column_name: str,
    label: str,
) -> List[Dict[str, Any]]:
    counter = Counter()

    for row in rows:
        rec = normalize_recommendation(row.get(column_name, ""))
        counter[rec] += 1

    total = len(rows)
    out = []

    for rec in ["매수", "보유", "매도", "기타/공백"]:
        count = counter.get(rec, 0)
        out.append(
            {
                "source": label,
                "source_column": column_name,
                "recommendation": rec,
                "count": count,
                "pct": pct(count, total),
                "total": total,
                "decision_rule": "scalar sign fallback only when posterior is unavailable; Hold only for exact zero/missing",
            }
        )

    return out


def build_subsector_distribution_rows(
    rows: List[Dict[str, Any]],
    column_name: str,
    label: str,
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        sub_sector = (
            str(row.get("sub_sector") or "").strip()
            or str(row.get("vc_role") or "").strip()
            or "미분류"
        )
        grouped[sub_sector].append(row)

    out = []

    for sub_sector, group_rows in sorted(grouped.items()):
        counter = Counter()

        for row in group_rows:
            rec = normalize_recommendation(row.get(column_name, ""))
            counter[rec] += 1

        total = len(group_rows)

        for rec in ["매수", "보유", "매도", "기타/공백"]:
            count = counter.get(rec, 0)
            out.append(
                {
                    "source": label,
                    "source_column": column_name,
                    "sub_sector": sub_sector,
                    "recommendation": rec,
                    "count": count,
                    "pct": pct(count, total),
                    "total": total,
                }
            )

    return out


def add_distribution_columns(
    rows: List[Dict[str, Any]],
    primary_column: str,
) -> List[Dict[str, Any]]:
    """
    기존 CSV에 분포 요약을 반복 컬럼으로 붙인 버전 생성.
    원본을 덮어쓰지 않고 별도 파일로 저장한다.
    """
    counter = Counter()

    for row in rows:
        rec = normalize_recommendation(row.get(primary_column, ""))
        counter[rec] += 1

    total = len(rows)
    buy_count = counter.get("매수", 0)
    hold_count = counter.get("보유", 0)
    sell_count = counter.get("매도", 0)
    other_count = counter.get("기타/공백", 0)

    out = []

    for row in rows:
        new_row = dict(row)
        rec = normalize_recommendation(row.get(primary_column, ""))

        new_row["baseline_distribution_source_column"] = primary_column
        new_row["baseline_total_count"] = total

        new_row["baseline_buy_count"] = buy_count
        new_row["baseline_hold_count"] = hold_count
        new_row["baseline_sell_count"] = sell_count
        new_row["baseline_other_count"] = other_count

        new_row["baseline_buy_pct"] = pct(buy_count, total)
        new_row["baseline_hold_pct"] = pct(hold_count, total)
        new_row["baseline_sell_pct"] = pct(sell_count, total)
        new_row["baseline_other_pct"] = pct(other_count, total)

        new_row["baseline_my_class"] = rec
        new_row["baseline_my_class_count"] = counter.get(rec, 0)
        new_row["baseline_my_class_pct"] = pct(counter.get(rec, 0), total)

        out.append(new_row)

    return out


def build_top_bottom_candidates(rows: List[Dict[str, Any]], signal_column: str) -> List[Dict[str, Any]]:
    """
    강사님 피드백 반영:
    상위 5개 vs 하위 5개 비교를 위한 후보 파일 생성.
    아직 수익률이 없더라도, 나중에 future_1m_excess_return을 붙여서 바로 비교 가능.
    """
    sorted_rows = sorted(
        rows,
        key=lambda r: safe_float(r.get(signal_column, 0.0)),
        reverse=True,
    )

    total = len(sorted_rows)
    out = []

    for rank, row in enumerate(sorted_rows, start=1):
        if rank <= 5:
            bucket = "Top5"
        elif rank > max(total - 5, 0):
            bucket = "Bottom5"
        else:
            bucket = "Middle"

        out.append(
            {
                "rank_desc": rank,
                "bucket": bucket,
                "company": row.get("company", ""),
                "slug": row.get("slug", ""),
                "sub_sector": row.get("sub_sector", ""),
                "vc_role": row.get("vc_role", ""),
                "fixed_weighted_signal": row.get("fixed_weighted_signal", ""),
                "fixed_weighted_signal_recomputed": row.get("fixed_weighted_signal_recomputed", ""),
                "fixed_recommendation_from_recomputed": row.get("fixed_recommendation_from_recomputed", ""),
                "fixed_final_recommendation": row.get("fixed_final_recommendation", ""),
                "primary_market_benchmark": row.get("primary_market_benchmark", ""),
                "sector_benchmark": row.get("sector_benchmark", ""),
                "primary_benchmark_1m_return": row.get("primary_benchmark_1m_return", ""),
                "sector_benchmark_1m_return": row.get("sector_benchmark_1m_return", ""),
                "benchmark_selection_rule": row.get("benchmark_selection_rule", ""),
                "future_1m_return": row.get("future_1m_return", ""),
                "future_1m_excess_return": row.get("future_1m_excess_return", ""),
            }
        )

    return out


def build_mismatch_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    packet의 final recommendation과 recomputed recommendation이 다른 기업 확인.
    이 파일은 나중에 왜 Chair packet과 Auditor packet 결과가 다른지 점검할 때 유용함.
    """
    out = []

    for row in rows:
        packet_final = normalize_recommendation(row.get("fixed_final_recommendation", ""))
        recomputed = normalize_recommendation(row.get("fixed_recommendation_from_recomputed", ""))

        signal_packet = safe_float(row.get("fixed_weighted_signal", 0.0))
        signal_recomputed = safe_float(row.get("fixed_weighted_signal_recomputed", 0.0))
        signal_gap = round(signal_packet - signal_recomputed, 8)

        if packet_final != recomputed or abs(signal_gap) > 0.000001:
            out.append(
                {
                    "company": row.get("company", ""),
                    "slug": row.get("slug", ""),
                    "packet_final_recommendation": packet_final,
                    "recomputed_recommendation": recomputed,
                    "fixed_weighted_signal_packet": signal_packet,
                    "fixed_weighted_signal_recomputed": signal_recomputed,
                    "signal_gap": signal_gap,
                    "auditor_packet_path": row.get("auditor_packet_path", ""),
                }
            )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check DMA posterior / reject-option recommendation distribution for Tensor Meta-Learner evaluation."
    )
    parser.add_argument("--root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--sector", default="반도체", help="Sector folder under data/.")
    parser.add_argument(
        "--input",
        default=None,
        help="Input CSV. Default: data/<sector>/_sector_common/evaluation/tensor_meta_learner/auditor_agent_signal_table.csv",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory. Default: same as input CSV directory.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()

    if args.input:
        input_csv = Path(args.input)
        if not input_csv.is_absolute():
            input_csv = root / input_csv
    else:
        input_csv = (
            root
            / "data"
            / args.sector
            / "_sector_common"
            / "evaluation"
            / "tensor_meta_learner"
            / "auditor_agent_signal_table.csv"
        )

    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = root / out_dir
    else:
        out_dir = input_csv.parent

    if not input_csv.exists():
        raise FileNotFoundError(f"input CSV not found: {input_csv}")

    rows = read_csv(input_csv)

    # 만약 기존 스크립트에서 recomputed 컬럼이 없으면 여기서 다시 만들어준다.
    for row in rows:
        if not row.get("fixed_recommendation_from_recomputed"):
            signal = safe_float(row.get("fixed_weighted_signal_recomputed", row.get("fixed_weighted_signal", 0.0)))
            row["fixed_recommendation_from_recomputed"] = classify_existing_threshold(signal)

        if not row.get("fixed_recommendation_recomputed"):
            signal = safe_float(row.get("fixed_weighted_signal", 0.0))
            row["fixed_recommendation_recomputed"] = classify_existing_threshold(signal)

    distribution_rows: List[Dict[str, Any]] = []

    distribution_rows.extend(
        build_distribution_rows(
            rows,
            "fixed_recommendation_from_recomputed",
            "recomputed_from_agent_signals",
        )
    )

    distribution_rows.extend(
        build_distribution_rows(
            rows,
            "fixed_recommendation_recomputed",
            "recomputed_from_packet_weighted_signal",
        )
    )

    distribution_rows.extend(
        build_distribution_rows(
            rows,
            "fixed_final_recommendation",
            "packet_final_recommendation",
        )
    )

    subsector_rows: List[Dict[str, Any]] = []
    subsector_rows.extend(
        build_subsector_distribution_rows(
            rows,
            "fixed_recommendation_from_recomputed",
            "recomputed_from_agent_signals",
        )
    )

    rows_with_distribution = add_distribution_columns(
        rows,
        "fixed_recommendation_from_recomputed",
    )

    top_bottom_rows = build_top_bottom_candidates(
        rows,
        "fixed_weighted_signal_recomputed",
    )

    mismatch_rows = build_mismatch_rows(rows)

    distribution_csv = out_dir / "baseline_recommendation_distribution.csv"
    subsector_csv = out_dir / "baseline_recommendation_distribution_by_subsector.csv"
    with_dist_csv = out_dir / "auditor_agent_signal_table_with_distribution.csv"
    top_bottom_csv = out_dir / "baseline_top_bottom_candidates.csv"
    mismatch_csv = out_dir / "baseline_recommendation_mismatch_check.csv"
    summary_json = out_dir / "baseline_distribution_summary.json"

    write_csv(
        distribution_csv,
        distribution_rows,
        [
            "source",
            "source_column",
            "recommendation",
            "count",
            "pct",
            "total",
            "threshold_rule",
        ],
    )

    write_csv(
        subsector_csv,
        subsector_rows,
        [
            "source",
            "source_column",
            "sub_sector",
            "recommendation",
            "count",
            "pct",
            "total",
        ],
    )

    original_fieldnames = list(rows[0].keys()) if rows else []
    extra_fieldnames = [
        "baseline_distribution_source_column",
        "baseline_total_count",
        "baseline_buy_count",
        "baseline_hold_count",
        "baseline_sell_count",
        "baseline_other_count",
        "baseline_buy_pct",
        "baseline_hold_pct",
        "baseline_sell_pct",
        "baseline_other_pct",
        "baseline_my_class",
        "baseline_my_class_count",
        "baseline_my_class_pct",
    ]

    write_csv(
        with_dist_csv,
        rows_with_distribution,
        original_fieldnames + [c for c in extra_fieldnames if c not in original_fieldnames],
    )

    write_csv(
        top_bottom_csv,
        top_bottom_rows,
        [
            "rank_desc",
            "bucket",
            "company",
            "slug",
            "sub_sector",
            "vc_role",
            "fixed_weighted_signal",
            "fixed_weighted_signal_recomputed",
            "fixed_recommendation_from_recomputed",
            "fixed_final_recommendation",
            "primary_market_benchmark",
            "sector_benchmark",
            "primary_benchmark_1m_return",
            "sector_benchmark_1m_return",
            "benchmark_selection_rule",
            "future_1m_return",
            "future_1m_excess_return",
        ],
    )

    write_csv(
        mismatch_csv,
        mismatch_rows,
        [
            "company",
            "slug",
            "packet_final_recommendation",
            "recomputed_recommendation",
            "fixed_weighted_signal_packet",
            "fixed_weighted_signal_recomputed",
            "signal_gap",
            "auditor_packet_path",
        ],
    )

    primary_counts = {
        row["recommendation"]: row
        for row in distribution_rows
        if row["source"] == "recomputed_from_agent_signals"
    }

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(input_csv).replace("\\", "/"),
        "total_companies": len(rows),
        "decision_rule": {
            "buy_sell": "larger posterior direction; scalar sign only when posterior fields are absent",
            "hold": "reject/no-trade when direction is tied or unavailable",
        },
        "primary_distribution_source": "fixed_recommendation_from_recomputed",
        "primary_distribution": {
            rec: {
                "count": int(primary_counts.get(rec, {}).get("count", 0)),
                "pct": float(primary_counts.get(rec, {}).get("pct", 0.0)),
            }
            for rec in ["매수", "보유", "매도", "기타/공백"]
        },
        "mismatch_count": len(mismatch_rows),
        "outputs": {
            "baseline_recommendation_distribution_csv": str(distribution_csv).replace("\\", "/"),
            "baseline_recommendation_distribution_by_subsector_csv": str(subsector_csv).replace("\\", "/"),
            "auditor_agent_signal_table_with_distribution_csv": str(with_dist_csv).replace("\\", "/"),
            "baseline_top_bottom_candidates_csv": str(top_bottom_csv).replace("\\", "/"),
            "baseline_recommendation_mismatch_check_csv": str(mismatch_csv).replace("\\", "/"),
            "baseline_distribution_summary_json": str(summary_json).replace("\\", "/"),
        },
    }

    write_json(summary_json, summary)

    print("=" * 80)
    print("[DMA Posterior Reject-Option Recommendation Distribution]")
    print(f"input_csv       : {input_csv}")
    print(f"total_companies : {len(rows)}")
    print()
    print("Primary distribution: fixed_recommendation_from_recomputed")
    for rec in ["매수", "보유", "매도", "기타/공백"]:
        item = summary["primary_distribution"][rec]
        print(f"- {rec}: {item['count']}개 ({item['pct']}%)")
    print()
    print(f"mismatch_count  : {len(mismatch_rows)}")
    print()
    print(f"distribution_csv: {distribution_csv}")
    print(f"with_dist_csv   : {with_dist_csv}")
    print(f"top_bottom_csv  : {top_bottom_csv}")
    print(f"summary_json    : {summary_json}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

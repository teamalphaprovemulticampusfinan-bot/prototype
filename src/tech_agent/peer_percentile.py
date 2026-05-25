from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from common.data_paths import DATA_DIR, company_agent_dir, ml_universe_dir
from typing import Any, Iterable

from common.output_paths import agent_output_path, output_candidates, read_json_first, shared_output_dir


FOCAL_DIR_TO_NAME: dict[str, str] = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}

NAME_TO_DIR: dict[str, str] = {v: k for k, v in FOCAL_DIR_TO_NAME.items()}
NAME_ALIASES: dict[str, str] = {
    "LTC": "ltc",
    "엘티씨": "ltc",
    "네패스": "nepes",
    "한미반도체": "hanmi",
    "한솔케미칼": "hansol",
    "덕산테코피아": "duksan",
}

GRADE_POLICY: list[tuple[float, str, str]] = [
    (85.0, "VALUE_CONVERSION_CONFIRMED", "peer 상위권 기술·IP 신호가 확인되어 기술-가치 연결을 긍정 보조 근거로 반영할 수 있습니다."),
    (70.0, "COMMERCIALIZATION_WATCH", "peer 대비 기술·IP 신호는 유효하지만 고객 채택·양산·매출·FCF 연결은 계속 추적해야 합니다."),
    (55.0, "TECH_FINANCE_GAP", "기술·IP 신호만으로 가치평가 가산을 확대하기 어렵고 재무 전환 근거 확인이 필요합니다."),
    (0.0, "TECH_EVIDENCE_WEAK", "peer 대비 기술·IP 신호 또는 근거 구조가 약해 보수적 반영이 필요합니다."),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return json.loads(path.read_text(encoding=enc, errors="replace"))
        except Exception:
            continue
    return {}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return None if math.isnan(v) or math.isinf(v) else v
    s = str(value).strip().replace(",", "").replace("%", "")
    if not s or s.lower() in {"nan", "none", "null", "확인 제한"}:
        return None
    try:
        v = float(s)
    except Exception:
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _round(value: Any, digits: int = 2) -> float | None:
    v = _num(value)
    return None if v is None else round(v, digits)


def _percentile_rank(values: Iterable[Any], value: Any, *, higher_is_better: bool = True) -> float | None:
    xs = [_num(x) for x in values]
    xs = [x for x in xs if x is not None]
    v = _num(value)
    if v is None or not xs:
        return None
    n = len(xs)
    if higher_is_better:
        less = sum(1 for x in xs if x < v)
        equal = sum(1 for x in xs if x == v)
    else:
        less = sum(1 for x in xs if x > v)
        equal = sum(1 for x in xs if x == v)
    return round(100.0 * (less + 0.5 * equal) / n, 2)


def _weighted_average(items: list[tuple[float | None, float]]) -> float | None:
    valid = [(v, w) for v, w in items if v is not None and w > 0]
    if not valid:
        return None
    denom = sum(w for _, w in valid)
    if denom <= 0:
        return None
    return round(sum((v or 0) * w for v, w in valid) / denom, 2)


def _grade(score: float | None) -> str:
    if score is None:
        return "COMMERCIALIZATION_WATCH"
    for threshold, grade, _ in GRADE_POLICY:
        if score >= threshold:
            return grade
    return "TECH_EVIDENCE_WEAK"


def _grade_interpretation(score: float | None) -> str:
    grade = _grade(score)
    for _, g, msg in GRADE_POLICY:
        if g == grade:
            return msg
    return "peer percentile 보정 결과는 보수적으로 해석합니다."


def _band(percentile: float | None) -> str:
    if percentile is None:
        return "확인 제한"
    if percentile >= 80:
        return "peer 상위권"
    if percentile >= 60:
        return "peer 중상위권"
    if percentile >= 40:
        return "peer 중위권"
    if percentile >= 20:
        return "peer 중하위권"
    return "peer 하위권"


def _safe_company_dir(row: dict[str, Any]) -> str:
    company_dir = str(row.get("company_dir") or "").strip()
    if company_dir:
        return company_dir
    name = str(row.get("company_name") or "").strip()
    return NAME_ALIASES.get(name, name)


def _load_clusters(workspace: Path) -> dict[str, Any]:
    path = ml_universe_dir() / "tech_peer_clusters.json"
    data = _read_json(path)
    if not data:
        raise FileNotFoundError(
            f"tech_peer_clusters.json을 찾지 못했습니다: {path}\n"
            "먼저 `python .\\scripts\\run_tech_peer_clustering.py`를 실행하세요."
        )
    return data


def _load_bridge(workspace: Path, company_dir: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    legacy = read_json_first(output_candidates(company_dir, "tech", f"{company_dir}_tech_to_value_bridge.json", root=workspace.parent))
    preferred = read_json_first(output_candidates(company_dir, "tech", f"{company_dir}_tech_to_value_inputs.json", root=workspace.parent))
    if isinstance(legacy, dict):
        result.update(legacy)
    if isinstance(preferred, dict):
        result.update(preferred)
    return result


def _load_ml_signal(workspace: Path, company_dir: str) -> dict[str, Any]:
    data = read_json_first(output_candidates(company_dir, "tech", f"{company_dir}_tech_ml_signal.json", root=workspace.parent))
    return data if isinstance(data, dict) else {}


def _resolve_assignment(assignments: list[dict[str, Any]], company_dir: str = "", company_name: str = "") -> dict[str, Any]:
    target_dir = company_dir.strip()
    target_name = company_name.strip()
    if not target_dir and target_name:
        target_dir = NAME_ALIASES.get(target_name, "")
    for row in assignments:
        if target_dir and _safe_company_dir(row).lower() == target_dir.lower():
            return row
    for row in assignments:
        if target_name and str(row.get("company_name") or "").strip() == target_name:
            return row
    if target_dir:
        for row in assignments:
            if target_dir.lower() in str(row.get("patent_csv") or "").lower():
                return row
    return {}


def _same_filter(assignments: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    return [r for r in assignments if str(r.get(key) or "") == str(value)]


def _focal_rows(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in assignments if int(_num(r.get("is_focal")) or 0) == 1 or int(_num(r.get("include_in_chair")) or 0) == 1]


def _metric_percentiles(rows: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any]:
    if not rows or not current:
        return {}
    metrics = {
        "selection_score": ("selection_score", True, "valuation/credit 후보 선별 점수"),
        "patent_rows": ("patent_rows", True, "KIPRIS/특허 레코드 수"),
        "document_chars": ("document_chars", True, "기술 문서 텍스트 커버리지"),
        "distance_to_centroid": ("distance_to_centroid", False, "cluster 중심 근접도"),
    }
    out: dict[str, Any] = {}
    for name, (field, hib, desc) in metrics.items():
        p = _percentile_rank([r.get(field) for r in rows], current.get(field), higher_is_better=hib)
        out[name] = {
            "value": _round(current.get(field), 4),
            "percentile": p,
            "band": _band(p),
            "higher_is_better": hib,
            "description": desc,
            "n": len([r for r in rows if _num(r.get(field)) is not None]),
        }
    return out


def _nearest_similarity_score(clusters: dict[str, Any], current: dict[str, Any]) -> tuple[float | None, list[dict[str, Any]]]:
    uid = current.get("universe_id")
    peers_map = clusters.get("nearest_peers_by_universe_id") if isinstance(clusters.get("nearest_peers_by_universe_id"), dict) else {}
    peers = peers_map.get(uid) if uid else []
    if not isinstance(peers, list):
        peers = []
    sims = [_num(p.get("similarity_percent") if p.get("similarity_percent") is not None else (_num(p.get("similarity")) or 0) * 100) for p in peers]
    sims = [s for s in sims if s is not None]
    if not sims:
        return None, peers[:5]
    # nearest peer가 높을수록 cluster 내부 기술 유사성이 뚜렷하다고 해석한다.
    top = max(sims)
    # 실무적으로 70% 이상이면 강한 peer anchor, 40~70은 보통, 40 미만은 약한 anchor로 본다.
    score = _clip((top / 70.0) * 100.0)
    return round(score, 2), peers[:5]


def _cluster_density_score(assignments: list[dict[str, Any]], current: dict[str, Any]) -> float | None:
    cluster_id = current.get("cluster_id")
    same = _same_filter(assignments, "cluster_id", cluster_id)
    if not same:
        return None
    focal = _focal_rows(same)
    # 30개 universe에서 같은 cluster에 너무 적게 몰리면 비교 안정성이 낮다.
    member_score = _clip(len(same) / 8.0 * 100.0)
    focal_score = _clip(len(focal) / 5.0 * 100.0)
    return round(0.65 * member_score + 0.35 * focal_score, 2)


def _bridge_base_score(bridge: dict[str, Any]) -> float | None:
    for key in ["auditor_adjusted_score", "score", "tech_to_value_bridge_score", "bridge_score", "base_signal_score"]:
        value = _num(bridge.get(key))
        if value is not None:
            return value
    return None


def _bridge_raw_score(bridge: dict[str, Any]) -> float | None:
    for key in ["tech_agent_raw_score", "raw_score", "tech_score", "tech_to_value_bridge_score"]:
        value = _num(bridge.get(key))
        if value is not None:
            return value
    return _bridge_base_score(bridge)


def _base_grade(bridge: dict[str, Any], base_score: float | None) -> str:
    raw = str(bridge.get("grade") or bridge.get("bridge_grade") or bridge.get("label") or "").upper()
    aliases = {
        "VALUE_BRIDGE_READY": "VALUE_CONVERSION_CONFIRMED",
        "VALUE_BRIDGE_CONFIRMED": "VALUE_CONVERSION_CONFIRMED",
        "VALUE_READY": "VALUE_CONVERSION_CONFIRMED",
    }
    for k, v in aliases.items():
        if k in raw:
            return v
    for _, g, _ in GRADE_POLICY:
        if g in raw:
            return g
    return _grade(base_score)


def build_peer_percentile_packet(
    *,
    workspace: Path,
    company_dir: str = "",
    company_name: str = "",
) -> dict[str, Any]:
    clusters = _load_clusters(workspace)
    assignments = clusters.get("assignments") if isinstance(clusters.get("assignments"), list) else []
    if not assignments:
        raise ValueError("tech_peer_clusters.json에 assignments가 없습니다.")

    current = _resolve_assignment(assignments, company_dir=company_dir, company_name=company_name)
    if not current:
        raise ValueError(f"reference universe에서 기업을 찾지 못했습니다: company_dir={company_dir}, company={company_name}")

    company_dir = _safe_company_dir(current) or company_dir
    company_name = str(current.get("company_name") or company_name or FOCAL_DIR_TO_NAME.get(company_dir, company_dir))

    bridge = _load_bridge(workspace, company_dir)
    ml_signal = _load_ml_signal(workspace, company_dir)

    # focal 기업의 실제 특허 ML 지표가 있으면 현재 기업 row에 보강한다.
    enriched_current = dict(current)
    for key in [
        "normalized_patent_records",
        "company_matched_patents",
        "registered_patents",
        "alive_patents",
        "recent_5y_patents",
        "ipc_cpc_count",
        "h01l_patents",
        "technology_keyword_hit_total",
        "patent_ml_score",
    ]:
        if ml_signal.get(key) is not None:
            enriched_current[key] = ml_signal.get(key)

    universe_pct = _metric_percentiles(assignments, enriched_current)
    same_cluster = _same_filter(assignments, "cluster_id", current.get("cluster_id"))
    same_sector = _same_filter(assignments, "sector_label", current.get("sector_label"))
    focal = _focal_rows(assignments)
    cluster_pct = _metric_percentiles(same_cluster, enriched_current)
    sector_pct = _metric_percentiles(same_sector, enriched_current)
    focal_pct = _metric_percentiles(focal, enriched_current)

    nearest_score, nearest_peers = _nearest_similarity_score(clusters, current)
    density_score = _cluster_density_score(assignments, current)

    # focal 30개 내 percentile은 sample이 작으므로 낮은 가중치만 준다.
    composite = _weighted_average([
        (universe_pct.get("selection_score", {}).get("percentile"), 0.24),
        (universe_pct.get("patent_rows", {}).get("percentile"), 0.20),
        (universe_pct.get("document_chars", {}).get("percentile"), 0.12),
        (universe_pct.get("distance_to_centroid", {}).get("percentile"), 0.14),
        (cluster_pct.get("selection_score", {}).get("percentile"), 0.10),
        (sector_pct.get("selection_score", {}).get("percentile"), 0.08),
        (focal_pct.get("selection_score", {}).get("percentile"), 0.04),
        (nearest_score, 0.04),
        (density_score, 0.04),
    ])

    base_score = _bridge_base_score(bridge)
    raw_score = _bridge_raw_score(bridge)
    base_grade = _base_grade(bridge, base_score)
    if base_score is None:
        base_score = _num(ml_signal.get("bridge_score")) or _num(ml_signal.get("patent_ml_score")) or 70.0

    # Peer correction: 50 percentile을 중립점으로 보고 최대 ±8점만 조정한다.
    # Tech 점수 남발 방지를 위해 상향은 제한적, 하향은 약간 더 빠르게 반영한다.
    if composite is None:
        adjustment = 0.0
        reason = "peer percentile 산출 제한으로 보정 0점 적용"
    else:
        delta = composite - 50.0
        adjustment = delta * 0.16 if delta >= 0 else delta * 0.20
        adjustment = _clip(adjustment, -10.0, 8.0)
        reason = f"peer composite percentile {composite:.2f} 기준 보정 {adjustment:+.2f}점"

    peer_adjusted = round(_clip((base_score or 0.0) + adjustment), 2)

    # Finance/FCF 연결이 약한 grade에서는 peer 상위권이라도 VALUE_CONVERSION_CONFIRMED로 바로 올리지 않는다.
    conservative_cap_applied = False
    if base_grade in {"TECH_FINANCE_GAP", "TECH_EVIDENCE_WEAK"} and peer_adjusted > 72:
        peer_adjusted = 72.0
        conservative_cap_applied = True
    elif base_grade == "COMMERCIALIZATION_WATCH" and peer_adjusted > 84:
        peer_adjusted = 84.0
        conservative_cap_applied = True

    peer_grade = _grade(peer_adjusted)
    if base_grade == "COMMERCIALIZATION_WATCH" and peer_grade == "VALUE_CONVERSION_CONFIRMED":
        peer_grade = "COMMERCIALIZATION_WATCH"
    if base_grade == "TECH_FINANCE_GAP" and peer_grade == "VALUE_CONVERSION_CONFIRMED":
        peer_grade = "COMMERCIALIZATION_WATCH"

    packet = {
        "created_at": _now(),
        "module": "tech_peer_percentile_bridge",
        "method": "Reference Universe percentile correction for Tech-to-Value Bridge",
        "company_dir": company_dir,
        "company_name": company_name,
        "ticker": current.get("ticker"),
        "sector_label": current.get("sector_label"),
        "peer_group": current.get("peer_group"),
        "cluster_id": current.get("cluster_id"),
        "cluster_name": _cluster_name(clusters, current.get("cluster_id")),
        "sample_size": {
            "universe": len(assignments),
            "same_cluster": len(same_cluster),
            "same_sector": len(same_sector),
            "focal": len(focal),
        },
        "base_bridge_score": round(base_score, 2) if base_score is not None else None,
        "base_raw_tech_score": round(raw_score, 2) if raw_score is not None else None,
        "base_bridge_grade": base_grade,
        "peer_composite_percentile": composite,
        "peer_percentile_band": _band(composite),
        "peer_adjustment_points": round(adjustment, 2),
        "peer_adjustment_reason": reason,
        "peer_adjusted_bridge_score": peer_adjusted,
        "peer_adjusted_grade": peer_grade,
        "peer_adjusted_interpretation": _grade_interpretation(peer_adjusted),
        "conservative_cap_applied": conservative_cap_applied,
        "metrics": {
            "universe_percentiles": universe_pct,
            "same_cluster_percentiles": cluster_pct,
            "same_sector_percentiles": sector_pct,
            "focal_percentiles": focal_pct,
            "nearest_similarity_score": nearest_score,
            "cluster_density_score": density_score,
        },
        "nearest_peers": nearest_peers,
        "current_assignment": enriched_current,
        "chair_reflection": {
            "principle": "peer percentile은 기술/IP 포트폴리오의 상대적 위치를 보정하는 ML 신호이며, 고객 채택·양산·매출 전환·FCF 확인 전에는 단독 매수 근거로 쓰지 않는다.",
            "score_use": "Chair 기술 섹션에는 base Bridge 점수와 peer percentile 보정 점수를 함께 표시한다.",
            "audit_note": "보정은 reference universe 내부 상대평가이며 미래 수익률이나 투자 성과 검증이 아니다.",
        },
        "source_files": {
            "tech_peer_clusters": str(ml_universe_dir() / "tech_peer_clusters.json"),
            "tech_to_value_inputs": str(agent_output_path(company_dir, "tech", f"{company_dir}_tech_to_value_inputs.json", root=workspace.parent)),
            "tech_ml_signal": str(agent_output_path(company_dir, "tech", f"{company_dir}_tech_ml_signal.json", root=workspace.parent)),
        },
    }
    return packet


def _cluster_name(clusters: dict[str, Any], cluster_id: Any) -> str:
    for c in clusters.get("clusters") or []:
        if str(c.get("cluster_id")) == str(cluster_id):
            return str(c.get("cluster_name") or "")
    return ""


def save_packet(workspace: Path, packet: dict[str, Any]) -> None:
    company_dir = str(packet.get("company_dir") or "")
    output_path = agent_output_path(company_dir, "tech", f"{company_dir}_tech_peer_percentile_bridge.json", root=workspace.parent)
    packets = workspace / "packets" / company_dir
    _write_json(output_path, packet)
    _write_json(packets / "tech_peer_percentile_bridge.json", packet)


def build_markdown(packets: list[dict[str, Any]]) -> str:
    lines = [
        "# Tech Peer Percentile Bridge Correction",
        "",
        "- 목적: 30개 reference universe와 focal 30개 기업의 상대적 기술/IP 위치를 이용해 Tech-to-Value Bridge 점수를 보정합니다.",
        "- 주의: 이 보정은 미래 수익률 예측이나 투자성과 검증이 아니라, 기술 포트폴리오의 peer-relative strength를 Chair에 반영하기 위한 보조 ML 신호입니다.",
        "",
        "| 기업 | Cluster | Base Bridge | Peer Percentile | 보정점 | Peer-adjusted Bridge | 판정 | 해석 |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for p in packets:
        lines.append(
            "| {company} | {cluster} | {base} | {pct} | {adj} | {score} | {grade} | {interp} |".format(
                company=p.get("company_name") or p.get("company_dir"),
                cluster=p.get("cluster_name") or p.get("cluster_id"),
                base=_fmt(p.get("base_bridge_score")),
                pct=_fmt(p.get("peer_composite_percentile")),
                adj=_fmt_signed(p.get("peer_adjustment_points")),
                score=_fmt(p.get("peer_adjusted_bridge_score")),
                grade=p.get("peer_adjusted_grade") or "-",
                interp=str(p.get("peer_percentile_band") or "-")[:40],
            )
        )
    lines += [
        "",
        "## 보정 방식",
        "",
        "1. universe percentile: selection_score, patent_rows, document_chars, distance_to_centroid를 30개 reference universe 안에서 백분위로 환산합니다.",
        "2. same-cluster/sector/focal percentile: 같은 cluster, 같은 sector, focal 30개 안에서 보조 백분위를 계산합니다.",
        "3. nearest similarity와 cluster density를 보조 신호로 반영합니다.",
        "4. composite percentile 50을 중립점으로 하여 최대 +8점, -10점 범위에서 Bridge 점수를 보정합니다.",
        "5. COMMERCIALIZATION_WATCH 또는 TECH_FINANCE_GAP 상태에서는 고객 채택·양산·매출·FCF 근거가 확인되기 전까지 보수 cap을 적용합니다.",
    ]
    return "\n".join(lines)


def _fmt(v: Any) -> str:
    x = _num(v)
    return "-" if x is None else f"{x:.2f}"


def _fmt_signed(v: Any) -> str:
    x = _num(v)
    return "-" if x is None else f"{x:+.2f}"


def run_peer_percentile_bridge(
    *,
    workspace: Path,
    company_dir: str = "",
    company: str = "",
    all_focal: bool = False,
    save: bool = True,
) -> list[dict[str, Any]]:
    clusters = _load_clusters(workspace)
    assignments = clusters.get("assignments") if isinstance(clusters.get("assignments"), list) else []
    targets: list[tuple[str, str]] = []
    if all_focal:
        for row in _focal_rows(assignments):
            targets.append((_safe_company_dir(row), str(row.get("company_name") or "")))
    else:
        targets.append((company_dir, company))

    packets: list[dict[str, Any]] = []
    for cdir, cname in targets:
        packet = build_peer_percentile_packet(workspace=workspace, company_dir=cdir, company_name=cname)
        packets.append(packet)
        if save:
            save_packet(workspace, packet)
            print(
                f"[Tech Peer Percentile] {packet.get('company_name')} 저장 완료: "
                f"score={packet.get('peer_adjusted_bridge_score')} "
                f"percentile={packet.get('peer_composite_percentile')} "
                f"grade={packet.get('peer_adjusted_grade')}"
            )

    if save:
        out = shared_output_dir("tech", root=workspace.parent)
        _write_json(out / "tech_peer_percentile_bridge_all.json", {"created_at": _now(), "packets": packets})
        _write_md(out / "tech_peer_percentile_bridge.md", build_markdown(packets))
    return packets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tech-to-Value Bridge peer percentile correction")
    parser.add_argument("--workspace", default="data", help="data directory")
    parser.add_argument("--company-dir", default="", help="company directory, e.g. nepes")
    parser.add_argument("--company", default="", help="display company name")
    parser.add_argument("--all", action="store_true", help="run all focal companies in reference universe")
    args = parser.parse_args(argv)

    workspace = DATA_DIR if args.workspace == "data" else Path(args.workspace).resolve()
    run_peer_percentile_bridge(
        workspace=workspace,
        company_dir=args.company_dir,
        company=args.company,
        all_focal=args.all or not args.company_dir,
        save=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path.cwd()

PATENT_FILE = ROOT / "src" / "tech_agent" / "patent_harvester.py"
BRIDGE_FILE = ROOT / "src" / "tech_agent" / "high_quality_report.py"


HELPER_CODE = r'''
def _load_kipris_tech_ml_features(company: dict[str, Any]) -> dict[str, Any]:
    """Load KIPRIS Tech ML features created from normalized KIPRIS CSV.

    Expected file example:
    data/반도체/네패스/tech/nepes_kipris_tech_ml_features.json
    """
    company_name = clean_text(
        company.get("corp_name")
        or company.get("company_name")
        or company.get("name")
        or ""
    )
    company_slug = clean_text(
        company.get("company_dir")
        or company.get("slug")
        or company.get("ticker")
        or company_name
        or "company"
    )

    root = Path(__file__).resolve().parents[2]

    candidates: list[Path] = []

    if company_name:
        candidates.extend(
            root.glob(f"data/*/{company_name}/tech/{company_slug}_kipris_tech_ml_features.json")
        )
        candidates.extend(
            root.glob(f"data/*/{company_name}/tech/*kipris*tech_ml*features*.json")
        )
        candidates.extend(
            root.glob(f"data/*/{company_name}/tech/*kipris*features*.json")
        )

    candidates.extend(
        root.glob(f"data/*/*/tech/{company_slug}_kipris_tech_ml_features.json")
    )
    candidates.extend(
        root.glob(f"data/*/*/tech/*kipris*tech_ml*features*.json")
    )

    seen: set[str] = set()
    unique_candidates: list[Path] = []
    for path in candidates:
        key = str(path.resolve())
        if key not in seen and path.exists():
            seen.add(key)
            unique_candidates.append(path)

    if not unique_candidates:
        return {}

    # 가장 최근에 생성된 feature 파일 우선
    feature_path = max(unique_candidates, key=lambda p: p.stat().st_mtime)

    try:
        data = json.loads(feature_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    data["_feature_path"] = str(feature_path)
    return data


def _merge_kipris_tech_ml_features(
    harvest: dict[str, Any],
    company: dict[str, Any],
) -> dict[str, Any]:
    """Merge KIPRIS Tech ML feature summary into patent harvest result.

    This does not replace raw KIPRIS evidence.
    It only adds normalized/ML-ready KIPRIS indicators so Tech-to-Value Bridge
    and Chair compact summary can use them.
    """
    features = _load_kipris_tech_ml_features(company)
    if not features:
        return harvest

    core_counts = features.get("core_counts") or {}
    core_rates = features.get("core_rates") or {}
    scores = features.get("scores") or {}
    bridge_adj = features.get("tech_to_value_bridge_adjustment") or {}

    if not isinstance(core_counts, dict):
        core_counts = {}
    if not isinstance(core_rates, dict):
        core_rates = {}
    if not isinstance(scores, dict):
        scores = {}
    if not isinstance(bridge_adj, dict):
        bridge_adj = {}

    def pick_number(*values: Any) -> float | int | None:
        for value in values:
            if value is None or value == "":
                continue
            try:
                number = float(value)
            except Exception:
                continue
            if number.is_integer():
                return int(number)
            return number
        return None

    # Chair summary / full report에서 바로 읽을 수 있게 top-level에도 반영
    harvest["kipris_tech_ml_features"] = features
    harvest["kipris_feature_path"] = features.get("_feature_path")

    harvest["total_patent_count"] = pick_number(
        core_counts.get("total_patents"),
        harvest.get("total_patent_count"),
    )
    harvest["registered_patent_count"] = pick_number(
        core_counts.get("registered_patents_estimated"),
        harvest.get("registered_patent_count"),
    )
    harvest["alive_patent_count"] = pick_number(
        core_counts.get("alive_patents_estimated"),
        harvest.get("alive_patent_count"),
    )
    harvest["negative_disposal_patent_count_estimated"] = pick_number(
        core_counts.get("negative_disposal_patents_estimated"),
    )
    harvest["recent_5y_patent_count"] = pick_number(
        core_counts.get("recent_5y_application_patents"),
        harvest.get("recent_5y_patent_count"),
    )
    harvest["core_ipc_h01l_patent_count"] = pick_number(
        core_counts.get("h01l_core_patents"),
        harvest.get("core_ipc_h01l_patent_count"),
    )
    harvest["semiconductor_related_ipc_patent_count"] = pick_number(
        core_counts.get("semiconductor_related_ipc_patents"),
    )
    harvest["ipc_subclass_count"] = pick_number(
        core_counts.get("ipc_subclass_count"),
        harvest.get("ipc_subclass_count"),
    )
    harvest["ipc_main_group_count"] = pick_number(
        core_counts.get("ipc_main_group_count"),
        harvest.get("ipc_main_group_count"),
    )
    harvest["keyword_match_count"] = pick_number(
        core_counts.get("tech_keyword_match_total"),
        harvest.get("keyword_match_count"),
    )

    harvest["registration_rate_estimated"] = core_rates.get("registration_rate_estimated")
    harvest["alive_rate_among_registered_estimated"] = core_rates.get("alive_rate_among_registered_estimated")
    harvest["negative_disposal_rate_estimated"] = core_rates.get("negative_disposal_rate_estimated")
    harvest["recent_5y_application_rate"] = core_rates.get("recent_5y_application_rate")
    harvest["semiconductor_related_ipc_rate"] = core_rates.get("semiconductor_related_ipc_rate")

    harvest["legal_stability_score_estimated"] = scores.get("legal_stability_score_estimated")
    harvest["portfolio_momentum_score"] = scores.get("portfolio_momentum_score")
    harvest["ip_technology_fit_score"] = scores.get("ip_technology_fit_score")
    harvest["kipris_tech_ml_score"] = scores.get("kipris_tech_ml_score")

    harvest["kipris_bridge_adjustment_points"] = bridge_adj.get("bridge_adjustment_points")
    harvest["kipris_bridge_signal"] = bridge_adj.get("bridge_signal")
    harvest["kipris_bridge_usage_rule"] = bridge_adj.get("usage_rule")

    metrics = harvest.setdefault("metrics", [])
    if not isinstance(metrics, list):
        metrics = []
        harvest["metrics"] = metrics

    def add_metric(metric: str, value: Any, unit: str, description: str) -> None:
        if value is None:
            return
        metrics.append(
            {
                "source": "KIPRIS Tech ML normalized features",
                "metric": metric,
                "value": value,
                "unit": unit,
                "description": description,
                "note": "원천 KIPRIS CSV를 normalized 후 산출한 Tech ML feature입니다. final_disposal 부재 항목은 추정값입니다.",
            }
        )

    add_metric(
        "KIPRIS 등록률 추정",
        core_rates.get("registration_rate_estimated"),
        "ratio",
        "등록특허 추정 건수 / 전체 특허 건수",
    )
    add_metric(
        "KIPRIS 존속률 추정",
        core_rates.get("alive_rate_among_registered_estimated"),
        "ratio",
        "존속 가능 특허 추정 건수 / 등록특허 추정 건수",
    )
    add_metric(
        "KIPRIS Legal Stability Score",
        scores.get("legal_stability_score_estimated"),
        "score",
        "등록률, 존속률, 부정 처분 추정 비중을 반영한 권리 안정성 점수",
    )
    add_metric(
        "KIPRIS Portfolio Momentum Score",
        scores.get("portfolio_momentum_score"),
        "score",
        "최근 5년 출원 비중을 반영한 특허 포트폴리오 모멘텀 점수",
    )
    add_metric(
        "KIPRIS IP-Technology Fit Score",
        scores.get("ip_technology_fit_score"),
        "score",
        "반도체 IPC 및 기술 키워드 매칭 기반 기술 적합도 점수",
    )
    add_metric(
        "KIPRIS Tech ML Score",
        scores.get("kipris_tech_ml_score"),
        "score",
        "권리 안정성, 포트폴리오 모멘텀, 기술 적합도를 결합한 KIPRIS 기반 Tech ML 점수",
    )

    quantitative_signals = harvest.setdefault("quantitative_signals", [])
    if not isinstance(quantitative_signals, list):
        quantitative_signals = []
        harvest["quantitative_signals"] = quantitative_signals

    for item in metrics[-6:]:
        quantitative_signals.append(
            {
                "source_type": "kipris_tech_ml_feature",
                "metric": item.get("metric"),
                "value": item.get("value"),
                "unit": item.get("unit"),
                "summary": item.get("description"),
            }
        )

    docs = harvest.setdefault("docs", [])
    if isinstance(docs, list):
        docs.append(
            {
                "source_type": "patent",
                "source": features.get("_feature_path"),
                "title": "KIPRIS normalized Tech ML feature summary",
                "snippet": (
                    f"KIPRIS 원천 특허 {core_counts.get('total_patents')}건 기준 "
                    f"등록률 추정 {core_rates.get('registration_rate_estimated')}, "
                    f"존속률 추정 {core_rates.get('alive_rate_among_registered_estimated')}, "
                    f"KIPRIS Tech ML Score {scores.get('kipris_tech_ml_score')}."
                ),
            }
        )

    return harvest
'''


def patch_patent_harvester() -> None:
    text = PATENT_FILE.read_text(encoding="utf-8")

    if "_merge_kipris_tech_ml_features" not in text:
        marker = "def harvest_patent_evidence(company: dict[str, Any]) -> dict[str, Any]:"
        if marker not in text:
            raise RuntimeError("patent_harvester.py에서 harvest_patent_evidence 함수를 찾지 못했습니다.")
        text = text.replace(marker, HELPER_CODE + "\n\n" + marker)

    if "return _merge_kipris_tech_ml_features(result, company)" not in text:
        pattern = re.compile(
            r'''    return \{
        "version": "v14_kipris_ipc_refined",
        "docs": docs,
        "patent_records": patent_records,
        "normalized_patent_csv_path": str\(normalized_csv\) if normalized_csv else None,
        "normalized_patent_count": normalized_count,
        "registered_patent_count": registered_count,
        "alive_patent_count": alive_count,
        "recent_5y_patent_count": recent_count,
        "ipc_cpc_class_count": ipc_class_count,
        "core_ipc_h01l_patent_count": h01l_count,
        "keyword_match_count": keyword_match_count,
        "top_ipc_codes": top_ipc_codes,
        "top_patent_titles": top_titles,
        "metrics": metrics,
    \}''',
            re.MULTILINE,
        )

        replacement = '''    result = {
        "version": "v14_kipris_ipc_refined",
        "docs": docs,
        "patent_records": patent_records,
        "normalized_patent_csv_path": str(normalized_csv) if normalized_csv else None,
        "normalized_patent_count": normalized_count,
        "registered_patent_count": registered_count,
        "alive_patent_count": alive_count,
        "recent_5y_patent_count": recent_count,
        "ipc_cpc_class_count": ipc_class_count,
        "core_ipc_h01l_patent_count": h01l_count,
        "keyword_match_count": keyword_match_count,
        "top_ipc_codes": top_ipc_codes,
        "top_patent_titles": top_titles,
        "metrics": metrics,
    }

    return _merge_kipris_tech_ml_features(result, company)'''

        text2, count = pattern.subn(replacement, text, count=1)
        if count == 0:
            raise RuntimeError("patent_harvester.py의 return 블록 패치에 실패했습니다. 파일 구조가 예상과 다릅니다.")
        text = text2

    PATENT_FILE.write_text(text, encoding="utf-8")


def patch_bridge() -> None:
    text = BRIDGE_FILE.read_text(encoding="utf-8")

    if "kipris_adjustment_points" not in text:
        old = '''    metric_count = len(harvest.get("quantitative_signals") or [])

    tech_agent_raw_score = round((int(score_report.get("total_score") or 0) / max(int(score_report.get("max_score") or 35), 1)) * 100, 2)
'''
        new = '''    metric_count = len(harvest.get("quantitative_signals") or [])

    kipris_features = harvest.get("kipris_tech_ml_features") or {}
    kipris_adjustment_points = 0.0
    kipris_signal = None
    kipris_score = None
    if isinstance(kipris_features, dict) and kipris_features:
        scores = kipris_features.get("scores") or {}
        adj = kipris_features.get("tech_to_value_bridge_adjustment") or {}
        if isinstance(scores, dict):
            kipris_score = scores.get("kipris_tech_ml_score")
        if isinstance(adj, dict):
            try:
                kipris_adjustment_points = float(adj.get("bridge_adjustment_points") or 0.0)
            except Exception:
                kipris_adjustment_points = 0.0
            kipris_signal = adj.get("bridge_signal")

    tech_agent_raw_score = round((int(score_report.get("total_score") or 0) / max(int(score_report.get("max_score") or 35), 1)) * 100, 2)
'''
        if old not in text:
            raise RuntimeError("high_quality_report.py에서 metric_count 블록을 찾지 못했습니다.")
        text = text.replace(old, new)

        old = '''    auditor_adjusted_score = round(max(0, min(100, score)), 2)
'''
        new = '''    # KIPRIS/IP feature는 기술 방어력 보조 가산으로만 사용한다.
    # 고객 채택·양산·매출·FCF 직접 근거를 대체하지 않도록 보수적으로 제한한다.
    if kipris_adjustment_points:
        score += max(-3.0, min(3.0, kipris_adjustment_points))
        if value < 2 or commercial < 2:
            score = min(score, 74)

    auditor_adjusted_score = round(max(0, min(100, score)), 2)
'''
        if old not in text:
            raise RuntimeError("high_quality_report.py에서 auditor_adjusted_score 블록을 찾지 못했습니다.")
        text = text.replace(old, new)

        old = '''            "quantitative_signal_count": metric_count,
'''
        new = '''            "quantitative_signal_count": metric_count,
            "kipris_tech_ml_score": kipris_score,
            "kipris_adjustment_points": kipris_adjustment_points,
            "kipris_signal": kipris_signal,
'''
        if old not in text:
            raise RuntimeError("high_quality_report.py에서 components 블록을 찾지 못했습니다.")
        text = text.replace(old, new)

    BRIDGE_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    if not PATENT_FILE.exists():
        raise FileNotFoundError(PATENT_FILE)
    if not BRIDGE_FILE.exists():
        raise FileNotFoundError(BRIDGE_FILE)

    patch_patent_harvester()
    patch_bridge()

    print("[DONE] KIPRIS Tech ML runtime patch applied")
    print(f"- patched: {PATENT_FILE}")
    print(f"- patched: {BRIDGE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

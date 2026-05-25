from __future__ import annotations

import re
from pathlib import Path


TARGET = Path("src") / "tech_agent" / "patent_harvester.py"


HELPER_CODE = r'''

# KIPRIS_TECH_ML_RUNTIME_PATCH_V2_START
def _find_kipris_tech_ml_feature_file(company: str, company_dir: str | None = None) -> Path | None:
    """Find prebuilt KIPRIS Tech ML feature JSON.

    Expected example:
    data/반도체/네패스/tech/nepes_kipris_tech_ml_features.json
    """
    root = Path.cwd()
    data_dir = root / "data"

    candidates: list[Path] = []

    if company_dir:
        candidates.extend(data_dir.glob(f"*/*/tech/{company_dir}_kipris_tech_ml_features.json"))
        candidates.extend(data_dir.glob(f"*/{company}/tech/{company_dir}_kipris_tech_ml_features.json"))

    if company:
        candidates.extend(data_dir.glob(f"*/{company}/tech/*_kipris_tech_ml_features.json"))

    candidates.extend(data_dir.glob("*/*/tech/*_kipris_tech_ml_features.json"))

    seen: set[str] = set()
    unique_candidates: list[Path] = []
    for path in candidates:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique_candidates.append(path)

    for path in unique_candidates:
        if path.exists() and path.is_file():
            return path

    return None


def _load_kipris_tech_ml_features(company: str, company_dir: str | None = None) -> dict[str, Any] | None:
    path = _find_kipris_tech_ml_feature_file(company, company_dir)
    if not path:
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    data["_source_path"] = str(path)
    return data


def _pct_from_rate(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value) * 100.0, 2)
    except Exception:
        return None


def _num_or_none(value: Any, digits: int = 2) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _merge_kipris_tech_ml_metrics(metrics: list[dict[str, Any]], features: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Merge normalized KIPRIS Tech ML features into patent metrics.

    This does not treat patents as direct commercialization evidence.
    It only adds conservative IP quality / legal stability / technology-fit signals.
    """
    if not features:
        return metrics

    metrics = list(metrics or [])
    existing_names = {str(m.get("metric_name") or "") for m in metrics if isinstance(m, dict)}

    core_counts = features.get("core_counts") or {}
    core_rates = features.get("core_rates") or {}
    scores = features.get("scores") or {}
    adjustment = features.get("tech_to_value_bridge_adjustment") or {}
    source_path = features.get("_source_path") or features.get("source_path") or "KIPRIS Tech ML features"

    def add_metric(metric_name: str, value: Any, unit: str, detail: str) -> None:
        if metric_name in existing_names:
            return
        if value is None:
            return
        metrics.append(
            {
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "detail": detail,
                "source_type": "kipris_tech_ml_features",
                "source": source_path,
            }
        )
        existing_names.add(metric_name)

    add_metric(
        "KIPRIS 총 특허 수",
        _num_or_none(core_counts.get("total_patents"), 0),
        "건",
        "정규화된 KIPRIS 원천 CSV 기준 전체 특허 레코드 수입니다.",
    )
    add_metric(
        "KIPRIS 등록 특허 수(추정)",
        _num_or_none(core_counts.get("registered_patents_estimated"), 0),
        "건",
        "register_status/register_number/register_date 기반 등록 특허 수 추정치입니다.",
    )
    add_metric(
        "KIPRIS 존속 가능 특허 수(추정)",
        _num_or_none(core_counts.get("alive_patents_estimated"), 0),
        "건",
        "등록 상태와 권리상태 추정 로직을 반영한 존속 가능 특허 수입니다.",
    )
    add_metric(
        "KIPRIS 등록률(추정)",
        _pct_from_rate(core_rates.get("registration_rate_estimated")),
        "%",
        "등록 특허 수를 전체 특허 수로 나눈 보수적 등록률 추정치입니다.",
    )
    add_metric(
        "KIPRIS 존속률(전체 대비 추정)",
        _pct_from_rate(core_rates.get("alive_rate_total_estimated")),
        "%",
        "존속 가능 특허 수를 전체 특허 수로 나눈 보수적 존속률 추정치입니다.",
    )
    add_metric(
        "KIPRIS 존속률(등록특허 중 추정)",
        _pct_from_rate(core_rates.get("alive_rate_among_registered_estimated")),
        "%",
        "존속 가능 특허 수를 등록 특허 수로 나눈 권리 안정성 지표입니다.",
    )
    add_metric(
        "KIPRIS 부정 처분 비중(추정)",
        _pct_from_rate(core_rates.get("negative_disposal_rate_estimated")),
        "%",
        "미등록·소멸·거절·취하 등으로 추정되는 부정 처분성 상태 비중입니다.",
    )
    add_metric(
        "KIPRIS 최근 5년 출원 비중",
        _pct_from_rate(core_rates.get("recent_5y_application_rate")),
        "%",
        "최근 5년 출원 특허 비중으로 포트폴리오의 최신성을 나타냅니다.",
    )
    add_metric(
        "KIPRIS 반도체 관련 IPC 특허 수",
        _num_or_none(core_counts.get("semiconductor_related_ipc_patents"), 0),
        "건",
        "반도체 관련 IPC/CPC 분류와 연결되는 특허 수입니다.",
    )
    add_metric(
        "KIPRIS 반도체 관련 IPC 비중",
        _pct_from_rate(core_rates.get("semiconductor_related_ipc_rate")),
        "%",
        "전체 특허 중 반도체 관련 IPC/CPC 분류 특허 비중입니다.",
    )
    add_metric(
        "KIPRIS H01L 핵심 IPC 특허 수",
        _num_or_none(core_counts.get("h01l_core_patents"), 0),
        "건",
        "H01L 반도체 소자·패키징 관련 핵심 IPC 특허 수입니다.",
    )
    add_metric(
        "KIPRIS 법적 안정성 점수",
        _num_or_none(scores.get("legal_stability_score_estimated"), 2),
        "점",
        "등록률·존속률·부정 처분 비중을 반영한 권리 안정성 점수입니다.",
    )
    add_metric(
        "KIPRIS 포트폴리오 모멘텀 점수",
        _num_or_none(scores.get("portfolio_momentum_score"), 2),
        "점",
        "최근 출원 비중과 포트폴리오 최신성을 반영한 점수입니다.",
    )
    add_metric(
        "KIPRIS 기술 적합도 점수",
        _num_or_none(scores.get("ip_technology_fit_score"), 2),
        "점",
        "반도체 IPC 비중, H01L 특허, 기술 키워드 매칭을 반영한 점수입니다.",
    )
    add_metric(
        "KIPRIS Tech ML 종합 점수",
        _num_or_none(scores.get("kipris_tech_ml_score"), 2),
        "점",
        "권리 안정성, 포트폴리오 모멘텀, 기술 적합도를 종합한 KIPRIS 기반 Tech ML 점수입니다.",
    )
    add_metric(
        "KIPRIS Tech-to-Value Bridge 보정점",
        _num_or_none(adjustment.get("bridge_adjustment_points"), 2),
        "점",
        "직접 사업화 근거가 아니라 IP 품질 보조 신호로만 사용하는 보수적 Bridge 보정점입니다.",
    )

    return metrics
# KIPRIS_TECH_ML_RUNTIME_PATCH_V2_END
'''


def main() -> int:
    if not TARGET.exists():
        raise FileNotFoundError(f"파일이 없습니다: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    backup = TARGET.with_suffix(TARGET.suffix + ".bak_kipris_tech_ml_v2")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
        print(f"[BACKUP] {backup}")

    changed = False

    if "KIPRIS_TECH_ML_RUNTIME_PATCH_V2_START" not in text:
        text = text.rstrip() + "\n" + HELPER_CODE + "\n"
        changed = True
        print("[PATCH] helper functions appended")

    if "kipris_tech_ml_features = _load_kipris_tech_ml_features" not in text:
        pattern = r"(?m)^(\s*)metrics\s*=\s*_build_metrics\(effective,\s*normalized\)\s*$"

        def repl(match: re.Match[str]) -> str:
            indent = match.group(1)
            return (
                f"{indent}metrics = _build_metrics(effective, normalized)\n"
                f"{indent}kipris_tech_ml_features = _load_kipris_tech_ml_features(company, locals().get('company_dir'))\n"
                f"{indent}if kipris_tech_ml_features:\n"
                f"{indent}    metrics = _merge_kipris_tech_ml_metrics(metrics, kipris_tech_ml_features)"
            )

        text2, count = re.subn(pattern, repl, text, count=1)
        if count == 0:
            raise RuntimeError(
                "patent_harvester.py에서 `metrics = _build_metrics(effective, normalized)` 라인을 찾지 못했습니다. "
                "먼저 `Select-String -Path src\\tech_agent\\patent_harvester.py -Pattern \"_build_metrics\"`로 현재 구조를 확인하세요."
            )
        text = text2
        changed = True
        print("[PATCH] KIPRIS Tech ML features merged into patent metrics")

    if '"kipris_tech_ml_features": kipris_tech_ml_features,' not in text:
        text2 = text.replace(
            '        "metrics": metrics,\n',
            '        "metrics": metrics,\n        "kipris_tech_ml_features": kipris_tech_ml_features,\n',
            1,
        )
        if text2 != text:
            text = text2
            changed = True
            print("[PATCH] return payload includes kipris_tech_ml_features")
        else:
            print("[WARN] return payload 위치는 자동 삽입하지 못했지만 metrics 병합은 적용됩니다.")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print(f"[DONE] patched: {TARGET}")
    else:
        print("[SKIP] already patched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

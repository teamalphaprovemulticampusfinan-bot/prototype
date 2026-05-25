from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any

from common.output_paths import shared_output_dir


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ml_universe_dir()

DEFAULT_OVERLAY_CANDIDATE_PATHS = [
    ml_universe_dir() / "valuation_credit_ml_overlay_candidate.csv",
    field_common_dir("data") / "valuation_credit_ml_overlay_candidate.csv",
    shared_output_dir("tech", root=ROOT) / "valuation_credit_ml_overlay_candidate.csv",
    ROOT / "valuation_credit_ml_overlay_candidate.csv",
]

FOCAL_COMPANIES = {
    "033640": "네패스",
    "042700": "한미반도체",
    "014680": "한솔케미칼",
    "317330": "덕산테코피아",
    "170920": "LTC",
}

FOCAL_NAME_ALIASES = {
    "네패스": "033640",
    "한미반도체": "042700",
    "한솔케미칼": "014680",
    "덕산테코피아": "317330",
    "LTC": "170920",
    "엘티씨": "170920",
}


@dataclass
class UniverseRow:
    universe_id: str
    company_name: str
    ticker: str
    market: str
    sector_theme: str
    sector_label: str
    peer_group: str
    semiconductor_tag: str
    is_focal: int
    selected_for_30: int
    include_in_chair: int
    reference_role: str
    selection_rank_global: int
    selection_rank_in_sector: int
    selection_score: float
    selection_reason: str
    valuation_proxy_score: str
    valuation_proxy_label: str
    credit_risk_score: str
    credit_proxy_label: str
    valuation_pred_label: str
    credit_pred_label: str
    valuation_confidence: str
    credit_confidence: str
    valuation_confidence_bucket: str
    credit_confidence_bucket: str
    credit_anomaly_flag_top15pct: str
    auditor_requires_human_review: str
    data_quality_status: str
    manual_review_priority: str
    market_data_available: str
    data_requirements: str
    source_type: str
    review_flag: str
    created_at: str
    notes: str


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_ticker(value: Any) -> str:
    text = clean_text(value)
    text = re.sub(r"[^0-9]", "", text)
    return text.zfill(6) if text else ""


def parse_bool(value: Any) -> bool:
    text = clean_text(value).lower()
    return text in {"true", "1", "yes", "y", "t"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = clean_text(value)
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def slugify(value: str) -> str:
    text = clean_text(value)
    if not text:
        return "unclassified"
    text = text.lower()
    text = text.replace("/", "_").replace("·", "_").replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^0-9a-zA-Z가-힣_]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unclassified"


def find_overlay_csv(path_arg: str | None = None) -> Path:
    if path_arg:
        path = Path(path_arg)
        if path.exists():
            return path
        raise FileNotFoundError(f"지정한 overlay CSV를 찾지 못했습니다: {path}")

    for path in DEFAULT_OVERLAY_CANDIDATE_PATHS:
        if path.exists():
            return path

    candidates = sorted(ROOT.rglob("valuation_credit_ml_overlay_candidate.csv"))
    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        "valuation_credit_ml_overlay_candidate.csv를 찾지 못했습니다. "
        "data/<분야>/common/ml_universe/valuation_credit_ml_overlay_candidate.csv 위치에 저장하거나 "
        "--overlay-csv 경로를 지정하세요."
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [{str(k): clean_text(v) for k, v in row.items()} for row in csv.DictReader(f)]
        except Exception:
            continue
    raise RuntimeError(f"CSV 인코딩을 읽지 못했습니다: {path}")


def row_ticker(row: dict[str, str]) -> str:
    return normalize_ticker(
        row.get("ticker6")
        or row.get("ticker")
        or row.get("stock_code")
        or row.get("종목코드")
    )


def row_company(row: dict[str, str]) -> str:
    return clean_text(
        row.get("company_name")
        or row.get("corp_name")
        or row.get("name")
        or row.get("기업명")
    )


def row_sector(row: dict[str, str]) -> tuple[str, str, str, str]:
    peer_group = clean_text(row.get("peer_group"))
    semiconductor_tag = clean_text(row.get("semiconductor_tag"))
    sector_label = semiconductor_tag or peer_group or "미분류"
    sector_theme = slugify(sector_label)
    return sector_theme, sector_label, peer_group, semiconductor_tag


def is_focal_company(row: dict[str, str]) -> int:
    ticker = row_ticker(row)
    name = row_company(row)
    if ticker in FOCAL_COMPANIES:
        return 1
    if name in FOCAL_NAME_ALIASES:
        return 1
    return 0


def build_review_flag(row: dict[str, str]) -> str:
    flags: list[str] = []

    data_quality = clean_text(row.get("data_quality_status"))
    manual_priority = clean_text(row.get("manual_review_priority"))
    market_available = parse_bool(row.get("market_data_available"))
    auditor_review = parse_bool(row.get("auditor_requires_human_review"))
    anomaly = parse_bool(row.get("credit_anomaly_flag_top15pct"))

    if not row_ticker(row):
        flags.append("MISSING_TICKER")
    if not row_company(row):
        flags.append("MISSING_COMPANY")
    if not market_available:
        flags.append("NO_MARKET_DATA")
    if data_quality and data_quality != "OK":
        flags.append(data_quality)
    if manual_priority and manual_priority.upper() in {"MEDIUM", "HIGH"}:
        flags.append(f"MANUAL_{manual_priority.upper()}")
    if auditor_review:
        flags.append("AUDITOR_REVIEW")
    if anomaly:
        flags.append("CREDIT_ANOMALY_TOP15PCT")

    return ";".join(flags) if flags else "OK"


def overlay_selection_score(row: dict[str, str]) -> float:
    valuation_score = safe_float(row.get("valuation_proxy_score"))
    credit_risk = safe_float(row.get("credit_risk_score"))
    valuation_conf = safe_float(row.get("valuation_confidence"))
    credit_conf = safe_float(row.get("credit_confidence"))

    market_available = parse_bool(row.get("market_data_available"))
    auditor_review = parse_bool(row.get("auditor_requires_human_review"))
    anomaly = parse_bool(row.get("credit_anomaly_flag_top15pct"))

    valuation_label = clean_text(row.get("valuation_proxy_label") or row.get("valuation_pred_label")).upper()
    credit_label = clean_text(row.get("credit_proxy_label") or row.get("credit_pred_label")).upper()
    data_quality = clean_text(row.get("data_quality_status")).upper()
    manual_priority = clean_text(row.get("manual_review_priority")).upper()

    score = 0.0

    # 기본: 가치 매력도와 신용 건전성을 동시에 반영
    score += valuation_score * 35.0
    score += (1.0 - min(max(credit_risk, 0.0), 1.0)) * 25.0
    score += valuation_conf * 15.0
    score += credit_conf * 15.0

    # 라벨 보정
    if valuation_label == "ATTRACTIVE":
        score += 8.0
    elif valuation_label == "FAIR":
        score += 4.0
    elif valuation_label == "EXPENSIVE":
        score -= 5.0

    if credit_label == "LOW_RISK":
        score += 8.0
    elif credit_label == "MEDIUM_RISK":
        score += 2.0
    elif credit_label == "HIGH_RISK":
        score -= 8.0

    # 데이터 품질 보정
    if market_available:
        score += 5.0
    else:
        score -= 10.0

    if data_quality == "OK":
        score += 5.0
    elif data_quality:
        score -= 8.0

    if manual_priority == "HIGH":
        score -= 12.0
    elif manual_priority == "MEDIUM":
        score -= 6.0

    if auditor_review:
        score -= 10.0
    if anomaly:
        score -= 5.0

    if is_focal_company(row):
        score += 1000.0

    return round(score, 4)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: dict[str, dict[str, str]] = {}

    for row in rows:
        ticker = row_ticker(row)
        name = row_company(row)
        if not ticker and not name:
            continue
        key = ticker or name.lower()

        prev = out.get(key)
        if prev is None:
            out[key] = row
            continue

        # 동일 기업 중 selection score가 높은 행 유지
        if overlay_selection_score(row) > overlay_selection_score(prev):
            out[key] = row

    return list(out.values())


def allocate_sector_quota(
    rows: list[dict[str, str]],
    max_total: int,
    min_per_sector: int,
) -> dict[str, int]:
    sectors = sorted({row_sector(r)[0] for r in rows})
    counts = {s: 0 for s in sectors}

    # 1차: 섹터별 최소 개수
    for s in sectors:
        available = sum(1 for r in rows if row_sector(r)[0] == s)
        counts[s] = min(min_per_sector, available)

    # max_total 초과 시 후보 수가 적은 뒤쪽부터 축소
    while sum(counts.values()) > max_total and any(v > 0 for v in counts.values()):
        for s in sorted(sectors, reverse=True):
            if sum(counts.values()) <= max_total:
                break
            if counts[s] > 0:
                counts[s] -= 1

    # 2차: 남은 quota는 후보 수와 고득점 섹터에 배분
    while sum(counts.values()) < max_total:
        progressed = False
        for s in sectors:
            available = sum(1 for r in rows if row_sector(r)[0] == s)
            if counts[s] < available and sum(counts.values()) < max_total:
                counts[s] += 1
                progressed = True
        if not progressed:
            break

    return counts


def select_rows(
    rows: list[dict[str, str]],
    max_total: int = 30,
    min_per_sector: int = 2,
    sector_filter: list[str] | None = None,
    exclude_human_review: bool = False,
) -> list[dict[str, str]]:
    rows = dedupe_rows(rows)

    if sector_filter:
        allowed = {slugify(s) for s in sector_filter} | set(sector_filter)
        rows = [r for r in rows if row_sector(r)[0] in allowed or row_sector(r)[1] in allowed]

    if exclude_human_review:
        rows = [r for r in rows if not parse_bool(r.get("auditor_requires_human_review"))]

    focal = [r for r in rows if is_focal_company(r)]
    non_focal = [r for r in rows if not is_focal_company(r)]

    # focal은 무조건 포함한다.
    selected: list[dict[str, str]] = []
    selected_keys: set[str] = set()

    for r in sorted(focal, key=overlay_selection_score, reverse=True):
        key = row_ticker(r) or row_company(r).lower()
        if key in selected_keys:
            continue
        selected.append(r)
        selected_keys.add(key)

    remaining_quota = max(0, max_total - len(selected))
    if remaining_quota <= 0:
        return selected[:max_total]

    quotas = allocate_sector_quota(non_focal, max_total=remaining_quota, min_per_sector=min_per_sector)

    for sector, quota in quotas.items():
        sector_rows = [r for r in non_focal if row_sector(r)[0] == sector]
        sector_rows = sorted(sector_rows, key=overlay_selection_score, reverse=True)

        picked_count = 0
        for r in sector_rows:
            if picked_count >= quota:
                break
            key = row_ticker(r) or row_company(r).lower()
            if key in selected_keys:
                continue
            selected.append(r)
            selected_keys.add(key)
            picked_count += 1

    # quota 배분 후 남는 자리는 전체 고득점으로 채움
    if len(selected) < max_total:
        candidates = sorted(non_focal, key=overlay_selection_score, reverse=True)
        for r in candidates:
            if len(selected) >= max_total:
                break
            key = row_ticker(r) or row_company(r).lower()
            if key in selected_keys:
                continue
            selected.append(r)
            selected_keys.add(key)

    return selected[:max_total]


def make_universe_rows(selected: list[dict[str, str]]) -> list[UniverseRow]:
    created_at = datetime.now().isoformat(timespec="seconds")

    sector_rank_counter: dict[str, int] = {}
    out: list[UniverseRow] = []

    ranked = sorted(selected, key=overlay_selection_score, reverse=True)

    for global_rank, row in enumerate(ranked, start=1):
        sector_theme, sector_label, peer_group, semiconductor_tag = row_sector(row)
        sector_rank_counter[sector_theme] = sector_rank_counter.get(sector_theme, 0) + 1
        sector_rank = sector_rank_counter[sector_theme]

        ticker = row_ticker(row)
        name = row_company(row)
        is_focal = is_focal_company(row)

        review_flag = build_review_flag(row)
        selected_for_30 = 1
        include_in_chair = 1 if is_focal else 0

        if is_focal:
            role = "FOCAL_REPORT_TARGET"
            reason_prefix = "현재 MVP focal 기업"
        else:
            role = "REFERENCE_PEER_FROM_VALUATION_CREDIT_ML"
            reason_prefix = "valuation/credit ML overlay 기반 reference peer 후보"

        selection_reason = (
            f"{reason_prefix}; "
            f"valuation={clean_text(row.get('valuation_proxy_label') or row.get('valuation_pred_label'))}; "
            f"credit={clean_text(row.get('credit_proxy_label') or row.get('credit_pred_label'))}; "
            f"quality={clean_text(row.get('data_quality_status'))}; "
            f"human_review={clean_text(row.get('auditor_requires_human_review'))}"
        )

        out.append(
            UniverseRow(
                universe_id=f"{sector_theme}_{sector_rank:02d}_{ticker or slugify(name)}",
                company_name=name,
                ticker=ticker,
                market=clean_text(row.get("krx_market") or row.get("market") or "CHECK"),
                sector_theme=sector_theme,
                sector_label=sector_label,
                peer_group=peer_group,
                semiconductor_tag=semiconductor_tag,
                is_focal=is_focal,
                selected_for_30=selected_for_30,
                include_in_chair=include_in_chair,
                reference_role=role,
                selection_rank_global=global_rank,
                selection_rank_in_sector=sector_rank,
                selection_score=overlay_selection_score(row),
                selection_reason=selection_reason,
                valuation_proxy_score=clean_text(row.get("valuation_proxy_score")),
                valuation_proxy_label=clean_text(row.get("valuation_proxy_label")),
                credit_risk_score=clean_text(row.get("credit_risk_score")),
                credit_proxy_label=clean_text(row.get("credit_proxy_label")),
                valuation_pred_label=clean_text(row.get("valuation_pred_label")),
                credit_pred_label=clean_text(row.get("credit_pred_label")),
                valuation_confidence=clean_text(row.get("valuation_confidence")),
                credit_confidence=clean_text(row.get("credit_confidence")),
                valuation_confidence_bucket=clean_text(row.get("valuation_confidence_bucket")),
                credit_confidence_bucket=clean_text(row.get("credit_confidence_bucket")),
                credit_anomaly_flag_top15pct=clean_text(row.get("credit_anomaly_flag_top15pct")),
                auditor_requires_human_review=clean_text(row.get("auditor_requires_human_review")),
                data_quality_status=clean_text(row.get("data_quality_status")),
                manual_review_priority=clean_text(row.get("manual_review_priority")),
                market_data_available=clean_text(row.get("market_data_available")),
                data_requirements="KIPRIS patents|DART business report|finance overlay|market data|news optional",
                source_type="valuation_credit_ml_overlay_candidate.csv",
                review_flag=review_flag,
                created_at=created_at,
                notes="개별 company 폴더 없이 reference universe/peer clustering/percentile 계산에 우선 사용",
            )
        )

    return out


def summarize(rows: list[UniverseRow], source_path: Path, raw_count: int) -> dict[str, Any]:
    sector_summary: dict[str, Any] = {}
    for row in rows:
        item = sector_summary.setdefault(
            row.sector_theme,
            {
                "sector_label": row.sector_label,
                "selected_count": 0,
                "focal_count": 0,
                "reference_count": 0,
                "human_review_count": 0,
                "avg_selection_score": 0.0,
                "scores": [],
            },
        )
        item["selected_count"] += 1
        item["focal_count"] += row.is_focal
        item["reference_count"] += 0 if row.is_focal else 1
        if "AUDITOR_REVIEW" in row.review_flag or "MANUAL_" in row.review_flag:
            item["human_review_count"] += 1
        item["scores"].append(row.selection_score)

    for item in sector_summary.values():
        scores = item.pop("scores", [])
        item["avg_selection_score"] = round(sum(scores) / len(scores), 4) if scores else 0.0

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_csv": str(source_path),
        "raw_candidate_count": raw_count,
        "selected_total": len(rows),
        "focal_total": sum(r.is_focal for r in rows),
        "reference_total": sum(1 for r in rows if not r.is_focal),
        "include_in_chair_total": sum(r.include_in_chair for r in rows),
        "selected_for_30_total": sum(r.selected_for_30 for r in rows),
        "sector_summary": sector_summary,
        "notes": [
            "source CSV의 peer_group/semiconductor_tag를 sector_theme로 변환해 분야별 universe를 생성했습니다.",
            "selection_score는 valuation proxy, credit risk, confidence, data quality, auditor review flag를 함께 반영합니다.",
            "include_in_chair=1은 현재 5개 focal 기업만 의미합니다. 30개 전체 Chair 실행은 company.yaml 생성 단계 이후 확장합니다.",
            "include_in_chair=0인 기업은 개별 폴더 없이 reference peer clustering, cosine similarity, percentile 계산에 사용합니다.",
        ],
    }


def write_csv(path: Path, rows: list[UniverseRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(UniverseRow.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_sector_peer_map(rows: list[UniverseRow]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for row in rows:
        sector = out.setdefault(
            row.sector_theme,
            {
                "sector_label": row.sector_label,
                "peer_group": row.peer_group,
                "semiconductor_tag": row.semiconductor_tag,
                "focal_companies": [],
                "reference_companies": [],
                "all_companies": [],
            },
        )

        item = {
            "company_name": row.company_name,
            "ticker": row.ticker,
            "market": row.market,
            "selection_score": row.selection_score,
            "valuation_proxy_label": row.valuation_proxy_label,
            "credit_proxy_label": row.credit_proxy_label,
            "valuation_confidence": row.valuation_confidence,
            "credit_confidence": row.credit_confidence,
            "review_flag": row.review_flag,
            "include_in_chair": row.include_in_chair,
        }

        sector["all_companies"].append(item)
        if row.is_focal:
            sector["focal_companies"].append(item)
        else:
            sector["reference_companies"].append(item)

    return out


def build_markdown(rows: list[UniverseRow], summary: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# Reference Universe from Valuation/Credit ML Overlay")
    lines.append("")
    lines.append("## 1. 생성 요약")
    lines.append(f"- 원천 CSV: `{summary.get('source_csv')}`")
    lines.append(f"- 원천 후보 수: **{summary.get('raw_candidate_count')}개**")
    lines.append(f"- 선택 기업 수: **{summary.get('selected_total')}개**")
    lines.append(f"- 현재 focal 기업 수: **{summary.get('focal_total')}개**")
    lines.append(f"- reference peer 전용 기업 수: **{summary.get('reference_total')}개**")
    lines.append(f"- 현재 Chair 직접 실행 대상: **{summary.get('include_in_chair_total')}개**")
    lines.append("")
    lines.append("## 2. 분야별 요약")
    lines.append("| 분야 | 선택 수 | Focal | Reference | 검토 필요 | 평균 선택점수 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for _, item in summary.get("sector_summary", {}).items():
        lines.append(
            f"| {item.get('sector_label')} | "
            f"{item.get('selected_count')} | "
            f"{item.get('focal_count')} | "
            f"{item.get('reference_count')} | "
            f"{item.get('human_review_count')} | "
            f"{item.get('avg_selection_score')} |"
        )
    lines.append("")

    lines.append("## 3. 선택 Universe")
    lines.append("| 순위 | 분야 | 기업 | 티커 | 시장 | 역할 | 선택점수 | 가치라벨 | 신용라벨 | 검토 |")
    lines.append("|---:|---|---|---|---|---|---:|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row.selection_rank_global} | "
            f"{row.sector_label} | "
            f"{row.company_name} | "
            f"{row.ticker} | "
            f"{row.market} | "
            f"{row.reference_role} | "
            f"{row.selection_score:.4f} | "
            f"{row.valuation_proxy_label or row.valuation_pred_label} | "
            f"{row.credit_proxy_label or row.credit_pred_label} | "
            f"{row.review_flag} |"
        )
    lines.append("")

    lines.append("## 4. 활용 원칙")
    for note in summary.get("notes", []):
        lines.append(f"- {note}")

    return "\n".join(lines).strip() + "\n"


def run_reference_universe_builder(
    overlay_csv: str | None = None,
    max_total: int = 30,
    min_per_sector: int = 2,
    sectors: list[str] | None = None,
    exclude_human_review: bool = False,
    output_dir: Path = OUT_DIR,
) -> dict[str, Any]:
    source_path = find_overlay_csv(overlay_csv)
    raw_rows = read_csv_rows(source_path)

    selected = select_rows(
        raw_rows,
        max_total=max_total,
        min_per_sector=min_per_sector,
        sector_filter=sectors,
        exclude_human_review=exclude_human_review,
    )

    universe_rows = make_universe_rows(selected)
    summary = summarize(universe_rows, source_path=source_path, raw_count=len(raw_rows))

    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "deeptech_reference_universe.csv"
    json_path = output_dir / "deeptech_reference_universe.json"
    md_path = output_dir / "deeptech_reference_universe.md"
    summary_path = output_dir / "reference_universe_summary.json"
    map_path = output_dir / "sector_peer_map.json"

    write_csv(csv_path, universe_rows)
    write_json(json_path, [asdict(row) for row in universe_rows])
    write_json(summary_path, summary)
    write_json(map_path, build_sector_peer_map(universe_rows))
    md_path.write_text(build_markdown(universe_rows, summary), encoding="utf-8")

    print(f"[Reference Universe] source={source_path}")
    print(f"[Reference Universe] CSV 저장 완료: {csv_path}")
    print(f"[Reference Universe] JSON 저장 완료: {json_path}")
    print(f"[Reference Universe] Markdown 저장 완료: {md_path}")
    print(f"[Reference Universe] 선택 기업 수: {summary['selected_total']}개")
    print(f"[Reference Universe] focal={summary['focal_total']} / reference={summary['reference_total']} / include_in_chair={summary['include_in_chair_total']}")

    return {
        "source_csv": str(source_path),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "summary_path": str(summary_path),
        "sector_peer_map_path": str(map_path),
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build sector-based reference universe from valuation_credit_ml_overlay_candidate.csv."
    )
    parser.add_argument("--overlay-csv", default="", help="path to valuation_credit_ml_overlay_candidate.csv")
    parser.add_argument("--max-total", type=int, default=30, help="selected universe size")
    parser.add_argument("--min-per-sector", type=int, default=2, help="minimum selected count per sector before global fill")
    parser.add_argument("--sectors", nargs="*", default=[], help="optional sector_label or slug filter")
    parser.add_argument("--exclude-human-review", action="store_true", help="exclude rows requiring human review")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    run_reference_universe_builder(
        overlay_csv=args.overlay_csv or None,
        max_total=args.max_total,
        min_per_sector=args.min_per_sector,
        sectors=args.sectors or None,
        exclude_human_review=args.exclude_human_review,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

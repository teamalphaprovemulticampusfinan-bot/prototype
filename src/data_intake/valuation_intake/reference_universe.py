from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from common.data_paths import ROOT_DIR, ml_universe_dir, rel_project_path

FOCAL_TICKER_TO_SLUG = {
    "033640": "nepes",
    "042700": "hanmi",
    "014680": "hansol",
    "317330": "duksan",
    "170920": "ltc",
    "000990": "dbhitek",
    "059090": "mico",
    "108320": "lxsemicon",
    "080220": "jeju_semicon",
    "102120": "abov",
    "054450": "telechips",
    "045970": "coasia",
    "399720": "gaochips",
    "240810": "wonik_ips",
    "084370": "eugene_tech",
    "319660": "psk",
    "095610": "tes",
    "083450": "gst",
    "039440": "sti",
    "348210": "nextin",
    "357780": "soulbrain",
    "005290": "dongjin_semichem",
    "104830": "wonik_materials",
    "102710": "enf_tech",
    "064760": "tck",
    "101160": "woldex",
    "095340": "isc",
    "036540": "sfa_semicon",
    "131970": "doosan_tesna",
    "058470": "leeno",
}

FOCAL_NAMES = {"네패스", "한미반도체", "한솔케미칼", "덕산테코피아", "엘티씨", "LTC", "DB하이텍", "미코", "LX세미콘", "제주반도체", "어보브반도체", "텔레칩스", "코아시아", "가온칩스", "원익IPS", "유진테크", "피에스케이", "테스", "GST", "에스티아이", "넥스틴", "솔브레인", "동진쎄미켐", "원익머트리얼즈", "이엔에프테크놀로지", "티씨케이", "월덱스", "ISC", "SFA반도체", "두산테스나", "리노공업"}

VALUATION_LABEL_KR = {
    "ATTRACTIVE": "가치 매력",
    "NEUTRAL": "중립",
    "UNATTRACTIVE": "가치 부담",
    "BUY": "매수 후보",
    "HOLD": "보유 후보",
    "SELL": "매도/주의 후보",
}

CREDIT_LABEL_KR = {
    "LOW_RISK": "저위험",
    "MEDIUM_RISK": "중위험",
    "HIGH_RISK": "고위험",
}


def _label_kr(value: Any, mapping: dict[str, str], default: str = "해당 없음") -> str:
    text = str(value or "").strip().upper()
    return mapping.get(text, default if not text else text)



def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "None", "none", "nan", "NaN", "null"}:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "ok"}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        with path.open("r", encoding="cp949", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        fieldnames = seen
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _candidate_paths(field: str = "반도체") -> list[Path]:
    name = "valuation_credit_ml_overlay_candidate.csv"
    return [
        ml_universe_dir(field=field, create=False) / name,
        ROOT_DIR / "src" / "auditor_agent" / "resources" / name,
        ROOT_DIR / "data" / "반도체" / "_sector_common" / "ml_universe" / name,
        ROOT_DIR / "data" / "#Ubc18#Ub3c4#Uccb4" / "_sector_common" / "ml_universe" / name,
    ]


def locate_reference_universe_csv(field: str = "반도체") -> Path | None:
    for path in _candidate_paths(field):
        try:
            if path.exists() and path.is_file():
                return path
        except Exception:
            continue
    return None


def _normalize_row(row: dict[str, Any], idx: int) -> dict[str, Any]:
    ticker = str(row.get("ticker6") or row.get("ticker") or row.get("stock_code") or "").strip().zfill(6)
    company = str(row.get("company_name") or row.get("company") or "").strip()
    market = str(row.get("krx_market") or row.get("market") or "").strip()
    peer_group = str(row.get("peer_group") or row.get("semiconductor_tag") or row.get("sector_label") or "미분류").strip() or "미분류"
    valuation_score = _to_float(row.get("valuation_proxy_score"))
    credit_risk = _to_float(row.get("credit_risk_score"))
    val_conf = _to_float(row.get("valuation_confidence"))
    credit_conf = _to_float(row.get("credit_confidence"))
    anomaly = _to_float(row.get("credit_anomaly_score"))
    focal = company in FOCAL_NAMES or ticker in FOCAL_TICKER_TO_SLUG
    valuation_label = row.get("valuation_proxy_label") or row.get("valuation_pred_label") or "해당 없음"
    credit_label = row.get("credit_proxy_label") or row.get("credit_pred_label") or "해당 없음"
    valuation_bucket = row.get("valuation_confidence_bucket") or "구간 미제공"
    credit_bucket = row.get("credit_confidence_bucket") or "구간 미제공"
    return {
        "universe_rank": idx,
        "company_dir": FOCAL_TICKER_TO_SLUG.get(ticker, ""),
        "company_name": company,
        "ticker6": ticker,
        "market": market,
        "peer_group": peer_group,
        "semiconductor_tag": str(row.get("semiconductor_tag") or peer_group),
        "is_focal_5": focal,
        "market_data_available": _to_bool(row.get("market_data_available")),
        "data_quality_status": row.get("data_quality_status") or "해당 없음",
        "data_quality_status_kr": "데이터 사용 가능" if _to_bool(row.get("market_data_available")) else "시장 데이터 일부 미제공",
        "manual_review_priority": row.get("manual_review_priority") or "검토 우선순위 미제공",
        "manual_review_priority_kr": str(row.get("manual_review_priority") or "보통"),
        "valuation_proxy_score": valuation_score,
        "valuation_proxy_label": valuation_label,
        "valuation_proxy_label_kr": _label_kr(valuation_label, VALUATION_LABEL_KR),
        "valuation_pred_label": row.get("valuation_pred_label") or valuation_label,
        "valuation_confidence": val_conf,
        "valuation_confidence_bucket": valuation_bucket,
        "valuation_confidence_bucket_kr": valuation_bucket,
        "credit_risk_score": credit_risk,
        "credit_proxy_label": credit_label,
        "credit_proxy_label_kr": _label_kr(credit_label, CREDIT_LABEL_KR),
        "credit_pred_label": row.get("credit_pred_label") or credit_label,
        "credit_confidence": credit_conf,
        "credit_confidence_bucket": credit_bucket,
        "credit_confidence_bucket_kr": credit_bucket,
        "credit_anomaly_score": anomaly,
        "credit_anomaly_flag_top15pct": _to_bool(row.get("credit_anomaly_flag_top15pct")),
        "auditor_requires_human_review": _to_bool(row.get("auditor_requires_human_review")),
        "source_type": "valuation_credit_ml_overlay_candidate.csv",
        "source_note": "208개 반도체 reference universe. Valuation Agent가 자체 intake 폴더로 복제해 Peer/ML/대시보드 비교에 사용.",
    }


def load_reference_universe(field: str = "반도체") -> tuple[list[dict[str, Any]], Path | None]:
    path = locate_reference_universe_csv(field)
    if path is None:
        return [], None
    rows = [_normalize_row(row, idx + 1) for idx, row in enumerate(_read_csv(path))]
    rows = [r for r in rows if r.get("company_name") or r.get("ticker6")]
    rows.sort(key=lambda r: (str(r.get("peer_group") or ""), -(float(r.get("valuation_proxy_score") or 0.0))))
    return rows, path


def build_reference_focus(
    universe: list[dict[str, Any]],
    *,
    target_company: str,
    target_ticker: str | None = None,
    target_slug: str | None = None,
    max_rows: int = 40,
) -> list[dict[str, Any]]:
    if not universe:
        return []
    ticker = str(target_ticker or "").zfill(6) if target_ticker else ""
    target = None
    for row in universe:
        if row.get("company_name") == target_company or (ticker and str(row.get("ticker6")) == ticker) or (target_slug and row.get("company_dir") == target_slug):
            target = row
            break
    target_group = target.get("peer_group") if target else None
    focus: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any], reason: str) -> None:
        key = str(row.get("ticker6") or row.get("company_name") or len(focus))
        if key in seen:
            return
        seen.add(key)
        out = dict(row)
        out["focus_reason"] = reason
        out["is_target"] = bool(target and key == str(target.get("ticker6")))
        focus.append(out)

    if target:
        add(target, "TARGET")
    if target_group:
        group_rows = [r for r in universe if r.get("peer_group") == target_group and r is not target]
        group_rows.sort(key=lambda r: (-(float(r.get("valuation_proxy_score") or 0.0)), float(r.get("credit_risk_score") or 9.0)))
        for r in group_rows[: max_rows // 2]:
            add(r, "SAME_PEER_GROUP")
    for r in universe:
        if r.get("is_focal_5"):
            add(r, "FOCAL_5")
    top_rows = sorted(universe, key=lambda r: (-(float(r.get("valuation_proxy_score") or 0.0)), float(r.get("credit_risk_score") or 9.0)))
    for r in top_rows:
        if len(focus) >= max_rows:
            break
        add(r, "TOP_REFERENCE")
    return focus[:max_rows]


def reference_universe_summary(universe: list[dict[str, Any]], focus: list[dict[str, Any]], *, target_company: str) -> dict[str, Any]:
    if not universe:
        return {
            "status": "WARN_NO_REFERENCE_UNIVERSE",
            "reference_universe_rows": 0,
            "focus_rows": 0,
            "message": "208개 reference universe CSV를 찾지 못했습니다.",
        }
    target = next((r for r in universe if r.get("company_name") == target_company or r.get("is_target")), None)
    peer_group = target.get("peer_group") if target else None
    peer_group_size = sum(1 for r in universe if peer_group and r.get("peer_group") == peer_group)
    focal_count = sum(1 for r in universe if r.get("is_focal_5"))
    attractive_count = sum(1 for r in universe if str(r.get("valuation_proxy_label") or "").upper() == "ATTRACTIVE")
    high_risk_count = sum(1 for r in universe if str(r.get("credit_proxy_label") or "").upper() == "HIGH_RISK")
    return {
        "status": "OK",
        "created_at": _now(),
        "reference_universe_rows": len(universe),
        "focus_rows": len(focus),
        "focal_5_rows": focal_count,
        "target_company": target_company,
        "target_peer_group": peer_group or "해당 없음",
        "target_peer_group_size": peer_group_size,
        "attractive_rows": attractive_count,
        "high_risk_rows": high_risk_count,
        "target_reference_row": target or {},
        "note": "Valuation Agent는 live DCF/PSR 산출과 별도로 208개 반도체 universe의 proxy score를 활용해 상대 위치를 보조 판단합니다.",
    }


def export_reference_universe(
    intake_dir: Path,
    *,
    company: str,
    company_dir: str,
    stock_code: str | None = None,
    field: str = "반도체",
    max_focus_rows: int = 40,
) -> dict[str, Any]:
    universe, source_path = load_reference_universe(field)
    focus = build_reference_focus(
        universe,
        target_company=company,
        target_ticker=stock_code,
        target_slug=company_dir,
        max_rows=max_focus_rows,
    )
    summary = reference_universe_summary(universe, focus, target_company=company)
    summary["source_path"] = rel_project_path(source_path) if source_path else ""
    summary["exported_at"] = _now()

    all_path = _write_csv(intake_dir / "valuation_reference_universe_208.csv", universe)
    focus_path = _write_csv(intake_dir / "valuation_reference_universe_focus.csv", focus)
    summary_path = intake_dir / "valuation_reference_universe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "universe": universe,
        "focus": focus,
        "summary": summary,
        "source_path": source_path,
        "all_path": all_path,
        "focus_path": focus_path,
        "summary_path": summary_path,
    }

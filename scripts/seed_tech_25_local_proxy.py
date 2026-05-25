from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_CSV = DATA / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"
ORIGINAL_5 = {"nepes", "hanmi", "hansol", "duksan", "ltc"}


def safe_name(value: Any, default: str = "unknown") -> str:
    text = str(value or "").strip().strip('"').strip("'")
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", "_", text).strip("._ ")
    return text or default


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "y", "yes", "include"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f) if truthy(r.get("include_in_evaluation", "1"))]


def tech_keywords(peer_group: str) -> list[str]:
    text = str(peer_group or "")
    base = ["반도체", "공정", "양산", "고객", "R&D", "특허", "기술경쟁력"]
    mapping = {
        "후공정": ["후공정", "패키징", "테스트", "WLP", "Bumping", "수율"],
        "패키징": ["후공정", "패키징", "테스트", "WLP", "Bumping", "수율"],
        "테스트": ["테스트", "검사", "소켓", "신뢰성", "수율"],
        "소켓": ["테스트", "소켓", "인터페이스", "신뢰성"],
        "소재": ["반도체 소재", "전구체", "고순도", "식각", "세정", "증착"],
        "부품": ["부품", "소모품", "공정 안정성", "수명"],
        "장비": ["반도체 장비", "공정장비", "검사장비", "자동화", "CAPEX"],
        "검사": ["검사장비", "계측", "수율", "품질관리"],
        "팹리스": ["팹리스", "설계", "시스템반도체", "MCU", "SoC"],
        "설계": ["팹리스", "설계", "시스템반도체", "SoC"],
        "디자인": ["디자인하우스", "디자인솔루션", "파운드리 연계", "설계"],
        "파운드리": ["파운드리", "웨이퍼", "공정기술", "수율"],
        "차량용": ["차량용 반도체", "전장", "MCU", "신뢰성"],
        "메모리": ["메모리", "반도체 설계", "스토리지"],
    }
    out = list(base)
    for key, vals in mapping.items():
        if key in text:
            out.extend(vals)
    seen = []
    for x in out:
        if x and x not in seen:
            seen.append(x)
    return seen


def company_dir_path(field: str, company: str) -> Path:
    return DATA / safe_name(field, "반도체") / company


def build_local_proxy_payload(row: dict[str, str]) -> dict[str, Any]:
    company = str(row.get("company_name") or "").strip()
    slug = safe_name(row.get("company_dir"), company)
    field = str(row.get("field") or "반도체").strip() or "반도체"
    peer_group = str(row.get("peer_group") or "").strip()
    stock_code = str(row.get("stock_code") or "").strip().zfill(6)
    market = str(row.get("market") or "").strip()
    keywords = tech_keywords(peer_group)
    generated_at = datetime.now().isoformat(timespec="seconds")

    source_text = f"""
# {company} Tech Local Proxy Evidence

- company_name: {company}
- company_slug: {slug}
- stock_code: {stock_code}
- market: {market}
- peer_group: {peer_group}
- evidence_status: FALLBACK_LOCAL_PROXY
- universe_lock: universe_30_semiconductor_20260514
- locked_as_of: 2026-05-14

## 사용 원칙

이 파일은 KIPRIS Plus, DART 사업보고서, 회사 IR, 공식 웹 수집이 아직 완료되지 않은 신규 Universe 기업을 위해 생성한 Tech Agent 부트스트랩 근거입니다.
수익률 확인 후 기업을 교체하지 않는 locked universe 원칙을 지키기 위한 초기 로컬 근거이며, 특허 수·고객사·수주·양산 실적을 임의로 확정하지 않습니다.
Chair와 Auditor에서는 이 근거를 OK가 아니라 FALLBACK_LOCAL_PROXY로 해석해야 합니다.

## 기술 후보 맥락

{company}은 Universe CSV에서 '{peer_group}' peer_group으로 분류되어 있습니다.
이 분류에 따라 Tech Agent는 다음 기술 후보 키워드를 우선 탐색합니다: {", ".join(keywords)}.

## 대표 기술 후보

- 반도체 value chain 내 위치: {peer_group}
- 탐색해야 할 기술 축: {", ".join(keywords[:10])}
- 핵심 확인 필요 항목: 제품/공정 직접성, 고객 적용 여부, 양산/수율/신뢰성 지표, R&D 및 특허 근거, 전방산업 확장성

## 핵심 제품/서비스 후보

- peer_group 기준 후보: {peer_group}
- 실제 제품명, 매출 비중, 고객 적용 사례는 DART 사업보고서/IR/공식 홈페이지/KIPRIS로 추가 검증해야 합니다.
- 이 로컬 근거는 제품·공정 후보 탐색용이며 확정 근거가 아닙니다.

## 고객 구매 이유 후보

- 성능, 원가, 품질, 신뢰성, 수율, 공정 안정성, 공급 안정성, 전방 고객 승인 여부를 확인해야 합니다.
- 고객사명, 공급계약, 양산 레퍼런스는 원천 확인 전까지 미확정으로 둡니다.

## 경쟁 우위/대체가능성 후보

- 특허, 공정 노하우, 고객 승인, 양산 난이도, 대체 비용, 국산화 여부를 확인해야 합니다.
- KIPRIS Plus 권한이 열리면 registration_status, final_status, expiry_status, right_holder, right_transfer_history, fee_payment_status로 권리 안정성을 재평가합니다.

## 활용 및 확장 산업 후보

- 후보 전방 산업: AI/HPC, 전장, 모바일, 서버, 데이터센터, 디스플레이, 파운드리/OSAT 생태계
- 실제 적용 산업은 기업별 사업보고서와 IR 자료로 보강합니다.

## R&D 강도 후보

- 연구개발비, 연구인력, 개발과제, 설비투자, 특허 포트폴리오를 확인해야 합니다.
- 현재 단계는 로컬 프록시이므로 R&D 수치를 임의 생성하지 않습니다.
""".strip() + "\n"

    categories = [
        ("대표 기술", "핵심 기술 키워드", "peer_group 기반 기술 후보 수", len(keywords), "개", ", ".join(keywords)),
        ("대표 기술", "적용 방식", "반도체 value-chain 분류", 1, "개", peer_group),
        ("핵심 제품/서비스", "제품명/서비스명", "제품 후보 축", len([x for x in keywords if x not in {"반도체", "공정", "양산", "고객", "R&D", "특허", "기술경쟁력"}]), "개", peer_group),
        ("고객 구매 이유", "고객 효익", "확인 필요 고객 효익 축", 4, "개", "성능/원가/품질/신뢰성"),
        ("경쟁 우위/대체가능성", "등록 특허", "특허 권리 안정성 확인 상태", 0, "건", "KIPRIS Plus 미확인"),
        ("활용 및 확장 산업", "활용 산업", "전방산업 후보", 5, "개", "AI/HPC/전장/모바일/서버"),
        ("진입 부담/장벽", "양산 난이도", "검증 필요 진입장벽 축", 4, "개", "양산/수율/고객승인/공정노하우"),
        ("R&D 강도", "개발 과제", "R&D 확인 필요 상태", 0, "건", "DART/IR 추가 확인 필요"),
    ]

    metric_rows = []
    for idx, (cat, item, metric, value, unit, note) in enumerate(categories, start=1):
        metric_rows.append({
            "company_slug": slug,
            "company_name": company,
            "source": "universe_locked_local_proxy",
            "sheet": "FALLBACK_LOCAL_PROXY",
            "excel_row": idx,
            "category": cat,
            "item_name": item,
            "metric_name": metric,
            "metric_value": value,
            "metric_unit": unit,
            "metric_value_source": note,
            "numeric_signal_count": 1 if value else 0,
            "keyword_signal_count": len(keywords),
            "content_present": 1,
            "content_char_count": len(source_text),
            "quantifiable_plan": "원천 확인 후 수치 보강",
            "major_source_plan": "DART/KIPRIS/IR/공식홈페이지",
            "middle_source_plan": "FALLBACK_LOCAL_PROXY",
        })

    item_rows = []
    for r in metric_rows:
        item_rows.append({
            "company_name": company,
            "sheet": "FALLBACK_LOCAL_PROXY",
            "excel_row": r["excel_row"],
            "category": r["category"],
            "major_source": r["major_source_plan"],
            "middle_source": r["middle_source_plan"],
            "quantifiable": r["quantifiable_plan"],
            "item_name": r["item_name"],
            "content": f"{company} / {peer_group} / {r['metric_name']} / {r['metric_value_source']}",
            "content_present": 1,
            "content_char_count": len(str(r["metric_value_source"])),
            "numeric_signal_count": r["numeric_signal_count"],
            "keyword_signal_count": r["keyword_signal_count"],
            "metric_name": r["metric_name"],
            "metric_value": r["metric_value"],
            "metric_unit": r["metric_unit"],
            "metric_value_source": r["metric_value_source"],
            "keyword_counts": json.dumps({k: 1 for k in keywords}, ensure_ascii=False),
            "numbers": json.dumps([{"raw": str(r["metric_value"]), "unit": r["metric_unit"], "context": r["metric_value_source"]}], ensure_ascii=False),
        })

    return {
        "status": "FALLBACK_LOCAL_PROXY",
        "generated_at": generated_at,
        "company_slug": slug,
        "company_name": company,
        "field": field,
        "peer_group": peer_group,
        "stock_code": stock_code,
        "market": market,
        "technology_keywords": keywords,
        "source_text": source_text,
        "company_items": item_rows,
        "quantified_metrics": metric_rows,
        "usage_rule": "Use only as bootstrap evidence until DART/KIPRIS/IR/official sources are collected.",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            safe = dict(row)
            for k, v in list(safe.items()):
                if isinstance(v, (dict, list)):
                    safe[k] = json.dumps(v, ensure_ascii=False)
            writer.writerow(safe)


def write_seed(row: dict[str, str], *, overwrite: bool = False) -> dict[str, Any]:
    payload = build_local_proxy_payload(row)
    company = payload["company_name"]
    slug = payload["company_slug"]
    field = payload["field"]

    tech_dir = company_dir_path(field, company) / "tech"
    source_dir = tech_dir / "source"
    tech_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "source_md": source_dir / f"{slug}_tech_local_proxy_evidence.md",
        "source_json": source_dir / f"{slug}_tech_local_proxy_evidence.json",
        "frame_json": tech_dir / "tech_excel_frame_full.json",
        "summary_md": tech_dir / "tech_excel_frame_summary.md",
        "items_csv": tech_dir / "tech_excel_frame_items.csv",
        "metrics_csv": tech_dir / "tech_excel_frame_metrics.csv",
        "quantified_csv": tech_dir / "quantified_metrics.csv",
        "quantified_typo_csv": tech_dir / "quanified_metrix.csv",
    }

    if paths["source_md"].exists() and not overwrite:
        return {
            "status": "SKIPPED_EXISTS",
            "company_name": company,
            "company_dir": slug,
            "source_md": str(paths["source_md"]),
        }

    paths["source_md"].write_text(payload["source_text"], encoding="utf-8")
    paths["source_json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["frame_json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["summary_md"].write_text(payload["source_text"], encoding="utf-8")

    item_fields = [
        "company_name", "sheet", "excel_row", "category", "major_source", "middle_source", "quantifiable",
        "item_name", "content", "content_present", "content_char_count", "numeric_signal_count", "keyword_signal_count",
        "metric_name", "metric_value", "metric_unit", "metric_value_source", "keyword_counts", "numbers",
    ]
    metric_fields = [
        "company_slug", "company_name", "source", "sheet", "excel_row", "category", "item_name",
        "metric_name", "metric_value", "metric_unit", "metric_value_source", "numeric_signal_count",
        "keyword_signal_count", "content_present", "content_char_count", "quantifiable_plan",
        "major_source_plan", "middle_source_plan",
    ]

    write_csv(paths["items_csv"], payload["company_items"], item_fields)
    write_csv(paths["metrics_csv"], payload["quantified_metrics"], metric_fields)
    write_csv(paths["quantified_csv"], payload["quantified_metrics"], metric_fields)
    write_csv(paths["quantified_typo_csv"], payload["quantified_metrics"], metric_fields)

    return {
        "status": "OK",
        "company_name": company,
        "company_dir": slug,
        "paths": {k: str(v) for k, v in paths.items()},
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Create fallback local-proxy Tech evidence files for new Universe 25.")
    p.add_argument("--csv", default=str(DEFAULT_CSV))
    p.add_argument("--only-new-25", action="store_true")
    p.add_argument("--only-company-dir", default="")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    rows = read_rows(Path(args.csv))
    if args.only_new_25:
        rows = [r for r in rows if safe_name(r.get("company_dir")) not in ORIGINAL_5]
    if args.only_company_dir:
        rows = [r for r in rows if safe_name(r.get("company_dir")) == args.only_company_dir]

    out = [write_seed(r, overwrite=args.overwrite) for r in rows]
    print(json.dumps({
        "status": "OK",
        "count": len(out),
        "results": out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

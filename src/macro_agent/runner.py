from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from common.data_paths import company_agent_dir, company_slug, macro_common_dir, rel_project_path
from common.grounded_output import finalize_agent_output
from common.output_paths import company_dir_from_name

from .decision import make_decision
from .feature_builder import build_macro_features
from .llm_analyzer import analyze_with_llm
from .loader import load_macro_data, resolve_macro_input_dir
from .preprocessor import preprocess_macro_data
from .reporter import save_csv_report, save_json_report, save_markdown_report
from .scorer import calculate_macro_score


def _signal_to_opinion(signal: str) -> str:
    signal = str(signal or "").upper()
    if signal == "BUY":
        return "매수"
    if signal == "SELL":
        return "매도"
    return "보유"


def _build_macro_evidences(score_result: dict[str, Any], run_date: str) -> list[dict[str, Any]]:
    evidences: list[dict[str, Any]] = []
    details = score_result.get("details") or {}
    idx = 1
    for section, values in details.items():
        if not isinstance(values, dict):
            continue
        snippet = "; ".join(f"{k}={v}" for k, v in list(values.items())[:8])
        if not snippet:
            continue
        evidences.append(
            {
                "evidence_id": f"macro_ev_{idx}",
                "source_type": "macro_csv_feature",
                "source_name": f"macro_{section}_{run_date}",
                "title": f"{section} 최신 macro feature",
                "snippet": snippet,
                "url": "",
                "as_of": run_date,
            }
        )
        idx += 1
    return evidences


def _build_macro_claims(reasons: list[str], evidences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_ids = [e.get("evidence_id") for e in evidences if e.get("evidence_id")]
    if not evidence_ids:
        return []
    claims = []
    for i, reason in enumerate(reasons[:6], start=1):
        claims.append(
            {
                "claim_id": f"macro_claim_{i}",
                "text": str(reason),
                "evidence_ids": evidence_ids,
            }
        )
    return claims


def _save_standard_packet(company_dir: str, packet: dict[str, Any]) -> dict[str, str]:
    out_dir = company_agent_dir(company_dir, "macro", create=True)
    primary = out_dir / f"{company_dir}_macro.json"
    packet_path = out_dir / f"{company_dir}_macro_agent_packet.json"
    save_json_report(packet, primary)
    save_json_report(packet, packet_path)
    return {
        "macro_json": rel_project_path(primary),
        "macro_agent_packet_json": rel_project_path(packet_path),
    }




def _env_bool(name: str, default: bool = False) -> bool:
    raw = __import__("os").getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_macro_intake_once_if_missing(input_dir: Path) -> None:
    """Build raw macro CSVs once when standalone macro is executed without source files.

    Full pipeline normally runs data_intake first.  This fallback is only for
    direct commands such as `python main.py macro ...` after a copy/patch step
    where data/_global_common/macro is empty.
    """
    if not _env_bool("MACRO_AUTO_INTAKE_IF_MISSING", True):
        return
    print("\n[Macro] raw CSV 없음 → macro_intake 1회 자동 실행을 시도합니다.")
    print("        자동 실행을 원하지 않으면 $env:MACRO_AUTO_INTAKE_IF_MISSING='0' 설정")
    try:
        from data_intake.macro_intake.runner import run as run_macro_intake
        run_macro_intake()
    except Exception as exc:
        print(f"⚠️ macro_intake 자동 실행 실패: {exc}")

def run(date: str = "latest", cutoff: str | None = "20250601", company_dir: str | None = None, company: str | None = None, use_llm: bool = True) -> dict[str, Any]:
    """Macro Agent 실행.

    원천 CSV 입력은 data/_global_common/macro 하나만 사용한다.
    결과는 company_dir이 있으면 data/<field>/<company>/macro에 저장한다.
    """
    print("=" * 60)
    print("📊 Macro Agent 실행 시작")
    print("=" * 60)

    slug = company_dir_from_name(company_dir or company or "macro")
    input_dir = macro_common_dir(create=True)
    run_date = datetime.now().strftime("%Y%m%d") if date == "latest" else date

    if company_dir or company:
        output_dir = company_agent_dir(slug, "macro", create=True)
    else:
        output_dir = macro_common_dir(create=True) / "analysis"
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 입력 데이터 위치: {input_dir}")
    print(f"📁 결과 저장 위치: {output_dir}")
    print(f"📅 분석 기준일: {run_date}")

    print("\n[1/6] 데이터 로드 중...")
    try:
        raw_data = load_macro_data(input_dir=input_dir, date=date, cutoff=cutoff)
    except ValueError as exc:
        if "CSV 파일이 없습니다" not in str(exc) and "raw CSV" not in str(exc):
            raise
        print(f"⚠️ Macro raw CSV 로드 실패: {exc}")
        _run_macro_intake_once_if_missing(input_dir)
        raw_data = load_macro_data(input_dir=input_dir, date=date, cutoff=cutoff)

    print("[2/6] 데이터 전처리 중...")
    clean_data = preprocess_macro_data(raw_data)

    print("[3/6] 매크로 Feature 생성 중...")
    feature_data = build_macro_features(clean_data)

    print("[4/6] 매크로 점수 계산 중...")
    score_result = calculate_macro_score(feature_data, company_dir=slug, company=company)

    if use_llm:
        try:
            llm_result = analyze_with_llm(score_result)
            print("LLM RESULT:", llm_result)
            score_result["llm_analysis"] = llm_result
        except Exception as exc:
            print(f"⚠️ Macro LLM 보조 분석 실패 → rule-based 결과만 사용: {exc}")
            score_result["llm_analysis"] = {
                "llm_summary": "LLM 보조 분석 실패로 rule-based macro score만 사용했습니다.",
                "macro_interpretation": "",
                "key_risks": [],
                "watch_points": [],
            }

    print("[5/6] BUY / SELL / HOLD 판단 중...")
    decision_result = make_decision(score_result)

    # 기존 결과 삭제
    for pattern in [
        "macro_signal_*.json",
        "macro_signal_*.csv",
        "macro_report_*.md",
    ]:
        for old_file in output_dir.glob(pattern):
            try:
                old_file.unlink()
                print(f"🗑️ 삭제: {old_file.name}")
            except Exception as e:
                print(f"⚠️ 삭제 실패: {e}")

    print("[6/6] 리포트 저장 중...")
    json_path = output_dir / f"macro_signal_{run_date}.json"
    csv_path = output_dir / f"macro_signal_{run_date}.csv"
    report_path = output_dir / f"macro_report_{run_date}.md"

    save_json_report(decision_result, json_path)
    save_csv_report(decision_result, csv_path)
    save_markdown_report(decision_result, report_path)

    evidences = _build_macro_evidences(score_result, run_date)
    claims = _build_macro_claims(decision_result.get("reasons", []) or [], evidences)
    opinion = _signal_to_opinion(decision_result.get("signal"))

    llm_result = (decision_result.get("details", {}).get("llm_analysis") or {})
    coverage_ratio = decision_result.get("coverage_ratio", 1.0)

    # watch_points: 구조화 객체 또는 문자열 리스트 모두 지원
    raw_watch = llm_result.get("watch_points") or []
    if raw_watch and isinstance(raw_watch[0], dict):
        watch_points_text = [
            f"{wp.get('indicator', '')}: {wp.get('current', '')} (기준: {wp.get('threshold', '')})"
            for wp in raw_watch
        ]
    else:
        watch_points_text = [str(wp) for wp in raw_watch]

    # macro_chair_summary: Chair가 바로 쓸 수 있는 구조화 요약
    macro_chair_summary = {
        "signal": decision_result.get("signal"),
        "score": decision_result.get("score"),
        "confidence": decision_result.get("confidence"),
        "coverage_ratio": coverage_ratio,
        "one_liner": decision_result.get("summary", ""),
        "sector_impact": llm_result.get("sector_impact", ""),
        "key_risks": llm_result.get("key_risks") or [],
        "watch_points": watch_points_text,
        "evidence_links": llm_result.get("evidence_links") or [],
        "macro_numeric_criteria": decision_result.get("details", {}).get("macro_numeric_criteria", {}),
        "company_macro_sensitivity": decision_result.get("details", {}).get("기업별_macro_민감도", {}),
    }

    packet = {
        "agent": "macro",
        "company_name": company or slug,
        "company": company or slug,
        "opinion": opinion,
        "confidence": decision_result.get("confidence", 0.5),
        "summary": decision_result.get("summary", ""),
        "key_points": [c.get("text", "") for c in claims[:3]],
        "risks": llm_result.get("key_risks", []),
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "macro_chair_summary": macro_chair_summary,
        "raw_payload": decision_result,
        "output_files": {
            "macro_signal_json": rel_project_path(json_path),
            "macro_signal_csv": rel_project_path(csv_path),
            "macro_report_md": rel_project_path(report_path),
        },
    }

    packet = finalize_agent_output(packet, agent_name="macro", company_name=company or slug)
    if company_dir or company:
        packet.setdefault("output_files", {}).update(_save_standard_packet(slug, packet))

    print("\n✅ Macro Agent 실행 완료")
    print(f"판단 결과: {decision_result.get('signal')} / opinion={opinion}")
    print(f"점수: {decision_result.get('score')}")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"REPORT: {report_path}")
    return packet


if __name__ == "__main__":
    run()
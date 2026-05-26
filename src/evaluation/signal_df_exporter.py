from __future__ import annotations

import csv
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]

OUTPUT_COLUMNS = [
    "date",
    "field",
    "company",
    "ticker",
    "stock_code",
    "recommendation",
    "weighted_signal",
    "as_of_date",
    "signal_source",
]
for _agent in AGENTS:
    OUTPUT_COLUMNS.extend([
        f"{_agent}_signal",
        f"{_agent}_weighted_signal",
        f"{_agent}_recommendation",
        f"{_agent}_weight",
    ])

BUY_WORDS = {"BUY", "STRONG_BUY", "매수", "상향", "긍정", "POSITIVE", "LONG"}
SELL_WORDS = {"SELL", "STRONG_SELL", "매도", "하향", "부정", "NEGATIVE", "SHORT"}
HOLD_WORDS = {"HOLD", "NEUTRAL", "보유", "중립", "관망", "WAIT"}


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _project_root() -> Path:
    # src/evaluation/signal_df_exporter.py -> project root
    return Path(__file__).resolve().parents[2]


def _as_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = _safe_text(value)
    if not text:
        return None
    up = text.upper()
    if up in BUY_WORDS:
        return 1.0
    if up in SELL_WORDS:
        return -1.0
    if up in HOLD_WORDS:
        return 0.0
    text = text.replace(",", "")
    percent = text.endswith("%")
    text = text[:-1] if percent else text
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        num = float(m.group(0))
    except ValueError:
        return None
    if percent:
        num = num / 100.0
    return num


def _normalize_signal(value: Any) -> float | None:
    num = _as_number(value)
    if num is None:
        return None
    # Generic score-like values occasionally arrive as 0~100. Convert only
    # when the number is clearly outside the signal range.
    if num > 1.0 and num <= 100.0:
        return max(-1.0, min(1.0, (num - 50.0) / 50.0))
    if num < -1.0 and num >= -100.0:
        return max(-1.0, min(1.0, num / 100.0))
    return max(-1.0, min(1.0, num))


def _recommendation(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    up = text.upper()
    if up in BUY_WORDS or any(word in text for word in ("매수", "상향", "긍정")):
        return "매수"
    if up in SELL_WORDS or any(word in text for word in ("매도", "하향", "부정")):
        return "매도"
    if up in HOLD_WORDS or any(word in text for word in ("보유", "중립", "관망")):
        return "보유"
    return ""


def _rec_to_signal(rec: str) -> float | None:
    rec = _recommendation(rec)
    if rec == "매수":
        return 1.0
    if rec == "매도":
        return -1.0
    if rec == "보유":
        return 0.0
    return None


def _signal_to_recommendation(signal: float | None) -> str:
    if signal is None:
        return ""
    if signal > 0.15:
        return "매수"
    if signal < -0.15:
        return "매도"
    return "보유"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [{k: _safe_text(v) for k, v in row.items()} for row in csv.DictReader(f)]
        except UnicodeDecodeError:
            continue
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        return [{k: _safe_text(v) for k, v in row.items()} for row in csv.DictReader(f)]


def _load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _candidate_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend([p for p in root.glob(pattern) if p.is_file()])
    # newest first
    return sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)


def _latest_file(root: Path, patterns: Iterable[str]) -> Path | None:
    files = _candidate_files(root, patterns)
    return files[0] if files else None


def _recursive_first(payload: Any, keys: set[str], *, max_list: int = 80) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in keys:
                return value
        for value in payload.values():
            hit = _recursive_first(value, keys, max_list=max_list)
            if hit not in (None, "", [], {}):
                return hit
    elif isinstance(payload, list):
        for value in payload[:max_list]:
            hit = _recursive_first(value, keys, max_list=max_list)
            if hit not in (None, "", [], {}):
                return hit
    return None


def _recursive_quantitative_decision(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    direct = payload.get("quantitative_decision")
    if isinstance(direct, dict):
        return direct
    auditor = payload.get("auditor_summary")
    if isinstance(auditor, dict) and isinstance(auditor.get("quantitative_decision"), dict):
        return auditor["quantitative_decision"]
    for value in payload.values():
        if isinstance(value, (dict, list)):
            hit = _recursive_quantitative_decision(value)
            if hit:
                return hit
    return {}


def _runtime_company_path(company_out: Path, company: str | None = None) -> Path | None:
    candidates: list[Path] = []
    runtime_root = company_out / "runtime_data"
    if runtime_root.exists():
        if company:
            candidates.append(runtime_root / company)
        candidates.extend([p for p in runtime_root.iterdir() if p.is_dir()])
    candidates.append(company_out)
    for candidate in candidates:
        if candidate.exists() and any((candidate / agent).exists() for agent in AGENTS + ["chair", "auditor"]):
            return candidate
    return None


def _company_out_candidates(out_root: Path, window: str, company_dir: str) -> list[Path]:
    return [
        out_root / "real_pipeline_outputs" / window / company_dir,
        out_root / "outputs" / window / company_dir,
        out_root / window / company_dir,
    ]


def _load_run_log(out_root: Path) -> list[dict[str, str]]:
    rows = _read_csv_rows(out_root / "monthly_cutoff_pipeline_run_log.csv")
    # Keep successful/recovered rows. If a run is still in progress, checkpoint rows
    # should not disappear just because later targets timed out.
    keep_status = {"OK", "OK_RECOVERED", "RECOVERED", "EXISTING_OK"}
    out: list[dict[str, str]] = []
    for row in rows:
        status = _safe_text(row.get("status")).upper()
        if status in keep_status or status.startswith("OK"):
            out.append(row)
    return out


def _agent_decision_from_qd(qd: dict[str, Any], agent: str) -> dict[str, Any]:
    decisions = qd.get("agent_decisions") or qd.get("agents") or {}
    item: Any = {}
    if isinstance(decisions, dict):
        item = decisions.get(agent) or decisions.get(agent.upper()) or decisions.get(agent.capitalize()) or {}
    elif isinstance(decisions, list):
        for row in decisions:
            if isinstance(row, dict) and _safe_text(row.get("agent")).lower() == agent:
                item = row
                break
    if not isinstance(item, dict):
        item = {}

    signal = _normalize_signal(
        item.get("signal")
        if item.get("signal") is not None else
        item.get("auditor_signal")
        if item.get("auditor_signal") is not None else
        item.get("final_signal")
        if item.get("final_signal") is not None else
        item.get("dma_signal")
    )
    rec = _recommendation(
        item.get("recommendation")
        or item.get("auditor_recommendation")
        or item.get("final_recommendation")
        or item.get("opinion")
        or item.get("decision")
        or item.get("label")
    )
    if signal is None:
        signal = _rec_to_signal(rec)
    if signal is not None and not rec:
        rec = _signal_to_recommendation(signal)

    weight = _as_number(
        item.get("weight")
        if item.get("weight") is not None else
        item.get("posterior_weight")
        if item.get("posterior_weight") is not None else
        item.get("dma_weight")
        if item.get("dma_weight") is not None else
        item.get("model_weight")
    )
    weighted = _as_number(
        item.get("weighted_contribution")
        if item.get("weighted_contribution") is not None else
        item.get("weighted_signal")
        if item.get("weighted_signal") is not None else
        item.get("contribution")
    )
    if weighted is None and signal is not None and weight is not None:
        weighted = signal * weight
    return {
        "signal": signal,
        "recommendation": rec,
        "weight": weight,
        "weighted_signal": weighted,
        "source": "auditor_quantitative_decision",
    }


def _agent_payload_paths(runtime: Path, agent: str) -> list[Path]:
    compact_dir = runtime / "auditor" / "first_auditor" / "compact_agent_packets"
    patterns: dict[str, list[str]] = {
        "finance": [
            "finance/*_finance_agent_packet.json",
            "finance/*_finance.json",
            "finance/finance*.json",
        ],
        "market": [
            "market/*_market_agent_packet.json",
            "market/*_market.json",
            "market/market*.json",
        ],
        "tech": [
            "tech/tech_chair_summary.json",
            "tech/*_tech_agent_packet.json",
            "tech/*_tech.json",
            "tech/tech.json",
        ],
        "valuation": [
            "valuation/*_valuation_agent_packet.json",
            "valuation/*_valuation.json",
            "valuation/*_valuation_metrics.json",
            "valuation/*_dashboard_payload.json",
            "valuation/valuation*.json",
        ],
        "issue": [
            "issue/*_issue_agent_packet.json",
            "issue/*_issue.json",
            "issue/issue*.json",
        ],
        "macro": [
            "macro/*_macro_agent_packet.json",
            "macro/*_macro.json",
            "macro/macro_signal_*.json",
            "macro/macro*.json",
        ],
    }
    paths: list[Path] = []
    paths.extend(_candidate_files(compact_dir, [f"{agent}_compact_packet.json", f"*{agent}*_compact*.json"]))
    paths.extend(_candidate_files(runtime, patterns.get(agent, [])))
    # Some runs place compact packets one level deeper.
    paths.extend(_candidate_files(runtime, [f"auditor/**/{agent}_compact_packet.json", f"**/{agent}_compact_packet.json"]))
    return list(dict.fromkeys(paths))


def _agent_decision_from_payload(runtime: Path, agent: str) -> dict[str, Any]:
    signal_keys = {
        "auditor_signal",
        "signal",
        "final_signal",
        "dma_signal",
        f"{agent}_signal",
    }
    if agent == "valuation":
        signal_keys.update({"valuation_gap_signal", "intrinsic_value_signal", "expected_return_signal"})
    rec_keys = {
        "recommendation",
        "auditor_recommendation",
        "final_recommendation",
        "opinion",
        "decision",
        "label",
    }
    for path in _agent_payload_paths(runtime, agent):
        payload = _load_json(path)
        if not payload:
            continue
        signal = _normalize_signal(_recursive_first(payload, signal_keys))
        rec = _recommendation(_recursive_first(payload, rec_keys))
        if signal is None:
            signal = _rec_to_signal(rec)
        if signal is not None and not rec:
            rec = _signal_to_recommendation(signal)
        if signal is not None or rec:
            return {
                "signal": signal,
                "recommendation": rec,
                "weight": None,
                "weighted_signal": None,
                "source": str(path),
            }
    return {"signal": None, "recommendation": "", "weight": None, "weighted_signal": None, "source": ""}


def _qd_candidates(runtime: Path) -> list[Path]:
    paths: list[Path] = []
    # Prefer the original auditor handoff. Chair packets can contain a sanitized
    # or partially reconstructed copy after timeout recovery.
    paths.extend(_candidate_files(runtime, [
        "auditor/first_auditor/compact_agent_packets/auditor_chair_packet.json",
        "auditor/**/auditor_chair_packet.json",
    ]))
    paths.extend(_candidate_files(runtime, [
        "chair/*_chair_agent_packet.json",
        "chair/*_chair.json",
        "chair/chair*.json",
    ]))
    return list(dict.fromkeys(paths))


def _load_best_qd(runtime: Path) -> tuple[dict[str, Any], str]:
    for path in _qd_candidates(runtime):
        payload = _load_json(path)
        qd = _recursive_quantitative_decision(payload)
        if qd:
            if "auditor_chair_packet" in path.name or "compact_agent_packets" in str(path):
                return qd, "auditor_compact:quantitative_decision"
            return qd, "chair:auditor_summary.quantitative_decision"
    return {}, "fallback:agent_packets"


def _weight_map(qd: dict[str, Any], decisions: dict[str, dict[str, Any]]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for agent, d in decisions.items():
        w = _as_number(d.get("weight"))
        if w is not None and w >= 0:
            weights[agent] = w
    if not weights:
        raw = qd.get("weights") or qd.get("agent_weights") or {}
        if isinstance(raw, dict):
            for agent in AGENTS:
                w = _as_number(raw.get(agent))
                if w is not None and w >= 0:
                    weights[agent] = w
    if not weights:
        available = [a for a, d in decisions.items() if d.get("signal") is not None]
        base = available or AGENTS
        equal = 1.0 / len(base)
        return {agent: (equal if agent in base else 0.0) for agent in AGENTS}

    total = sum(weights.values())
    if total <= 0:
        equal = 1.0 / len(AGENTS)
        return {agent: equal for agent in AGENTS}
    return {agent: weights.get(agent, 0.0) / total for agent in AGENTS}


def _read_company_row(
    *,
    field: str,
    window: str,
    as_of_date: str,
    company_out: Path,
    target_meta: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    target_meta = target_meta or {}
    runtime = _runtime_company_path(company_out, target_meta.get("company"))
    if runtime is None:
        return None

    qd, qd_source = _load_best_qd(runtime)
    qd_decisions = {agent: _agent_decision_from_qd(qd, agent) for agent in AGENTS}
    decisions: dict[str, dict[str, Any]] = {}
    used_fallback = False

    for agent in AGENTS:
        qd_d = qd_decisions.get(agent, {})
        fallback = _agent_decision_from_payload(runtime, agent)
        qd_signal = qd_d.get("signal")
        fb_signal = fallback.get("signal")
        qd_rec = _recommendation(qd_d.get("recommendation"))
        fb_rec = _recommendation(fallback.get("recommendation"))

        # If the qd signal is missing, or it is a placeholder 0 while the raw
        # packet has a non-zero signal/recommendation, use the raw packet.
        use_fallback = False
        if qd_signal is None:
            use_fallback = fb_signal is not None or bool(fb_rec)
        elif abs(float(qd_signal)) < 1e-12 and fb_signal is not None and abs(float(fb_signal)) > 1e-12:
            use_fallback = True
        elif qd_rec in ("", "보유") and fb_rec in ("매수", "매도"):
            use_fallback = True

        if use_fallback:
            merged = dict(qd_d)
            merged.update({k: v for k, v in fallback.items() if v not in (None, "")})
            decisions[agent] = merged
            used_fallback = True
        else:
            decisions[agent] = qd_d

    weights = _weight_map(qd, decisions)
    for agent, d in decisions.items():
        d["weight"] = weights.get(agent)
        if d.get("signal") is not None:
            d["weighted_signal"] = float(d["signal"]) * float(d["weight"] or 0.0)
        if not d.get("recommendation"):
            d["recommendation"] = _signal_to_recommendation(d.get("signal"))

    qd_weighted = _as_number(qd.get("weighted_signal") or qd.get("dma_weighted_signal") or qd.get("final_signal"))
    if used_fallback or qd_weighted is None:
        used = [d for d in decisions.values() if d.get("signal") is not None and d.get("weight") is not None]
        weighted_signal = sum(float(d["signal"]) * float(d["weight"]) for d in used) if used else None
    else:
        weighted_signal = qd_weighted

    recommendation = _recommendation(
        qd.get("final_recommendation")
        or qd.get("recommendation")
        or qd.get("opinion")
        or qd.get("decision")
        or qd.get("label")
    )
    if weighted_signal is not None and (used_fallback or not recommendation):
        recommendation = _signal_to_recommendation(weighted_signal)
    if not recommendation:
        recommendation = "보유"

    stock_code = _safe_text(target_meta.get("stock_code"))
    row: dict[str, Any] = {
        "date": window,
        "field": field,
        "company": _safe_text(target_meta.get("company")) or runtime.name,
        "ticker": stock_code,
        "stock_code": stock_code,
        "recommendation": recommendation,
        "weighted_signal": round(float(weighted_signal), 6) if weighted_signal is not None else "",
        "as_of_date": as_of_date,
        "signal_source": f"real_pipeline:{qd_source}" + ("+agent_packet_fallback" if used_fallback else ""),
    }
    for agent in AGENTS:
        d = decisions[agent]
        signal = d.get("signal")
        weight = d.get("weight")
        weighted = d.get("weighted_signal")
        row[f"{agent}_signal"] = round(float(signal), 6) if signal is not None else ""
        row[f"{agent}_weighted_signal"] = round(float(weighted), 6) if weighted is not None else ""
        row[f"{agent}_recommendation"] = _recommendation(d.get("recommendation")) or ""
        row[f"{agent}_weight"] = round(float(weight), 6) if weight is not None else ""
    return {col: row.get(col, "") for col in OUTPUT_COLUMNS}


def export_signal_df(
    *,
    out_root: str | Path,
    field: str,
    run_id: str,
    stamp: str | None = None,
    manifest_name: str = "signal_df_manifest.json",
) -> dict[str, Any]:
    out_root = Path(out_root)
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    rows: list[dict[str, Any]] = []

    for log_row in _load_run_log(out_root):
        window = _safe_text(log_row.get("window")) or _safe_text(log_row.get("as_of_date"))[:7]
        as_of_date = _safe_text(log_row.get("as_of_date")) or (window + "-01")
        company_dir = _safe_text(log_row.get("company_dir"))
        if not window or not company_dir:
            continue
        company_row = None
        for company_out in _company_out_candidates(out_root, window, company_dir):
            if not company_out.exists():
                continue
            company_row = _read_company_row(
                field=_safe_text(log_row.get("field")) or field,
                window=window,
                as_of_date=as_of_date,
                company_out=company_out,
                target_meta=log_row,
            )
            if company_row:
                break
        if company_row:
            rows.append(company_row)

    # Stable order: month then original run-log order.
    combined_csv = out_root / f"signal_df_monthly_all_{run_id}_{stamp}.csv"
    combined_xlsx = out_root / f"signal_df_monthly_all_{run_id}_{stamp}.xlsx"

    if pd is not None:
        frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
        frame.to_csv(combined_csv, index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(combined_xlsx, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="Sheet1")
            ws = writer.book["Sheet1"]
            ws.freeze_panes = "A2"
            for col_cells in ws.columns:
                header = str(col_cells[0].value or "")
                width = min(36, max(10, len(header) + 2))
                ws.column_dimensions[col_cells[0].column_letter].width = width
    else:
        with combined_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        combined_xlsx = Path("")

    manifest = {
        "status": "OK",
        "rows": len(rows),
        "columns": OUTPUT_COLUMNS,
        "combined_csv": str(combined_csv),
        "combined_xlsx": str(combined_xlsx),
        "run_id": run_id,
        "stamp": stamp,
        "note": "Signals prefer auditor compact quantitative_decision and fall back to raw agent packets when qd contains placeholder zeros.",
    }
    (out_root / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest

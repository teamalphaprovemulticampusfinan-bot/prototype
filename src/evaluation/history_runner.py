from __future__ import annotations

import json
import math
import os
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

from evaluation.pipeline_executor import daily_dates, month_ends, read_universe_rows

AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def _window_key(frequency: str, as_of_date: str) -> str:
    return as_of_date[:7] if frequency == "monthly" else as_of_date


def _load_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}
    return {}


def _find_json(root: Path, patterns: list[str]) -> tuple[Path | None, dict[str, Any]]:
    for pattern in patterns:
        matches = sorted(root.rglob(pattern)) if root.exists() else []
        for path in matches:
            data = _load_json(path)
            if data:
                return path, data
    return None, {}


def _dig(data: Any, paths: list[list[str]], default: Any = None) -> Any:
    for path in paths:
        cur = data
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        x = float(str(value).replace(",", "").replace("%", ""))
    except Exception:
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def _recommendation_from_signal(value: Any) -> str:
    x = _to_float(value)
    if x is None:
        return "보유"
    if x > 0:
        return "매수"
    if x < 0:
        return "매도"
    return "보유"


def _normalize_recommendation(value: Any, fallback_signal: Any = None) -> str:
    text = str(value or "").strip().lower()
    if text in {"buy", "long", "매수", "상향"}:
        return "매수"
    if text in {"sell", "short", "매도", "하향"}:
        return "매도"
    if text in {"hold", "neutral", "보유", "중립", "관망"}:
        return "보유"
    return _recommendation_from_signal(fallback_signal)


def _extract_chair_values(chair_payload: dict[str, Any], auditor_payload: dict[str, Any]) -> dict[str, Any]:
    qd = _dig(auditor_payload, [["quantitative_decision"], ["auditor_quantitative_decision"]], {}) or {}
    rec = _dig(
        qd,
        [["recommendation"], ["final_recommendation"], ["decision"]],
        None,
    )
    weighted = _dig(qd, [["weighted_signal"], ["final_weighted_signal"], ["score"]], None)
    if rec is None:
        rec = _dig(
            chair_payload,
            [
                ["recommendation"],
                ["final_recommendation"],
                ["decision"],
                ["chair", "recommendation"],
                ["result", "recommendation"],
            ],
            None,
        )
    if weighted is None:
        weighted = _dig(
            chair_payload,
            [
                ["weighted_signal"],
                ["final_weighted_signal"],
                ["score"],
                ["chair", "weighted_signal"],
                ["result", "weighted_signal"],
            ],
            None,
        )
    return {
        "recommendation": _normalize_recommendation(rec, weighted),
        "weighted_signal": _to_float(weighted),
        "signal_source": "auditor_quantitative_decision" if qd else ("chair_json" if chair_payload else "missing"),
    }


def _extract_agent_signal(agent: str, compact_payload: dict[str, Any], auditor_payload: dict[str, Any], chair_payload: dict[str, Any]) -> dict[str, Any]:
    agent_qd = _dig(auditor_payload, [["quantitative_decision", "agents", agent], ["agent_decisions", agent], ["agent_signals", agent]], {}) or {}
    payload = compact_payload or agent_qd
    signal = _dig(
        payload,
        [["signal"], ["score"], ["weighted_signal"], ["final_signal"], ["agent_signal"], ["summary", "signal"]],
        _dig(agent_qd, [["signal"], ["score"]], None),
    )
    weighted = _dig(payload, [["weighted_signal"], ["weighted_score"], ["contribution"]], _dig(agent_qd, [["weighted_signal"], ["contribution"]], None))
    rec = _dig(payload, [["recommendation"], ["decision"], ["opinion"], ["summary", "recommendation"]], None)
    weight = _dig(payload, [["weight"], ["agent_weight"], ["dma_weight"]], _dig(agent_qd, [["weight"]], None))
    basis = _dig(payload, [["basis"], ["summary"], ["rationale"], ["reason"]], "")
    return {
        "signal": "" if _to_float(signal) is None else _to_float(signal),
        "weighted_signal": "" if _to_float(weighted) is None else _to_float(weighted),
        "recommendation": _normalize_recommendation(rec, signal),
        "weight": "" if _to_float(weight) is None else _to_float(weight),
        "signal_source": "compact_packet" if compact_payload else ("auditor_packet" if agent_qd else "missing"),
        "basis": str(basis)[:500] if basis is not None else "",
    }


def _company_snapshot_root(out_root: Path, frequency: str, as_of_date: str, company_dir: str) -> Path | None:
    base = out_root / "real_pipeline_outputs" / _window_key(frequency, as_of_date) / company_dir
    preferred = base / "operational_data_snapshot"
    if preferred.exists():
        return preferred
    fallback = base / "runtime_data"
    if fallback.exists():
        return fallback
    return None


def _row_from_snapshot(out_root: Path, field: str, frequency: str, as_of_date: str, target: dict[str, str], run_id: str) -> dict[str, Any]:
    root = _company_snapshot_root(out_root, frequency, as_of_date, target["company_dir"])
    chair_path, chair_payload = _find_json(root or Path("__missing__"), [f"{target['company_dir']}_chair.json", "*_chair.json", "*_chair_agent_packet.json", "*_chair_debug_packet.json"])
    auditor_path, auditor_payload = _find_json(root or Path("__missing__"), ["auditor_chair_packet.json", "first_auditor_receipt.json"])
    values = _extract_chair_values(chair_payload, auditor_payload)
    row: dict[str, Any] = {
        "date": as_of_date[:7] if frequency == "monthly" else as_of_date,
        "ticker": target.get("company_name", ""),
        "recommendation": values["recommendation"],
        "weighted_signal": "" if values["weighted_signal"] is None else round(float(values["weighted_signal"]), 6),
        "stock_code": target.get("stock_code", ""),
        "company_dir": target.get("company_dir", ""),
        "field": field,
        "as_of_date": as_of_date,
        "run_id": run_id,
        "signal_source": values["signal_source"],
        "chair_json_path": str(chair_path or ""),
        "auditor_packet_path": str(auditor_path or ""),
    }
    for agent in AGENTS:
        _compact_path, compact = _find_json(root or Path("__missing__"), [f"{agent}_compact_packet.json", f"*{agent}*compact*.json", f"*_{agent}_agent_packet.json", f"*_{agent}.json"])
        sig = _extract_agent_signal(agent, compact, auditor_payload, chair_payload)
        row[f"{agent}_signal"] = sig["signal"]
        row[f"{agent}_weighted_signal"] = sig["weighted_signal"]
        row[f"{agent}_recommendation"] = sig["recommendation"]
        row[f"{agent}_weight"] = sig["weight"]
        row[f"{agent}_signal_source"] = sig["signal_source"]
        row[f"{agent}_basis"] = sig["basis"]
    return row


def _write_outputs(df: "pd.DataFrame", out_root: Path, frequency: str, start: str, end: str) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    csv_path = out_root / f"signal_df_{frequency}_{start}_to_{end}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    xlsx_path = out_root / f"eval_history_outputs_{frequency}_{start}_to_{end}.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:  # type: ignore[attr-defined]
            df.to_excel(writer, index=False, sheet_name="signal_df")
    except Exception:
        # Excel export is a convenience only.  CSV is the canonical output.
        pass
    return out_root


def run_range(
    field: str,
    frequency: str,
    start: str,
    end: str,
    universe_csv: str | Path,
    run_id: str,
    history_csv: str | Path | None = None,
    limit: int | None = None,
    write_sheets: bool = False,
    output_root: str | Path | None = None,
) -> Path:
    """Build standardized evaluation CSV/XLSX from local v49-style pipeline outputs.

    This is a local replacement for the removed src_eval history runner.  It does
    not call Google Sheets and does not mutate agent outputs.  It only reads
    ``real_pipeline_outputs/<window>/<company>/...`` under ``output_root``.
    """
    if pd is None:  # pragma: no cover
        raise RuntimeError("pandas가 필요합니다. requirements.txt 설치 상태를 확인하세요.")
    if write_sheets:
        print("[history-runner] write_sheets=True 요청은 무시합니다. 이 패치는 로컬 CSV/XLSX만 생성합니다.")
    out_root = Path(output_root or os.environ.get("ALPHAPROVE_EVAL_OUTPUT_ROOT") or ".").resolve()
    targets = read_universe_rows(universe_csv, limit=limit, field=field)
    windows = month_ends(start, end) if frequency == "monthly" else daily_dates(start, end)
    rows: list[dict[str, Any]] = []
    for as_of_date in windows:
        for target in targets:
            rows.append(_row_from_snapshot(out_root, field, frequency, as_of_date, target, run_id))
    df = pd.DataFrame(rows)
    final_root = _write_outputs(df, out_root, frequency, start, end)
    manifest = {
        "run_id": run_id,
        "field": field,
        "frequency": frequency,
        "start": start,
        "end": end,
        "windows": windows,
        "targets": len(targets),
        "rows": len(rows),
        "output_root": str(final_root),
        "history_csv": str(history_csv or ""),
        "write_sheets": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    (final_root / "run_manifest_post.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return final_root

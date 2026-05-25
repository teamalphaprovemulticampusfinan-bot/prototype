from __future__ import annotations

import csv
import json
import math
import re
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
    "finance_signal",
    "finance_weighted_signal",
    "finance_recommendation",
    "finance_weight",
    "market_signal",
    "market_weighted_signal",
    "market_recommendation",
    "market_weight",
    "tech_signal",
    "tech_weighted_signal",
    "tech_recommendation",
    "tech_weight",
    "valuation_signal",
    "valuation_weighted_signal",
    "valuation_recommendation",
    "valuation_weight",
    "issue_signal",
    "issue_weighted_signal",
    "issue_recommendation",
    "issue_weight",
    "macro_signal",
    "macro_weighted_signal",
    "macro_recommendation",
    "macro_weight",
]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = _safe_text(value).replace(",", "")
    if not text:
        return None
    upper = text.upper()
    if upper in {"BUY", "매수"}:
        return 1.0
    if upper in {"SELL", "매도"}:
        return -1.0
    if upper in {"HOLD", "보유", "중립"}:
        return 0.0
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        num = float(m.group(0))
    except Exception:
        return None
    # Normalize percent-like or 0~100 score-like values to roughly -1~1 only
    # when a numeric source is clearly outside the signal range.
    if abs(num) > 1.5 and abs(num) <= 100:
        if 0 <= num <= 100:
            return round((num - 50.0) / 50.0, 6)
        return round(num / 100.0, 6)
    return num


def _recommendation(value: Any) -> str:
    text = _safe_text(value)
    upper = text.upper()
    if text in {"매수", "보유", "매도"}:
        return text
    if upper == "BUY":
        return "매수"
    if upper == "SELL":
        return "매도"
    if upper == "HOLD":
        return "보유"
    return text


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _latest_file(root: Path, patterns: Iterable[str]) -> Path | None:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(root.glob(pattern))
    found = [p for p in found if p.is_file()]
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def _runtime_company_path(company_out: Path) -> Path | None:
    status = company_out / "COPY_STATUS.json"
    if status.exists():
        payload = _load_json(status)
        for key in ["runtime_data", "destination"]:
            raw = _safe_text(payload.get(key))
            if raw and Path(raw).exists():
                return Path(raw)
    runtime_root = company_out / "runtime_data"
    if runtime_root.exists():
        dirs = [p for p in runtime_root.iterdir() if p.is_dir()]
        if dirs:
            return max(dirs, key=lambda p: p.stat().st_mtime)
    return None


def _get_quantitative_decision(chair: dict[str, Any]) -> dict[str, Any]:
    if not chair:
        return {}
    for path in [
        ("auditor_summary", "quantitative_decision"),
        ("quantitative_decision",),
        ("decision", "quantitative_decision"),
    ]:
        cur: Any = chair
        ok = True
        for key in path:
            if isinstance(cur, dict) and isinstance(cur.get(key), dict):
                cur = cur[key]
            else:
                ok = False
                break
        if ok and isinstance(cur, dict):
            return cur
    return {}


def _weight_map(qd: dict[str, Any]) -> dict[str, float]:
    for candidate in [
        qd.get("weights_adjusted"),
        qd.get("weights"),
        (qd.get("dma_model") or {}).get("weights_adjusted") if isinstance(qd.get("dma_model"), dict) else None,
        (qd.get("dma_model") or {}).get("weights") if isinstance(qd.get("dma_model"), dict) else None,
    ]:
        if isinstance(candidate, dict) and candidate:
            return {str(k): float(v) for k, v in candidate.items() if _as_number(v) is not None}
    return {}


def _agent_decisions(qd: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = qd.get("agent_decisions")
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items() if isinstance(v, dict)}
    return {}


def _recursive_first(payload: Any, keys: Iterable[str]) -> Any:
    keyset = set(keys)
    if isinstance(payload, dict):
        for key in keyset:
            if key in payload and payload.get(key) not in (None, ""):
                return payload.get(key)
        for value in payload.values():
            hit = _recursive_first(value, keyset)
            if hit not in (None, ""):
                return hit
    elif isinstance(payload, list):
        for value in payload:
            hit = _recursive_first(value, keyset)
            if hit not in (None, ""):
                return hit
    return None


def _extract_agent_fallback(agent_payload: dict[str, Any]) -> tuple[float | None, str]:
    signal = _as_number(_recursive_first(agent_payload, [
        "auditor_signal", "signal", "weighted_signal", "final_signal", "score", "normalized_score", "market_signal", "tech_signal",
    ]))
    rec = _recommendation(_recursive_first(agent_payload, [
        "recommendation", "auditor_recommendation", "final_recommendation", "opinion", "decision", "label",
    ]))
    return signal, rec


def _read_company_row(
    *,
    field: str,
    window: str,
    as_of_date: str,
    company_out: Path,
    target_meta: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    runtime = _runtime_company_path(company_out)
    if runtime is None or not runtime.exists():
        return None

    chair_path = _latest_file(runtime / "chair", ["*_chair_agent_packet.json", "*_chair.json", "chair*.json"])
    chair = _load_json(chair_path)
    qd = _get_quantitative_decision(chair)
    weights = _weight_map(qd)
    decisions = _agent_decisions(qd)

    company = _safe_text((target_meta or {}).get("company")) or _safe_text(chair.get("company")) or runtime.name
    company_dir = _safe_text((target_meta or {}).get("company_dir")) or _safe_text(chair.get("company_dir")) or company_out.name
    stock_code = _safe_text((target_meta or {}).get("stock_code"))
    ticker = stock_code

    weighted_signal = _as_number(qd.get("weighted_signal"))
    if weighted_signal is None:
        weighted_signal = _as_number(qd.get("dma_weighted_signal")) or _as_number(qd.get("final_signal"))
    recommendation = _recommendation(qd.get("final_recommendation") or qd.get("base_recommendation") or chair.get("opinion") or chair.get("recommendation"))

    row: dict[str, Any] = {
        "date": window,
        "field": field,
        "company": company,
        "ticker": ticker,
        "stock_code": stock_code,
        "recommendation": recommendation,
        "weighted_signal": round(weighted_signal, 6) if weighted_signal is not None else "",
        "as_of_date": as_of_date,
        "signal_source": "real_pipeline:chair:auditor_summary.quantitative_decision.dma" if qd else "real_pipeline:agent_fallback",
    }

    agent_payloads: dict[str, dict[str, Any]] = {}
    for agent in AGENTS:
        agent_dir = runtime / agent
        patterns = [f"*_{agent}_agent_packet.json", f"*_{agent}.json", f"*{agent}*.json"]
        agent_payloads[agent] = _load_json(_latest_file(agent_dir, patterns))

    if not weights:
        available = [a for a in AGENTS if decisions.get(a) or agent_payloads.get(a)]
        if available:
            uniform = 1.0 / len(available)
            weights = {a: uniform for a in available}

    for agent in AGENTS:
        decision = decisions.get(agent, {})
        signal = _as_number(decision.get("signal"))
        if signal is None:
            signal = _as_number(decision.get("auditor_signal"))
        rec = _recommendation(decision.get("recommendation") or decision.get("auditor_recommendation") or decision.get("original_recommendation"))
        if signal is None or not rec:
            fallback_signal, fallback_rec = _extract_agent_fallback(agent_payloads.get(agent, {}))
            if signal is None:
                signal = fallback_signal
            if not rec:
                rec = fallback_rec
        weight = weights.get(agent)
        weighted = _as_number(decision.get("weighted_contribution"))
        if weighted is None and signal is not None and weight is not None:
            weighted = signal * weight
        row[f"{agent}_signal"] = round(signal, 6) if signal is not None else ""
        row[f"{agent}_weighted_signal"] = round(weighted, 6) if weighted is not None else ""
        row[f"{agent}_recommendation"] = rec
        row[f"{agent}_weight"] = round(weight, 6) if weight is not None else ""

    return {col: row.get(col, "") for col in OUTPUT_COLUMNS}


def _load_run_log(out_root: Path) -> dict[tuple[str, str], dict[str, str]]:
    path = out_root / "monthly_cutoff_pipeline_run_log.csv"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        window = _safe_text(row.get("window")) or _safe_text(row.get("as_of_date"))[:7]
        company_dir = _safe_text(row.get("company_dir"))
        if window and company_dir:
            out[(window, company_dir)] = row
    return out


def export_signal_df(
    *,
    out_root: str | Path,
    field: str = "반도체",
    run_id: str = "monthly_cutoff_30",
) -> dict[str, str]:
    out_root = Path(out_root)
    base = out_root / "real_pipeline_outputs"
    run_log = _load_run_log(out_root)
    rows: list[dict[str, Any]] = []

    if not base.exists():
        raise FileNotFoundError(f"real_pipeline_outputs not found: {base}")

    for window_dir in sorted([p for p in base.iterdir() if p.is_dir()]):
        window = window_dir.name
        # Recover as-of from log first; otherwise use month-end key as a label only.
        for company_out in sorted([p for p in window_dir.iterdir() if p.is_dir()]):
            meta = run_log.get((window, company_out.name), {})
            as_of_date = _safe_text(meta.get("as_of_date")) or window
            row = _read_company_row(field=field, window=window, as_of_date=as_of_date, company_out=company_out, target_meta=meta)
            if row:
                rows.append(row)

    if not rows:
        raise RuntimeError(f"No signal rows extracted from {base}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_csv = out_root / f"signal_df_monthly_all_{run_id}_{stamp}.csv"
    combined_xlsx = out_root / f"signal_df_monthly_all_{run_id}_{stamp}.xlsx"

    if pd is not None:
        df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
        df.to_csv(combined_csv, index=False, encoding="utf-8-sig")
        try:
            df.to_excel(combined_xlsx, index=False)
        except Exception:
            combined_xlsx = Path("")
        for window, group in df.groupby("date", dropna=False):
            safe_window = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(window))
            window_csv = out_root / f"signal_df_monthly_{safe_window}_{run_id}_{stamp}.csv"
            group.to_csv(window_csv, index=False, encoding="utf-8-sig")
    else:  # pragma: no cover
        with combined_csv.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
            w.writeheader()
            w.writerows(rows)
        combined_xlsx = Path("")

    latest = {
        "status": "OK",
        "rows": str(len(rows)),
        "combined_csv": str(combined_csv),
        "combined_xlsx": str(combined_xlsx) if combined_xlsx else "",
        "columns": ",".join(OUTPUT_COLUMNS),
        "note": "Columns intentionally stop at macro_weight to match the requested signal_df format.",
    }
    (out_root / "signal_df_export_manifest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest


__all__ = ["OUTPUT_COLUMNS", "export_signal_df"]

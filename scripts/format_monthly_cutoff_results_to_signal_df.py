from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


SIGNAL_COLUMNS = [
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

AGENTS = ("finance", "market", "tech", "valuation", "issue", "macro")

DEFAULT_WEIGHTS = {
    "finance": 0.20,
    "market": 0.20,
    "tech": 0.15,
    "valuation": 0.25,
    "issue": 0.10,
    "macro": 0.10,
}

REC_TO_SIGNAL = {
    "매수": 1.0,
    "buy": 1.0,
    "BUY": 1.0,
    "보유": 0.0,
    "hold": 0.0,
    "HOLD": 0.0,
    "매도": -1.0,
    "sell": -1.0,
    "SELL": -1.0,
}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        if text in REC_TO_SIGNAL:
            return REC_TO_SIGNAL[text]
        try:
            x = float(text.replace(",", "").replace("%", ""))
        except Exception:
            return None
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        x = float(value)
    else:
        return None
    if abs(x) > 1.5 and abs(x) <= 100:
        return x / 100.0
    if abs(x) > 100:
        return None
    return x


def _round(value: Any, ndigits: int = 6) -> float | None:
    x = _safe_float(value)
    if x is None:
        return None
    return round(float(x), ndigits)


def _rec(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    low = text.lower()
    if text in {"매수", "보유", "매도"}:
        return text
    if low == "buy":
        return "매수"
    if low == "hold":
        return "보유"
    if low == "sell":
        return "매도"
    return text


def _signal_to_rec(value: Any) -> str:
    x = _safe_float(value)
    if x is None:
        return "보유"
    if x > 0.05:
        return "매수"
    if x < -0.05:
        return "매도"
    return "보유"


def _read_json(path: Any) -> Any:
    if path is None:
        return None
    text = str(path).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    p = Path(text)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def _walk(obj: Any):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _find_numeric(obj: Any, keys: list[str], contains: list[str] | None = None) -> float | None:
    if obj is None:
        return None
    keys_l = {k.lower() for k in keys}
    contains = contains or []
    candidates: list[tuple[int, float]] = []
    for k, v in _walk(obj):
        kl = k.lower()
        x = _safe_float(v)
        if x is None:
            continue
        if kl in keys_l:
            candidates.append((0, x))
        elif any(t in kl for t in contains):
            candidates.append((10, x))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]


def _find_text(obj: Any, keys: list[str], contains: list[str] | None = None) -> str | None:
    if obj is None:
        return None
    keys_l = {k.lower() for k in keys}
    contains = contains or []
    candidates: list[tuple[int, str]] = []
    for k, v in _walk(obj):
        if isinstance(v, (dict, list)):
            continue
        text = str(v).strip() if v is not None else ""
        if not text or text.lower() in {"nan", "none", "null"}:
            continue
        kl = k.lower()
        if kl in keys_l:
            candidates.append((0, text))
        elif any(t in kl for t in contains):
            candidates.append((10, text))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]


def _weight_map(chair: Any) -> dict[str, float]:
    out = {}
    for agent in AGENTS:
        w = _find_numeric(chair, [f"{agent}_weight", f"{agent}_dma_weight"], [f"{agent}_weight"])
        if w is not None:
            out[agent] = w
    for k, v in _walk(chair):
        if k.lower() in {"weights", "agent_weights", "dynamic_weights", "dma_weights"} and isinstance(v, dict):
            for agent in AGENTS:
                if agent in v:
                    w = _safe_float(v[agent])
                    if w is not None:
                        out[agent] = w
    total = sum(out.values())
    if total > 1.5:
        out = {k: v / 100.0 for k, v in out.items()}
    return out


def _extract_agent(packet: Any, agent: str) -> dict[str, Any]:
    signal = _find_numeric(packet, [f"{agent}_signal", "signal", "agent_signal", "numeric_signal", "final_signal"], ["signal"])
    weighted = _find_numeric(packet, [f"{agent}_weighted_signal", "weighted_signal", "weighted_score"], ["weighted_signal"])
    rec = _rec(_find_text(packet, [f"{agent}_recommendation", "recommendation", "final_recommendation", "opinion", "decision"], ["recommendation", "opinion", "decision"]))
    weight = _find_numeric(packet, [f"{agent}_weight", "weight", "agent_weight"], ["weight"])
    if signal is None and rec in REC_TO_SIGNAL:
        signal = REC_TO_SIGNAL[rec]
    if rec is None and signal is not None:
        rec = _signal_to_rec(signal)
    return {"signal": _round(signal), "weighted_signal": _round(weighted), "recommendation": rec, "weight": _round(weight)}


def convert(input_csv: Path, output_csv: Path, output_xlsx: Path | None = None) -> Path:
    if pd is None:
        raise RuntimeError("pandas is required for this converter.")

    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    out_rows = []

    for _, src in df.iterrows():
        chair = _read_json(src.get("chair_json_path"))
        weights = dict(DEFAULT_WEIGHTS)
        weights.update(_weight_map(chair))

        row = {
            "date": src.get("window") or src.get("date"),
            "field": src.get("field") or "반도체",
            "company": src.get("company"),
            "ticker": src.get("ticker") or src.get("stock_code"),
            "stock_code": src.get("stock_code") or src.get("ticker"),
            "recommendation": _rec(src.get("chair_recommendation")),
            "weighted_signal": _round(src.get("weighted_signal") or src.get("chair_weighted_signal") or src.get("chair_score")),
            "as_of_date": src.get("as_of_date") or src.get("MARKET_AS_OF_DATE"),
            "signal_source": "converted_from_monthly_cutoff_pipeline_results",
        }

        weighted_sum = 0.0
        seen = False

        for agent in AGENTS:
            packet = _read_json(src.get(f"{agent}_json_path"))
            vals = _extract_agent(packet, agent)
            # Existing flat columns in the first CSV override only when packet values are missing.
            if vals["signal"] is None:
                vals["signal"] = _round(src.get(f"{agent}_signal"))
            if vals["weighted_signal"] is None:
                vals["weighted_signal"] = _round(src.get(f"{agent}_weighted_signal"))
            if vals["recommendation"] is None:
                vals["recommendation"] = _rec(src.get(f"{agent}_recommendation"))
            if vals["weight"] is None:
                vals["weight"] = _round(src.get(f"{agent}_weight") or weights.get(agent))

            if vals["weighted_signal"] is None and vals["signal"] is not None and vals["weight"] is not None:
                vals["weighted_signal"] = _round(float(vals["signal"]) * float(vals["weight"]))

            row[f"{agent}_signal"] = vals["signal"]
            row[f"{agent}_weighted_signal"] = vals["weighted_signal"]
            row[f"{agent}_recommendation"] = vals["recommendation"] or _signal_to_rec(vals["signal"])
            row[f"{agent}_weight"] = vals["weight"]

            if vals["weighted_signal"] is not None:
                weighted_sum += float(vals["weighted_signal"])
                seen = True

        if row["weighted_signal"] is None and seen:
            row["weighted_signal"] = round(weighted_sum, 6)
        if row["recommendation"] is None:
            row["recommendation"] = _signal_to_rec(row["weighted_signal"])

        out_rows.append({col: row.get(col) for col in SIGNAL_COLUMNS})

    out = pd.DataFrame(out_rows, columns=SIGNAL_COLUMNS)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False, encoding="utf-8-sig")
    if output_xlsx:
        out.to_excel(output_xlsx, index=False)
    return output_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert monthly_cutoff_pipeline_results.csv into signal_df-style schema.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--xlsx", default="")
    ns = parser.parse_args()

    inp = Path(ns.input)
    out = Path(ns.output) if ns.output else inp.with_name("signal_df_monthly_converted.csv")
    xlsx = Path(ns.xlsx) if ns.xlsx else None
    convert(inp, out, xlsx)
    print(f"[OK] wrote {out}")
    if xlsx:
        print(f"[OK] wrote {xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

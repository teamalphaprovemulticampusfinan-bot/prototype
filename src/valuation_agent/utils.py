from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "None", "nan", "null"}:
        return None
    neg = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        num = float(text)
        return -num if neg else num
    except Exception:
        return None


def safe_div(a: Any, b: Any) -> float | None:
    x = to_float(a)
    y = to_float(b)
    if x is None or y in (None, 0):
        return None
    return x / y


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def pct(value: Any, digits: int = 1) -> str:
    v = to_float(value)
    if v is None:
        return "확인 제한"
    return f"{v * 100:.{digits}f}%"


def money_krw_mm(value: Any) -> float | None:
    v = to_float(value)
    if v is None:
        return None
    return v / 1_000_000.0

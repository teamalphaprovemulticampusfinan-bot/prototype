from __future__ import annotations

"""Schema and value-range hygiene for official macro intake CSVs.

Policy:
- Missing official columns are added as NA, not as sample values.
- Out-of-range observations are masked to NA, not clipped to arbitrary values.
- Values are sourced upstream from ECOS/FRED/KRX-compatible collectors or user
  supplied official CSVs; this module never fabricates macro or market values.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from .schemas import SCHEMAS, VALUE_RANGES


_FILENAME_TO_SCHEMA: tuple[tuple[str, str], ...] = (
    ("ecos_일별", "ecos_daily"),
    ("ecos_월별", "ecos_monthly"),
    ("ecos_분기별", "ecos_quarterly"),
    ("ext_일별", "ext_daily"),
    ("ext_월별", "ext_monthly"),
    ("rare_earth", "rare_earth"),
    ("희토류", "rare_earth"),
    ("helium", "helium"),
    ("헬륨", "helium"),
)


def infer_schema_from_path(path: str | Path) -> str | None:
    name = Path(path).name
    for prefix, schema_name in _FILENAME_TO_SCHEMA:
        if name.startswith(prefix):
            return schema_name
    return None


def enforce_schema_columns(df: pd.DataFrame, schema_name: str) -> pd.DataFrame:
    if schema_name not in SCHEMAS:
        return df

    expected = list(SCHEMAS[schema_name])
    out = df.copy()

    for col in expected:
        if col not in out.columns:
            out[col] = pd.NA

    extras = [c for c in out.columns if c not in expected]
    return out[expected + extras]


def sanitize_value_ranges(df: pd.DataFrame, schema_name: str | None = None) -> pd.DataFrame:
    """Mask official-data outliers with NA.

    This is intentionally conservative.  The function does not replace outliers
    with average/sample values because that would contaminate the macro signal.
    """

    out = df.copy()
    for col, bounds in VALUE_RANGES.items():
        if col not in out.columns:
            continue
        low, high = bounds
        numeric = pd.to_numeric(out[col], errors="coerce")
        invalid = numeric.notna() & ((numeric < low) | (numeric > high))
        if invalid.any():
            count = int(invalid.sum())
            print(f"⚠️ [{schema_name or 'macro'}] {col} 이상값 {count}건 → NA 처리")
            out.loc[invalid, col] = pd.NA
    return out


def prepare_official_macro_csv(df: pd.DataFrame, path: str | Path, schema_name: str | None = None) -> pd.DataFrame:
    """Apply schema completion and outlier hygiene before writing a CSV."""

    inferred = schema_name or infer_schema_from_path(path)
    out = df.copy()

    if inferred:
        out = enforce_schema_columns(out, inferred)
        out = sanitize_value_ranges(out, inferred)
    else:
        out = sanitize_value_ranges(out, None)

    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        out = out.dropna(subset=["date"]).sort_values("date").drop_duplicates(subset=["date"], keep="last")

    return out

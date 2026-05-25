from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
import re

import pandas as pd

from common.data_paths import DATA_DIR, ROOT_DIR, field_common_dir, rel_project_path, safe_name


CANONICAL_SOURCE_FILES = (
    "market_external_daily_v44.csv",
    "market_news_attention_daily.csv",
    "semiconductor_cycle_daily.csv",
)

TEXT_HEAVY_COLUMNS = {
    "source_files",
    "evidence_note",
    "source_file",
    "raw_text",
    "snippet",
    "summary",
    "description",
}

DEFAULT_START_DATE = "2021-01-01"
OUTPUT_DAILY_NAME = "market_semiconductor_daily.csv"
OUTPUT_MONTHLY_NAME = "market_semiconductor_monthly.csv"
OUTPUT_MANIFEST_NAME = "market_semiconductor_manifest.json"


@dataclass(frozen=True)
class MarketSemiconductorBuildResult:
    status: str
    daily_csv: str
    monthly_csv: str
    sector_daily_csv: str
    sector_monthly_csv: str
    manifest_json: str
    start_date: str
    end_date: str
    rows_daily: int
    rows_monthly: int
    source_files: list[str]
    source_min_date: str | None
    source_max_date: str | None
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "daily_csv": self.daily_csv,
            "monthly_csv": self.monthly_csv,
            "sector_daily_csv": self.sector_daily_csv,
            "sector_monthly_csv": self.sector_monthly_csv,
            "manifest_json": self.manifest_json,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "rows_daily": self.rows_daily,
            "rows_monthly": self.rows_monthly,
            "source_files": self.source_files,
            "source_min_date": self.source_min_date,
            "source_max_date": self.source_max_date,
            "notes": self.notes,
        }


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_date(value: Any) -> pd.Timestamp | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        ts = pd.to_datetime(value, errors="coerce")
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).normalize()


def _default_end_date() -> str:
    env = os.getenv("MARKET_SEMICONDUCTOR_END_DATE", "").strip()
    if env:
        ts = _parse_date(env)
        if ts is not None:
            return ts.strftime("%Y-%m-%d")
    return date.today().strftime("%Y-%m-%d")


def _decode_escaped_unicode(text: Any) -> str:
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text or ""))


def _market_excel_dir(create: bool = True) -> Path:
    path = ROOT_DIR / "data" / "market_excel"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _sector_market_dir(field: str = "반도체", create: bool = True) -> Path:
    canonical = field_common_dir("market", field=field, create=False)
    if canonical.exists():
        return canonical

    # ZIPs extracted on some systems can preserve Korean paths as #Ubc18#...
    # Resolve those folders as read sources instead of creating a parallel tree.
    if DATA_DIR.exists():
        for child in DATA_DIR.iterdir():
            if not child.is_dir():
                continue
            if _decode_escaped_unicode(child.name) == field:
                candidate = child / "_sector_common" / "market"
                if candidate.exists():
                    return candidate

    return field_common_dir("market", field=field, create=create)


def _read_csv_safe(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception as exc:
            errors.append(f"{enc}: {exc}")
    raise RuntimeError(f"CSV read failed: {path} / {errors[-2:]}")


def _read_excel_safe(path: Path) -> pd.DataFrame:
    try:
        return pd.read_excel(path)
    except Exception as exc:
        raise RuntimeError(f"Excel read failed: {path}: {exc}") from exc


def _find_date_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "date",
        "Date",
        "DATE",
        "날짜",
        "일자",
        "as_of_date",
        "base_date",
        "trade_date",
        "trading_date",
        "timestamp",
        "datetime",
        "basDt",
        "basdt",
        "기준일",
    ]
    if df is None or df.empty:
        return None

    lower_to_original = {str(c).lower().strip(): c for c in df.columns}
    for col in candidates:
        found = lower_to_original.get(str(col).lower().strip())
        if found is None:
            continue
        parsed = pd.to_datetime(df[found], errors="coerce")
        if parsed.notna().any():
            return str(found)

    # Do not infer numeric columns such as current_price as dates.  The old
    # heuristic sometimes parsed a single numeric price as 1970-01-01 and made
    # source_min_date wrong.  Only text/object columns with a date-like name or
    # strong parse ratio are eligible for inference.
    best_col = None
    best_score = 0.0
    sample_size = min(len(df), 300)
    if sample_size <= 0:
        return None
    for col in df.columns[:30]:
        series = df[col].head(sample_size)
        if pd.api.types.is_numeric_dtype(series):
            continue
        try:
            parsed = pd.to_datetime(series, errors="coerce")
            score = float(parsed.notna().mean())
        except Exception:
            score = 0.0
        col_text = str(col).lower()
        name_hint = any(token in col_text for token in ("date", "time", "일자", "날짜", "기준"))
        adjusted = score + (0.15 if name_hint else 0.0)
        if adjusted > best_score:
            best_score = adjusted
            best_col = str(col)
    return best_col if best_col is not None and best_score >= 0.5 else None


def _standardize_daily_frame(df: pd.DataFrame, *, source_name: str) -> tuple[pd.DataFrame, str | None, str | None]:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date"]), None, None

    work = df.copy()
    date_col = _find_date_column(work)
    if date_col is None:
        return pd.DataFrame(columns=["date"]), None, None

    work["date"] = pd.to_datetime(work[date_col], errors="coerce").dt.normalize()
    work = work.dropna(subset=["date"])
    if work.empty:
        return pd.DataFrame(columns=["date"]), None, None

    source_min = work["date"].min().strftime("%Y-%m-%d")
    source_max = work["date"].max().strftime("%Y-%m-%d")

    drop_cols = {date_col} if date_col != "date" else set()
    for col in list(work.columns):
        lower = str(col).strip().lower()
        if lower in TEXT_HEAVY_COLUMNS:
            drop_cols.add(col)
    if drop_cols:
        work = work.drop(columns=[c for c in drop_cols if c in work.columns], errors="ignore")

    # Convert bool to numeric-friendly 0/1 only when mixed aggregation would fail.
    for col in list(work.columns):
        if col == "date":
            continue
        if work[col].dtype == bool:
            work[col] = work[col].astype(int)

    numeric_cols = [c for c in work.columns if c != "date" and pd.api.types.is_numeric_dtype(work[c])]
    non_numeric_cols = [c for c in work.columns if c != "date" and c not in numeric_cols]

    aggregations: dict[str, str] = {c: "mean" for c in numeric_cols}
    aggregations.update({c: "first" for c in non_numeric_cols})

    if aggregations:
        grouped = work.groupby("date", as_index=False).agg(aggregations)
    else:
        grouped = work[["date"]].drop_duplicates().copy()

    prefix = safe_name(source_name, "market_source").lower()
    renamed: dict[str, str] = {}
    for col in grouped.columns:
        if col == "date":
            continue
        clean_col = safe_name(col, "col")
        renamed[col] = f"{prefix}__{clean_col}"
    grouped = grouped.rename(columns=renamed)
    grouped["date"] = pd.to_datetime(grouped["date"]).dt.strftime("%Y-%m-%d")
    return grouped, source_min, source_max


def _calendar_status_for_dates(dates: pd.Series, source_min: pd.Timestamp, source_max: pd.Timestamp) -> list[str]:
    status: list[str] = []
    for raw in dates:
        ts = _parse_date(raw)
        if ts is None:
            status.append("calendar_unknown")
        elif ts < source_min:
            status.append("calendar_backfilled_from_first_available")
        elif ts > source_max:
            status.append("calendar_extended_ffill")
        else:
            status.append("source_or_merged")
    return status


def _calendar_extend_source_frame(
    df: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, str | None, str | None, int]:
    """Extend one market source CSV to a daily 2021~latest calendar.

    This is intentionally limited to market_intake source CSVs.  It does not
    create external facts; dates before the first source row are backfilled from
    the first available row, and dates after the last source row are forward
    filled.  The per-row status column records which rows are original/merged,
    backfilled, or forward-filled.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["date"]), None, None, 0

    date_col = _find_date_column(df)
    if date_col is None:
        return df.copy(), None, None, 0

    start_ts = _parse_date(start_date) or pd.Timestamp(DEFAULT_START_DATE)
    end_ts = _parse_date(end_date) or pd.Timestamp(_default_end_date())
    if end_ts < start_ts:
        end_ts = start_ts

    work = df.copy()
    work["date"] = pd.to_datetime(work[date_col], errors="coerce").dt.normalize()
    work = work.dropna(subset=["date"])
    if work.empty:
        return pd.DataFrame(columns=["date"]), None, None, 0

    source_min_ts = pd.Timestamp(work["date"].min()).normalize()
    source_max_ts = pd.Timestamp(work["date"].max()).normalize()
    source_min = source_min_ts.strftime("%Y-%m-%d")
    source_max = source_max_ts.strftime("%Y-%m-%d")

    drop_cols = []
    for col in list(work.columns):
        if col != "date" and str(col) == str(date_col):
            drop_cols.append(col)
    if drop_cols:
        work = work.drop(columns=drop_cols, errors="ignore")

    for col in list(work.columns):
        if col == "date":
            continue
        if work[col].dtype == bool:
            work[col] = work[col].astype(int)

    numeric_cols = [c for c in work.columns if c != "date" and pd.api.types.is_numeric_dtype(work[c])]
    non_numeric_cols = [c for c in work.columns if c != "date" and c not in numeric_cols]
    aggregations: dict[str, str] = {c: "mean" for c in numeric_cols}
    aggregations.update({c: "first" for c in non_numeric_cols})
    if aggregations:
        grouped = work.groupby("date", as_index=False).agg(aggregations)
    else:
        grouped = work[["date"]].drop_duplicates().copy()

    calendar = pd.DataFrame({"date": pd.date_range(start_ts, end_ts, freq="D")})
    merged = calendar.merge(grouped, on="date", how="left")
    original_missing = int(merged.drop(columns=["date"], errors="ignore").isna().any(axis=1).sum()) if len(merged.columns) > 1 else 0

    value_cols = [c for c in merged.columns if c != "date"]
    if value_cols:
        merged[value_cols] = merged[value_cols].ffill().bfill()
        try:
            merged[value_cols] = merged[value_cols].infer_objects(copy=False)
        except Exception:
            pass

    merged["market_source_calendar_fill_status"] = _calendar_status_for_dates(merged["date"], source_min_ts, source_max_ts)
    merged["market_source_original_min_date"] = source_min
    merged["market_source_original_max_date"] = source_max
    merged["market_source_calendar_start_date"] = start_ts.strftime("%Y-%m-%d")
    merged["market_source_calendar_end_date"] = end_ts.strftime("%Y-%m-%d")
    merged["market_source_calendar_generated_at"] = datetime.now().isoformat(timespec="seconds")
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    return merged, source_min, source_max, original_missing


def _write_market_source_csv(df: pd.DataFrame, *, filename: str, excel_dir: Path, sector_dir: Path) -> Path:
    target = excel_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False, encoding="utf-8-sig")

    sector_target = sector_dir / filename
    sector_target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(sector_target, index=False, encoding="utf-8-sig")
    return target


def _copy_if_changed(src: Path, dst: Path) -> bool:
    try:
        if not src.exists() or not src.is_file():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size == src.stat().st_size and int(dst.stat().st_mtime) >= int(src.stat().st_mtime):
            return False
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False


def _mirror_market_data_folder(src_dir: Path, dst_dir: Path) -> int:
    if not src_dir.exists() or not src_dir.is_dir():
        return 0
    copied = 0
    for src in src_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        if _copy_if_changed(src, dst):
            copied += 1
    return copied


def mirror_sector_market_sources_to_market_excel(field: str = "반도체") -> dict[str, Any]:
    """Copy sector-common market intake sources into data/market_excel.

    The function copies instead of deleting the source files. This keeps the
    existing sector-common structure stable while making the new market_excel
    layout available to market_intake and market_agent.
    """

    sector_dir = _sector_market_dir(field, create=True)
    excel_dir = _market_excel_dir(create=True)
    copied_files: list[str] = []
    missing: list[str] = []

    for filename in CANONICAL_SOURCE_FILES:
        src = sector_dir / filename
        dst = excel_dir / filename
        # data/market_excel is now the canonical working source for market_intake.
        # If the user has already refreshed that file to a wider 2021~latest
        # calendar, do not overwrite it with the older sector_common copy.
        if dst.exists():
            copied_files.append(rel_project_path(dst))
        elif src.exists():
            _copy_if_changed(src, dst)
            copied_files.append(rel_project_path(dst))
        else:
            missing.append(filename)

    copied_market_data = _mirror_market_data_folder(sector_dir / "market_data", excel_dir / "market_data")

    return {
        "sector_market_dir": rel_project_path(sector_dir),
        "market_excel_dir": rel_project_path(excel_dir),
        "copied_files": copied_files,
        "missing_files": missing,
        "copied_market_data_files": copied_market_data,
    }


def _load_source_frames(field: str, *, network_update: bool, start_date: str, end_date: str) -> tuple[list[pd.DataFrame], list[str], list[str], list[str], str | None, str | None]:
    excel_dir = _market_excel_dir(create=True)
    sector_dir = _sector_market_dir(field, create=True)

    frames: list[pd.DataFrame] = []
    source_files: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    min_dates: list[str] = []
    max_dates: list[str] = []

    external_frame = _network_external_market_frame(start_date=start_date, end_date=end_date) if network_update else None

    for filename in CANONICAL_SOURCE_FILES:
        preferred = excel_dir / filename
        fallback = sector_dir / filename
        path = preferred if preferred.exists() else fallback
        if not path.exists():
            warnings.append(f"missing source file: {filename}")
            continue
        try:
            df = _read_csv_safe(path)
            if filename == "market_external_daily_v44.csv" and external_frame is not None and not external_frame.empty:
                df = _combine_existing_and_network_external(df, external_frame)
                notes.append("market_external_daily_v44.csv was refreshed with yfinance-compatible market indices where available.")

            extended, original_min, original_max, filled_count = _calendar_extend_source_frame(
                df,
                start_date=start_date,
                end_date=end_date,
            )
            if original_min and original_max:
                df = extended
                path = _write_market_source_csv(df, filename=filename, excel_dir=excel_dir, sector_dir=sector_dir)
                notes.append(
                    f"{filename} calendar-normalized to {start_date}~{end_date} "
                    f"(original {original_min}~{original_max}, filled_rows={filled_count})."
                )
        except Exception as exc:
            warnings.append(f"read failed {filename}: {exc}")
            continue

        prefix = {
            "market_external_daily_v44.csv": "external",
            "market_news_attention_daily.csv": "news",
            "semiconductor_cycle_daily.csv": "cycle",
        }.get(filename, Path(filename).stem)
        daily, src_min, src_max = _standardize_daily_frame(df, source_name=prefix)
        if not daily.empty:
            frames.append(daily)
            source_files.append(rel_project_path(path))
            if src_min:
                min_dates.append(src_min)
            if src_max:
                max_dates.append(src_max)

    market_data_dir = excel_dir / "market_data"
    if market_data_dir.exists():
        for path in sorted(market_data_dir.rglob("*")):
            if not path.is_file() or path.name.startswith("~$"):
                continue
            if path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
                continue
            try:
                df = _read_csv_safe(path) if path.suffix.lower() == ".csv" else _read_excel_safe(path)
                daily, src_min, src_max = _standardize_daily_frame(df, source_name=f"marketdata_{path.stem}")
                if not daily.empty:
                    frames.append(daily)
                    source_files.append(rel_project_path(path))
                    if src_min:
                        min_dates.append(src_min)
                    if src_max:
                        max_dates.append(src_max)
            except Exception as exc:
                warnings.append(f"market_data file skipped {path.name}: {exc}")

    source_min = min(min_dates) if min_dates else None
    source_max = max(max_dates) if max_dates else None
    return frames, source_files, warnings, notes, source_min, source_max


def _combine_existing_and_network_external(existing: pd.DataFrame, network: pd.DataFrame) -> pd.DataFrame:
    if network is None or network.empty:
        return existing
    date_col = _find_date_column(existing) or "date"
    old = existing.copy()
    if date_col != "date":
        old = old.rename(columns={date_col: "date"})
    old["date"] = pd.to_datetime(old["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    new = network.copy()
    new["date"] = pd.to_datetime(new["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined = pd.concat([old, new], ignore_index=True, sort=False)
    combined = combined.dropna(subset=["date"])
    combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return combined


def _network_external_market_frame(*, start_date: str, end_date: str) -> pd.DataFrame | None:
    """Best-effort market-index refresh via yfinance.

    This never raises. If network, yfinance, or a ticker fails, the caller keeps
    using the existing local CSV and the final daily file is calendar-extended
    with a clear status flag.
    """

    if not _env_bool("MARKET_SEMICONDUCTOR_ENABLE_NETWORK_UPDATE", False):
        return None

    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return None

    tickers = {
        "sox": "^SOX",
        "nasdaq": "^IXIC",
        "sp500": "^GSPC",
        "vix_yf": "^VIX",
        "korea_etf": os.getenv("MARKET_KOREA_SEMICONDUCTOR_ETF_TICKER", "091160.KS"),
    }

    end_plus = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    base = pd.DataFrame({"date": pd.date_range(start_date, end_date, freq="D")})

    for prefix, ticker in tickers.items():
        try:
            raw = yf.download(ticker, start=start_date, end=end_plus, progress=False, auto_adjust=False, threads=False)
        except Exception:
            continue
        if raw is None or raw.empty:
            continue
        # yfinance can return MultiIndex columns depending on version.
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = [str(c[0]).lower() for c in raw.columns]
        else:
            raw.columns = [str(c).lower().replace(" ", "_") for c in raw.columns]
        raw = raw.reset_index().rename(columns={"Date": "date", "index": "date"})
        if "date" not in raw.columns and "datetime" in raw.columns:
            raw = raw.rename(columns={"datetime": "date"})
        raw["date"] = pd.to_datetime(raw["date"], errors="coerce").dt.normalize()
        cols: dict[str, str] = {}
        for source, target in (("close", "close"), ("adj_close", "adj_close"), ("volume", "volume")):
            if source in raw.columns:
                cols[source] = f"{prefix}_{target}"
        if not cols:
            continue
        part = raw[["date", *cols.keys()]].rename(columns=cols)
        base = base.merge(part, on="date", how="left")

    if len(base.columns) <= 1:
        return None
    base["date"] = base["date"].dt.strftime("%Y-%m-%d")
    return base.dropna(how="all", subset=[c for c in base.columns if c != "date"])


def _fill_daily_frame(daily: pd.DataFrame, *, source_min: str | None, source_max: str | None) -> pd.DataFrame:
    work = daily.copy()
    if work.empty:
        return work

    status_col = []
    src_min_ts = _parse_date(source_min) if source_min else None
    src_max_ts = _parse_date(source_max) if source_max else None
    for raw_date in work["date"]:
        ts = _parse_date(raw_date)
        if src_min_ts is not None and ts is not None and ts < src_min_ts:
            status_col.append("calendar_backfilled_from_first_available")
        elif src_max_ts is not None and ts is not None and ts > src_max_ts:
            status_col.append("calendar_extended_ffill")
        else:
            status_col.append("source_or_merged")

    for col in list(work.columns):
        if col == "date":
            continue
        if pd.api.types.is_numeric_dtype(work[col]):
            work[col] = work[col].ffill().bfill()
        else:
            work[col] = work[col].ffill().bfill()

    meta = pd.DataFrame({
        "market_semiconductor_data_status": status_col,
        "market_semiconductor_source_min_date": source_min or "",
        "market_semiconductor_source_max_date": source_max or "",
        "market_semiconductor_generated_at": datetime.now().isoformat(timespec="seconds"),
    }, index=work.index)
    return pd.concat([work.copy(), meta], axis=1)


def build_market_semiconductor_daily(
    *,
    field: str = "반도체",
    start_date: str | None = None,
    end_date: str | None = None,
    network_update: bool | None = None,
) -> dict[str, Any]:
    """Build the unified daily semiconductor market dataset.

    Inputs are mirrored from:
      data/<field>/_sector_common/market/market_data
      data/<field>/_sector_common/market/market_external_daily_v44.csv
      data/<field>/_sector_common/market/market_news_attention_daily.csv
      data/<field>/_sector_common/market/semiconductor_cycle_daily.csv

    Outputs are written to both:
      data/market_excel/market_semiconductor_daily.csv
      data/<field>/_sector_common/market/market_semiconductor_daily.csv
    """

    start_date = start_date or os.getenv("MARKET_SEMICONDUCTOR_START_DATE", DEFAULT_START_DATE).strip() or DEFAULT_START_DATE
    end_date = end_date or _default_end_date()
    start_ts = _parse_date(start_date) or pd.Timestamp(DEFAULT_START_DATE)
    end_ts = _parse_date(end_date) or pd.Timestamp(_default_end_date())
    if end_ts < start_ts:
        end_ts = start_ts
    start_date = start_ts.strftime("%Y-%m-%d")
    end_date = end_ts.strftime("%Y-%m-%d")

    do_network = network_update if network_update is not None else _env_bool("MARKET_SEMICONDUCTOR_ENABLE_NETWORK_UPDATE", False)

    mirror_info = mirror_sector_market_sources_to_market_excel(field=field)
    frames, source_files, warnings, notes, source_min, source_max = _load_source_frames(
        field,
        network_update=bool(do_network),
        start_date=start_date,
        end_date=end_date,
    )

    calendar = pd.DataFrame({"date": pd.date_range(start_date, end_date, freq="D").strftime("%Y-%m-%d")})
    daily = calendar.copy()
    for frame in frames:
        if frame is None or frame.empty:
            continue
        daily = daily.merge(frame, on="date", how="left")

    daily = _fill_daily_frame(daily, source_min=source_min, source_max=source_max)

    excel_dir = _market_excel_dir(create=True)
    sector_dir = _sector_market_dir(field, create=True)
    daily_csv = excel_dir / OUTPUT_DAILY_NAME
    monthly_csv = excel_dir / OUTPUT_MONTHLY_NAME
    sector_daily_csv = sector_dir / OUTPUT_DAILY_NAME
    sector_monthly_csv = sector_dir / OUTPUT_MONTHLY_NAME
    manifest_json = excel_dir / OUTPUT_MANIFEST_NAME

    daily.to_csv(daily_csv, index=False, encoding="utf-8-sig")
    daily.to_csv(sector_daily_csv, index=False, encoding="utf-8-sig")

    monthly = daily.copy()
    monthly["date"] = pd.to_datetime(monthly["date"], errors="coerce")
    monthly = monthly.dropna(subset=["date"]).sort_values("date")
    monthly = monthly.groupby(monthly["date"].dt.to_period("M"), as_index=False).tail(1)
    monthly["date"] = monthly["date"].dt.strftime("%Y-%m-%d")
    monthly.to_csv(monthly_csv, index=False, encoding="utf-8-sig")
    monthly.to_csv(sector_monthly_csv, index=False, encoding="utf-8-sig")

    status = "OK" if source_files else "WARN_NO_SOURCE_FILES"
    all_notes = [
        "Source files are copied, not deleted, from sector_common/market to data/market_excel.",
        "Daily calendar is guaranteed from start_date to end_date. Rows after the latest actual source date are flagged as calendar_extended_ffill.",
        *notes,
        *[f"warning: {w}" for w in warnings],
    ]
    result = MarketSemiconductorBuildResult(
        status=status,
        daily_csv=rel_project_path(daily_csv),
        monthly_csv=rel_project_path(monthly_csv),
        sector_daily_csv=rel_project_path(sector_daily_csv),
        sector_monthly_csv=rel_project_path(sector_monthly_csv),
        manifest_json=rel_project_path(manifest_json),
        start_date=start_date,
        end_date=end_date,
        rows_daily=int(len(daily)),
        rows_monthly=int(len(monthly)),
        source_files=source_files,
        source_min_date=source_min,
        source_max_date=source_max,
        notes=all_notes,
    )

    manifest = {
        "agent": "market",
        "artifact": "market_semiconductor_daily",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "network_update_enabled": bool(do_network),
        "mirror_info": mirror_info,
        **result.as_dict(),
    }
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return result.as_dict()


def load_latest_market_semiconductor_row(as_of_date: str | None = None, *, field: str = "반도체") -> dict[str, Any]:
    """Read the latest row from the unified market_semiconductor_daily file."""

    candidates = [
        _market_excel_dir(create=True) / OUTPUT_DAILY_NAME,
        _sector_market_dir(field, create=True) / OUTPUT_DAILY_NAME,
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        build_market_semiconductor_daily(field=field)
        path = next((p for p in candidates if p.exists()), None)
    if path is None or not path.exists():
        return {}

    try:
        df = _read_csv_safe(path)
    except Exception:
        return {}
    if df.empty or "date" not in df.columns:
        return {}

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    if as_of_date:
        ts = _parse_date(as_of_date)
        if ts is not None:
            df = df[df["date"] <= ts]
    if df.empty:
        return {}

    row = df.iloc[-1].to_dict()
    row["date"] = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
    row["source_file"] = rel_project_path(path)
    return row

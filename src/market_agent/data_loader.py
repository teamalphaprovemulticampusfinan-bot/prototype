from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
import os
import re
from typing import Any, Iterable

import pandas as pd
import requests

from .config import MARKET_WORKBOOK_PATH, MARKET_WORKBOOK_URL, resolve_company_key


@dataclass
class WorkbookData:
    df_base: pd.DataFrame
    df_policy: pd.DataFrame
    df_growth: pd.DataFrame
    df_comp: pd.DataFrame
    df_chain: pd.DataFrame
    df_oecd_raw: pd.DataFrame
    source_path: str = ""
    source_format: str = ""
    market_csvs: dict[str, pd.DataFrame] = field(default_factory=dict)


ROOT_DIR = Path(__file__).resolve().parents[2]
MARKET_EXCEL_DIRNAME = "market_excel"
WORKBOOK_FILENAME = "Market_통합.xlsx"
LEGACY_REQUIRED_SHEETS = {
    "기본",
    "산업정책",
    "산업성장률+진입장벽",
    "산업 내 경쟁구조",
    "벨류체인",
    "OECD 경개선행지수",
}
FINAL_WORKBOOK_SHEETS = {"종합현황", "마켓점수", "밸류체인", "경쟁구조", "정부R&D정책"}

DATE_COLUMN_CANDIDATES: tuple[str, ...] = (
    "date",
    "Date",
    "DATE",
    "일자",
    "기준일",
    "날짜",
    "trading_date",
    "trade_date",
    "base_date",
    "as_of_date",
    "timestamp",
    "datetime",
)


def market_excel_dir() -> Path:
    """Canonical local folder for market intake outputs."""
    return Path(os.getenv("MARKET_EXCEL_DIR", "") or (ROOT_DIR / "data" / MARKET_EXCEL_DIRNAME))


def _decode_escaped_unicode(text: object) -> str:
    """Decode zip-extracted names like '#Ud1b5#Ud569' into Korean."""
    s = str(text or "")
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)


def _same_workbook_name(path: Path) -> bool:
    return _decode_escaped_unicode(path.name) == WORKBOOK_FILENAME


def _existing_file(path: Path | str | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    try:
        if p.exists() and p.is_file():
            return p
    except Exception:
        return None
    return None


def _normalize_company_token(value: object) -> str:
    """Normalize Korean/English company names for workbook matching.

    zip-extracted files may contain escaped unicode names such as
    market_final_SFA#Ubc18#Ub3c4#Uccb4.xlsx.  Also, users may pass
    "SFA 반도체" while the generated file is "SFA반도체".
    This token removes whitespace and punctuation after decoding #Uxxxx.
    """
    text = _decode_escaped_unicode(value)
    text = text.replace("㈜", "").replace("주식회사", "")
    text = re.sub(r"[^0-9A-Za-z가-힣]+", "", text)
    return text.lower()


def _company_final_workbook(company: str | None = None) -> Path | None:
    """Return the exact company workbook under data/market_excel.

    Important: never fall back to the newest market_final_*.xlsx when the
    requested company file is missing.  That caused SFA 반도체 runs to read
    market_final_네패스.xlsx.  If no exact/normalized match exists, return
    None so the caller can use the common Market_통합.xlsx or CSV sources.
    """
    root = market_excel_dir()
    if not root.exists() or not company:
        return None

    company_tokens = {
        _normalize_company_token(company),
        _normalize_company_token(resolve_company_key(company)),
    }
    company_tokens = {token for token in company_tokens if token}
    if not company_tokens:
        return None

    # Fast exact attempts for normal Windows filenames.
    direct_candidates = [
        root / f"market_final_{company}.xlsx",
        root / f"market_final_{str(company).replace(' ', '')}.xlsx",
    ]
    for exact in direct_candidates:
        if exact.exists() and exact.is_file():
            return exact

    # Robust match for zip-escaped Korean filenames (#Uxxxx) and spacing variants.
    for path in sorted(root.glob("market_final_*.xlsx")):
        if not path.is_file():
            continue
        decoded_stem = _decode_escaped_unicode(path.stem)
        if decoded_stem.startswith("market_final_"):
            suffix = decoded_stem[len("market_final_"):]
        else:
            suffix = decoded_stem
        if _normalize_company_token(suffix) in company_tokens:
            return path

    return None


def _candidate_workbook_paths(company: str | None = None) -> list[Path]:
    """Return workbook candidates, with data/market_excel strictly preferred.

    Team note: do not let the old sector_common/source_data/Market_통합.xlsx
    win over files generated into data/market_excel by market_intake/market_issues.db.
    """
    root = market_excel_dir()
    candidates: list[Path] = []

    final = _company_final_workbook(company)
    if final is not None:
        candidates.append(final)

    candidates.extend([
        root / WORKBOOK_FILENAME,
        root / "market_final.xlsx",
    ])

    env_path = os.getenv("MARKET_WORKBOOK_PATH", "").strip()
    if env_path:
        env_p = Path(env_path)
        # Use explicit env path only after data/market_excel candidates. This keeps
        # backward compatibility without reverting the default route.
        candidates.append(env_p)

    candidates.append(Path(MARKET_WORKBOOK_PATH))

    # Last-resort legacy locations. These are intentionally after data/market_excel.
    candidates.extend([
        ROOT_DIR / "data" / "반도체" / "_sector_common" / "source_data" / WORKBOOK_FILENAME,
        ROOT_DIR / "data" / "반도체" / "_sector_common" / "data" / WORKBOOK_FILENAME,
        ROOT_DIR / "data" / "반도체" / "common" / "data" / WORKBOOK_FILENAME,
        ROOT_DIR / "data" / "반도체" / "source_data" / WORKBOOK_FILENAME,
        ROOT_DIR / "data" / "반도체" / "data" / WORKBOOK_FILENAME,
        ROOT_DIR / "data" / WORKBOOK_FILENAME,
        ROOT_DIR / "workspace" / "data" / WORKBOOK_FILENAME,
        ROOT_DIR / "workspace" / WORKBOOK_FILENAME,
    ])

    seen: set[str] = set()
    unique: list[Path] = []
    for p in candidates:
        key = str(p).replace("\\", "/")
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _recursive_find_workbook(search_roots: Iterable[Path], company: str | None = None) -> Path | None:
    roots = list(search_roots)

    # Search data/market_excel first and allow market_final_*.xlsx files.
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        try:
            if root.name == MARKET_EXCEL_DIRNAME:
                final = _company_final_workbook(company)
                if final is not None:
                    return final
                for path in root.rglob("*.xlsx"):
                    if _same_workbook_name(path):
                        return path
            else:
                for path in root.rglob("*.xlsx"):
                    if _same_workbook_name(path):
                        return path
        except Exception:
            continue
    return None


def resolve_workbook_path(
    destination: str | Path | None = None,
    *,
    company: str | None = None,
) -> Path:
    explicit = _existing_file(destination)
    if explicit:
        return explicit

    for candidate in _candidate_workbook_paths(company=company):
        found = _existing_file(candidate)
        if found:
            return found

    recursive = _recursive_find_workbook([
        market_excel_dir(),
        ROOT_DIR / "data",
        ROOT_DIR / "workspace",
    ], company=company)
    if recursive:
        return recursive

    return market_excel_dir() / WORKBOOK_FILENAME


def download_workbook(
    destination: str | Path | None = None,
    *,
    company: str | None = None,
) -> Path:
    path = resolve_workbook_path(destination, company=company)
    if path.exists() and path.is_file():
        return path
    raise FileNotFoundError(
        "Local Market workbook not found. Preferred folder is data/market_excel. "
        "If MARKET_WORKBOOK_URL is set, load_workbook() will read it in memory."
    )


def _get_workbook_url() -> str:
    url = os.getenv("MARKET_WORKBOOK_URL", "") or MARKET_WORKBOOK_URL or ""
    return url.strip().strip('"').strip("'")


def _load_excel_from_url() -> pd.ExcelFile:
    url = _get_workbook_url()
    if not url:
        checked = "\n".join(f"- {p}" for p in _candidate_workbook_paths())
        raise FileNotFoundError(
            "Market workbook not found and MARKET_WORKBOOK_URL is empty.\n"
            f"Preferred folder: {market_excel_dir()}\n"
            f"Expected filename: {WORKBOOK_FILENAME} or market_final_<company>.xlsx\n"
            "Checked candidate paths:\n"
            f"{checked}\n\n"
            "Set MARKET_WORKBOOK_URL in .env with a raw xlsx URL only if local files are unavailable."
        )

    response = requests.get(
        url,
        timeout=int(os.getenv("REQUEST_TIMEOUT", "30") or 30),
        headers={
            "User-Agent": "AlphaProve-MarketAgent/1.0",
            "Accept": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                "application/octet-stream,*/*"
            ),
        },
    )
    response.raise_for_status()
    content = response.content or b""
    if len(content) < 1024 or content[:2] != b"PK":
        raise ValueError("MARKET_WORKBOOK_URL response is not a valid xlsx file. Use GitHub raw URL, not blob URL.")

    print("[Market] local workbook 없음 → MARKET_WORKBOOK_URL 원천을 메모리에서 직접 로딩")
    print("[Market] workbook source: remote_market_workbook_in_memory")
    return pd.ExcelFile(BytesIO(content))


def _empty_workbook(source_path: str = "", source_format: str = "empty") -> WorkbookData:
    return WorkbookData(
        df_base=pd.DataFrame(),
        df_policy=pd.DataFrame(),
        df_growth=pd.DataFrame(),
        df_comp=pd.DataFrame(),
        df_chain=pd.DataFrame(),
        df_oecd_raw=pd.DataFrame(),
        source_path=source_path,
        source_format=source_format,
        market_csvs=load_market_excel_csvs(),
    )


def _parse_excel_file(xl: pd.ExcelFile, source_path: str) -> WorkbookData:
    sheets = set(xl.sheet_names)

    if LEGACY_REQUIRED_SHEETS.issubset(sheets):
        return WorkbookData(
            df_base=xl.parse("기본"),
            df_policy=xl.parse("산업정책"),
            df_growth=xl.parse("산업성장률+진입장벽"),
            df_comp=xl.parse("산업 내 경쟁구조"),
            df_chain=xl.parse("벨류체인"),
            df_oecd_raw=xl.parse("OECD 경개선행지수"),
            source_path=source_path,
            source_format="legacy_market_workbook",
            market_csvs=load_market_excel_csvs(),
        )

    # New workbooks generated under data/market_excel/market_final_<company>.xlsx.
    if sheets & FINAL_WORKBOOK_SHEETS:
        return WorkbookData(
            df_base=xl.parse("종합현황") if "종합현황" in sheets else pd.DataFrame(),
            df_policy=xl.parse("정부R&D정책") if "정부R&D정책" in sheets else pd.DataFrame(),
            df_growth=xl.parse("마켓점수") if "마켓점수" in sheets else pd.DataFrame(),
            df_comp=xl.parse("경쟁구조") if "경쟁구조" in sheets else pd.DataFrame(),
            df_chain=xl.parse("밸류체인") if "밸류체인" in sheets else pd.DataFrame(),
            df_oecd_raw=pd.DataFrame(),
            source_path=source_path,
            source_format="market_final_workbook",
            market_csvs=load_market_excel_csvs(),
        )

    # Unknown xlsx shape: keep pipeline alive and attach CSVs.
    return _empty_workbook(source_path=source_path, source_format="unknown_workbook_shape")


def load_workbook(
    destination: str | Path | None = None,
    *,
    company: str | None = None,
    force_download: bool = False,
) -> WorkbookData:
    # force_download is preserved for compatibility but local data/market_excel wins by default.
    workbook_path = resolve_workbook_path(destination, company=company)

    if workbook_path.exists() and workbook_path.is_file() and not force_download:
        print(f"[Market] workbook path: {workbook_path}")
        xl = pd.ExcelFile(workbook_path)
    else:
        xl = _load_excel_from_url()
        workbook_path = Path("remote_market_workbook_in_memory")

    return _parse_excel_file(xl, str(workbook_path))


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return "" if text.lower() == "nan" else text


def _row_for_company(df: pd.DataFrame, company: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    for col in ("기업명", "company", "company_name", "회사명"):
        if col in df.columns:
            rows = df[df[col].astype(str).str.contains(str(company), na=False, regex=False)]
            if not rows.empty:
                return rows.iloc[0]
    return df.iloc[0]


def get_static_data(company: str, workbook: WorkbookData) -> dict:
    chain = _get_chain_data(company, workbook)
    base = _get_base_data(company, workbook)
    competitors = _get_competitor_data(company, workbook)
    policy = _get_policy_data(workbook)
    growth = _get_growth_data(workbook)

    return {
        "chain": chain,
        "base": base,
        "competitors": competitors,
        "policy": policy,
        "growth": growth,
        "market_csv_files": list((workbook.market_csvs or {}).keys()),
        "workbook_source": workbook.source_path,
        "workbook_source_format": workbook.source_format,
    }


def _get_chain_data(company: str, workbook: WorkbookData) -> dict[str, str]:
    df = workbook.df_chain
    if df is None or df.empty:
        return {}

    # New market_final workbook shape.
    if "company_name" in df.columns or "vc_role" in df.columns:
        row = _row_for_company(df, company)
        if row is None:
            return {}
        domestic = _as_text(row.get("domestic_peers", ""))
        global_peers = _as_text(row.get("global_peers", ""))
        return {
            "position": _as_text(row.get("vc_role", row.get("position", ""))),
            "products": _as_text(row.get("products", domestic or global_peers)),
            "process": _as_text(row.get("process", row.get("differentiation", ""))),
        }

    # Legacy workbook shape.
    row_df = df[df.iloc[:, 0] == company]
    if row_df.empty:
        return {}
    row = row_df.iloc[0]
    return {
        "position": _as_text(row.iloc[1] if len(row) > 1 else ""),
        "products": _as_text(row.iloc[2] if len(row) > 2 else ""),
        "process": _as_text(row.iloc[3] if len(row) > 3 else ""),
    }


def _get_base_data(company: str, workbook: WorkbookData) -> dict[str, str]:
    df = workbook.df_base
    if df is None or df.empty:
        return {}

    # New market_final 종합현황 sheet.
    if "기업명" in df.columns:
        row = _row_for_company(df, company)
        if row is None:
            return {}
        return {str(k): _as_text(v) for k, v in row.items() if _as_text(v) and str(k) != "기업명"}

    base: dict[str, str] = {}
    for _, row in df.iterrows():
        label = _as_text(row.iloc[0] if len(row) else "")
        val = _as_text(row.get(company, ""))
        if label and val:
            base[label] = val
    return base


def _get_competitor_data(company: str, workbook: WorkbookData) -> list[dict[str, str]]:
    df = workbook.df_comp
    if df is None or df.empty:
        return []

    # New market_final 경쟁구조 sheet.
    if "company_name" in df.columns or "domestic_peers" in df.columns:
        row = _row_for_company(df, company)
        if row is None:
            return []
        peers = []
        for name in re.split(r"[,/|;]+", _as_text(row.get("domestic_peers", ""))):
            name = name.strip()
            if name:
                peers.append({
                    "name": name,
                    "price": "",
                    "momentum": _as_text(row.get("competition_intensity", "")),
                })
        if not peers and _as_text(row.get("peer_group", "")):
            peers.append({"name": _as_text(row.get("peer_group", "")), "price": "", "momentum": ""})
        return peers

    rows = df[df.iloc[:, 0].astype(str).str.contains(company, na=False, regex=False)]
    competitors: list[dict[str, str]] = []
    for _, row in rows.iterrows():
        competitors.append({
            "name": _as_text(row.iloc[1] if len(row) > 1 else ""),
            "price": _as_text(row.iloc[4] if len(row) > 4 else ""),
            "momentum": _as_text(row.iloc[9] if len(row) > 9 else ""),
        })
    return competitors


def _get_policy_data(workbook: WorkbookData) -> dict[str, list[str]]:
    df = workbook.df_policy
    if df is None or df.empty:
        return {"policies": [], "trends": []}

    # New market_final 정부R&D정책 shape.
    if {"segment", "keyword"}.issubset(set(df.columns)):
        policies = df["keyword"].dropna().astype(str).tolist()
        trends = df["segment"].dropna().astype(str).tolist()
        return {"policies": policies, "trends": trends}

    return {
        "policies": df.iloc[:, 0].dropna().astype(str).tolist() if df.shape[1] >= 1 else [],
        "trends": df.iloc[:, 1].dropna().astype(str).tolist() if df.shape[1] >= 2 else [],
    }


def _get_growth_data(workbook: WorkbookData) -> dict[str, dict[str, str]]:
    df = workbook.df_growth
    if df is None or df.empty:
        return {}

    # New market_final 마켓점수 shape.
    if "기업명" in df.columns:
        row = _row_for_company(df, "")
        if row is None:
            return {}
        return {"마켓점수": {str(k): _as_text(v) for k, v in row.items() if _as_text(v)}}

    rows = df.dropna(how="all").iloc[1:]
    growth: dict[str, dict[str, str]] = {}
    for _, row in rows.iterrows():
        category = _as_text(row.iloc[0] if len(row) else "")
        if category:
            growth[category] = {
                "반도체": _as_text(row.iloc[1] if len(row) > 1 else ""),
                "배터리": _as_text(row.iloc[2] if len(row) > 2 else ""),
                "바이오": _as_text(row.iloc[3] if len(row) > 3 else ""),
            }
    return growth


def fallback_oecd_from_excel(workbook: WorkbookData) -> dict[str, float]:
    df = workbook.df_oecd_raw
    if df is None or df.empty or df.shape[0] < 4 or df.shape[1] < 5:
        return {"G20": 0.0, "한국": 0.0, "미국": 0.0, "중국": 0.0}
    try:
        work = df.iloc[3:].dropna(how="all")
        if work.empty:
            return {"G20": 0.0, "한국": 0.0, "미국": 0.0, "중국": 0.0}
        last_row = work.iloc[-1]
        return {
            "G20": float(last_row.iloc[1]),
            "한국": float(last_row.iloc[2]),
            "미국": float(last_row.iloc[3]),
            "중국": float(last_row.iloc[4]),
        }
    except Exception:
        return {"G20": 0.0, "한국": 0.0, "미국": 0.0, "중국": 0.0}


def _read_csv_any_encoding(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return pd.DataFrame()


def detect_date_column(df: "pd.DataFrame", preferred: str = "date") -> str | None:
    if df is None or df.empty:
        return None

    columns = [str(c) for c in df.columns]
    lower_to_original = {c.lower().strip(): c for c in columns}

    for candidate in (preferred, *DATE_COLUMN_CANDIDATES):
        found = lower_to_original.get(str(candidate).lower().strip())
        if found is not None:
            parsed = pd.to_datetime(df[found], errors="coerce")
            if parsed.notna().any():
                return found

    best_col: str | None = None
    best_score = 0.0
    for col in columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            continue
        parsed = pd.to_datetime(series, errors="coerce")
        valid = int(parsed.notna().sum())
        if valid <= 0:
            continue
        score = valid / max(len(series), 1)
        name_hint = any(token in col.lower() for token in ("date", "일", "날짜", "기준"))
        adjusted = score + (0.15 if name_hint else 0.0)
        if adjusted > best_score:
            best_col = col
            best_score = adjusted

    if best_col is not None and best_score >= 0.3:
        return best_col
    return None


def normalize_date_column(
    df: "pd.DataFrame",
    date_col: str = "date",
    *,
    keep_original_date_col: bool = True,
) -> "pd.DataFrame":
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    work = df.copy()
    detected = detect_date_column(work, preferred=date_col)
    if detected is None:
        return work

    parsed = pd.to_datetime(work[detected], errors="coerce")
    work = work.loc[parsed.notna()].copy()
    if work.empty:
        return work

    parsed = pd.to_datetime(work[detected], errors="coerce")
    if detected != "date" and keep_original_date_col:
        original_name = f"original_{detected}"
        if original_name not in work.columns:
            work[original_name] = work[detected]
    work["date"] = parsed.dt.normalize()
    return work


def filter_by_cutoff(df: "pd.DataFrame", as_of_date: str, date_col: str = "date") -> "pd.DataFrame":
    """Filter a dataframe to rows on or before `as_of_date`.

    This team-facing function is intentionally preserved. It now also detects
    common date column names in every CSV under data/market_excel.
    """
    cutoff_str = as_of_date or os.getenv("MARKET_AS_OF_DATE", "")
    if not cutoff_str:
        return df
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    cutoff = pd.to_datetime(cutoff_str, errors="coerce")
    if pd.isna(cutoff):
        return df

    work = df.copy()
    detected = date_col if date_col in work.columns else detect_date_column(work, preferred=date_col)
    if detected is None:
        return work
    parsed = pd.to_datetime(work[detected], errors="coerce")
    return work.loc[parsed.notna() & (parsed <= cutoff)].copy()


def read_market_excel_csv(path: str | Path, as_of_date: str | None = None) -> "pd.DataFrame":
    csv_path = Path(path)
    df = _read_csv_any_encoding(csv_path)
    df = normalize_date_column(df)
    return filter_by_cutoff(df, as_of_date or os.getenv("MARKET_AS_OF_DATE", ""))


def load_market_excel_csvs(
    as_of_date: str | None = None,
    market_excel_dir: str | Path | None = None,
    *,
    recursive: bool = True,
) -> dict[str, "pd.DataFrame"]:
    root = Path(market_excel_dir) if market_excel_dir else market_excel_dir_func()
    if not root.exists() or not root.is_dir():
        return {}
    pattern = "**/*.csv" if recursive else "*.csv"
    loaded: dict[str, pd.DataFrame] = {}
    for path in sorted(root.glob(pattern)):
        if not path.is_file():
            continue
        try:
            key = path.relative_to(root).as_posix()
        except Exception:
            key = path.name
        try:
            loaded[key] = read_market_excel_csv(path, as_of_date=as_of_date)
        except Exception as exc:
            loaded[key] = pd.DataFrame({"load_error": [str(exc)], "source_file": [str(path)]})
    return loaded


def market_excel_dir_func() -> Path:
    # Compatibility helper so older code can monkeypatch/load by name if needed.
    return market_excel_dir()


def summarize_market_excel_csv_dates(
    as_of_date: str | None = None,
    market_excel_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    root = Path(market_excel_dir) if market_excel_dir else market_excel_dir_func()
    if not root.exists() or not root.is_dir():
        return []

    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/*.csv")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        try:
            raw = _read_csv_any_encoding(path)
            detected = detect_date_column(raw)
            filtered = filter_by_cutoff(raw, as_of_date or os.getenv("MARKET_AS_OF_DATE", ""))
            if detected:
                parsed = pd.to_datetime(raw[detected], errors="coerce")
                min_date = parsed.min()
                max_date = parsed.max()
                min_text = "" if pd.isna(min_date) else pd.Timestamp(min_date).strftime("%Y-%m-%d")
                max_text = "" if pd.isna(max_date) else pd.Timestamp(max_date).strftime("%Y-%m-%d")
            else:
                min_text = max_text = ""
            rows.append({
                "file": rel,
                "rows": int(len(raw)),
                "filtered_rows": int(len(filtered)),
                "date_column": detected or "",
                "min_date": min_text,
                "max_date": max_text,
                "status": "OK" if detected else "NO_DATE_COLUMN",
            })
        except Exception as exc:
            rows.append({
                "file": rel,
                "rows": 0,
                "filtered_rows": 0,
                "date_column": "",
                "min_date": "",
                "max_date": "",
                "status": f"ERROR: {exc}",
            })
    return rows

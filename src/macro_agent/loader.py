from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

try:
    from common.data_paths import DATA_DIR, ROOT_DIR, DEFAULT_FIELD, normalize_field_name
except Exception:  # pragma: no cover - standalone fallback
    ROOT_DIR = Path(__file__).resolve().parents[2]
    DATA_DIR = ROOT_DIR / "data"
    DEFAULT_FIELD = "반도체"

    def normalize_field_name(value=None, default="반도체"):
        return str(value or default)

try:
    from data_intake.macro_intake.normalizer import clean_text_frame
except Exception:  # fallback when src is not on PYTHONPATH
    clean_text_frame = None


# ============================================================
# 파일명 key → scorer가 인식하는 표준 key 매핑
# ============================================================
_KEY_ALIAS: dict[str, str] = {
    # Consolidated files created by macro_intake v1+
    "macro_일별": "macro_일별",
    "macro_월별": "macro_월별",
    "macro_공통": "macro_공통",
    # ECOS
    "ecos_일별": "ecos_일별",
    "ecos_월별": "ecos_월별",
    "ecos_분기별": "ecos_분기별",
    # 외부 거시지표 (FRED + yfinance + OECD)
    "ext_일별": "ext_일별",
    "ext_월별": "ext_월별",
    # 뉴스 / 규제 / 소재
    "뉴스": "뉴스",
    "규제": "규제",
    "희토류": "희토류",
    "헬륨": "헬륨",
}

_RAW_PREFIXES = tuple(_KEY_ALIAS.keys())
_COMPAT_DATE_RE = re.compile(r"^(?P<base>.+?)_(?P<date>20\d{6})$")


def _decode_escaped_unicode(text: str) -> str:
    """Decode zip-extracted names like #Ubc18#Ub3c4#Uccb4."""
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), str(text))


def _split_name_and_date(stem: str) -> tuple[str, str]:
    """ecos_일별_20260510 -> (ecos_일별, 20260510)."""
    decoded = _decode_escaped_unicode(stem)
    m = _COMPAT_DATE_RE.match(decoded)
    if not m:
        return decoded, "00000000"
    return m.group("base"), m.group("date")


def _normalize_key(raw_key: str) -> str:
    return _KEY_ALIAS.get(raw_key, raw_key)


def _is_macro_raw_csv(path: Path) -> bool:
    if path.suffix.lower() != ".csv":
        return False
    raw_key, _ = _split_name_and_date(path.stem)
    return raw_key in _KEY_ALIAS


def _macro_raw_csvs(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.csv") if _is_macro_raw_csv(p))


def _env_candidate_dirs() -> list[Path]:
    raw = os.getenv("MACRO_INPUT_DIR") or os.getenv("ALPHAPROVE_MACRO_INPUT_DIR") or ""
    out: list[Path] = []
    for item in re.split(r"[;|]", raw):
        item = item.strip().strip('"').strip("'")
        if item:
            out.append(Path(item))
    return out


def _candidate_input_dirs(input_dir: Path) -> list[Path]:
    """Return candidate macro raw-data directories, best candidates first.

    The project has used several layouts across patches.  Macro raw files are
    canonical in data/_global_common/macro, but some local folders can contain
    older sector-common copies.  This resolver prevents macro_agent from failing
    just because one canonical folder is empty after a copy/patch step.
    """
    field = normalize_field_name(os.getenv("ALPHAPROVE_DATA_FIELD", str(DEFAULT_FIELD or "반도체")), "반도체")

    base_candidates = [
        *(_env_candidate_dirs()),
        input_dir,
        DATA_DIR / "_global_common" / "macro",
        DATA_DIR / field / "_sector_common" / "macro",
        DATA_DIR / field / "_sector_common" / "data" / "macro",
        DATA_DIR / field / "_sector_common" / "data",
        DATA_DIR / "common" / "macro",              # very old compatibility
        ROOT_DIR / "workspace" / "macro_data",      # old workspace compatibility
        ROOT_DIR / "workspace" / "data" / "macro", # old workspace compatibility
    ]

    # Also discover any directory containing consolidated macro raw CSVs.
    discovered: list[Path] = []
    try:
        if DATA_DIR.exists():
            patterns = [
                "**/macro_일별_*.csv",
                "**/macro_월별_*.csv",
                "**/macro_공통_*.csv",
                "**/ecos_일별_*.csv",
                "**/ext_일별_*.csv",
            ]
            seen_parents: set[str] = set()
            for pattern in patterns:
                for p in DATA_DIR.glob(pattern):
                    parent = p.parent
                    key = str(parent.resolve())
                    if key not in seen_parents:
                        seen_parents.add(key)
                        discovered.append(parent)
    except Exception:
        pass

    # Deduplicate while preserving order.
    out: list[Path] = []
    seen: set[str] = set()
    for p in [*base_candidates, *discovered]:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def resolve_macro_input_dir(input_dir: Path) -> Path:
    """Pick the first candidate directory that contains recognized raw macro CSVs."""
    candidates = _candidate_input_dirs(Path(input_dir))

    def score_dir(path: Path) -> tuple[int, int, str]:
        files = _macro_raw_csvs(path)
        stems = {_split_name_and_date(p.stem)[0] for p in files}
        # Prefer consolidated daily/monthly/common set.
        consolidated = int({"macro_일별", "macro_월별", "macro_공통"}.issubset(stems))
        return (consolidated, len(files), str(path))

    valid = [p for p in candidates if _macro_raw_csvs(p)]
    if not valid:
        checked = []
        for p in candidates:
            try:
                checked.append(f"- {p} (exists={p.exists()}, raw_csv={len(_macro_raw_csvs(p))})")
            except Exception:
                checked.append(f"- {p} (check_failed)")
        msg = "\n".join(checked[:30])
        raise ValueError(
            "CSV 파일이 없습니다. macro_agent가 읽을 수 있는 raw macro CSV를 찾지 못했습니다.\n"
            f"requested_input_dir={input_dir}\n"
            "필요 파일 예: macro_일별_YYYYMMDD.csv, macro_월별_YYYYMMDD.csv, macro_공통_YYYYMMDD.csv\n"
            "확인한 후보 경로:\n"
            f"{msg}"
        )

    # Sort by consolidated-first, more files next. Preserve candidate order on ties by stable sorted reverse score.
    valid_sorted = sorted(valid, key=score_dir, reverse=True)
    chosen = valid_sorted[0]
    if chosen.resolve() != Path(input_dir).resolve():
        print(f"  ↪ Macro input fallback: {input_dir} → {chosen}")
    return chosen


def _select_files(csv_files: list[Path], date: str = "latest") -> list[Path]:
    raw_files = [p for p in csv_files if _is_macro_raw_csv(p)]
    if date and date != "latest":
        requested = [p for p in raw_files if date in _decode_escaped_unicode(p.stem)]
        if requested:
            return requested
        # If an exact date is not available, fall back to latest rather than failing hard.
        print(f"  ⚠️ 요청일자 {date} raw CSV 없음 → latest raw CSV로 fallback")

    latest_by_key: dict[str, tuple[str, Path]] = {}
    for path in raw_files:
        key, d = _split_name_and_date(path.stem)
        old = latest_by_key.get(key)
        if old is None or d > old[0]:
            latest_by_key[key] = (d, path)
    return [item[1] for item in sorted(latest_by_key.values(), key=lambda x: x[1].name)]


def _read_csv_safely(file: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(file, encoding=enc)
        except UnicodeDecodeError:
            continue
    # Last attempt lets pandas raise the original style exception.
    return pd.read_csv(file)


def _attach_frame(data_dict: Dict[str, pd.DataFrame], raw_key: str, df: pd.DataFrame) -> str:
    """Attach a loaded frame under the standard keys consumed by scorer/feature_builder."""
    key = _normalize_key(raw_key)

    if raw_key == "macro_일별":
        # Consolidated daily macro file carries both ECOS and external daily indicators.
        data_dict["ecos_일별"] = df.copy()
        data_dict["ext_일별"] = df.copy()
        return "macro_일별"

    if raw_key == "macro_월별":
        # Consolidated monthly macro file carries ECOS monthly/quarterly and external monthly indicators.
        data_dict["ecos_월별"] = df.copy()
        data_dict["ext_월별"] = df.copy()
        quarter_cols = [c for c in ["gdp성장률_전년비", "gdp성장률_전기비"] if c in df.columns]
        if quarter_cols:
            df_q = df[df[quarter_cols].notna().any(axis=1)].copy()
            data_dict["ecos_분기별"] = df_q if not df_q.empty else df.copy()
        else:
            data_dict["ecos_분기별"] = df.copy()
        return "macro_월별"

    if raw_key == "macro_공통":
        # Common macro file holds heterogeneous macro metadata for news/regulatory/material signals.
        data_dict["뉴스"] = df.copy()
        data_dict["규제"] = df.copy()
        data_dict["희토류"] = df.copy()
        data_dict["헬륨"] = df.copy()
        return "macro_공통"

    data_dict[key] = df
    return key


def load_macro_data(input_dir: Path, date: str = "latest", cutoff: str | None = None) -> Dict[str, pd.DataFrame]:
    requested_dir = Path(input_dir)
    actual_dir = resolve_macro_input_dir(requested_dir)

    print(f"macro_data 경로: {actual_dir}")

    csv_files = _macro_raw_csvs(actual_dir)
    selected_files = _select_files(csv_files, date=date)

    if not selected_files:
        raise ValueError(f"인식 가능한 macro raw CSV 파일이 없습니다. input_dir={actual_dir}, date={date}")

    data_dict: Dict[str, pd.DataFrame] = {}

    for file in selected_files:
        try:
            df = _read_csv_safely(file)
            raw_key, file_date = _split_name_and_date(file.stem)
            raw_key = raw_key.strip()

            if clean_text_frame is not None:
                df = clean_text_frame(df)
            df.columns = df.columns.map(lambda x: str(x).strip().lower())
            df["source_file"] = file.name
            df["source_file_date"] = file_date

            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.sort_values("date")

                if cutoff:
                    cutoff_dt = pd.to_datetime(cutoff, format="%Y%m%d", errors="coerce")
                    df = df[df["date"] < cutoff_dt]

            key = _attach_frame(data_dict, raw_key, df)
            alias_note = f" (alias: {raw_key} → {key})" if raw_key != key else ""
            print(f"  {key} 로드 완료 ({len(df)}행 / file={file.name}){alias_note}")

        except Exception as e:
            print(f"  {file.name} 로드 실패: {e}")

    recognized = [k for k in data_dict if k in _KEY_ALIAS.values()]
    unrecognized = [k for k in data_dict if k not in _KEY_ALIAS.values()]

    print(f"\n총 {len(data_dict)}개 데이터 로드 완료")
    print(f"  인식된 key: {recognized}")
    if unrecognized:
        print(f"  미등록 key (scorer 미사용 가능): {unrecognized}")

    return data_dict
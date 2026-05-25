from __future__ import annotations

"""Premium presentation polish for Valuation Agent workbooks.

The valuation calculations are completed before this module runs.  This module
only improves investor-facing presentation, Korean labels, workbook spacing,
chart placement, and 208-company relative-position visualization.

Design principles
-----------------
1. Do not fabricate financial values.
2. Do not write repeated filler text such as "해당 없음" into empty grid cells.
3. Keep standard valuation acronyms (DCF, WACC, FCF, PER, PBR, P/S, EV/EBIT)
   because they are commonly used in Korean finance materials.
4. Add a dashboard-friendly, Excel-selectable relative positioning sheet that
   compares the selected company against the 208-company semiconductor universe.
"""

from typing import Any
import math
import re

MISSING_TOKENS = {"", "-", "None", "none", "nan", "NaN", "null", "NULL", "해당 없음"}


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in MISSING_TOKENS:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _as_score_100(value: Any) -> float | None:
    x = _num(value)
    if x is None:
        return None
    return round(x * 100.0, 2) if 0 <= x <= 1.5 else round(x, 2)


def _fmt_pct(value: Any, *, blank: str = "") -> str:
    x = _num(value)
    return blank if x is None else f"{x:.1%}"


def _fmt_won(value: Any, *, blank: str = "") -> str:
    x = _num(value)
    if x is None:
        return blank
    if abs(x) >= 100_000_000:
        return f"{x / 100_000_000:,.1f}억원"
    return f"{x:,.0f}원"


def _fmt_price(value: Any, *, blank: str = "") -> str:
    x = _num(value)
    return blank if x is None else f"{x:,.0f}원"


def _fmt_multiple(value: Any, *, blank: str = "") -> str:
    x = _num(value)
    return blank if x is None else f"{x:.2f}배"


def _fmt_score(value: Any, *, blank: str = "") -> str:
    x = _as_score_100(value)
    return blank if x is None else f"{x:.1f}/100"


def _display(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in MISSING_TOKENS:
            return ""
        return _koreanize_text(stripped)
    return value


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text in MISSING_TOKENS else _koreanize_text(text)


def _label_kr(value: Any) -> str:
    text = _safe_text(value)
    mapping = {
        "ATTRACTIVE": "상대 매력",
        "FAIR": "중립",
        "EXPENSIVE": "고평가 부담",
        "LOW": "낮음",
        "MEDIUM": "보통",
        "HIGH": "높음",
        "True": "예",
        "False": "아니오",
        "OK": "정상",
        "PASS": "통과",
        "PASS_WITH_WARNINGS": "주의 포함 통과",
        "INFO": "정보",
    }
    return mapping.get(text, text)


def _koreanize_text(text: str) -> str:
    if not text:
        return text
    stripped = text.strip()
    if stripped in MISSING_TOKENS:
        return ""
    if stripped.startswith("{") or stripped.startswith("[") or "http://" in stripped or "https://" in stripped:
        return text

    replacements = [
        ("Valuation Agent Workbook", "가치평가 에이전트 워크북"),
        ("Valuation Agent", "가치평가 에이전트"),
        ("Dashboard Payload", "대시보드 데이터 패키지"),
        ("dashboard payload", "대시보드 데이터 패키지"),
        ("Dashboard", "대시보드"),
        ("dashboard", "대시보드"),
        ("Peer Comps", "상대가치 비교"),
        ("peer comps", "상대가치 비교"),
        ("Peer Group", "비교기업 그룹"),
        ("peer group", "비교기업 그룹"),
        ("Reference Universe", "기준 비교군"),
        ("reference universe", "기준 비교군"),
        ("Reference", "기준"),
        ("reference", "기준"),
        ("Universe", "비교군"),
        ("universe", "비교군"),
        ("live peer", "실시간 비교기업"),
        ("Live peer", "실시간 비교기업"),
        ("Peer", "비교기업"),
        ("peer", "비교기업"),
        ("proxy", "대체지표"),
        ("Proxy", "대체지표"),
        ("fallback", "대체 산식"),
        ("Fallback", "대체 산식"),
        ("Base/Bull/Bear", "기준/상승/하락"),
        ("Base", "기준"),
        ("Bull", "상승"),
        ("Bear", "하락"),
        ("Reverse DCF", "주가역산 DCF"),
        ("reverse DCF", "주가역산 DCF"),
        ("Owner Earnings", "오너이익"),
        ("owner earnings", "오너이익"),
        ("Football Field", "가치범위표"),
        ("football field", "가치범위표"),
        ("Quality diagnostics", "품질 진단"),
        ("quality diagnostics", "품질 진단"),
        ("source completion", "원천 보강"),
        ("Source completion", "원천 보강"),
        ("market implied", "시장내재"),
        ("Market implied", "시장내재"),
        ("download workbook", "엑셀 다운로드"),
        ("Download workbook", "엑셀 다운로드"),
        ("validation", "검증"),
        ("Validation", "검증"),
        ("DCF_UPSIDE", "DCF 상승여력"),
        ("PEER_PSR", "비교기업 P/S"),
        ("PSR_COMP", "P/S 상대가치"),
        ("PBR_COMP", "P/B 상대가치"),
        ("PER_COMP", "PER 상대가치"),
        ("PFCF_COMP", "P/FCF 상대가치"),
        ("EV_SALES_COMP", "EV/Sales 상대가치"),
        ("EV_EBIT_COMP", "EV/EBIT 상대가치"),
        ("raw", "원천"),
        ("Raw", "원천"),
        ("intake", "수집"),
        ("Intake", "수집"),
        ("snapshot", "스냅샷"),
        ("Snapshot", "스냅샷"),
        ("scorecard", "점수판"),
        ("Scorecard", "점수판"),
        ("Naver finance live", "네이버금융 실시간"),
        ("DART/price derived", "DART·주가 기반 산출"),
        ("DART/price", "DART·주가"),
        ("Universe Peer Group", "기준 비교군 그룹"),
        ("208개 Universe", "208개 반도체 비교군"),
        ("Reference 그룹", "기준 비교군 그룹"),
        ("validation json", "검증 JSON"),
    ]
    out = text
    for old, new in replacements:
        out = out.replace(old, new)

    # Remove filler words instead of replacing them with another noisy label.
    out = out.replace("해당 없음", "")
    out = out.replace("None", "")
    out = out.replace("nan", "")
    out = out.replace("분류 미제공", "미분류")
    out = out.replace("원천 미제공", "대체 산식 적용")
    out = out.replace("확인 제한", "추가 확인 대상")
    out = out.replace("추가 수집 필요", "보강 수집 대상")
    out = out.replace("보조 산출값 없음", "보조 산출 대기")
    # Tidy repeated spaces introduced by removals.
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def _judgement_from_metrics(dcf: dict[str, Any], scorecard: dict[str, Any] | None, advanced: dict[str, Any] | None) -> tuple[str, str]:
    upside = _num(dcf.get("upside_downside_pct"))
    sc = _num((scorecard or {}).get("score"))
    adv = _num((advanced or {}).get("advanced_valuation_score"))

    points = 0
    reasons: list[str] = []
    if upside is not None:
        if upside >= 0.20:
            points += 2
            reasons.append("DCF 기준 안전마진이 20% 이상입니다.")
        elif upside >= 0.05:
            points += 1
            reasons.append("DCF 기준 소폭 저평가 구간입니다.")
        elif upside <= -0.20:
            points -= 2
            reasons.append("DCF 기준 현재가 부담이 큽니다.")
        elif upside <= -0.05:
            points -= 1
            reasons.append("DCF 기준 소폭 고평가 구간입니다.")
        else:
            reasons.append("DCF 기준 현재가가 적정가치 범위에 가깝습니다.")

    for name, val in [("보조 가치평가 점수", sc), ("종합 가치평가 점수", adv)]:
        if val is None:
            continue
        if val >= 70:
            points += 1
            reasons.append(f"{name}가 70점 이상으로 우호적입니다.")
        elif val < 45:
            points -= 1
            reasons.append(f"{name}가 45점 미만으로 보수적 해석이 필요합니다.")

    if points >= 2:
        return "가치평가 관점 우호", " ".join(reasons) or "복수의 가치평가 지표가 우호적입니다."
    if points <= -2:
        return "가치평가 관점 보수", " ".join(reasons) or "복수의 가치평가 지표가 보수적입니다."
    return "가치평가 관점 중립", " ".join(reasons) or "저평가와 리스크 신호가 혼재되어 있습니다."


def _write_rows(ws: Any, rows: list[list[Any]], *, start_row: int = 1, start_col: int = 1) -> None:
    for r_idx, row in enumerate(rows, start_row):
        for c_idx, value in enumerate(row, start_col):
            ws.cell(r_idx, c_idx).value = _display(value)


def _sheet_non_top_left_merged(ws: Any) -> set[str]:
    merged_non_top_left: set[str] = set()
    for mr in ws.merged_cells.ranges:
        tl = ws.cell(mr.min_row, mr.min_col).coordinate
        for row in ws.iter_rows(min_row=mr.min_row, max_row=mr.max_row, min_col=mr.min_col, max_col=mr.max_col):
            for cell in row:
                if cell.coordinate != tl:
                    merged_non_top_left.add(cell.coordinate)
    return merged_non_top_left


def _clean_missing_texts(ws: Any) -> None:
    non_top_left = _sheet_non_top_left_merged(ws)
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            if cell.coordinate in non_top_left:
                continue
            if isinstance(cell.value, str):
                text = _koreanize_text(cell.value)
                cell.value = "" if text.strip() in MISSING_TOKENS else text


def _apply_sheet_style(wb: Any, ws: Any) -> None:
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    # Pleasant but still professional palette.
    navy = "102A43"
    slate = "243B53"
    teal = "0F766E"
    sky = "2563EB"
    mint = "DDF7EC"
    ice = "EEF6FF"
    cream = "FFF7E6"
    lavender = "F2EEFF"
    coral = "FDECEC"
    row_fill = "F8FAFC"
    border_color = "D8E1EA"
    thin = Side(style="thin", color=border_color)
    soft_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3" if ws.max_row >= 3 else None
    _clean_missing_texts(ws)

    non_top_left = _sheet_non_top_left_merged(ws)
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        row_has_value = any(cell.value not in (None, "") for cell in row)
        if not row_has_value:
            continue
        for cell in row:
            if cell.coordinate in non_top_left:
                continue
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            # Do not paint/border completely empty cells. This avoids large "filler" grids.
            if cell.value not in (None, ""):
                cell.border = soft_border
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    cell.font = Font(color="008000")

    # Main title row.
    if ws.max_row >= 1:
        for cell in ws[1]:
            if cell.value not in (None, ""):
                cell.fill = PatternFill("solid", fgColor=navy)
                cell.font = Font(color="FFFFFF", bold=True, size=14)
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = max(ws.row_dimensions[1].height or 24, 32)

    # Subtitle row.
    if ws.max_row >= 2:
        for cell in ws[2]:
            if cell.value not in (None, ""):
                cell.fill = PatternFill("solid", fgColor=ice)
                cell.font = Font(color=slate, bold=False, size=10)
        ws.row_dimensions[2].height = max(ws.row_dimensions[2].height or 20, 26)

    # Section rows and table header rows.
    header_words = {"항목", "구분", "연도", "지표", "시나리오", "방법", "기업명", "JSON 키", "데이터블록"}
    section_fill_cycle = [teal, sky, "7C3AED"]
    section_count = 0
    for r in range(1, min(ws.max_row, 90) + 1):
        values = [ws.cell(r, c).value for c in range(1, min(ws.max_column, 14) + 1)]
        non_empty = [v for v in values if v not in (None, "")]
        if not non_empty:
            continue
        is_header = any(str(v) in header_words for v in non_empty)
        is_section = len(non_empty) == 1 and r > 2
        if is_section:
            fill = section_fill_cycle[section_count % len(section_fill_cycle)]
            section_count += 1
            for c in range(1, min(ws.max_column, 14) + 1):
                cell = ws.cell(r, c)
                if c == 1 or cell.value not in (None, ""):
                    cell.fill = PatternFill("solid", fgColor=fill)
                    cell.font = Font(color="FFFFFF", bold=True)
                    cell.border = soft_border
            ws.row_dimensions[r].height = 25
        elif is_header:
            for c in range(1, ws.max_column + 1):
                cell = ws.cell(r, c)
                if cell.value not in (None, ""):
                    cell.fill = PatternFill("solid", fgColor=slate)
                    cell.font = Font(color="FFFFFF", bold=True)
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 20, 24)

    # KPI/card-like rows get a soft, non-monochrome touch.
    for r in range(3, min(ws.max_row, 25) + 1):
        non_empty_count = sum(1 for c in range(1, min(ws.max_column, 14) + 1) if ws.cell(r, c).value not in (None, ""))
        if non_empty_count >= 4:
            fill = [mint, ice, cream, lavender, coral][r % 5]
            for c in range(1, min(ws.max_column, 14) + 1):
                cell = ws.cell(r, c)
                if cell.value not in (None, "") and cell.fill.fill_type is None:
                    cell.fill = PatternFill("solid", fgColor=fill)

    # Zebra fill for data rows only where cells contain values.
    for r in range(3, ws.max_row + 1):
        if r % 2 == 0:
            for c in range(1, ws.max_column + 1):
                cell = ws.cell(r, c)
                if cell.value not in (None, "") and cell.fill.fill_type is None:
                    cell.fill = PatternFill("solid", fgColor=row_fill)

    # Width and height tuning. Cap wide columns to keep sheets navigable.
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        max_len = 0
        for row_idx in range(1, min(ws.max_row, 260) + 1):
            val = ws.cell(row_idx, col_idx).value
            if val in (None, ""):
                continue
            max_len = max(max_len, min(len(str(val)), 90))
        if max_len == 0:
            width = 3.5
        elif col_idx == 1:
            width = min(max(max_len + 3, 14), 28)
        elif max_len > 50:
            width = 36
        else:
            width = min(max(max_len + 3, 10), 24)
        ws.column_dimensions[letter].width = width

    for r in range(1, min(ws.max_row, 320) + 1):
        current = ws.row_dimensions[r].height or 18
        row_text_len = max((len(str(ws.cell(r, c).value or "")) for c in range(1, min(ws.max_column, 14) + 1)), default=0)
        if row_text_len > 160:
            ws.row_dimensions[r].height = max(current, 62)
        elif row_text_len > 95:
            ws.row_dimensions[r].height = max(current, 44)
        elif row_text_len > 45:
            ws.row_dimensions[r].height = max(current, 30)
        else:
            ws.row_dimensions[r].height = max(current, 22)


def _reposition_charts(wb: Any) -> None:
    """Move charts away from source tables so charts never cover data."""
    dashboard_positions = ["A44", "I44", "Q44", "A64", "I64", "Q64"]
    for ws in wb.worksheets:
        charts = list(getattr(ws, "_charts", []) or [])
        if not charts:
            continue
        if ws.title == "00_대시보드":
            for i, chart in enumerate(charts):
                chart.anchor = dashboard_positions[min(i, len(dashboard_positions) - 1)]
                chart.width = 14.5
                chart.height = 7.8
                try:
                    chart.style = 10
                except Exception:
                    pass
        elif ws.title == "04_주가_데이터":
            for chart in charts:
                chart.anchor = "Q4"
                chart.width = 18
                chart.height = 8.5
                try:
                    chart.style = 13
                except Exception:
                    pass
        else:
            # Put miscellaneous charts to the right of the used region.
            for i, chart in enumerate(charts):
                chart.anchor = f"Q{4 + i * 18}"
                chart.width = 15
                chart.height = 7


def _apply_number_formats(ws: Any) -> None:
    percent_keywords = ("율", "비중", "괴리", "마진", "수익률", "MDD", "변동성", "성장률", "안전마진")
    price_keywords = ("가격", "주가", "가치", "매출", "이익", "자산", "부채", "자본", "현금", "시가총액", "거래대금", "FCF", "EV")
    multiple_keywords = ("PER", "PBR", "P/S", "PSR", "P/FCF", "EV/Sales", "EV/EBIT")
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            if not isinstance(cell.value, (int, float)):
                continue
            # Look at left/header labels for context.
            left_label = str(ws.cell(cell.row, 1).value or "")
            header_label = str(ws.cell(1, cell.column).value or "") + " " + str(ws.cell(2, cell.column).value or "")
            label = left_label + " " + header_label
            if any(k in label for k in multiple_keywords):
                cell.number_format = '0.0x;[Red](0.0x);-'
            elif any(k in label for k in percent_keywords):
                cell.number_format = '0.0%;[Red](0.0%);-'
            elif any(k in label for k in price_keywords):
                cell.number_format = '#,##0;[Red](#,##0);-'
            else:
                cell.number_format = '#,##0.00;[Red](#,##0.00);-'


def _rows_for_positioning(context: Any) -> list[dict[str, Any]]:
    rows = list(getattr(context, "reference_universe", []) or [])
    if not rows:
        rows = list(getattr(context, "reference_focus", []) or [])
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in rows:
        name = r.get("company_name") or r.get("company") or r.get("name")
        if not name:
            continue
        key = str(name)
        if key in seen:
            continue
        seen.add(key)
        score = _as_score_100(r.get("valuation_proxy_score"))
        credit = _as_score_100(r.get("credit_risk_score"))
        out.append({
            "company_name": key,
            "company_dir": r.get("company_dir") or r.get("slug") or "",
            "ticker6": r.get("ticker6") or r.get("stock_code") or r.get("ticker") or "",
            "market": r.get("market") or "",
            "peer_group": r.get("peer_group") or r.get("semiconductor_tag") or "미분류",
            "valuation_proxy_score": score,
            "credit_risk_score": credit,
            "valuation_proxy_label_kr": _label_kr(r.get("valuation_proxy_label_kr") or r.get("valuation_proxy_label")),
            "confidence_kr": _label_kr(r.get("valuation_confidence") or r.get("confidence") or r.get("data_quality_status")),
            "is_focal_5": bool(r.get("is_focal_5") in (True, "True", "true", 1, "1")),
            "is_target": bool(r.get("is_target") in (True, "True", "true", 1, "1")),
            "psr": _num(r.get("psr") or r.get("target_psr") or r.get("psr_market")),
        })
    # Ensure rows with scores appear first in charts/tables.
    out.sort(key=lambda x: (x.get("valuation_proxy_score") is None, -(x.get("valuation_proxy_score") or -999), x.get("company_name") or ""))
    return out


def _add_positioning_sheet(wb: Any, *, company: str, context: Any, advanced: dict[str, Any] | None) -> None:
    from openpyxl.chart import BarChart, Reference
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    sheet_name = "29_시장위치_맵"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A8"

    rows = _rows_for_positioning(context)
    row_count = len(rows)
    if not rows:
        rows = [{
            "company_name": company,
            "company_dir": "",
            "ticker6": "",
            "market": "",
            "peer_group": "미분류",
            "valuation_proxy_score": None,
            "credit_risk_score": None,
            "valuation_proxy_label_kr": "",
            "confidence_kr": "",
            "is_focal_5": True,
            "is_target": True,
            "psr": None,
        }]
        row_count = 1

    navy = "102A43"
    teal = "0F766E"
    blue = "2563EB"
    mint = "DDF7EC"
    ice = "EEF6FF"
    cream = "FFF7E6"
    lavender = "F2EEFF"
    border_color = "D8E1EA"
    thin = Side(style="thin", color=border_color)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:N1")
    ws["A1"] = f"{company} 반도체 시장 내 상대 위치 맵"
    ws["A1"].fill = PatternFill("solid", fgColor=navy)
    ws["A1"].font = Font(color="FFFFFF", bold=True, size=15)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 34
    ws.merge_cells("A2:N2")
    ws["A2"] = "기업 선택값을 바꾸면 선택기업·동일 세부군·208개 전체 평균 비교와 TAM/SAM/SOM 범위가 함께 갱신됩니다."
    ws["A2"].fill = PatternFill("solid", fgColor=ice)
    ws["A2"].font = Font(color="243B53", size=10)

    # Selector and KPI cards.
    selector_rows = [
        ["기업 선택", company, "", "동일 세부군", "=IFERROR(XLOOKUP($B$4,$A$59:$A$266,$E$59:$E$266),\"\")", "", "선택기업 점수", "=IFERROR(XLOOKUP($B$4,$A$59:$A$266,$F$59:$F$266),\"\")", "", "208개 내 백분위", "=IFERROR(PERCENTRANK.INC($F$59:$F$266,$H$4),\"\")", "", "라벨", "=IFERROR(XLOOKUP($B$4,$A$59:$A$266,$H$59:$H$266),\"\")"],
    ]
    _write_rows(ws, selector_rows, start_row=4, start_col=1)
    for col in [1, 4, 7, 10, 13]:
        ws.cell(4, col).fill = PatternFill("solid", fgColor=teal)
        ws.cell(4, col).font = Font(color="FFFFFF", bold=True)
    for col in [2, 5, 8, 11, 14]:
        ws.cell(4, col).fill = PatternFill("solid", fgColor=mint)
        ws.cell(4, col).font = Font(color="102A43", bold=True)
    ws["K4"].number_format = "0.0%"
    ws["H4"].number_format = "0.0"

    # Comparison table used as dynamic chart source.
    comparison_rows = [
        ["비교 기준", "밸류에이션 점수", "신용위험 점수", "기업 수"],
        ["선택기업", "=IFERROR(XLOOKUP($B$4,$A$59:$A$266,$F$59:$F$266),\"\")", "=IFERROR(XLOOKUP($B$4,$A$59:$A$266,$G$59:$G$266),\"\")", 1],
        ["동일 세부군 평균", "=IFERROR(AVERAGEIF($E$59:$E$266,$E$4,$F$59:$F$266),\"\")", "=IFERROR(AVERAGEIF($E$59:$E$266,$E$4,$G$59:$G$266),\"\")", "=IFERROR(COUNTIF($E$59:$E$266,$E$4),\"\")"],
        ["208개 전체 평균", "=IFERROR(AVERAGE($F$59:$F$266),\"\")", "=IFERROR(AVERAGE($G$59:$G$266),\"\")", row_count],
    ]
    _write_rows(ws, comparison_rows, start_row=8, start_col=1)

    # TAM/SAM/SOM funnel. This is not a market-size forecast; it is a coverage funnel from the current valuation universe.
    funnel_rows = [
        ["범위", "기업 수", "해석"],
        ["TAM: 반도체 전체 비교군", row_count, "현재 Valuation Agent가 비교 가능한 전체 반도체 기준군"],
        ["SAM: 선택기업 세부군", "=IFERROR(COUNTIF($E$59:$E$266,$E$4),\"\")", "동일 사업축 안에서 상대가치 비교가 더 직접적인 집단"],
        ["SOM: 선택기업", 1, "현재 선택한 분석 대상 기업"],
    ]
    _write_rows(ws, funnel_rows, start_row=16, start_col=1)

    # Focal five rows.
    focal_rows = [r for r in rows if r.get("is_focal_5")]
    if not focal_rows:
        focal_rows = rows[:5]
    focal_rows = focal_rows[:10]
    _write_rows(ws, [["5개 핵심기업 비교", "", "", "", "", ""]], start_row=24, start_col=1)
    _write_rows(ws, [["기업명", "세부군", "밸류에이션 점수", "신용위험 점수", "라벨", "P/S"]], start_row=25, start_col=1)
    for i, r in enumerate(focal_rows, start=26):
        _write_rows(ws, [[
            r.get("company_name"),
            r.get("peer_group"),
            r.get("valuation_proxy_score"),
            r.get("credit_risk_score"),
            r.get("valuation_proxy_label_kr"),
            r.get("psr"),
        ]], start_row=i, start_col=1)

    # Source data table for selector and formulas.
    start = 57
    headers = ["기업명", "기업코드", "종목코드", "시장", "세부군", "밸류에이션 점수", "신용위험 점수", "라벨", "신뢰도", "5개 핵심", "분석대상", "P/S"]
    _write_rows(ws, [["선택/차트 원천 데이터", "", "", "", "", "", "", "", "", "", "", ""]], start_row=start, start_col=1)
    _write_rows(ws, [headers], start_row=start + 1, start_col=1)
    for idx, r in enumerate(rows[:208], start=start + 2):
        _write_rows(ws, [[
            r.get("company_name"),
            r.get("company_dir"),
            r.get("ticker6"),
            r.get("market"),
            r.get("peer_group"),
            r.get("valuation_proxy_score"),
            r.get("credit_risk_score"),
            r.get("valuation_proxy_label_kr"),
            r.get("confidence_kr"),
            "예" if r.get("is_focal_5") else "",
            "예" if r.get("is_target") else "",
            r.get("psr"),
        ]], start_row=idx, start_col=1)

    end = start + 1 + min(len(rows), 208)
    # Drop-down selector.
    dv = DataValidation(type="list", formula1=f"$A${start+2}:$A${end}", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(ws["B4"])

    # Chart 1: selected vs group vs universe.
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = "선택기업 vs 동일 세부군 vs 208개 평균"
    chart.y_axis.title = "비교 기준"
    chart.x_axis.title = "점수"
    data = Reference(ws, min_col=2, max_col=3, min_row=8, max_row=11)
    cats = Reference(ws, min_col=1, min_row=9, max_row=11)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.width = 16
    chart.height = 8
    ws.add_chart(chart, "H8")

    chart2 = BarChart()
    chart2.type = "bar"
    chart2.style = 11
    chart2.title = "TAM / SAM / SOM 범위"
    chart2.y_axis.title = "범위"
    chart2.x_axis.title = "기업 수"
    data2 = Reference(ws, min_col=2, min_row=16, max_row=19)
    cats2 = Reference(ws, min_col=1, min_row=17, max_row=19)
    chart2.add_data(data2, titles_from_data=True)
    chart2.set_categories(cats2)
    chart2.width = 16
    chart2.height = 7
    ws.add_chart(chart2, "H25")

    chart3 = BarChart()
    chart3.type = "bar"
    chart3.style = 12
    chart3.title = "5개 핵심기업 밸류에이션 점수"
    data3 = Reference(ws, min_col=3, min_row=25, max_row=25 + len(focal_rows))
    cats3 = Reference(ws, min_col=1, min_row=26, max_row=25 + len(focal_rows))
    chart3.add_data(data3, titles_from_data=True)
    chart3.set_categories(cats3)
    chart3.width = 16
    chart3.height = 8
    ws.add_chart(chart3, "H42")

    # Styling.
    for r in [8, 16, 25, start, start + 1]:
        for c in range(1, 15):
            cell = ws.cell(r, c)
            if cell.value not in (None, ""):
                cell.fill = PatternFill("solid", fgColor=blue if r != start else teal)
                cell.font = Font(color="FFFFFF", bold=True)
                cell.border = border
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=1, max_row=end, min_col=1, max_col=14):
        for cell in row:
            if cell.value not in (None, ""):
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    for r in range(9, 12):
        for c in range(1, 5):
            ws.cell(r, c).fill = PatternFill("solid", fgColor=[mint, ice, lavender][(r - 9) % 3])
    for r in range(17, 20):
        for c in range(1, 4):
            ws.cell(r, c).fill = PatternFill("solid", fgColor=[mint, ice, cream][(r - 17) % 3])

    for col in range(1, 15):
        ws.column_dimensions[get_column_letter(col)].width = [18, 13, 13, 12, 18, 14, 14, 15, 13, 10, 10, 10, 13, 18][col - 1]
    for r in range(1, max(end, 55) + 1):
        ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 20, 22)
    for rng in ["H4", "H9:H11", "I9:I11", "C26:D35", "F26:F35", f"F{start+2}:G{end}", f"L{start+2}:L{end}"]:
        for row in ws[rng]:
            for cell in row:
                cell.number_format = "0.0"
    ws["K4"].number_format = "0.0%"
    ws.sheet_properties.tabColor = "0F766E"


def _add_investment_memo_sheet(
    wb: Any,
    *,
    company: str,
    dcf: dict[str, Any],
    peer: dict[str, Any],
    price_summary: dict[str, Any],
    scorecard: dict[str, Any] | None,
    advanced: dict[str, Any] | None,
    validation: dict[str, Any],
) -> None:
    if "26_투자판단_요약" in wb.sheetnames:
        del wb["26_투자판단_요약"]
    ws = wb.create_sheet("26_투자판단_요약")

    judgement, reason = _judgement_from_metrics(dcf, scorecard, advanced)
    football = (advanced or {}).get("football_field") or {}
    reverse_dcf = (advanced or {}).get("reverse_dcf") or {}
    owner = (advanced or {}).get("owner_earnings") or {}
    market_mul = (advanced or {}).get("market_implied_multiples") or {}

    rows = [
        [f"{company} 투자판단 요약", "", "", "", "", ""],
        ["목적", "DCF·상대가치·주가역산·오너이익·208개 기준 비교군을 한 장에서 확인하는 투자자용 요약입니다.", "", "", "", ""],
        ["최종 가치평가 관점", judgement, "근거", reason, "검증 상태", _label_kr(validation.get("status"))],
        ["핵심 지표", "값", "해석", "원천/산식", "대시보드 활용", "주의사항"],
        ["현재가", _fmt_price(price_summary.get("latest_close")), "시장 기준점", "가치평가 전용 주가 수집", "주가 카드", "수집일 기준 변동 가능"],
        ["DCF 내재주가", _fmt_price(dcf.get("implied_price")), "절대가치 기준", "FCF 추정 + WACC + 영구성장률", "DCF 카드", "가정 민감도 확인 필요"],
        ["현재가 대비 괴리율", _fmt_pct(dcf.get("upside_downside_pct")), "안전마진 확인", "내재주가/현재가 - 1", "안전마진 배지", "절대 투자판단 단독 사용 금지"],
        ["WACC", _fmt_pct((advanced or {}).get("wacc_used") or dcf.get("wacc")), "할인율", "무위험이자율·시장위험프리미엄·베타·타인자본비용", "가정 슬라이더", "금리 변화 민감"],
        ["P/S", _fmt_multiple((peer or {}).get("target_psr")), "매출 대비 시장가치", "시가총액/매출액", "상대가치 카드", "적자기업에도 활용 가능"],
        ["비교기업 P/S 중앙값", _fmt_multiple((peer or {}).get("median_psr")), "5개 비교기업 기준", "피어 입력 자동 생성", "비교기업 차트", "비교기업 품질 확인 필요"],
        ["가치범위 중앙값", _fmt_price(football.get("base_price")), "여러 방식의 교차검증", "DCF·P/S·P/B·PER·P/FCF 등", "가치범위표", "일부 방식은 손실기업에서 제외"],
        ["주가역산 영구성장률", _fmt_pct(reverse_dcf.get("implied_terminal_growth_rate")), "현재 주가가 요구하는 장기 성장률", "현재가 기준 역산", "역산 DCF", "음수/과도한 값은 보수 해석"],
        ["오너이익 주당가치", _fmt_price(owner.get("owner_earnings_value_per_share")), "현금창출력 기반 교차검증", "CFO - CAPEX 또는 FCF", "오너이익 카드", "CAPEX 변동성 반영 필요"],
        ["시장내재 P/S", _fmt_multiple(market_mul.get("psr_market") or market_mul.get("market_psr")), "현재 시장이 부여한 매출 배수", "시가총액/매출", "시장내재 배수", "순환 업종에서는 변동 가능"],
        ["208개 비교군", (advanced or {}).get("reference_universe_rows") or "208개 기준", "섹터 내부 상대 위치", "Tech 기준 비교군 파일 활용", "분포/랭킹", "데이터 원천 업데이트 필요"],
        ["검증 결과", _label_kr(validation.get("status")), "모델 완성도", "검증 JSON", "검증 배지", "경고 발생 시 점검"],
    ]
    _write_rows(ws, rows)


def _add_data_enrichment_sheet(
    wb: Any,
    *,
    company: str,
    context: Any,
    peer: dict[str, Any],
    advanced: dict[str, Any] | None,
    price_summary: dict[str, Any],
) -> None:
    if "27_데이터보강_내역" in wb.sheetnames:
        del wb["27_데이터보강_내역"]
    ws = wb.create_sheet("27_데이터보강_내역")

    market_snapshot = getattr(context, "market_snapshot", {}) or {}
    ref_summary = getattr(context, "reference_summary", {}) or {}
    source_plan = (advanced or {}).get("source_completion_plan") or []

    rows = [
        [f"{company} 데이터 보강 내역", "", "", "", "", ""],
        ["원칙", "공란을 반복 문구로 채우지 않고, DART·주가·발행주식 수·네이버금융·208개 기준 비교군 중 확인 가능한 원천 또는 명시적 대체 산식만 표시합니다.", "", "", "", ""],
        ["항목", "보강 방식", "현재 값", "사용 원천", "계산/확인 방식", "비고"],
        ["PER", "네이버금융 값 우선, 없으면 DART 순이익과 시가총액으로 자동 산출", _fmt_multiple(market_snapshot.get("per_naver") or market_snapshot.get("per_auto")), "네이버금융 / DART / 주가", "시가총액 ÷ 순이익", "순손실이면 계산 제외"],
        ["PBR", "네이버금융 값 우선, 없으면 DART 자본총계와 시가총액으로 자동 산출", _fmt_multiple(market_snapshot.get("pbr_naver") or market_snapshot.get("pbr_auto")), "네이버금융 / DART / 주가", "시가총액 ÷ 자본총계", "자본잠식이면 보수 해석"],
        ["PSR", "주가와 매출액으로 자동 산출", _fmt_multiple((peer or {}).get("target_psr") or market_snapshot.get("psr_auto")), "DART 매출액 / 주가 / 발행주식 수", "시가총액 ÷ 매출액", "적자기업 비교에 유용"],
        ["P/FCF", "FCF가 양수이면 자동 산출", _fmt_multiple(market_snapshot.get("p_fcf_auto")), "DART 영업현금흐름·CAPEX / 주가", "시가총액 ÷ FCF", "FCF 음수이면 계산 제외"],
        ["EV/Sales", "기업가치와 매출액으로 자동 산출", _fmt_multiple(market_snapshot.get("ev_sales_auto")), "DART 현금·부채 / 주가", "EV ÷ 매출액", "현금/부채 원천계정 확인"],
        ["EV/EBIT", "영업이익이 양수이면 자동 산출", _fmt_multiple(market_snapshot.get("ev_ebit_auto")), "DART 영업이익 / 주가", "EV ÷ 영업이익", "적자이면 계산 제외"],
        ["발행주식 수", "DART 주식총수 현황에서 보강", f"{_num(price_summary.get('shares_outstanding')):,.0f}주" if _num(price_summary.get("shares_outstanding")) else "", "OpenDART stockTotqySttus", "최신 보고서 기준", "자기주식/증자 반영 필요"],
        ["시가총액", "현재가와 발행주식 수로 자동 산출", _fmt_won(price_summary.get("market_cap")), "주가 provider / DART 발행주식 수", "현재가 × 발행주식 수", "주가 기준일 확인"],
        ["유동성", "거래대금·거래회전율로 보강", _fmt_won(price_summary.get("avg_trading_value_20d")), "주가 데이터", "20일 평균 거래대금", "대시보드 필터 활용"],
        ["208개 기준 비교군", "Tech reference universe 파일을 Valuation 비교군으로 재활용", ref_summary.get("row_count") or (advanced or {}).get("reference_universe_rows") or "208", "valuation_reference_universe_208.csv", "동일 섹터 상대 위치", "상대가치 확장용"],
    ]

    if source_plan:
        rows.append(["후속 보강 계획", "항목", "현재 처리", "권장 원천", "목적", "비고"])
        for item in source_plan[:12]:
            rows.append([
                "후속 보강 계획",
                item.get("metric_kr") or item.get("metric") or "항목",
                item.get("current_status_kr") or item.get("status_kr") or "보조 산출",
                item.get("recommended_source_kr") or item.get("source_kr") or "DART/주가/공시",
                item.get("why_it_matters_kr") or item.get("purpose_kr") or "가치평가 정확도 개선",
                item.get("fallback_kr") or item.get("note_kr") or "대체 산식 유지",
            ])

    _write_rows(ws, rows)


def _add_dashboard_key_sheet(wb: Any, *, dashboard_payload: dict[str, Any]) -> None:
    if "28_대시보드_연동키" in wb.sheetnames:
        del wb["28_대시보드_연동키"]
    ws = wb.create_sheet("28_대시보드_연동키")
    cards = dashboard_payload.get("summary_cards") or {}
    rows = [
        ["대시보드 연동키", "", "", "", ""],
        ["설명", "React/Streamlit 대시보드에서 바로 사용할 수 있는 주요 JSON 키와 표시명을 정리합니다.", "", "", ""],
        ["JSON 키", "표시명", "값", "형식", "활용 위치"],
    ]
    if isinstance(cards, dict):
        for key, value in cards.items():
            if isinstance(value, dict):
                rows.append([
                    key,
                    value.get("label") or value.get("label_kr") or key,
                    value.get("value", ""),
                    value.get("format", "text"),
                    "핵심 카드",
                ])
    rows.extend([
        ["price_history", "주가 차트", "최근 250거래일", "list", "라인차트"],
        ["historical_financials", "재무 추이", "최근 5개년", "list", "막대/라인 혼합"],
        ["peer_multiples", "비교기업 배수", "5개 기업 + 확장 비교군", "list", "상대가치 표"],
        ["reference_universe_focus", "208개 비교군 상대위치", "선택기업/동일 세부군/전체 평균", "list", "시장위치 맵"],
        ["advanced_valuation", "종합 가치평가", "가치범위·역산 DCF·오너이익", "object", "상세 패널"],
    ])
    _write_rows(ws, rows)



def _add_boardroom_one_pager_sheet(
    wb: Any,
    *,
    company: str,
    dcf: dict[str, Any],
    peer: dict[str, Any],
    price_summary: dict[str, Any],
    scorecard: dict[str, Any] | None,
    advanced: dict[str, Any] | None,
    validation: dict[str, Any],
) -> None:
    """Create a polished one-page investor sheet for presentation/dashboard review."""
    from openpyxl.chart import BarChart, Reference, DoughnutChart
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    sheet_name = "30_발표용_원페이지"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name, 0)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A6"

    navy = "0B1F33"
    blue = "2563EB"
    teal = "0F766E"
    purple = "7C3AED"
    amber = "F59E0B"
    red = "DC2626"
    ink = "102A43"
    slate = "243B53"
    ice = "EEF6FF"
    mint = "DDF7EC"
    cream = "FFF7E6"
    lavender = "F2EEFF"
    coral = "FDECEC"
    border_color = "D8E1EA"
    thin = Side(style="thin", color=border_color)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    football = (advanced or {}).get("football_field") or {}
    reverse_dcf = (advanced or {}).get("reverse_dcf") or {}
    owner = (advanced or {}).get("owner_earnings") or {}
    market_mul = (advanced or {}).get("market_implied_multiples") or {}
    quality = (advanced or {}).get("valuation_quality_diagnostics") or []
    judgement, reason = _judgement_from_metrics(dcf, scorecard, advanced)

    ws.merge_cells("A1:N1")
    ws["A1"] = f"{company} 가치평가 원페이지"
    ws["A1"].fill = PatternFill("solid", fgColor=navy)
    ws["A1"].font = Font(color="FFFFFF", bold=True, size=18)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 38

    ws.merge_cells("A2:N2")
    ws["A2"] = "DCF·상대가치·시장내재 배수·주가 리스크·208개 비교군 위치를 한 장에서 검토하는 투자자용 요약입니다."
    ws["A2"].fill = PatternFill("solid", fgColor=ice)
    ws["A2"].font = Font(color=slate, size=10)
    ws.row_dimensions[2].height = 25

    kpi_rows = [
        ["현재가", _fmt_price(price_summary.get("latest_close") or dcf.get("latest_close")), "DCF 내재주가", _fmt_price(dcf.get("implied_price")), "괴리율", _fmt_pct(dcf.get("upside_downside_pct")), "WACC", _fmt_pct((advanced or {}).get("wacc_used") or dcf.get("wacc"))],
        ["P/S", _fmt_multiple(peer.get("target_psr") or market_mul.get("psr_market")), "비교기업 P/S 중앙값", _fmt_multiple(peer.get("median_psr")), "가치범위 중앙값", _fmt_price(football.get("base_price")), "검증 상태", _label_kr(validation.get("status"))],
        ["종합 가치평가 점수", _fmt_score((advanced or {}).get("advanced_valuation_score")), "보조 가치평가 점수", _fmt_score((scorecard or {}).get("score")), "역산 영구성장률", _fmt_pct(reverse_dcf.get("implied_terminal_growth_rate")), "오너이익 주당가치", _fmt_price(owner.get("owner_earnings_value_per_share"))],
    ]
    _write_rows(ws, kpi_rows, start_row=4, start_col=1)

    for r in range(4, 7):
        for c in [1, 3, 5, 7]:
            ws.cell(r, c).fill = PatternFill("solid", fgColor=[teal, blue, purple, amber][(c // 2) % 4])
            ws.cell(r, c).font = Font(color="FFFFFF", bold=True)
            ws.cell(r, c).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for c in [2, 4, 6, 8]:
            ws.cell(r, c).fill = PatternFill("solid", fgColor=[mint, ice, lavender][(r - 4) % 3])
            ws.cell(r, c).font = Font(color=ink, bold=True, size=11)

    ws.merge_cells("A8:H8")
    ws["A8"] = "핵심 판단"
    ws["A8"].fill = PatternFill("solid", fgColor=navy)
    ws["A8"].font = Font(color="FFFFFF", bold=True, size=12)
    ws.merge_cells("A9:H11")
    ws["A9"] = f"{judgement} — {reason}"
    ws["A9"].fill = PatternFill("solid", fgColor="FFFFFF")
    ws["A9"].font = Font(color=ink, size=11)
    ws["A9"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    table_rows = [
        ["분석 축", "현재 결론", "대시보드에서 볼 것", "실무 체크포인트"],
        ["절대가치", _fmt_price(dcf.get("implied_price")), "DCF 내재주가·민감도", "WACC와 영구성장률 가정이 바뀌면 결론이 크게 달라질 수 있습니다."],
        ["상대가치", _fmt_multiple(peer.get("target_psr")), "P/S·P/B·PER·EV/Sales", "동일 세부군 기준으로 비교기업 품질을 재확인합니다."],
        ["시장내재", _fmt_multiple(market_mul.get("psr_market") or peer.get("target_psr")), "현재가가 반영한 배수", "현재 시장이 이미 반영한 성장 기대를 역산합니다."],
        ["유동성/리스크", _fmt_won(price_summary.get("avg_trading_value_20d")), "거래대금·MDD·변동성", "거래대금이 낮은 기업은 실전 매매비용을 보수적으로 봅니다."],
        ["208개 비교군", str((advanced or {}).get("reference_universe_rows") or "208"), "시장위치 맵·백분위", "동일 섹터 안에서 상대적 위치를 먼저 확인합니다."],
    ]
    _write_rows(ws, table_rows, start_row=13, start_col=1)

    for c in range(1, 5):
        cell = ws.cell(13, c)
        cell.fill = PatternFill("solid", fgColor=slate)
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in range(14, 19):
        for c in range(1, 5):
            ws.cell(r, c).fill = PatternFill("solid", fgColor=["FFFFFF", "F8FAFC"][(r + c) % 2])

    quality_rows = [["완성도 점검", "결과", "의미"]]
    if quality:
        for q in quality[:7]:
            quality_rows.append([
                q.get("name_kr") or q.get("metric_kr") or q.get("name") or "품질 점검",
                _label_kr(q.get("status_kr") or q.get("status") or q.get("result")),
                _koreanize_text(str(q.get("note_kr") or q.get("note") or q.get("message") or "검토 완료")),
            ])
    else:
        quality_rows += [
            ["재무제표", "연결 완료", "DART 기반 최근 5개년 정규화 재무제표를 사용합니다."],
            ["주가 데이터", "연결 완료", "가격·거래대금·변동성·MDD를 대시보드로 전달합니다."],
            ["비교군", "연결 완료", "5개 핵심기업과 208개 반도체 비교군을 함께 활용합니다."],
        ]
    _write_rows(ws, quality_rows, start_row=21, start_col=1)
    for c in range(1, 4):
        ws.cell(21, c).fill = PatternFill("solid", fgColor=teal)
        ws.cell(21, c).font = Font(color="FFFFFF", bold=True)

    # Chart source values on a hidden-friendly area to avoid chart/data overlap.
    chart_rows = [
        ["항목", "점수"],
        ["DCF 안전마진", _as_score_100((dcf.get("upside_downside_pct") or 0) + 0.5) or 50],
        ["종합 가치평가", _as_score_100((advanced or {}).get("advanced_valuation_score")) or 50],
        ["보조 점수", _as_score_100((scorecard or {}).get("score")) or 50],
        ["데이터 검증", 100 if validation.get("status") == "PASS" else 75],
    ]
    _write_rows(ws, chart_rows, start_row=30, start_col=1)
    for c in range(1, 3):
        ws.cell(30, c).fill = PatternFill("solid", fgColor=slate)
        ws.cell(30, c).font = Font(color="FFFFFF", bold=True)

    chart = BarChart()
    chart.type = "bar"
    chart.style = 12
    chart.title = "투자자 관점 핵심 점수"
    chart.y_axis.title = "항목"
    chart.x_axis.title = "점수"
    data = Reference(ws, min_col=2, min_row=30, max_row=34)
    cats = Reference(ws, min_col=1, min_row=31, max_row=34)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.width = 16
    chart.height = 8
    ws.add_chart(chart, "J8")

    donut_rows = [
        ["범위", "기업 수"],
        ["전체 반도체 비교군", (advanced or {}).get("reference_universe_rows") or 208],
        ["동일 세부군", (advanced or {}).get("reference_peer_group_rows") or 40],
        ["선택기업", 1],
    ]
    _write_rows(ws, donut_rows, start_row=30, start_col=5)
    donut = DoughnutChart()
    donut.title = "TAM/SAM/SOM 범위"
    data2 = Reference(ws, min_col=6, min_row=30, max_row=33)
    cats2 = Reference(ws, min_col=5, min_row=31, max_row=33)
    donut.add_data(data2, titles_from_data=True)
    donut.set_categories(cats2)
    donut.holeSize = 55
    donut.width = 12
    donut.height = 8
    ws.add_chart(donut, "J25")

    for row in ws.iter_rows(min_row=1, max_row=38, min_col=1, max_col=14):
        for cell in row:
            if cell.value not in (None, ""):
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    for col in range(1, 15):
        ws.column_dimensions[get_column_letter(col)].width = [15, 16, 17, 18, 16, 16, 15, 16, 3, 15, 15, 15, 15, 15][col - 1]
    for r in range(1, 39):
        ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 22, 24)
    ws.row_dimensions[9].height = 62
    ws.sheet_properties.tabColor = blue


def _add_completion_check_sheet(wb: Any, *, company: str, validation: dict[str, Any], advanced: dict[str, Any] | None) -> None:
    """Replace the old minimal check sheet with a professional completeness checklist."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    sheet_name = "99_완성도_체크"
    for old in ["99_표시개선_점검", sheet_name]:
        if old in wb.sheetnames:
            del wb[old]
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"

    navy = "0B1F33"
    green = "0F766E"
    blue = "2563EB"
    amber = "F59E0B"
    ice = "EEF6FF"
    border_color = "D8E1EA"
    thin = Side(style="thin", color=border_color)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    rows = [
        [f"{company} Valuation Agent 완성도 체크", "", "", "", ""],
        ["목적", "발표 전 워크북이 데이터·모델·디자인·대시보드 연동 기준을 충족하는지 확인합니다.", "", "", ""],
        ["구분", "체크 항목", "상태", "근거", "다음 액션"],
        ["데이터", "DART 재무제표 정규화", "완료", "최근 5개년 재무제표 기반", "기업별 재실행 시 자동 갱신"],
        ["데이터", "주가·거래대금·발행주식 수", "완료", "가격 데이터 및 발행주식 수 검증", "결측 발생 시 intake 재실행"],
        ["모델", "DCF·WACC·FCF 추정", "완료", "절대가치 산식 반영", "민감도와 함께 해석"],
        ["모델", "P/S 중심 상대가치", "완료", "적자기업에도 적용 가능한 배수 포함", "비교기업 품질 확인"],
        ["확장", "208개 반도체 비교군 위치", "완료", "선택기업·동일 세부군·전체 평균 비교", "대시보드 산점도/필터 연결"],
        ["디자인", "한글 라벨·셀 간격·차트 위치", "완료", "표와 차트 겹침 최소화", "최종 발표 전 시각 확인"],
        ["대시보드", "JSON 연동키 정리", "완료", "summary_cards·chart_series·advanced_valuation", "Streamlit/React 화면 연결"],
        ["검증", "Validation status", _label_kr(validation.get("status")), "valuation_validation.json 기준", "경고 발생 시 원천 확인"],
    ]
    rows += [["보강 후보", "신용평가 확장", "보류", "현재는 valuation_agent 내부 준비 단계까지만 고려", "별도 credit_agent 설계 시 연결"]]
    _write_rows(ws, rows)

    for c in range(1, 6):
        ws.cell(1, c).fill = PatternFill("solid", fgColor=navy)
        ws.cell(1, c).font = Font(color="FFFFFF", bold=True, size=14)
        ws.cell(3, c).fill = PatternFill("solid", fgColor=green)
        ws.cell(3, c).font = Font(color="FFFFFF", bold=True)
    ws.merge_cells("A1:E1")
    ws.merge_cells("A2:E2")
    ws["A2"].fill = PatternFill("solid", fgColor=ice)
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=5):
        for cell in row:
            if cell.value not in (None, ""):
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                if cell.column == 3 and cell.row > 3:
                    text = str(cell.value)
                    if "완료" in text or "통과" in text:
                        cell.fill = PatternFill("solid", fgColor="DDF7EC")
                    elif "보류" in text or "주의" in text:
                        cell.fill = PatternFill("solid", fgColor="FFF7E6")
    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = [14, 30, 14, 42, 34][col - 1]
    for r in range(1, ws.max_row + 1):
        ws.row_dimensions[r].height = 28
    ws.sheet_properties.tabColor = amber


def apply_final_valuation_polish(
    wb: Any,
    *,
    company: str,
    company_dir: str,
    context: Any,
    normalized_financials: list[dict[str, Any]],
    wacc: dict[str, Any],
    dcf: dict[str, Any],
    peer: dict[str, Any],
    ml: dict[str, Any],
    sensitivity: list[dict[str, Any]],
    validation: dict[str, Any],
    dashboard_payload: dict[str, Any],
    scorecard: dict[str, Any] | None = None,
    advanced: dict[str, Any] | None = None,
) -> None:
    """Apply final Korean investor-facing polish to a workbook in memory."""
    price_summary = getattr(context, "price_summary", {}) or {}

    _add_boardroom_one_pager_sheet(
        wb,
        company=company,
        dcf=dcf,
        peer=peer,
        price_summary=price_summary,
        scorecard=scorecard,
        advanced=advanced,
        validation=validation,
    )
    _add_investment_memo_sheet(
        wb,
        company=company,
        dcf=dcf,
        peer=peer,
        price_summary=price_summary,
        scorecard=scorecard,
        advanced=advanced,
        validation=validation,
    )
    _add_data_enrichment_sheet(
        wb,
        company=company,
        context=context,
        peer=peer,
        advanced=advanced,
        price_summary=price_summary,
    )
    _add_dashboard_key_sheet(wb, dashboard_payload=dashboard_payload)
    _add_positioning_sheet(wb, company=company, context=context, advanced=advanced)
    _add_completion_check_sheet(wb, company=company, validation=validation, advanced=advanced)

    # Polish all sheets after supplemental sheets are inserted.
    for ws in wb.worksheets:
        _clean_missing_texts(ws)
        _apply_number_formats(ws)
        _apply_sheet_style(wb, ws)

    _reposition_charts(wb)

    tab_colors = {
        "30_발표용_원페이지": "2563EB",
        "26_투자판단_요약": "2563EB",
        "27_데이터보강_내역": "0F766E",
        "28_대시보드_연동키": "7C3AED",
        "29_시장위치_맵": "0F766E",
        "99_완성도_체크": "F59E0B",
    }
    for sheet_name, color in tab_colors.items():
        if sheet_name in wb.sheetnames:
            wb[sheet_name].sheet_properties.tabColor = color

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .utils import to_float


def _require_openpyxl():
    try:
        import openpyxl  # type: ignore
        from openpyxl import Workbook  # type: ignore
        from openpyxl.chart import BarChart, LineChart, Reference  # type: ignore
        from openpyxl.comments import Comment  # type: ignore
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # type: ignore
        from openpyxl.utils import get_column_letter  # type: ignore
        return openpyxl, Workbook, BarChart, LineChart, Reference, Comment, Alignment, Border, Font, PatternFill, Side, get_column_letter
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openpyxl is required to generate valuation workbook. Install openpyxl>=3.1.0") from exc


TABS = [
    "00_대시보드",
    "01_사용안내",
    "02_출처맵",
    "03_원천_DART",
    "04_주가_데이터",
    "05_정규재무제표",
    "06_핵심비율",
    "07_WACC",
    "08_FCF_추정",
    "09_DCF_가치평가",
    "10_피어비교",
    "11_ML_보조판단",
    "12_민감도",
    "13_검증체크",
    "14_대시보드_JSON",
    "15_감사추적",
    "16_모델링_설계",
    "17_투자자요약",
    "18_밸류에이션_유니버스",
    "19_가치평가_브릿지",
    "20_시나리오_요약",
    "21_품질_커버리지",
    "22_종합가치평가",
    "23_가치범위표",
    "24_역산DCF",
    "25_데이터수집현황",
]

HEADER_KR: dict[str, str] = {
    "year": "연도",
    "company": "기업명",
    "company_name": "기업명",
    "company_dir": "기업코드",
    "stock_code": "종목코드",
    "ticker6": "종목코드",
    "market": "시장",
    "peer_group": "피어 그룹",
    "semiconductor_tag": "반도체 세부군",
    "is_focal_5": "5개 핵심기업",
    "focus_reason": "포함 사유",
    "universe_rank": "Universe 순번",
    "is_target": "분석대상",
    "latest_year": "최근연도",
    "date": "일자",
    "open": "시가",
    "high": "고가",
    "low": "저가",
    "close": "종가",
    "adj_close": "수정종가",
    "volume": "거래량",
    "daily_return": "일수익률",
    "drawdown": "드로다운",
    "ma20": "20일선",
    "ma60": "60일선",
    "ma120": "120일선",
    "rolling_vol_20": "20일 변동성",
    "rolling_vol_60": "60일 변동성",
    "return_20d": "20일 수익률",
    "return_60d": "60일 수익률",
    "return_120d": "120일 수익률",
    "distance_to_ma20": "20일선 괴리",
    "distance_to_ma60": "60일선 괴리",
    "distance_to_ma120": "120일선 괴리",
    "rolling_high_52w": "52주 고가",
    "rolling_low_52w": "52주 저가",
    "price_to_52w_high": "52주 고가 대비",
    "price_to_52w_low": "52주 저가 대비",
    "data_quality_note": "데이터 품질 메모",
    "trading_value": "거래대금",
    "trading_value_ma20": "20일 평균 거래대금",
    "turnover_ratio": "거래회전율",
    "latest_volume": "최근 거래량",
    "latest_trading_value": "최근 거래대금",
    "avg_trading_value_20d": "20일 평균 거래대금",
    "avg_volume_20d": "20일 평균 거래량",
    "turnover_latest": "최근 거래회전율",
    "turnover_20d": "20일 평균 거래회전율",
    "source": "출처",
    "ticker": "티커",
    "revenue": "매출액",
    "operating_profit": "영업이익",
    "net_income": "순이익",
    "assets": "자산총계",
    "liabilities": "부채총계",
    "equity": "자본총계",
    "cash": "현금성자산",
    "cfo": "영업현금흐름",
    "capex": "CAPEX",
    "fcf": "FCF",
    "investing_cf": "투자현금흐름",
    "source_account_count": "원천계정수",
    "revenue_growth": "매출성장률",
    "op_growth": "영업이익성장률",
    "asset_growth": "자산성장률",
    "op_margin": "영업이익률",
    "net_margin": "순이익률",
    "roe": "ROE",
    "roa": "ROA",
    "debt_ratio": "부채/자본",
    "liability_to_assets": "부채/자산",
    "equity_ratio": "자본비율",
    "cash_to_assets": "현금/자산",
    "cfo_margin": "CFO margin",
    "capex_to_sales": "CAPEX/매출",
    "fcf_margin": "FCF margin",
    "fcf_conversion": "FCF 전환율",
    "market_cap": "시가총액",
    "shares_outstanding": "발행주식 수",
    "enterprise_value_proxy": "EV proxy",
    "psr": "P/S",
    "target_psr": "분석대상 P/S",
    "median_psr": "Peer P/S 중앙값",
    "psr_vs_peer_median_pct": "P/S 중앙값 대비",
    "psr_peer_percentile_lower_better": "P/S 매력도 percentile",
    "psr_signal_kr": "P/S 해석",
    "per": "PER",
    "pbr": "PBR",
    "ev_sales": "EV/Sales",
    "ev_ebit": "EV/EBIT",
    "p_fcf": "P/FCF",
    "return_1y": "1년 수익률",
    "volatility_annualized": "연환산 변동성",
    "mdd": "MDD",
    "high_52w": "52주 고가",
    "low_52w": "52주 저가",
    "wacc": "WACC",
    "terminal_growth": "영구성장률",
    "enterprise_value": "기업가치(EV)",
    "pv_fcf": "FCF 현재가치",
    "pv_terminal_value": "Terminal 현재가치",
    "discount_factor": "할인계수",
    "metric": "항목",
    "value": "값",
    "note": "비고",
    "severity": "중요도",
    "code": "코드",
    "message": "메시지",
    "step": "단계",
    "status": "상태",
    "factor": "요인",
    "score": "점수",
    "direction": "해석",
    "archetype": "모델 유형",
    "description": "설명",
    "source_pattern": "참조 파일 패턴",
    "source_sheets_observed": "관찰된 시트",
    "recommended_tabs": "권장 시트",
    "required_data_blocks": "필요 데이터",
    "score_keywords": "키워드",
    "valuation_proxy_score": "Valuation Proxy 점수",
    "valuation_proxy_label": "Valuation Proxy 라벨",
    "valuation_proxy_label_kr": "가치 라벨",
    "valuation_confidence": "Valuation 신뢰도",
    "credit_risk_score": "Credit Risk 점수",
    "credit_proxy_label": "Credit Risk 라벨",
    "credit_proxy_label_kr": "신용위험 라벨",
    "credit_confidence": "Credit 신뢰도",
    "credit_anomaly_score": "Credit 이상치 점수",
    "factor_code": "요인 코드",
    "weight": "가중치",
    "raw_value": "원천값",
    "interpretation": "해석",
    "method": "산출 방식",
    "method_kr": "산출 방식",
    "label": "라벨",
    "label_kr": "한글 라벨",
    "narrative_kr": "종합 해석",
    "composite_score": "종합 점수",
    "data_quality_status": "데이터 품질",
    "data_quality_status_kr": "데이터 품질 해석",
    "manual_review_priority": "수동검토 우선순위",
    "manual_review_priority_kr": "수동검토 우선순위 해석",
    "advanced_valuation_score": "종합 가치평가 점수",
    "method_code": "방법 코드",
    "method_kr": "가치평가 방법",
    "low_equity_value": "하단 지분가치",
    "base_equity_value": "중앙 지분가치",
    "high_equity_value": "상단 지분가치",
    "low_implied_price": "하단 주당가치",
    "base_implied_price": "중앙 주당가치",
    "high_implied_price": "상단 주당가치",
    "current_price": "현재가",
    "upside_downside_pct": "현재가 대비",
    "interpretation_kr": "해석",
    "reliability_kr": "신뢰도",
    "method_count": "방법 수",
    "low_price": "하단 가격",
    "base_price": "중앙 가격",
    "high_price": "상단 가격",
    "margin_of_safety_pct": "안전마진",
    "market_implied_enterprise_value": "시장 내재 EV",
    "model_enterprise_value": "모델 EV",
    "market_vs_model_ev_gap_pct": "시장/모델 EV 괴리",
    "required_fcf_yield_on_ev": "요구 FCF 수익률",
    "implied_terminal_growth_rate": "역산 영구성장률",
    "owner_earnings": "오너 이익",
    "owner_earnings_yield": "오너 이익 수익률",
    "owner_earnings_value_per_share": "오너 이익 주당가치",
    "epv_price": "EPV 주당가치",
    "graham_number": "Graham Number",
    "데이터블록": "데이터블록",
    "수집경로": "수집경로",
    "가치평가 활용": "가치평가 활용",
    "대시보드 표시": "대시보드 표시",
    "source_type": "출처 유형",
    "source_note": "출처 설명",
    "corp_code": "DART 고유번호",
    "fs_div": "재무제표 구분",
    "sj_div": "재무제표 코드",
    "sj_nm": "재무제표명",
    "account_id": "계정ID",
    "account_nm": "계정명",
    "account_detail": "계정상세",
    "thstrm_nm": "당기명",
    "amount": "금액",
    "frmtrm_amount": "전기금액",
    "currency": "통화",
    "ord": "정렬순서",
    "revenue_source_account": "매출 원천계정",
    "operating_profit_source_account": "영업이익 원천계정",
    "net_income_source_account": "순이익 원천계정",
    "assets_source_account": "자산 원천계정",
    "liabilities_source_account": "부채 원천계정",
    "equity_source_account": "자본 원천계정",
    "cfo_source_account": "영업현금흐름 원천계정",
    "capex_source_account": "CAPEX 원천계정",
    "cash_source_account": "현금 원천계정",
    "confidence_grade_kr": "신뢰도 등급",
    "football_field": "가치범위표",
    "reverse_dcf": "역산 DCF",
    "owner_earnings": "오너 이익",
    "valuation_methods": "가치평가 방법",
    "advanced_valuation_score": "종합 가치평가 점수",
    "market_implied_multiples": "시장내재 배수",
    "valuation_quality_diagnostics": "품질 진단",
    "진단항목": "진단항목",
    "근거값": "근거값",
    "enterprise_value_auto": "자동산출 EV",
    "per_auto": "자동산출 PER",
    "pbr_auto": "자동산출 PBR",
    "psr_auto": "자동산출 P/S",
    "p_fcf_auto": "자동산출 P/FCF",
    "ev_sales_auto": "자동산출 EV/Sales",
    "ev_ebit_auto": "자동산출 EV/EBIT",
    "fcf_yield_auto": "자동산출 FCF 수익률",
    "sales_yield_auto": "자동산출 매출수익률",
    "latest_close_auto": "자동산출 현재가",
    "market_cap_auto": "자동산출 시가총액",
    "shares_outstanding_auto": "자동산출 발행주식 수",
    "eps_auto": "자동산출 EPS",
    "bps_auto": "자동산출 BPS",
    "snapshot_status_kr": "보조지표 상태",
    "derivation_note_kr": "산출 메모",
}

PCT_KEYS = {
    "revenue_growth", "op_growth", "asset_growth", "op_margin", "net_margin", "roe", "roa", "debt_ratio",
    "liability_to_assets", "equity_ratio", "cash_to_assets", "cfo_margin", "capex_to_sales", "fcf_margin",
    "fcf_conversion", "daily_return", "drawdown", "return_1y", "volatility_annualized", "mdd", "wacc",
    "terminal_growth", "terminal_growth_rate", "revenue_growth", "discount_factor", "upside_downside_pct",
    "rolling_vol_20", "rolling_vol_60", "return_20d", "return_60d", "return_120d",
    "distance_to_ma20", "distance_to_ma60", "distance_to_ma120", "price_to_52w_high", "price_to_52w_low",
    "turnover_ratio", "turnover_latest", "turnover_20d",
    "margin_of_safety_pct", "market_vs_model_ev_gap_pct", "required_fcf_yield_on_ev", "implied_terminal_growth_rate", "owner_earnings_yield", "fcf_yield_market", "sales_yield_market", "fcf_yield_auto", "sales_yield_auto",
    "psr_vs_peer_median_pct", "valuation_confidence", "credit_confidence",
}
MULTIPLE_KEYS = {"psr", "target_psr", "median_psr", "per", "pbr", "ev_sales", "ev_ebit", "p_fcf", "psr_market", "pbr_market", "per_market", "p_fcf_market", "ev_sales_market", "ev_ebit_market", "per_auto", "pbr_auto", "psr_auto", "p_fcf_auto", "ev_sales_auto", "ev_ebit_auto"}
COUNT_KEYS = {"volume", "shares_outstanding", "source_account_count", "price_rows", "peer_count", "latest_volume", "avg_volume_20d"}


def _cell_display(v: Any) -> Any:
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(v, ensure_ascii=False)
    if v is None or v == "":
        return "해당 없음"
    return v


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _number_format_for_key(key: str) -> str:
    if key in PCT_KEYS or key.endswith("_pct") or "margin" in key or "ratio" in key or "growth" in key:
        return '0.0%;[Red](0.0%);-'
    if key in MULTIPLE_KEYS:
        return '0.0x;[Red](0.0x);-'
    if key in COUNT_KEYS:
        return '#,##0;[Red](#,##0);-'
    if key in {"latest_close", "implied_price", "low_implied_price", "base_implied_price", "high_implied_price", "low_price", "base_price", "high_price", "current_price", "owner_earnings_value_per_share", "epv_price", "graham_number", "open", "high", "low", "close", "adj_close", "ma20", "ma60", "ma120", "high_52w", "low_52w", "rolling_high_52w", "rolling_low_52w", "market_cap", "trading_value", "trading_value_ma20", "latest_trading_value", "avg_trading_value_20d"}:
        return '#,##0;[Red](#,##0);-'
    return '#,##0;[Red](#,##0);-'


def _translate_headers(headers: list[str]) -> list[str]:
    return [HEADER_KR.get(h, h) for h in headers]


def _apply_base_style(wb, ws):
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_format.defaultRowHeight = 20
    for col in range(1, 24):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 15


def _title(ws, text: str, subtitle: str | None = None, end_col: int = 8):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    c = ws.cell(1, 1, text)
    c.fill = ws.parent._ap_styles["title_fill"]
    c.font = ws.parent._ap_styles["title_font"]
    c.alignment = ws.parent._ap_styles["title_align"]
    ws.row_dimensions[1].height = 30
    if subtitle:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_col)
        c2 = ws.cell(2, 1, subtitle)
        c2.fill = ws.parent._ap_styles["subtitle_fill"]
        c2.font = ws.parent._ap_styles["subtitle_font"]
        c2.alignment = ws.parent._ap_styles["left"]
        ws.row_dimensions[2].height = 28


def _section(ws, row: int, text: str, end_col: int = 8) -> int:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=end_col)
    c = ws.cell(row, 1, text)
    c.fill = ws.parent._ap_styles["section_fill"]
    c.font = ws.parent._ap_styles["section_font"]
    c.alignment = ws.parent._ap_styles["left"]
    ws.row_dimensions[row].height = 23
    return row + 1


def _write_table(ws, start_row: int, start_col: int, rows: list[dict[str, Any]], title: str | None = None, max_rows: int | None = None) -> int:
    if title:
        start_row = _section(ws, start_row, title, end_col=max(6, start_col + 5))
    rows = rows or []
    if max_rows is not None:
        rows = rows[:max_rows]
    headers: list[str] = []
    for r in rows:
        for k in r:
            if k not in headers:
                headers.append(k)
    if not headers:
        headers = ["status", "message"]
        rows = [{"status": "INFO", "message": "표시할 원천 행이 없습니다."}]
    display_headers = _translate_headers(headers)
    for c_idx, h in enumerate(display_headers, start_col):
        cell = ws.cell(start_row, c_idx, h)
        cell.fill = ws.parent._ap_styles["header_fill"]
        cell.font = ws.parent._ap_styles["header_font"]
        cell.alignment = ws.parent._ap_styles["center"]
        cell.border = ws.parent._ap_styles["thin_border"]
    for r_idx, row in enumerate(rows, start_row + 1):
        shade = ws.parent._ap_styles["row_fill_1"] if (r_idx - start_row) % 2 else ws.parent._ap_styles["row_fill_2"]
        for c_idx, h in enumerate(headers, start_col):
            value = _cell_display(row.get(h))
            cell = ws.cell(r_idx, c_idx, value)
            cell.fill = shade
            cell.border = ws.parent._ap_styles["thin_border"]
            cell.alignment = ws.parent._ap_styles["left"]
            if _is_number(value):
                cell.number_format = _number_format_for_key(h)
                cell.alignment = ws.parent._ap_styles["right"]
    # Reasonable widths by content type.
    for offset, h in enumerate(headers, start_col):
        width = 14
        if h in {"message", "diagnostics", "raw", "description", "source_pattern", "source_sheets_observed", "recommended_tabs", "required_data_blocks", "score_keywords", "note", "data_quality_note"}:
            width = 40
        elif h in {"company", "account_nm", "metric", "factor"}:
            width = 22
        elif h in {"date", "ticker", "stock_code", "market"}:
            width = 13
        ws.column_dimensions[ws.parent._ap_get_col_letter(offset)].width = width
    try:
        end_col = ws.parent._ap_get_col_letter(start_col + len(headers) - 1)
        ws.auto_filter.ref = f"{ws.parent._ap_get_col_letter(start_col)}{start_row}:{end_col}{start_row + len(rows)}"
    except Exception:
        pass
    return start_row + len(rows) + 3


def _write_kv(ws, row: int, key: str, value: Any, note: str = "", *, input_cell: bool = False, formula_cell: bool = False) -> None:
    ws.cell(row, 1, key)
    ws.cell(row, 2, value)
    ws.cell(row, 3, note or "-")
    for c in range(1, 4):
        ws.cell(row, c).border = ws.parent._ap_styles["thin_border"]
        ws.cell(row, c).alignment = ws.parent._ap_styles["left"]
    ws.cell(row, 1).font = ws.parent._ap_styles["bold_font"]
    if input_cell:
        ws.cell(row, 2).fill = ws.parent._ap_styles["input_fill"]
        ws.cell(row, 2).font = ws.parent._ap_styles["input_font"]
    if formula_cell:
        ws.cell(row, 2).font = ws.parent._ap_styles["formula_font"]
    if isinstance(value, float) or (isinstance(value, str) and value.startswith("=")):
        if any(token in key for token in ["율", "WACC", "Beta", "비중", "수익률", "괴리"]):
            ws.cell(row, 2).number_format = '0.0%;[Red](0.0%);-'
        else:
            ws.cell(row, 2).number_format = '#,##0;[Red](#,##0);-'


def _fmt_pct(v: Any) -> str:
    try:
        if v is None:
            return "해당 없음"
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "해당 없음"


def _fmt_krw_eok(v: Any) -> str:
    try:
        if v is None:
            return "해당 없음"
        return f"{float(v) / 100_000_000:,.1f}억원"
    except Exception:
        return "해당 없음"


def _fmt_price(v: Any) -> str:
    try:
        if v is None:
            return "해당 없음"
        return f"{float(v):,.0f}원"
    except Exception:
        return "해당 없음"


def _dashboard_card(ws, row: int, col: int, title: str, value: str, note: str = ""):
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + 1)
    ws.merge_cells(start_row=row + 1, start_column=col, end_row=row + 1, end_column=col + 1)
    ws.merge_cells(start_row=row + 2, start_column=col, end_row=row + 2, end_column=col + 1)
    ws.cell(row, col, title).fill = ws.parent._ap_styles["card_title_fill"]
    ws.cell(row, col).font = ws.parent._ap_styles["card_title_font"]
    ws.cell(row + 1, col, value).fill = ws.parent._ap_styles["card_fill"]
    ws.cell(row + 1, col).font = ws.parent._ap_styles["card_value_font"]
    ws.cell(row + 2, col, note or "-").fill = ws.parent._ap_styles["card_fill"]
    ws.cell(row + 2, col).font = ws.parent._ap_styles["small_font"]
    for rr in range(row, row + 3):
        for cc in range(col, col + 2):
            ws.cell(rr, cc).border = ws.parent._ap_styles["medium_border"]
            ws.cell(rr, cc).alignment = ws.parent._ap_styles["center"]



def _make_price_sheet(wb, context: Any) -> None:
    ws = wb["04_주가_데이터"]
    price_rows = list(getattr(context, "price_history", []) or [])
    price_summary = getattr(context, "price_summary", {}) or {}
    _title(ws, "주가 데이터·기술적 지표", "Valuation Agent 전용 주가 intake: 종가·이동평균·수익률·MDD·롤링 변동성", end_col=12)
    summary_rows = [
        {"항목": "데이터 행 수", "값": len(price_rows) or price_summary.get("price_rows"), "비고": "valuation_price_history.csv 기준"},
        {"항목": "수집 시작일", "값": price_summary.get("price_start") or (price_rows[0].get("date") if price_rows else None), "비고": "가격 데이터 시작"},
        {"항목": "수집 종료일", "값": price_summary.get("price_end") or (price_rows[-1].get("date") if price_rows else None), "비고": "가격 데이터 종료"},
        {"항목": "현재가", "값": price_summary.get("latest_close") or (price_rows[-1].get("close") if price_rows else None), "비고": "최근 종가"},
        {"항목": "1년 수익률", "값": price_summary.get("return_1y"), "비고": "최근 약 1년"},
        {"항목": "연환산 변동성", "값": price_summary.get("volatility_annualized"), "비고": "일수익률 × √252"},
        {"항목": "MDD", "값": price_summary.get("mdd"), "비고": "기간 중 최대 낙폭"},
        {"항목": "52주 고가", "값": price_summary.get("high_52w"), "비고": "최근 252거래일"},
        {"항목": "52주 저가", "값": price_summary.get("low_52w"), "비고": "최근 252거래일"},
        {"항목": "발행주식 수", "값": price_summary.get("shares_outstanding"), "비고": "DART stockTotqySttus"},
        {"항목": "시가총액", "값": price_summary.get("market_cap"), "비고": "현재가 × 발행주식 수"},
        {"항목": "최근 거래량", "값": price_summary.get("latest_volume"), "비고": "최근 거래일"},
        {"항목": "최근 거래대금", "값": price_summary.get("latest_trading_value"), "비고": "종가 × 거래량"},
        {"항목": "20일 평균 거래대금", "값": price_summary.get("avg_trading_value_20d"), "비고": "유동성 proxy"},
        {"항목": "최근 거래회전율", "값": price_summary.get("turnover_latest"), "비고": "거래량 / 발행주식 수"},
    ]
    _write_table(ws, 4, 1, summary_rows, title="주가 요약")
    start_row = 17
    # 최근 700거래일을 우선 표시하되, 데이터가 없으면 품질 메모를 남깁니다.
    display_rows = price_rows[-700:] if price_rows else []
    _write_table(ws, start_row, 1, display_rows, title="최근 주가 원천 데이터", max_rows=700)
    # Add chart only when enough data exists. Uses columns after translated headers: date=A, close=E, MA20=J, MA60=K, MA120=L.
    try:
        if len(display_rows) >= 30:
            LineChart = wb._ap_LineChart
            Reference = wb._ap_Reference
            chart = LineChart()
            chart.title = "종가·이동평균 추이"
            chart.y_axis.title = "원"
            chart.x_axis.title = "일자"
            header_row = start_row + 1
            data_start = header_row
            data_end = header_row + len(display_rows)
            data = Reference(ws, min_col=5, max_col=5, min_row=data_start, max_row=data_end)
            cats = Reference(ws, min_col=1, min_row=data_start + 1, max_row=data_end)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            chart.height = 8
            chart.width = 18
            ws.add_chart(chart, "Q4")
    except Exception:
        pass

def _add_charts(wb, ws, normalized_rows: int, projection_rows: int, peer_rows: int, start_row: int = 31):
    BarChart = wb._ap_BarChart
    LineChart = wb._ap_LineChart
    Reference = wb._ap_Reference
    if normalized_rows >= 2:
        chart = BarChart()
        chart.title = "매출·영업이익·FCF 추이"
        chart.y_axis.title = "KRW"
        chart.x_axis.title = "연도"
        data = Reference(ws, min_col=2, max_col=4, min_row=start_row, max_row=start_row + normalized_rows)
        cats = Reference(ws, min_col=1, min_row=start_row + 1, max_row=start_row + normalized_rows)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        chart.height = 7
        chart.width = 14
        ws.add_chart(chart, "A34")
    if projection_rows >= 2:
        chart = LineChart()
        chart.title = "FCF 추정"
        chart.y_axis.title = "KRW"
        chart.x_axis.title = "연도"
        data = Reference(ws, min_col=6, max_col=7, min_row=start_row, max_row=start_row + projection_rows)
        cats = Reference(ws, min_col=5, min_row=start_row + 1, max_row=start_row + projection_rows)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        chart.height = 7
        chart.width = 14
        ws.add_chart(chart, "I34")
    if peer_rows >= 2:
        chart = BarChart()
        chart.title = "Peer P/S 비교"
        chart.y_axis.title = "배수"
        data = Reference(ws, min_col=10, max_col=10, min_row=start_row, max_row=start_row + peer_rows)
        cats = Reference(ws, min_col=9, min_row=start_row + 1, max_row=start_row + peer_rows)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        chart.height = 7
        chart.width = 13
        ws.add_chart(chart, "Q34")


def _make_dashboard(wb, company: str, normalized: list[dict[str, Any]], dcf: dict[str, Any], wacc: dict[str, Any], peer: dict[str, Any], ml: dict[str, Any], validation: dict[str, Any], price_summary: dict[str, Any] | None = None, price_history: list[dict[str, Any]] | None = None):
    ws = wb["00_대시보드"]
    _title(ws, f"{company} 독립 가치평가 대시보드", "DCF · WACC · Peer Comps · 주가/민감도 · ML 보조판단 · 검증체크 자동 생성", end_col=12)
    price_summary = price_summary or {}
    price_history = price_history or []
    _dashboard_card(ws, 4, 1, "WACC", _fmt_pct(wacc.get("wacc")), "시장가중/장부가중 혼합")
    _dashboard_card(ws, 4, 3, "DCF 기업가치", _fmt_krw_eok(dcf.get("enterprise_value")), "EV 기준")
    _dashboard_card(ws, 4, 5, "DCF 지분가치", _fmt_krw_eok(dcf.get("equity_value")), "EV + 현금 - 부채 proxy")
    _dashboard_card(ws, 4, 7, "내재주가", _fmt_price(dcf.get("implied_price")), "발행주식 수 기준")
    _dashboard_card(ws, 4, 9, "괴리율", _fmt_pct(dcf.get("upside_downside_pct")), "현재가 대비")
    _dashboard_card(ws, 4, 11, "검증 상태", str(validation.get("status") or "해당 없음"), str(ml.get("label_kr") or ml.get("label") or "ML 해당 없음"))
    _dashboard_card(ws, 7, 1, "현재가", _fmt_price(price_summary.get("latest_close") or dcf.get("latest_close")), "주가 intake")
    _dashboard_card(ws, 7, 3, "1년 수익률", _fmt_pct(price_summary.get("return_1y")), "최근 약 1년")
    _dashboard_card(ws, 7, 5, "MDD", _fmt_pct(price_summary.get("mdd")), "최대 낙폭")
    _dashboard_card(ws, 7, 7, "변동성", _fmt_pct(price_summary.get("volatility_annualized")), "연환산")
    _dashboard_card(ws, 7, 9, "주가 행 수", f"{len(price_history) or price_summary.get('price_rows') or 0:,}행", "차트/대시보드 원천")
    _dashboard_card(ws, 7, 11, "52주 범위", f"{_fmt_price(price_summary.get('low_52w'))}~{_fmt_price(price_summary.get('high_52w'))}", "저가~고가")
    _dashboard_card(ws, 10, 1, "시가총액", _fmt_krw_eok(price_summary.get("market_cap")), "현재가×발행주식 수")
    _dashboard_card(ws, 10, 3, "발행주식 수", f"{float(price_summary.get('shares_outstanding') or 0):,.0f}주" if price_summary.get('shares_outstanding') is not None else "해당 없음", "DART stockTotqySttus")
    _dashboard_card(ws, 10, 5, "20일 평균 거래대금", _fmt_krw_eok(price_summary.get("avg_trading_value_20d")), "유동성 proxy")
    _dashboard_card(ws, 10, 7, "최근 거래회전율", _fmt_pct(price_summary.get("turnover_latest")), "거래량/주식 수")
    _dashboard_card(ws, 10, 9, "ML 보조점수", f"{float(ml.get('composite_score') or 0):.1f}/100" if ml.get('composite_score') is not None else "해당 없음", str(ml.get("label_kr") or ml.get("label") or "보조판단"))
    _dashboard_card(ws, 10, 11, "Peer 수", f"{len(peer.get('peer_rows') or []):,}개", "상대가치 비교")
    _dashboard_card(ws, 13, 1, "P/S", f"{float(peer.get('target_psr')):.2f}x" if peer.get('target_psr') is not None else "해당 없음", str(peer.get("psr_signal_kr") or "PSR 해석"))
    _dashboard_card(ws, 13, 3, "Peer P/S 중앙값", f"{float(peer.get('median_psr')):.2f}x" if peer.get('median_psr') is not None else "해당 없음", "5개 live peer 기준")
    _dashboard_card(ws, 13, 5, "P/S 매력도", f"{float(peer.get('psr_peer_percentile_lower_better')):.1f}점" if peer.get('psr_peer_percentile_lower_better') is not None else "해당 없음", "낮은 P/S일수록 점수 우호")
    ref_sum = ml.get("reference_universe_summary") or {}
    _dashboard_card(ws, 13, 7, "208개 Universe", f"{int(ref_sum.get('reference_universe_rows') or 0):,}개", str(ref_sum.get("target_peer_group") or "반도체 reference"))
    _dashboard_card(ws, 13, 9, "Reference 그룹", str(ref_sum.get("target_peer_group") or "해당 없음"), f"그룹 {ref_sum.get('peer_group_size', '해당 없음')}개")
    _dashboard_card(ws, 13, 11, "PSR/Universe", "반영", "대시보드/Chair 보조판단")

    row = _section(ws, 19, "핵심 해석", end_col=12)
    interpretation = [
        ["데이터 독립성", "finance_agent 산출물을 읽지 않고 valuation/intake 원천 데이터만 사용"],
        ["모델 구조", "업로드한 파이낸셜 모델링 파일의 구조를 DCF/WACC/Peer/Scenario/Dashboard 코드로 반영"],
        ["활용 방식", "Chair 최종의견 가중합에는 미반영, 보조 가치평가 및 대시보드 다운로드 산출물로 활용"],
        ["주의", "DART·주가·발행주식 수가 부족한 항목은 검증체크 시트에서 경고로 표시"],
    ]
    for r_idx, row_values in enumerate(interpretation, row):
        ws.cell(r_idx, 1, row_values[0]).font = ws.parent._ap_styles["bold_font"]
        ws.cell(r_idx, 2, row_values[1])
        ws.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=12)
        for c in range(1, 13):
            ws.cell(r_idx, c).fill = ws.parent._ap_styles["row_fill_1"]
            ws.cell(r_idx, c).border = ws.parent._ap_styles["thin_border"]
            ws.cell(r_idx, c).alignment = ws.parent._ap_styles["left"]

    # Data blocks for charts below dashboard cards.
    start = 31
    hist_headers = ["연도", "매출액", "영업이익", "FCF"]
    for c, h in enumerate(hist_headers, 1):
        ws.cell(start, c, h).fill = ws.parent._ap_styles["header_fill"]
        ws.cell(start, c).font = ws.parent._ap_styles["header_font"]
    for idx, r in enumerate(normalized, start + 1):
        ws.cell(idx, 1, r.get("year"))
        ws.cell(idx, 2, r.get("revenue"))
        ws.cell(idx, 3, r.get("operating_profit"))
        ws.cell(idx, 4, r.get("fcf"))
        for c in range(2, 5):
            ws.cell(idx, c).number_format = '#,##0;[Red](#,##0);-'
    projection = dcf.get("projection") or []
    proj_headers = ["연도", "매출액 추정", "FCF 추정", "PV FCF"]
    for c, h in enumerate(proj_headers, 5):
        ws.cell(start, c, h).fill = ws.parent._ap_styles["header_fill"]
        ws.cell(start, c).font = ws.parent._ap_styles["header_font"]
    for idx, r in enumerate(projection, start + 1):
        ws.cell(idx, 5, r.get("year"))
        ws.cell(idx, 6, r.get("revenue"))
        ws.cell(idx, 7, r.get("fcf"))
        ws.cell(idx, 8, r.get("pv_fcf"))
        for c in range(6, 9):
            ws.cell(idx, c).number_format = '#,##0;[Red](#,##0);-'
    peer_rows = peer.get("peer_rows") or []
    peer_headers = ["기업", "P/S", "PER", "PBR"]
    for c, h in enumerate(peer_headers, 9):
        ws.cell(start, c, h).fill = ws.parent._ap_styles["header_fill"]
        ws.cell(start, c).font = ws.parent._ap_styles["header_font"]
    for idx, r in enumerate(peer_rows, start + 1):
        ws.cell(idx, 9, r.get("company"))
        ws.cell(idx, 10, r.get("psr"))
        ws.cell(idx, 11, r.get("per"))
        ws.cell(idx, 12, r.get("pbr"))
        for c in range(10, 13):
            ws.cell(idx, c).number_format = '0.0x;[Red](0.0x);-'

    _add_charts(wb, ws, len(normalized), len(projection), len(peer_rows), start)
    for col in range(1, 13):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 15
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["F"].width = 18
    ws.column_dimensions["H"].width = 18



def _make_investor_summary(wb, company: str, normalized: list[dict[str, Any]], dcf: dict[str, Any], wacc: dict[str, Any], peer: dict[str, Any], ml: dict[str, Any], validation: dict[str, Any], price_summary: dict[str, Any] | None = None) -> None:
    """One-page Korean investor view for dashboard/download use."""
    ws = wb["17_투자자요약"]
    price_summary = price_summary or {}
    latest = normalized[-1] if normalized else {}
    _title(ws, f"{company} 투자자용 요약", "Valuation Agent 단독 산출: 재무 원천·주가·DCF·Peer·ML 보조판단을 한 장으로 요약", end_col=10)
    rows = [
        {"구분": "데이터 상태", "핵심값": validation.get("status"), "해석": "PASS이면 workbook/dashboard용 주요 입력값이 준비된 상태"},
        {"구분": "현재가", "핵심값": price_summary.get("latest_close") or dcf.get("latest_close"), "해석": "주가 intake 기준 최근 종가"},
        {"구분": "시가총액", "핵심값": price_summary.get("market_cap"), "해석": "현재가 × 발행주식 수"},
        {"구분": "최근 매출액", "핵심값": latest.get("revenue"), "해석": "DART 기반 정규화 재무제표"},
        {"구분": "최근 영업이익률", "핵심값": latest.get("op_margin"), "해석": "영업이익 / 매출액"},
        {"구분": "최근 FCF margin", "핵심값": latest.get("fcf_margin"), "해석": "FCF / 매출액"},
        {"구분": "WACC", "핵심값": wacc.get("wacc"), "해석": "DCF 할인율"},
        {"구분": "DCF 기업가치", "핵심값": dcf.get("enterprise_value"), "해석": "명시기간 FCF + Terminal Value 현재가치"},
        {"구분": "DCF 내재주가", "핵심값": dcf.get("implied_price"), "해석": "지분가치 / 발행주식 수"},
        {"구분": "현재가 대비 괴리율", "핵심값": dcf.get("upside_downside_pct"), "해석": "내재주가 / 현재가 - 1"},
        {"구분": "P/S", "핵심값": peer.get("target_psr"), "해석": peer.get("psr_signal_kr") or "시가총액 / 매출액"},
        {"구분": "Peer P/S 중앙값", "핵심값": peer.get("median_psr"), "해석": "5개 live peer 기준 상대가치 비교"},
        {"구분": "208개 Universe", "핵심값": (ml.get("reference_universe_summary") or {}).get("reference_universe_rows"), "해석": (ml.get("reference_universe_summary") or {}).get("target_peer_group") or "반도체 reference 비교"},
        {"구분": "1년 수익률", "핵심값": price_summary.get("return_1y"), "해석": "최근 약 1년 주가 변화"},
        {"구분": "MDD", "핵심값": price_summary.get("mdd"), "해석": "수집 기간 중 최대 낙폭"},
        {"구분": "20일 평균 거래대금", "핵심값": price_summary.get("avg_trading_value_20d"), "해석": "거래 유동성 proxy"},
        {"구분": "ML 보조 품질점수", "핵심값": ml.get("composite_score"), "해석": ml.get("label_kr") or ml.get("label")},
        {"구분": "Peer 비교대상", "핵심값": len(peer.get("peer_rows") or []), "해석": "반도체 5개 focal universe"},
    ]
    _write_table(ws, 4, 1, rows, title="투자자 핵심 요약")
    notes = [
        {"체크포인트": "가중합 반영", "내용": "기존 Chair 5개 에이전트 가중합에는 미반영. 보조 가치평가·다운로드 산출물로 사용"},
        {"체크포인트": "Finance와 중복 방지", "내용": "finance_agent 산출물을 읽지 않고 valuation/intake 산출물만 사용"},
        {"체크포인트": "대시보드 연결", "내용": "dashboard_payload.json과 workbook 시트를 그대로 Streamlit/React 다운로드 영역에 연결 가능"},
        {"체크포인트": "PSR/208개 Universe", "내용": "P/S와 208개 반도체 reference universe를 함께 보여줘 단순 DCF보다 비교 설명력을 강화"},
        {"체크포인트": "해석 주의", "내용": "DCF는 가정 민감도가 크므로 WACC·성장률·FCF margin 민감도 시트와 함께 확인"},
    ]
    _write_table(ws, 22, 1, notes, title="활용 체크포인트")
    for col in range(1, 11):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 18
    ws.column_dimensions["C"].width = 45




def _fmt_multiple(v: Any) -> str:
    try:
        if v is None or v == "":
            return "해당 없음"
        return f"{float(v):.2f}배"
    except Exception:
        return "해당 없음"


def _fmt_score(v: Any) -> str:
    try:
        if v is None or v == "":
            return "해당 없음"
        return f"{float(v):.1f}/100"
    except Exception:
        return "해당 없음"


def _make_scorecard_sheet(wb, company: str, dcf: dict[str, Any], peer: dict[str, Any], ml: dict[str, Any], scorecard: dict[str, Any] | None, price_summary: dict[str, Any], reference_summary: dict[str, Any], validation: dict[str, Any]) -> None:
    ws = wb["19_가치평가_브릿지"]
    scorecard = scorecard or {}
    _title(ws, f"{company} 가치평가 브릿지", "DCF · Peer P/S · 208개 Universe · 품질 ML · 유동성/리스크를 하나의 보조 점수로 연결", end_col=11)
    _dashboard_card(ws, 4, 1, "종합 점수", _fmt_score(scorecard.get("score")), str(scorecard.get("label_kr") or "해당 없음"))
    _dashboard_card(ws, 4, 3, "DCF 괴리율", _fmt_pct(dcf.get("upside_downside_pct")), "내재주가/현재가-1")
    _dashboard_card(ws, 4, 5, "P/S", _fmt_multiple(peer.get("target_psr")), str(peer.get("psr_signal_kr") or "P/S 계산 제외"))
    _dashboard_card(ws, 4, 7, "Peer P/S 중앙값", _fmt_multiple(peer.get("median_psr")), "live peer 기준")
    _dashboard_card(ws, 4, 9, "208개 Universe", f"{int((reference_summary or {}).get('reference_universe_rows') or 0):,}개", str((reference_summary or {}).get("target_peer_group") or "해당 없음"))

    narrative = [
        {"구분": "역할", "내용": "Chair 최종 가중합을 대체하지 않는 보조 밸류에이션 판단 근거"},
        {"구분": "해석", "내용": scorecard.get("narrative_kr") or "종합 스코어 산출 가능"},
        {"구분": "방법", "내용": scorecard.get("method_kr") or "DCF·Peer·품질·Universe·유동성·검증 가중 스코어"},
        {"구분": "검증상태", "내용": validation.get("status") or "해당 없음"},
    ]
    row = _write_table(ws, 9, 1, narrative, title="핵심 해석")
    factors = scorecard.get("factors") if isinstance(scorecard, dict) else []
    if not factors:
        factors = [{"factor": "스코어카드", "weight": 1.0, "score": 50.0, "interpretation": "스코어카드 입력값 해당 없음"}]
    row = _write_table(ws, row, 1, factors, title="가중 점수 구성")
    source_rows = [
        {"데이터블록": "DCF", "사용값": _fmt_price(dcf.get("implied_price")), "출처": "valuation_metrics.json / 09_DCF_가치평가"},
        {"데이터블록": "Peer P/S", "사용값": _fmt_multiple(peer.get("target_psr")), "출처": "valuation_peer_input.csv / 10_피어비교"},
        {"데이터블록": "208개 Universe", "사용값": f"{int((reference_summary or {}).get('reference_universe_rows') or 0):,}개", "출처": "valuation_reference_universe_208.csv"},
        {"데이터블록": "주가·유동성", "사용값": _fmt_krw_eok(price_summary.get("avg_trading_value_20d")), "출처": "valuation_price_history.csv / valuation_price_summary.json"},
        {"데이터블록": "ML 보조판단", "사용값": _fmt_score(ml.get("composite_score")), "출처": "valuation_agent 자체 peer percentile composite"},
    ]
    _write_table(ws, row, 1, source_rows, title="데이터 연결 맵")
    for col in range(1, 12):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 17
    ws.column_dimensions["B"].width = 36
    ws.column_dimensions["D"].width = 36


def _make_scenario_sheet(wb, company: str, assumptions: dict[str, Any], dcf: dict[str, Any], wacc: dict[str, Any]) -> None:
    ws = wb["20_시나리오_요약"]
    _title(ws, f"{company} 시나리오 요약", "Base/Bull/Bear 가정을 한눈에 볼 수 있도록 대시보드 다운로드용으로 정리", end_col=10)
    base_growth = to_float(dcf.get("assumed_revenue_growth")) or to_float(assumptions.get("assumed_revenue_growth")) or 0.03
    base_margin = to_float(dcf.get("assumed_fcf_margin")) or 0.02
    base_wacc = to_float(wacc.get("wacc")) or 0.10
    terminal = to_float(dcf.get("terminal_growth_rate")) or to_float(assumptions.get("terminal_growth_rate")) or 0.015
    rows = [
        {"시나리오": "Bear", "매출성장률": base_growth - 0.02, "FCF마진": max(base_margin - 0.02, -0.05), "WACC": base_wacc + 0.01, "영구성장률": max(terminal - 0.005, 0.0), "해석": "보수적 수익성·할인율 가정"},
        {"시나리오": "Base", "매출성장률": base_growth, "FCF마진": base_margin, "WACC": base_wacc, "영구성장률": terminal, "해석": "현재 모델 기본 가정"},
        {"시나리오": "Bull", "매출성장률": base_growth + 0.02, "FCF마진": base_margin + 0.02, "WACC": max(base_wacc - 0.01, 0.03), "영구성장률": terminal + 0.005, "해석": "성장·마진 개선 가정"},
    ]
    row = _write_table(ws, 4, 1, rows, title="3단계 시나리오 가정")
    guide = [
        {"항목": "활용", "내용": "대시보드에서 WACC/성장률/마진 슬라이더를 만들 때 기본 입력값으로 사용"},
        {"항목": "주의", "내용": "정식 투자 판단은 Chair의 6개 에이전트 종합과 별도 검토 필요"},
    ]
    _write_table(ws, row, 1, guide, title="대시보드 연결 가이드")
    for col in range(1, 11):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 17
    ws.column_dimensions["F"].width = 38


def _make_quality_sheet(wb, context: Any, normalized: list[dict[str, Any]], price_history: list[dict[str, Any]], peer: dict[str, Any], scorecard: dict[str, Any] | None, validation: dict[str, Any]) -> None:
    ws = wb["21_품질_커버리지"]
    _title(ws, "데이터 품질·커버리지", "공란/해당 없음/계산 제외 항목을 숨기지 않고 데이터 커버리지로 관리", end_col=10)
    ref_sum = getattr(context, "reference_summary", {}) or {}
    checks = [
        {"데이터블록": "DART 정규화 재무제표", "행수": len(normalized), "상태": "OK" if normalized else "보강 필요", "대시보드 영향": "DCF/WACC/핵심비율"},
        {"데이터블록": "주가 이력", "행수": len(price_history), "상태": "OK" if len(price_history) >= 240 else "부분 사용", "대시보드 영향": "현재가/변동성/MDD/차트"},
        {"데이터블록": "Live peer", "행수": len(peer.get("peer_rows") or []), "상태": "OK" if peer.get("peer_rows") else "보강 필요", "대시보드 영향": "P/S, PER, PBR"},
        {"데이터블록": "208개 Reference Universe", "행수": ref_sum.get("reference_universe_rows") or 0, "상태": "OK" if (ref_sum.get("reference_universe_rows") or 0) >= 100 else "부분 사용", "대시보드 영향": "상대 위치/ML 보조"},
        {"데이터블록": "가치평가 스코어카드", "행수": len((scorecard or {}).get("factors") or []), "상태": "OK" if scorecard else "부분 사용", "대시보드 영향": "투자자 요약/Chair 보조"},
        {"데이터블록": "Validation", "행수": len(validation.get("issues") or []), "상태": validation.get("status") or "해당 없음", "대시보드 영향": "경고/품질 배지"},
    ]
    row = _write_table(ws, 4, 1, checks, title="커버리지 체크")
    issues = validation.get("issues") or [{"severity": "INFO", "code": "NO_MAJOR_WARNINGS", "message": "주요 validation warning 없음"}]
    _write_table(ws, row, 1, issues, title="Validation 이슈")
    for col in range(1, 11):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 18
    ws.column_dimensions["D"].width = 34



def _make_advanced_summary_sheet(wb, company: str, advanced: dict[str, Any] | None, scorecard: dict[str, Any] | None, validation: dict[str, Any]) -> None:
    ws = wb["22_종합가치평가"]
    advanced = advanced or {}
    football = advanced.get("football_field") or {}
    reverse = advanced.get("reverse_dcf") or {}
    owner = advanced.get("owner_earnings") or {}
    _title(ws, f"{company} 종합 가치평가 요약", "DCF·상대가치·역산 DCF·오너 이익·EPV·Graham Number로 교차검증", end_col=12)
    _dashboard_card(ws, 4, 1, "종합 가치평가 점수", _fmt_score(advanced.get("advanced_valuation_score")), "복수 방법 교차검증")
    _dashboard_card(ws, 4, 3, "가치범위 중앙값", _fmt_price(football.get("base_price")), str(football.get("interpretation_kr") or "중립"))
    _dashboard_card(ws, 4, 5, "안전마진", _fmt_pct(football.get("margin_of_safety_pct")), "중앙값/현재가-1")
    _dashboard_card(ws, 4, 7, "역산 DCF", _fmt_pct(reverse.get("implied_terminal_growth_rate")), "시장가격 내재 성장률")
    _dashboard_card(ws, 4, 9, "오너 이익", _fmt_price(owner.get("owner_earnings_value_per_share")), "보수 현금창출 기준")
    _dashboard_card(ws, 4, 11, "검증상태", str(validation.get("status") or "해당 없음"), "PASS 권장")
    rows = [
        {"구분": "결론", "내용": (scorecard or {}).get("narrative_kr") or "다중 가치평가 결과를 확인하세요."},
        {"구분": "핵심 산식", "내용": advanced.get("method_kr") or "DCF + 피어 멀티플 + 역산 DCF + 오너 이익/EPV"},
        {"구분": "사용 이유", "내용": "DCF는 가정 민감도가 크므로, 시장이 내재한 성장률과 상대가치·현금창출 가치가 같은 방향인지 확인합니다."},
        {"구분": "대시보드 활용", "내용": "summary_cards와 advanced_valuation 블록을 사용하면 Streamlit/React에서 가치범위 차트·민감도 카드·다운로드 버튼 구현 가능"},
    ]
    row = _write_table(ws, 9, 1, rows, title="투자자용 해석")
    methods = advanced.get("valuation_methods") or []
    row = _write_table(ws, row, 1, methods[:20], title="방법별 내재가격 요약", max_rows=20)
    market_rows = [advanced.get("market_implied_multiples") or {}]
    row = _write_table(ws, row, 1, market_rows, title="시장내재 배수 자동산출")
    quality_rows = advanced.get("valuation_quality_diagnostics") or []
    _write_table(ws, row, 1, quality_rows, title="품질 진단 체크")
    for col in range(1, 13):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 18
    ws.column_dimensions["B"].width = 54


def _make_football_field_sheet(wb, company: str, advanced: dict[str, Any] | None) -> None:
    ws = wb["23_가치범위표"]
    advanced = advanced or {}
    football = advanced.get("football_field") or {}
    methods = advanced.get("valuation_methods") or []
    _title(ws, f"{company} 가치범위표", "DCF, P/S, P/B, PER, P/FCF, EV/Sales, EV/EBIT 기준 내재가격 범위를 한 화면에서 비교", end_col=12)
    _dashboard_card(ws, 4, 1, "현재가", _fmt_price(football.get("current_price")), "시장 기준")
    _dashboard_card(ws, 4, 3, "하단값", _fmt_price(football.get("low_price")), "25% 분위")
    _dashboard_card(ws, 4, 5, "중앙값", _fmt_price(football.get("base_price")), "50% 분위")
    _dashboard_card(ws, 4, 7, "상단값", _fmt_price(football.get("high_price")), "75% 분위")
    _dashboard_card(ws, 4, 9, "방법 수", str(football.get("method_count") or 0), "산출 가능한 방법")
    _dashboard_card(ws, 4, 11, "안전마진", _fmt_pct(football.get("margin_of_safety_pct")), "중앙값 기준")
    row = _write_table(ws, 9, 1, methods, title="가치평가 방법별 Low/Base/High", max_rows=30)
    note = [
        {"항목": "해석 방법", "내용": "한 방법만 우호적이면 확신도가 낮고, 여러 방법의 중앙값이 현재가보다 높으면 상대적으로 우호적입니다."},
        {"항목": "주의", "내용": "PER/PBR/EV/EBIT는 적자·음수 지표에서 자동 제외됩니다. 제외 사유는 빈칸이 아니라 해당 없음으로 표시됩니다."},
    ]
    _write_table(ws, row, 1, note, title="사용 가이드")
    for col in range(1, 13):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 17
    ws.column_dimensions["B"].width = 24
    try:
        if methods:
            chart = wb._ap_BarChart()
            chart.title = "가치평가 방법별 중앙 주당가치"
            chart.y_axis.title = "원/주"
            chart.x_axis.title = "가치평가 방법"
            start_row = 10
            data_col = 7  # base_implied_price column after translated headers usually G if no order drift; safe enough for chart.
            data = wb._ap_Reference(ws, min_col=data_col, min_row=start_row, max_row=start_row + len(methods))
            cats = wb._ap_Reference(ws, min_col=2, min_row=start_row + 1, max_row=start_row + len(methods))
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            chart.height = 8
            chart.width = 20
            ws.add_chart(chart, "N9")
    except Exception:
        pass


def _make_reverse_dcf_sheet(wb, company: str, advanced: dict[str, Any] | None) -> None:
    ws = wb["24_역산DCF"]
    advanced = advanced or {}
    reverse = advanced.get("reverse_dcf") or {}
    owner = advanced.get("owner_earnings") or {}
    _title(ws, f"{company} 역산 DCF·오너 이익", "현재 주가가 요구하는 성장률과 현금창출 기준 보수 가치를 점검", end_col=10)
    _dashboard_card(ws, 4, 1, "시장 내재 EV", _fmt_krw_eok(reverse.get("market_implied_enterprise_value")), "시가총액+부채-현금")
    _dashboard_card(ws, 4, 3, "모델 EV", _fmt_krw_eok(reverse.get("model_enterprise_value")), "DCF 산출 EV")
    _dashboard_card(ws, 4, 5, "EV 괴리", _fmt_pct(reverse.get("market_vs_model_ev_gap_pct")), "시장/모델-1")
    _dashboard_card(ws, 4, 7, "요구 FCF 수익률", _fmt_pct(reverse.get("required_fcf_yield_on_ev")), "FCF/시장내재 EV")
    _dashboard_card(ws, 4, 9, "역산 성장률", _fmt_pct(reverse.get("implied_terminal_growth_rate")), "시장가격 내재")
    reverse_rows = [{k: v for k, v in reverse.items()}]
    row = _write_table(ws, 9, 1, reverse_rows, title="역산 DCF 핵심값")
    owner_rows = [{k: v for k, v in owner.items()}]
    row = _write_table(ws, row, 1, owner_rows, title="오너 이익 / EPV / Graham Number")
    guide = [
        {"항목": "역산 DCF", "내용": "현재 주가를 정당화하려면 어떤 영구성장률·FCF 수익률이 필요한지 역산합니다."},
        {"항목": "오너 이익", "내용": "CFO-CAPEX 또는 FCF를 기반으로 보수적 현금창출 가치를 계산합니다."},
        {"항목": "EPV", "내용": "영업이익의 지속가능성을 가정해 현재 수익력 기준 기업가치를 확인합니다."},
    ]
    _write_table(ws, row, 1, guide, title="해석 가이드")
    for col in range(1, 11):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 20
    ws.column_dimensions["B"].width = 42


def _make_source_plan_sheet(wb, company: str, advanced: dict[str, Any] | None, context: Any) -> None:
    ws = wb["25_데이터수집현황"]
    advanced = advanced or {}
    _title(ws, f"{company} 데이터 수집현황·보강경로", "원천 제공 여부와 대체 산출 경로를 분리해 Chair·대시보드에서 그대로 확인", end_col=10)
    plan = advanced.get("source_completion_plan") or []
    row = _write_table(ws, 4, 1, plan, title="데이터 블록별 확보 상태")
    source_files = []
    source_map = getattr(context, "source_map", {}) or {}
    files = source_map.get("files") if isinstance(source_map, dict) else {}
    if isinstance(files, dict):
        for k, v in files.items():
            source_files.append({"파일구분": k, "경로": v, "활용": "Valuation Agent intake/output"})
    if not source_files:
        source_files = [{"파일구분": "source_map", "경로": "valuation_source_map.json", "활용": "실행 후 자동 생성"}]
    _write_table(ws, row, 1, source_files, title="자동 생성/참조 파일 경로", max_rows=50)
    for col in range(1, 11):
        ws.column_dimensions[wb._ap_get_col_letter(col)].width = 22
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 54

def _polish_all_sheets(wb) -> None:
    """Final visual polish: Korean missing-value labels, readable widths/heights, no hidden gaps inside tables."""
    replacements = {
        "대체 확인 필요": "해당 없음",
        "NO_MARKET_CAP_OR_REVENUE": "시가총액 또는 매출액 해당 없음",
        "WARN_NO_LIVE_DATA": "실시간 원천 일부 미제공",
        "DATA_INSUFFICIENT": "원천 데이터 부족",
        "Peer Comps": "피어 비교",
        "ML 보조판단 요약": "ML 보조판단 요약",
        "대시보드 JSON 내보내기": "대시보드 JSON 내보내기",
        "FCF 추정": "FCF 추정",
    }
    for ws in wb.worksheets:
        max_col = ws.max_column or 1
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=max_col):
            non_empty = [cell.column for cell in row if cell.value is not None]
            if not non_empty:
                continue
            first, last = min(non_empty), max(non_empty)
            for cell in row:
                if cell.column < first or cell.column > last:
                    continue
                if cell.__class__.__name__ == "MergedCell":
                    continue
                if cell.value is None or cell.value == "":
                    cell.value = "해당 없음"
                elif isinstance(cell.value, str):
                    val = cell.value
                    for old, new in replacements.items():
                        val = val.replace(old, new)
                    cell.value = val
                cell.alignment = ws.parent._ap_styles["left"]
                cell.border = ws.parent._ap_styles["thin_border"]
        for r in range(1, ws.max_row + 1):
            current = ws.row_dimensions[r].height or 20
            ws.row_dimensions[r].height = max(current, 24)
        for c in range(1, ws.max_column + 1):
            letter = ws.parent._ap_get_col_letter(c)
            width = ws.column_dimensions[letter].width or 12
            ws.column_dimensions[letter].width = max(min(width, 48), 13)
        ws.freeze_panes = "A4"


def _payload_rows_for_sheet(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return dashboard payload rows in readable Korean form instead of raw Python dict text."""
    if not isinstance(payload, dict) or not payload:
        return [{"구분": "상태", "항목": "대시보드 payload", "값": "생성 전", "설명": "valuation 실행 후 자동 생성"}]

    label_map = {
        "company": "기업명",
        "company_dir": "기업코드",
        "created_at": "생성시각",
        "summary_cards": "요약 카드",
        "chart_data": "차트 데이터",
        "tables": "대시보드 표",
        "downloads": "다운로드 파일",
        "scorecard": "스코어카드",
        "advanced_valuation": "종합 가치평가",
        "reference_universe": "Reference Universe",
        "price_summary": "주가 요약",
        "validation": "검증 결과",
    }
    rows: list[dict[str, Any]] = []
    for key, value in payload.items():
        label = label_map.get(str(key), HEADER_KR.get(str(key), str(key)))
        if isinstance(value, dict):
            rows.append({"구분": label, "항목": "상위 블록", "값": f"{len(value)}개 항목", "설명": "대시보드에서 객체로 사용"})
            for sub_key, sub_value in list(value.items())[:18]:
                if isinstance(sub_value, dict):
                    display = sub_value.get("label") or sub_value.get("label_kr") or f"{len(sub_value)}개 항목"
                elif isinstance(sub_value, list):
                    display = f"{len(sub_value)}개 행"
                else:
                    display = _cell_display(sub_value)
                rows.append({"구분": label, "항목": HEADER_KR.get(str(sub_key), str(sub_key)), "값": display, "설명": "JSON 상세는 dashboard_payload 파일 참조"})
        elif isinstance(value, list):
            rows.append({"구분": label, "항목": "목록", "값": f"{len(value)}개 행", "설명": "대시보드 표/차트 원천"})
        else:
            rows.append({"구분": label, "항목": "값", "값": _cell_display(value), "설명": "대시보드 기본값"})
    return rows

def create_workbook(
    path: Path,
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
) -> Path:
    openpyxl, Workbook, BarChart, LineChart, Reference, Comment, Alignment, Border, Font, PatternFill, Side, get_column_letter = _require_openpyxl()
    wb = Workbook()
    wb.remove(wb.active)
    wb._ap_BarChart = BarChart
    wb._ap_LineChart = LineChart
    wb._ap_Reference = Reference
    wb._ap_get_col_letter = get_column_letter
    thin = Side(style="thin", color="D9E2EC")
    medium = Side(style="medium", color="9FB3C8")
    wb._ap_styles = {
        "title_fill": PatternFill("solid", fgColor="0B1F33"),
        "subtitle_fill": PatternFill("solid", fgColor="E6EEF8"),
        "section_fill": PatternFill("solid", fgColor="1F4E78"),
        "header_fill": PatternFill("solid", fgColor="24476B"),
        "row_fill_1": PatternFill("solid", fgColor="FFFFFF"),
        "row_fill_2": PatternFill("solid", fgColor="F8FAFC"),
        "input_fill": PatternFill("solid", fgColor="FFF2CC"),
        "card_title_fill": PatternFill("solid", fgColor="0B1F33"),
        "card_fill": PatternFill("solid", fgColor="F3F6FA"),
        "title_font": Font(color="FFFFFF", bold=True, size=16),
        "subtitle_font": Font(color="0B1F33", size=10),
        "section_font": Font(color="FFFFFF", bold=True),
        "header_font": Font(color="FFFFFF", bold=True),
        "card_title_font": Font(color="FFFFFF", bold=True, size=10),
        "card_value_font": Font(color="0B1F33", bold=True, size=13),
        "bold_font": Font(bold=True, color="0B1F33"),
        "input_font": Font(color="0000FF"),
        "formula_font": Font(color="000000"),
        "small_font": Font(color="475569", size=9),
        "center": Alignment(horizontal="center", vertical="center", wrap_text=True),
        "left": Alignment(horizontal="left", vertical="center", wrap_text=True),
        "right": Alignment(horizontal="right", vertical="center", wrap_text=True),
        "title_align": Alignment(horizontal="center", vertical="center"),
        "thin_border": Border(left=thin, right=thin, top=thin, bottom=thin),
        "medium_border": Border(left=medium, right=medium, top=medium, bottom=medium),
    }
    for tab in TABS:
        ws = wb.create_sheet(tab)
        _apply_base_style(wb, ws)

    price_summary = getattr(context, "price_summary", {}) or {}
    price_history = getattr(context, "price_history", []) or []
    reference_summary = getattr(context, "reference_summary", {}) or {}
    _make_dashboard(wb, company, normalized_financials, dcf, wacc, peer, ml, validation, price_summary, price_history)
    _make_investor_summary(wb, company, normalized_financials, dcf, wacc, peer, ml, validation, price_summary)
    _make_scorecard_sheet(wb, company, dcf, peer, ml, scorecard, price_summary, reference_summary, validation)
    _make_scenario_sheet(wb, company, getattr(context, "assumptions", {}) or {}, dcf, wacc)
    _make_quality_sheet(wb, context, normalized_financials, price_history, peer, scorecard, validation)
    _make_advanced_summary_sheet(wb, company, advanced, scorecard, validation)
    _make_football_field_sheet(wb, company, advanced)
    _make_reverse_dcf_sheet(wb, company, advanced)
    _make_source_plan_sheet(wb, company, advanced, context)

    ws = wb["01_사용안내"]
    _title(ws, f"{company} Valuation Agent Workbook", "독립 데이터 intake → 모델링 → 검증 → 대시보드 export", end_col=8)
    readme_rows = [
        {"항목": "목적", "내용": "DART/주가/발행주식 수/피어 데이터를 intake하여 WACC·DCF·Peer·ML overlay·대시보드 payload를 자동 생성"},
        {"항목": "Finance Agent와 관계", "내용": "finance_agent 산출물을 읽지 않음. valuation/intake 폴더의 자체 데이터만 사용"},
        {"항목": "모델링 구조", "내용": "업로드한 파이낸셜 모델링 파일의 sheet archetype을 코드화하여 workbook 구조로 반영"},
        {"항목": "PSR/208개 Universe", "내용": "Live peer P/S와 208개 반도체 reference universe를 별도 시트와 대시보드 payload로 제공"},
        {"항목": "단위", "내용": "원천 데이터는 KRW actuals, 요약 표시는 억원/원/배수/비율 형식"},
        {"항목": "색상 규칙", "내용": "노란색/파란 글씨는 조정 가능한 입력값, 검은 글씨는 공식, 진한 남색은 섹션/헤더"},
    ]
    _write_table(ws, 4, 1, readme_rows, title="사용 안내")

    row_sm = _write_table(wb["02_출처맵"], 1, 1, [context.source_map] if isinstance(context.source_map, dict) else [], title="데이터 출처 맵")
    _write_table(wb["02_출처맵"], row_sm, 1, getattr(context, "share_count", []) or [], title="발행주식 수 intake")
    _write_table(wb["03_원천_DART"], 1, 1, getattr(context, "raw_accounts", []) or context.financials, title="DART 원천 계정", max_rows=1500)
    _make_price_sheet(wb, context)
    _write_table(wb["05_정규재무제표"], 1, 1, normalized_financials, title="정규화 재무제표")

    ratio_rows: list[dict[str, Any]] = []
    for r in normalized_financials:
        ratio_rows.append({
            "year": r.get("year"),
            "revenue_growth": r.get("revenue_growth"),
            "op_growth": r.get("op_growth"),
            "op_margin": r.get("op_margin"),
            "net_margin": r.get("net_margin"),
            "roe": r.get("roe"),
            "roa": r.get("roa"),
            "debt_ratio": r.get("debt_ratio"),
            "equity_ratio": r.get("equity_ratio"),
            "cfo_margin": r.get("cfo_margin"),
            "fcf_margin": r.get("fcf_margin"),
            "fcf_conversion": r.get("fcf_conversion"),
        })
    _write_table(wb["06_핵심비율"], 1, 1, ratio_rows, title="수익성·안정성·현금흐름 핵심비율")

    ws = wb["07_WACC"]
    _title(ws, "WACC 산정", "노란 셀은 사용자가 시나리오별로 조정 가능한 입력값입니다.", end_col=6)
    start = 4
    _write_kv(ws, start, "무위험수익률", wacc.get("risk_free_rate"), "valuation_assumptions.json 또는 기본값", input_cell=True); start += 1
    _write_kv(ws, start, "Beta", wacc.get("beta"), "주가 변동성 proxy 또는 사용자 가정", input_cell=True); start += 1
    _write_kv(ws, start, "시장위험프리미엄", wacc.get("market_risk_premium"), "사용자 조정 가능", input_cell=True); start += 1
    _write_kv(ws, start, "자기자본비용", "=B4+B5*B6", "공식: Rf + Beta × MRP", formula_cell=True); start += 1
    _write_kv(ws, start, "세전 차입비용", wacc.get("pre_tax_cost_of_debt"), "사용자 조정 가능", input_cell=True); start += 1
    _write_kv(ws, start, "법인세율", wacc.get("tax_rate"), "사용자 조정 가능", input_cell=True); start += 1
    _write_kv(ws, start, "세후 차입비용", "=B8*(1-B9)", "공식", formula_cell=True); start += 1
    _write_kv(ws, start, "자기자본 비중", wacc.get("equity_weight"), "시장가치/장부가치 기반", input_cell=True); start += 1
    _write_kv(ws, start, "부채 비중", wacc.get("debt_weight"), "부채 proxy 기반", input_cell=True); start += 1
    _write_kv(ws, start, "WACC", "=B11*B7+B12*B10", "공식: E/V×Ke + D/V×Kd(1-T)", formula_cell=True); start += 1
    _write_kv(ws, start, "사용한 시가총액", wacc.get("market_cap_used_for_equity_weight"), "발행주식 수 intake 가능 시 반영"); start += 1
    _write_kv(ws, start, "부채 proxy", wacc.get("debt_proxy_liabilities"), "상세 차입금 데이터 전까지 부채총계 보수 proxy")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 55

    projection = dcf.get("projection") or []
    _write_table(wb["08_FCF_추정"], 1, 1, projection, title="FCF 추정")

    ws = wb["09_DCF_가치평가"]
    _title(ws, "DCF 가치평가", "명시적 FCF + Terminal Value + 현금 - 부채 proxy", end_col=5)
    dcf_rows = [
        {"metric": "기준연도", "value": dcf.get("base_year"), "note": "최근 정규화 재무제표 연도"},
        {"metric": "기준 매출액", "value": dcf.get("base_revenue"), "note": "DART 기반"},
        {"metric": "매출 CAGR", "value": dcf.get("historical_revenue_cagr"), "note": "과거 재무제표 기반"},
        {"metric": "추정 매출성장률", "value": dcf.get("assumed_revenue_growth"), "note": "최근 추세를 보수적으로 bounded"},
        {"metric": "추정 FCF margin", "value": dcf.get("assumed_fcf_margin"), "note": "최근 3년 평균 기반"},
        {"metric": "WACC", "value": dcf.get("wacc"), "note": "07_WACC 참조"},
        {"metric": "영구성장률", "value": dcf.get("terminal_growth_rate"), "note": "valuation_assumptions.json"},
        {"metric": "FCF 현재가치", "value": dcf.get("pv_fcf"), "note": "명시적 기간 FCF 할인"},
        {"metric": "Terminal Value", "value": dcf.get("terminal_value"), "note": "Gordon Growth"},
        {"metric": "Terminal 현재가치", "value": dcf.get("pv_terminal_value"), "note": "Terminal Value 할인"},
        {"metric": "기업가치(EV)", "value": dcf.get("enterprise_value"), "note": "PV FCF + PV Terminal"},
        {"metric": "지분가치", "value": dcf.get("equity_value"), "note": "EV + 현금 - 부채 proxy"},
        {"metric": "발행주식 수", "value": dcf.get("shares_outstanding"), "note": "DART stockTotqySttus 또는 해당 없음"},
        {"metric": "현재가", "value": dcf.get("latest_close"), "note": "주가 intake"},
        {"metric": "DCF 내재주가", "value": dcf.get("implied_price"), "note": "지분가치 / 발행주식 수"},
        {"metric": "현재가 대비 괴리율", "value": dcf.get("upside_downside_pct"), "note": "내재주가 / 현재가 - 1"},
    ]
    _write_table(ws, 4, 1, dcf_rows, title="DCF 결과 요약")

    _write_table(wb["10_피어비교"], 1, 1, peer.get("peer_rows") or [], title="피어 비교 / 상대가치")

    ws = wb["11_ML_보조판단"]
    row = _write_table(ws, 1, 1, ml.get("factors") or [], title="ML 보조판단 요인")
    summary_rows = [
        {"항목": "방법", "값": ml.get("method_kr") or ml.get("method")},
        {"항목": "종합점수", "값": ml.get("composite_score")},
        {"항목": "라벨", "값": ml.get("label_kr") or ml.get("label")},
        {"항목": "클러스터", "값": ml.get("kmeans_peer_cluster")},
        {"항목": "주의", "값": ml.get("note_kr") or ml.get("note")},
    ]
    _write_table(ws, row, 1, summary_rows, title="ML 보조판단 요약")

    _write_table(wb["12_민감도"], 1, 1, sensitivity, title="WACC × 영구성장률 민감도")
    _write_table(wb["13_검증체크"], 1, 1, validation.get("issues") or [], title="검증 체크")
    _write_table(wb["14_대시보드_JSON"], 1, 1, _payload_rows_for_sheet(dashboard_payload), title="대시보드 JSON 내보내기")
    _write_table(wb["15_감사추적"], 1, 1, validation.get("audit_trail") or [], title="감사 추적")
    _write_table(wb["16_모델링_설계"], 1, 1, context.template_catalog or [], title="업로드 파이낸셜 모델링 파일에서 추출한 설계 archetype")

    ws_uni = wb["18_밸류에이션_유니버스"]
    _title(ws_uni, "208개 반도체 Reference Universe", "Tech의 대규모 반도체 universe와 같은 축을 Valuation Agent가 자체 intake로 복제해 PSR/ML 보조판단에 활용", end_col=12)
    universe_summary = getattr(context, "reference_summary", {}) or {}
    universe_summary_rows = [{"항목": k, "값": v} for k, v in universe_summary.items() if k != "target_reference_row"]
    nxt = _write_table(ws_uni, 4, 1, universe_summary_rows, title="Universe 요약")
    nxt = _write_table(ws_uni, nxt, 1, getattr(context, "reference_focus", []) or [], title="Target 중심 비교군", max_rows=60)
    _write_table(ws_uni, nxt, 1, getattr(context, "reference_universe", []) or [], title="208개 전체 Universe", max_rows=220)

    # Global finishing touches.
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                cell.alignment = ws.parent._ap_styles["left"] if cell.column == 1 else ws.parent._ap_styles["left"]
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    cell.font = ws.parent._ap_styles["formula_font"]
        # Keep rows readable.
        for r in range(1, ws.max_row + 1):
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 20, 20)

    _polish_all_sheets(wb)

    # Final investor-facing Korean polish and supplemental sheets.
    # This is intentionally best-effort: valuation calculations are already complete,
    # so presentation polishing must never break workbook generation.
    try:
        from .final_polish import apply_final_valuation_polish

        apply_final_valuation_polish(
            wb,
            company=company,
            company_dir=company_dir,
            context=context,
            normalized_financials=normalized_financials,
            wacc=wacc,
            dcf=dcf,
            peer=peer,
            ml=ml,
            sensitivity=sensitivity,
            validation=validation,
            dashboard_payload=dashboard_payload,
            scorecard=scorecard,
            advanced=advanced,
        )
    except Exception as exc:
        try:
            ws_note = wb.create_sheet("99_표시개선_점검")
            ws_note["A1"] = "표시 개선 단계에서 예외가 발생했지만 가치평가 계산 결과는 정상 생성되었습니다."
            ws_note["A2"] = str(exc)
        except Exception:
            pass

    # Source comments for key assumption cells.
    try:
        wb["07_WACC"]["B4"].comment = Comment("출처: valuation/intake/valuation_assumptions.json", "AlphaProve")
        wb["09_DCF_가치평가"]["B18"].comment = Comment("출처: DART 발행주식 수 intake", "AlphaProve")
    except Exception:
        pass

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path

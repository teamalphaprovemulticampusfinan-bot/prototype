from __future__ import annotations
from langgraph.graph import END, StateGraph
from .analyzer import analyze_node
from .data_loader import WorkbookData, get_static_data
from .schemas import MarketState
from .sources import fetch_dart_subsidy, fetch_market_news, fetch_oecd, fetch_stock
from .sector_semiconductor import load_market_semiconductor_snapshot


def build_market_graph(llm, workbook: WorkbookData):
    oecd_cache: dict = {}

    def collect_node(state: MarketState) -> dict:
        nonlocal oecd_cache
        company = state["company"]
        print(f"[{company}] 데이터 수집 중...")

        stock  = fetch_stock(company)
        dart   = fetch_dart_subsidy(company)
        news   = fetch_market_news("반도체 업황")
        static = get_static_data(company, workbook)
        try:
            sector_snapshot = load_market_semiconductor_snapshot(company=company)
            if sector_snapshot:
                static["market_semiconductor_daily"] = sector_snapshot
        except Exception as exc:
            static.setdefault("market_semiconductor_daily", {"load_error": str(exc)})

        # DB에서 DART 파싱 결과 읽기
        try:
            from .db_manager import get_conn
            import pandas as pd
            conn = get_conn()
            vc_df = pd.read_sql(
                "SELECT * FROM value_chain WHERE company_name=?", conn, params=(company,)
            )
            if not vc_df.empty:
                dart.update(vc_df.iloc[0].to_dict())
            conn.close()
        except Exception:
            pass

        if not oecd_cache:
            oecd_cache = fetch_oecd(workbook)

        print(f"[{company}] 수집 완료 - 주가 {stock.get('current_price', '?')}원")
        return {
            "stock_data":  stock,
            "oecd_data":   oecd_cache,
            "dart_data":   dart,
            "news_data":   news,
            "static_data": static,
        }

    def wrapped_analyze_node(state: MarketState) -> dict:
        return analyze_node(state, llm)

    builder = StateGraph(MarketState)
    builder.add_node("collect", collect_node)
    builder.add_node("analyze", wrapped_analyze_node)
    builder.set_entry_point("collect")
    builder.add_edge("collect", "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()
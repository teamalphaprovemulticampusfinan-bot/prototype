from .data_loader import get_static_data


def build_company_row(company, stock_data, oecd_data, dart_data, news_data, workbook):
    static_data = get_static_data(company, workbook)

    return {
        "company": company,
        "current_price": stock_data.get("current_price"),
        "week52_high": stock_data.get("week52_high"),
        "week52_low": stock_data.get("week52_low"),
        "beta": stock_data.get("beta"),
        "volume": stock_data.get("volume"),
        "price_change_5d": stock_data.get("price_change_5d"),

        "oecd_g20": oecd_data.get("G20"),
        "oecd_korea": oecd_data.get("한국"),
        "oecd_usa": oecd_data.get("미국"),
        "oecd_china": oecd_data.get("중국"),

        "latest_report": dart_data.get("latest_report"),
        "dart_date": dart_data.get("date"),

        "value_chain_position": static_data.get("chain", {}).get("position"),
        "products": static_data.get("chain", {}).get("products"),
        "process": static_data.get("chain", {}).get("process"),

        "news_titles": " | ".join([n.get("title", "") for n in news_data[:5]]),
        "news_dates": " | ".join([n.get("date", "") for n in news_data[:5]]),
    }
# src/market_agent/ntis_fetcher.py
from __future__ import annotations
import time
import xml.etree.ElementTree as ET

import requests

NTIS_KEY = "DEV_TEST_APPRV_KEY"

POLICY_KEYWORDS = {
    "후공정 장비":   ["TC본더", "후공정 장비", "HBM", "패키징 장비"],
    "반도체 소재":   ["반도체 소재", "소부장", "프리커서", "과산화수소"],
    "후공정 패키징": ["팬아웃", "WLP", "패키징", "후공정"],
}


def fetch_policy_trend(segment: str, keywords: list[str]) -> list[dict]:
    results = []
    for kw in keywords:
        year_funds  = {}
        year_counts = {}

        for year in ["2022", "2023", "2024", "2025", "2026"]:
            params = {
                "apprvKey":      NTIS_KEY,
                "collection":    "project",
                "SRWR":          kw,
                "searchFd":      "BI",
                "addQuery":      f"PY={year}/SAME",
                "startPosition": 1,
                "displayCnt":    100,
                "cmbnApiYn":     "Y",
            }
            try:
                res  = requests.get(
                    "https://www.ntis.go.kr/rndopen/openApi/public_project",
                    params=params, timeout=10
                )
                root  = ET.fromstring(res.text)
                total = int(root.findtext("TOTALHITS", "0"))
                year_counts[year] = total

                fund_sum = 0
                for hit in root.findall(".//HIT"):
                    fund = hit.findtext("GovernmentFunds", "0")
                    fund_sum += int(fund) if fund.isdigit() else 0
                year_funds[year] = fund_sum

            except Exception as e:
                print(f"  NTIS 오류 [{kw}/{year}]: {e}")
                year_counts[year] = 0
                year_funds[year]  = 0

            time.sleep(0.2)

        results.append({
            "segment":     segment,
            "keyword":     kw,
            "year_funds":  year_funds,
            "year_counts": year_counts,
        })
        print(f"  [{kw}] 완료")

    return results


def run_ntis_fetcher() -> list[dict]:
    all_trends = []
    for segment, keywords in POLICY_KEYWORDS.items():
        print(f"\n=== {segment} ===")
        trends = fetch_policy_trend(segment, keywords)
        all_trends.extend(trends)
    return all_trends
from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

import pandas as pd
import requests


KRX_URL = "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010305"
API_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"


def _sync_playwright() -> Any:
    """Load playwright only when the manual KRX session helper is used.

    This removes the IDE/Pylance yellow warning on
    `from playwright.sync_api import sync_playwright` in environments where
    playwright is not installed. The finance pipeline can still run without
    playwright; only the optional browser-login KRX helper needs it.
    """
    try:
        module = import_module("playwright.sync_api")
        return getattr(module, "sync_playwright")
    except Exception as exc:
        raise RuntimeError(
            "playwright is optional and is only needed for manual KRX browser-session collection. "
            "Install it only if you need this helper: "
            "pip install playwright && python -m playwright install chromium"
        ) from exc


def get_krx_session(headless: bool = False) -> requests.Session:
    sync_playwright = _sync_playwright()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        context = browser.new_context()
        page = context.new_page()

        page.goto(KRX_URL, wait_until="networkidle")

        if not headless:
            print("브라우저에서 KRX 로그인이 필요한 경우 로그인하세요.")
            input("로그인 완료 후 Enter: ")

        cookies = context.cookies()

        session = requests.Session()

        for c in cookies:
            session.cookies.set(
                name=c["name"],
                value=c["value"],
                domain=c.get("domain"),
                path=c.get("path", "/"),
            )

        browser.close()
        return session


def fetch_vkospi(session: requests.Session) -> pd.DataFrame:
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://data.krx.co.kr",
        "referer": KRX_URL,
        "user-agent": "Mozilla/5.0",
        "x-requested-with": "XMLHttpRequest",
    }

    payload = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT01403",
        "locale": "ko_KR",
        "indTpCd": "1",
        "idxIndCd": "300",
        "tboxidxCd_finder_drvetcidx0_0": "코스피 200 변동성지수",
        "idxCd": "1",
        "idxCd2": "300",
        "codeNmidxCd_finder_drvetcidx0_0": "코스피 200 변동성지수",
        "param1idxCd_finder_drvetcidx0_0": "",
        "csvxls_isNo": "false",
    }

    res = session.post(API_URL, headers=headers, data=payload, timeout=20)

    print("status:", res.status_code)
    print("response preview:", res.text[:300])

    if res.text.strip() == "LOGOUT":
        raise RuntimeError("KRX 세션이 LOGOUT 상태입니다. 브라우저 로그인 세션이 필요합니다.")

    res.raise_for_status()

    data = res.json()

    if "OutBlock_1" not in data:
        raise KeyError(f"OutBlock_1 없음. 응답: {data}")

    df = pd.DataFrame(data["OutBlock_1"])

    df = df.rename(
        columns={
            "TRD_DD": "date",
            "CLSPRC_IDX": "vkospi",
            "CMPPREVDD_IDX": "change",
            "FLUC_RT": "change_rate",
            "FLUC_TP_CD": "direction_code",
        }
    )

    df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d", errors="coerce")
    df["vkospi"] = pd.to_numeric(df["vkospi"].astype(str).str.replace(",", ""), errors="coerce")
    df["change"] = pd.to_numeric(df["change"].astype(str).str.replace(",", ""), errors="coerce")
    df["change_rate"] = pd.to_numeric(df["change_rate"].astype(str).str.replace(",", ""), errors="coerce")

    return df.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    OUTPUT_PATH = (
        Path(__file__).resolve().parents[3]
        / "data" / "_global_common" / "vkospi.csv"
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    session = get_krx_session(headless=False)
    df = fetch_vkospi(session)

    print(df.head())
    print(df.tail())

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {OUTPUT_PATH}")

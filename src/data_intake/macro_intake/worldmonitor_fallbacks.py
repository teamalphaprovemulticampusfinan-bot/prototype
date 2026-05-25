# worldmonitor_fallbacks.py
"""
WorldMonitor 참고형 Macro fallback collector.

목적
- GDELT 429/timeout, NewsAPI/Serper quota 부족, SMM 로그인 제한처럼 외부 수집이 일부 실패해도
  반도체 매크로/공급망/규제 신호를 최소한으로 계속 확보한다.
- 기존 AlphaProve 구조는 유지하고, 저장 위치는 data/_global_common/macro 하나로 통일한다.
- workspace에는 절대 쓰지 않는다.

참고한 WorldMonitor 아이디어
- Google News RSS를 fallback으로 사용
- 반도체/AI/하드웨어 RSS 피드와 정책/정부 피드 분리
- 공급망/원자재/항만 차질 같은 매크로 리스크를 별도 레이어로 저장
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import feedparser
import pandas as pd
import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xml,text/xml,*/*",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.7",
}


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() not in {"0", "false", "no", "off", ""}


def _clean(text: str | None, limit: int = 280) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _parse_date(value) -> pd.Timestamp:
    if not value:
        return pd.NaT
    try:
        return pd.to_datetime(value, utc=True).tz_localize(None)
    except Exception:
        return pd.NaT


def _domain_from_url(url: str) -> str:
    try:
        return re.sub(r"^www\.", "", str(url).split("/")[2])
    except Exception:
        return ""


def _is_english(text: str | None, threshold: float = 0.60) -> bool:
    if not text:
        return False
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    return (ascii_count / max(len(text), 1)) >= threshold


def _dedupe_by_title(df: pd.DataFrame, title_col: str = "title") -> pd.DataFrame:
    if df is None or df.empty or title_col not in df.columns:
        return pd.DataFrame() if df is None else df
    out = df.copy()
    out["_key"] = out[title_col].fillna("").str.lower().str.replace(r"\W+", " ", regex=True).str[:80]
    out = out.drop_duplicates(subset=["_key"]).drop(columns=["_key"])
    return out.reset_index(drop=True)


def _google_news_rss_url(query: str, *, days: int = 7, lang: str = "en-US", gl: str = "US") -> str:
    # Google News RSS supports search operators. `when:Xd` makes the fallback fresh.
    q = f"{query} when:{max(int(days), 1)}d"
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl={lang}&gl={gl}&ceid={gl}:en"


# WorldMonitor의 tech/hardware/news fallback 아이디어를 AlphaProve 반도체 도메인에 맞게 축소 적용.
SEMICONDUCTOR_NEWS_SOURCES = {
    "반도체_공급망": [
        {"name": "GoogleNews_SemiconductorSupply", "url": _google_news_rss_url('semiconductor supply chain OR chip shortage OR advanced packaging', days=7)},
        {"name": "GoogleNews_HBMMemory", "url": _google_news_rss_url('HBM DRAM memory semiconductor AI chip supply', days=7)},
        {"name": "TomHardware", "url": "https://www.tomshardware.com/feeds/all"},
        {"name": "SemiAnalysis", "url": "https://www.semianalysis.com/feed"},
        {"name": "SemiconductorDigest", "url": "https://www.semiconductordigest.com/feed/"},
    ],
    "반도체_수출규제": [
        {"name": "GoogleNews_ExportControl", "url": _google_news_rss_url('semiconductor export controls BIS entity list advanced chips', days=14)},
        {"name": "GoogleNews_ChinaChipControls", "url": _google_news_rss_url('China semiconductor export control gallium germanium rare earth', days=14)},
    ],
    "반도체_원자재": [
        {"name": "GoogleNews_GalliumGermanium", "url": _google_news_rss_url('gallium germanium export control semiconductor material', days=14)},
        {"name": "GoogleNews_RareEarth", "url": _google_news_rss_url('rare earth semiconductor supply chain China export', days=14)},
    ],
    "물류_항만_리스크": [
        {"name": "GoogleNews_Shipping", "url": _google_news_rss_url('shipping disruption port congestion Red Sea semiconductor supply chain', days=14)},
    ],
}

SEMICONDUCTOR_KEYWORDS = {
    "반도체_공급망": ["semiconductor", "chip", "HBM", "DRAM", "memory", "packaging", "foundry", "supply"],
    "반도체_수출규제": ["export", "control", "BIS", "entity list", "sanction", "chip", "semiconductor"],
    "반도체_원자재": ["gallium", "germanium", "rare earth", "helium", "copper", "semiconductor"],
    "물류_항만_리스크": ["shipping", "port", "freight", "Red Sea", "congestion", "supply chain"],
}


def fetch_semiconductor_worldmonitor_news(today: datetime, max_per_category: int = 15) -> pd.DataFrame:
    """GDELT 실패 시에도 쓸 수 있는 반도체 특화 RSS/Google News fallback."""
    if not _env_bool("MACRO_ENABLE_WORLDMONITOR_RSS", True):
        return pd.DataFrame()

    rows: list[dict] = []
    since = pd.Timestamp(today - timedelta(days=int(os.getenv("MACRO_WM_RSS_DAYS", "30"))))

    for category, feeds in SEMICONDUCTOR_NEWS_SOURCES.items():
        keywords = [kw.lower() for kw in SEMICONDUCTOR_KEYWORDS.get(category, [])]
        for meta in feeds:
            feed_url = meta["url"]
            source_name = meta.get("name") or _domain_from_url(feed_url)
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:50]:
                    title = _clean(entry.get("title", ""))
                    summary = _clean(entry.get("summary", ""), limit=500)
                    combined = f"{title} {summary}".lower()
                    if not title or not _is_english(title):
                        continue
                    if keywords and not any(kw.lower() in combined for kw in keywords):
                        continue
                    date = _parse_date(entry.get("published") or entry.get("updated"))
                    if pd.notna(date) and date < since:
                        continue
                    url = entry.get("link", "")
                    rows.append({
                        "source": f"WM_RSS:{source_name}",
                        "category": category,
                        "date": date,
                        "title": title,
                        "url": url,
                        "domain": _domain_from_url(url) or _domain_from_url(feed_url),
                    })
            except Exception as exc:
                print(f"  ⚠️ WM_RSS [{category}/{source_name}] 스킵: {exc}")
            time.sleep(float(os.getenv("MACRO_WM_RSS_SLEEP_SEC", "0.05")))

    df = pd.DataFrame(rows)
    if df.empty:
        print("  ⚠️ WM_RSS 반도체 뉴스 0건")
        return df

    df = _dedupe_by_title(df)
    df = df.sort_values(["category", "date"], ascending=[True, False]).groupby("category", as_index=False).head(max_per_category)
    df = df.sort_values(["category", "date"], ascending=[True, False]).reset_index(drop=True)
    print(f"  ✅ WM_RSS 반도체 뉴스 fallback {len(df)}건")
    return df


# NewsAPI/Serper/GDELT가 막힐 때 공식/준공식 RSS·Google News RSS로 규제 공고를 보강.


def fetch_federal_register_semiconductor_rules(today: datetime, max_rows: int = 20) -> pd.DataFrame:
    """Direct Federal Register API fallback for U.S. semiconductor/export rules.

    This avoids spending Serper quota and keeps at least one official-policy
    source even when GDELT/NewsAPI are rate-limited.
    """
    if not _env_bool("MACRO_ENABLE_FEDERAL_REGISTER_API", True):
        return pd.DataFrame()
    since = (pd.Timestamp(today) - pd.Timedelta(days=int(os.getenv("MACRO_FR_DAYS", "365")))).strftime("%Y-%m-%d")
    queries = [
        ("semiconductor export controls", "미국", "수출규제", "FederalRegister_BIS_semiconductor"),
        ("entity list advanced computing chips", "미국", "수출규제", "FederalRegister_entity_list"),
        ("PFAS semiconductor", "미국", "환경규제", "FederalRegister_PFAS_semiconductor"),
        ("greenhouse gas semiconductor", "미국", "환경규제", "FederalRegister_GHG_semiconductor"),
    ]
    rows: list[dict] = []
    endpoint = "https://www.federalregister.gov/api/v1/documents.json"
    for query, country, reg_type, source in queries:
        params = {
            "conditions[term]": query,
            "conditions[publication_date][gte]": since,
            "per_page": min(20, max_rows),
            "order": "newest",
            "fields[]": ["title", "html_url", "publication_date", "type"],
        }
        try:
            resp = requests.get(endpoint, params=params, headers=HEADERS, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")))
            resp.raise_for_status()
            for item in resp.json().get("results", []):
                title = _clean(item.get("title", ""), 260)
                if not title:
                    continue
                rows.append({
                    "country": country,
                    "type": reg_type,
                    "date": _parse_date(item.get("publication_date")),
                    "title": title,
                    "url": item.get("html_url", ""),
                    "source": f"WM_REG:{source}",
                })
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠️ FederalRegister [{source}] 스킵: {exc}")
        time.sleep(float(os.getenv("MACRO_FR_SLEEP_SEC", "0.05")))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return _dedupe_by_title(df).sort_values("date", ascending=False).head(max_rows).reset_index(drop=True)

REGULATORY_FALLBACK_SOURCES = [
    # 미국: 실제 공고/정책은 Federal Register/BIS/Commerce 쪽을 우선 감시
    {"country": "미국", "type": "수출규제", "source": "FR_BIS_ExportControls", "url": _google_news_rss_url('site:federalregister.gov BIS export controls semiconductor entity list', days=30)},
    {"country": "미국", "type": "수출규제", "source": "Commerce_BIS", "url": _google_news_rss_url('site:bis.doc.gov semiconductor export controls entity list advanced chips', days=30)},
    {"country": "미국", "type": "환경규제", "source": "EPA_Semiconductor", "url": _google_news_rss_url('site:epa.gov semiconductor PFAS greenhouse gas regulation', days=30)},
    # EU
    {"country": "EU", "type": "수출규제", "source": "EU_DualUse", "url": _google_news_rss_url('site:eur-lex.europa.eu dual-use export control semiconductor regulation', days=45)},
    {"country": "EU", "type": "환경규제", "source": "EU_CBAM", "url": _google_news_rss_url('site:ec.europa.eu CBAM carbon border adjustment semiconductor supply chain', days=45)},
    # 일본/중국은 공식 RSS 접근성이 낮아 Google News site 제한 fallback 사용
    {"country": "일본", "type": "수출규제", "source": "Japan_METI", "url": _google_news_rss_url('site:meti.go.jp export control semiconductor technology', days=45)},
    {"country": "중국", "type": "수출규제", "source": "China_MOFCOM", "url": _google_news_rss_url('site:mofcom.gov.cn export control gallium germanium semiconductor', days=45)},
    {"country": "중국", "type": "환경규제", "source": "China_MEE", "url": _google_news_rss_url('site:mee.gov.cn carbon emissions trading environmental regulation', days=45)},
]


def fetch_regulatory_worldmonitor_fallback(today: datetime, max_rows: int = 40) -> pd.DataFrame:
    if not _env_bool("MACRO_ENABLE_WORLDMONITOR_REG_FALLBACK", True):
        return pd.DataFrame()

    rows: list[dict] = []
    since = pd.Timestamp(today - timedelta(days=int(os.getenv("MACRO_WM_REG_DAYS", "180"))))

    df_fr = fetch_federal_register_semiconductor_rules(today)
    if df_fr is not None and not df_fr.empty:
        rows.extend(df_fr.to_dict("records"))

    for meta in REGULATORY_FALLBACK_SOURCES:
        try:
            parsed = feedparser.parse(meta["url"])
            for entry in parsed.entries[:25]:
                title = _clean(entry.get("title", ""))
                if not title or not _is_english(title):
                    continue
                date = _parse_date(entry.get("published") or entry.get("updated"))
                if pd.notna(date) and date < since:
                    continue
                rows.append({
                    "country": meta["country"],
                    "type": meta["type"],
                    "date": date,
                    "title": title,
                    "url": entry.get("link", ""),
                    "source": f"WM_REG:{meta['source']}",
                })
        except Exception as exc:
            print(f"  ⚠️ WM_REG [{meta['source']}] 스킵: {exc}")
        time.sleep(float(os.getenv("MACRO_WM_REG_SLEEP_SEC", "0.05")))

    df = pd.DataFrame(rows)
    if df.empty:
        print("  ⚠️ WM_REG 규제 fallback 0건")
        return df

    df = _dedupe_by_title(df)
    df = df.sort_values(["country", "type", "date"], ascending=[True, True, False]).head(max_rows).reset_index(drop=True)
    print(f"  ✅ WM_REG/FederalRegister 규제 fallback {len(df)}건")
    return df


def fetch_portwatch_disruptions(today: datetime) -> pd.DataFrame:
    """IMF PortWatch ArcGIS active disruption feed.

    WorldMonitor가 사용한 항만/물류 차질 레이어를 Python으로 축소 구현했다.
    실패해도 macro intake를 막지 않는다.
    """
    if not _env_bool("MACRO_ENABLE_PORTWATCH", True):
        return pd.DataFrame()

    base = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/portwatch_disruptions_database/FeatureServer/0/query"
    since = (pd.Timestamp(today) - pd.Timedelta(days=int(os.getenv("MACRO_PORTWATCH_DAYS", "30")))).strftime("%Y-%m-%d %H:%M:%S")
    params = {
        "where": f"todate > timestamp '{since}' OR todate IS NULL",
        "outFields": "eventid,eventtype,eventname,alertlevel,country,fromdate,todate,severitytext,affectedports,n_affectedports",
        "orderByFields": "fromdate DESC",
        "resultRecordCount": "500",
        "outSR": "4326",
        "f": "json",
    }
    try:
        r = requests.get(base, params=params, headers=HEADERS, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")))
        r.raise_for_status()
        body = r.json()
        if body.get("error"):
            raise RuntimeError(body["error"].get("message", "ArcGIS error"))
        rows = []
        for feat in body.get("features", []):
            a = feat.get("attributes") or {}
            event_name = _clean(a.get("eventname", ""))
            if not event_name:
                continue
            fromdate = pd.to_datetime(a.get("fromdate"), unit="ms", errors="coerce") if a.get("fromdate") else pd.NaT
            rows.append({
                "date": fromdate,
                "signal_type": "port_disruption",
                "country": a.get("country", ""),
                "event_type": a.get("eventtype", ""),
                "event_name": event_name,
                "alert_level": str(a.get("alertlevel", "")).upper(),
                "severity": _clean(a.get("severitytext", ""), limit=180),
                "affected_ports": _clean(a.get("affectedports", ""), limit=180),
                "affected_port_count": a.get("n_affectedports", None),
                "source": "IMF_PortWatch_ArcGIS",
                "url": "https://portwatch.imf.org/",
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("date", ascending=False).reset_index(drop=True)
        print(f"  ✅ PortWatch 항만/물류 차질 {len(df)}건")
        return df
    except Exception as exc:
        print(f"  ⚠️ PortWatch 스킵: {exc}")
        return pd.DataFrame()


def build_semiconductor_material_risk_snapshot(today: datetime) -> pd.DataFrame:
    """반도체 핵심 소재 공급 집중도 정적 snapshot.

    실시간 가격 수집이 막혀도 gallium/germanium/rare earth/helium 등 핵심 소재 리스크가
    Macro Agent에 최소한 전달되도록 하는 보조 테이블이다.
    """
    if not _env_bool("MACRO_ENABLE_MATERIAL_RISK_STATIC", True):
        return pd.DataFrame()

    date = pd.Timestamp(today.date())
    rows = [
        {
            "date": date,
            "signal_type": "critical_material_concentration",
            "material": "Gallium",
            "semiconductor_relevance": "compound semiconductor, power/RF device, LED, advanced chip supply chain",
            "dominant_supplier_note": "China-centered supply concentration; export control sensitivity high",
            "risk_level": "HIGH",
            "source": "WM_Static_CriticalMinerals",
            "url": "local_static_reference",
        },
        {
            "date": date,
            "signal_type": "critical_material_concentration",
            "material": "Germanium",
            "semiconductor_relevance": "fiber optics, infrared optics, semiconductor substrate/material ecosystem",
            "dominant_supplier_note": "China-centered supply concentration; export control sensitivity high",
            "risk_level": "HIGH",
            "source": "WM_Static_CriticalMinerals",
            "url": "local_static_reference",
        },
        {
            "date": date,
            "signal_type": "critical_material_concentration",
            "material": "Rare Earths",
            "semiconductor_relevance": "magnets, precision equipment, upstream electronics supply chain",
            "dominant_supplier_note": "high geographic concentration; downstream shock can affect equipment/components",
            "risk_level": "MEDIUM_HIGH",
            "source": "WM_Static_CriticalMinerals",
            "url": "local_static_reference",
        },
        {
            "date": date,
            "signal_type": "critical_material_concentration",
            "material": "Helium",
            "semiconductor_relevance": "wafer fabrication, cooling, leak detection, controlled atmosphere processes",
            "dominant_supplier_note": "supply interruptions can pressure fab operating cost and availability",
            "risk_level": "MEDIUM_HIGH",
            "source": "AlphaProve_Static_SemiconductorMaterials",
            "url": "local_static_reference",
        },
    ]
    return pd.DataFrame(rows)


def collect_semiconductor_supply_chain_risks(today: datetime) -> pd.DataFrame:
    frames = [
        build_semiconductor_material_risk_snapshot(today),
        fetch_portwatch_disruptions(today),
    ]
    frames = [df for df in frames if df is not None and not df.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)

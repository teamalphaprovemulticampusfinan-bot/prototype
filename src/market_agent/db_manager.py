# src/market_agent/db_manager.py
from __future__ import annotations
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "market_issues.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db():
    conn = get_conn()

    # 밸류체인 테이블
    conn.execute("""
    CREATE TABLE IF NOT EXISTS value_chain (
        company_name     TEXT,
        vc_role          TEXT,
        direct_flag      TEXT,
        platform_flag    TEXT,
        domestic_peers   TEXT,
        global_peers     TEXT,
        competition_intensity TEXT,
        differentiation  TEXT,
        confidence       TEXT,
        evidence_summary TEXT,
        rcept_no         TEXT,
        updated_at       TEXT
    )
    """)

    # 산업 성장률 테이블
    conn.execute("""
    CREATE TABLE IF NOT EXISTS industry_growth (
        segment       TEXT,
        cagr_pct      REAL,
        source_name   TEXT,
        update_method TEXT,
        confidence    TEXT
    )
    """)

    # 경쟁구조 테이블
    conn.execute("""
    CREATE TABLE IF NOT EXISTS competition (
        company_name          TEXT,
        peer_group            TEXT,
        domestic_peers        TEXT,
        global_peers          TEXT,
        competition_intensity TEXT,
        differentiation       TEXT,
        updated_at            TEXT
    )
    """)

    # 정부 R&D 정책 트렌드
    conn.execute("""
    CREATE TABLE IF NOT EXISTS policy_trend (
        segment    TEXT,
        keyword    TEXT,
        year       TEXT,
        proj_count INTEGER,
        gov_fund   INTEGER,
        updated_at TEXT
    )
    """)

    conn.commit()
    conn.close()
    print(f"✅ DB 초기화 완료: {DB_PATH}")
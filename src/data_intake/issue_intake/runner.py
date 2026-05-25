from __future__ import annotations

from pprint import pprint
from .collector import fetch_news_for_company, fetch_rss_articles
from .config import SETTINGS
from .excel_loader import load_excel
from .preprocessor import (
    build_company_context,
    build_news_context,
    filter_company_keywords,
    filter_company_rss,
)
from .schema import PipelineOutput, RawStats


def collect_and_preprocess(company_name: str | None = None) -> PipelineOutput:
    company = company_name or SETTINGS.default_company

    df_keywords, df_news = load_excel()

    related_rows = filter_company_keywords(df_keywords, company)

    news_items = fetch_news_for_company(company)

    rss_articles = fetch_rss_articles()
    rss_items = filter_company_rss(company, rss_articles)

    company_context = build_company_context(related_rows)
    news_context = build_news_context(news_items, rss_items)

    return PipelineOutput(
        company_name=company,
        related_rows=related_rows,
        news_items=news_items,
        rss_items=rss_items,
        company_context=company_context,
        news_context=news_context,
        raw=RawStats(
            keyword_rows=len(related_rows),
            news_count=len(news_items),
            rss_count=len(rss_items),
            df_news_rows=0 if df_news is None else len(df_news),
        ),
    )


# ---------------------------------------------------------------------
# AlphaProve unified data_intake wrapper
# ---------------------------------------------------------------------
def run_issue_intake(company_dir: str, company: str | None = None, field: str = "반도체", **_: object):
    """Run issue intake and save an explicit manifest/output file.

    The Chair pipeline expects every selected agent to have a real intake stage.
    This wrapper keeps the original collect_and_preprocess logic intact while
    making issue intake visible to the unified data_intake manifest.
    """

    import json
    from datetime import datetime
    from common.data_paths import company_agent_dir

    started = datetime.now()
    company_name = company or company_dir
    out_dir = company_agent_dir(company_dir, "issue", create=True) / "intake"
    out_dir.mkdir(parents=True, exist_ok=True)

    status = "OK"
    error = None
    output_path = out_dir / "issue_intake_output.json"

    try:
        result = collect_and_preprocess(company_name)
        payload = result.model_dump(mode="json")
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        raw = payload.get("raw") or {}
    except Exception as exc:
        status = "PARTIAL"
        error = str(exc)
        raw = {}
        payload = {
            "company_name": company_name,
            "error": error,
            "note": "issue_intake failed; issue_agent can still use its local fallback sources.",
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "agent": "issue",
        "status": status,
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "company_dir": company_dir,
        "company": company_name,
        "field": field,
        "output_file": str(output_path),
        "keyword_rows": raw.get("keyword_rows", 0),
        "news_count": raw.get("news_count", 0),
        "rss_count": raw.get("rss_count", 0),
        "df_news_rows": raw.get("df_news_rows", 0),
        "error": error,
        "principle": "issue_intake collect_and_preprocess를 unified data_intake에서 실행",
    }
    manifest_path = out_dir / "issue_intake_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Issue Intake] manifest 저장: {manifest_path}")
    return manifest


def run_intake(company_dir: str, company: str | None = None, **kwargs: object):
    return run_issue_intake(company_dir=company_dir, company=company, **kwargs)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Issue Intake")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--field", default="반도체")
    args = parser.parse_args(argv)
    run_issue_intake(args.company_dir, args.company, field=args.field)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Phase 4B: SNS・ブログ・note調査（Google/Bing検索経由）"""
from __future__ import annotations

import argparse
import random
import re
import time

from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, today_str, write_csv
from phase4_helpers import (
    PHASE4B_FIELDS,
    extract_company_from_text,
    log_error_phase4,
    search_web,
)

OUT_CSV = BASE_DIR / "phase4b_sns_blog.csv"

QUERIES: list[tuple[str, str]] = [
    ("twitter", 'site:x.com "SES営業" "粗利" OR "インセンティブ" OR "還元"'),
    ("twitter", 'site:x.com "SES営業" "報酬" OR "年収" OR "給与"'),
    ("twitter", 'site:x.com "BP営業" "粗利" OR "インセンティブ"'),
    ("twitter", 'site:x.com "SES" "営業" "粗利30%" OR "粗利40%" OR "粗利50%"'),
    ("note", 'site:note.com "SES営業" "粗利" OR "インセンティブ" OR "還元"'),
    ("note", 'site:note.com "SES営業" "報酬設計" OR "給与体系"'),
    ("note", 'site:note.com "SES" "営業" "高還元"'),
    ("wantedly_story", 'site:wantedly.com/companies "SES営業" "インセンティブ" OR "粗利"'),
    (
        "blog",
        '"SES営業" "粗利" "インセンティブ" -site:note.com -site:x.com -site:wantedly.com -site:en-gage.net',
    ),
    ("blog", '"SES" "営業報酬" OR "営業給与" "粗利連動"'),
    ("blog", '"BP営業" "報酬設計" OR "インセンティブ設計"'),
    ("blog", '"SES営業" "ストック型" "報酬"'),
]


def _classify_url(url: str, default_type: str) -> str:
    u = url.lower()
    if "x.com" in u or "twitter.com" in u:
        return "twitter"
    if "note.com" in u:
        return "note"
    if "wantedly.com" in u:
        return "wantedly_story"
    return default_type


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--limit-queries", type=int, default=0)
    args = parser.parse_args()

    queries = QUERIES
    if args.limit_queries:
        queries = queries[: args.limit_queries]

    all_rows: list[dict] = []
    seen_urls: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        for idx, (source_type, query) in enumerate(queries, 1):
            print(f"[4B {idx}/{len(queries)}] {query[:80]}...", flush=True)
            try:
                results = search_web(
                    page,
                    query,
                    max_results=args.max_results,
                    max_pages=min(10, args.max_results // 10 + 1),
                    rate_limit=args.rate_limit,
                    phase="phase4b",
                )
            except Exception as e:
                log_error_phase4("phase4b", query, type(e).__name__, str(e))
                continue

            for r in results:
                url = r.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                company = extract_company_from_text(f"{title} {snippet}")
                st = _classify_url(url, source_type)
                all_rows.append(
                    {
                        "source_type": st,
                        "url": url,
                        "title": title[:300],
                        "snippet": snippet[:500],
                        "company_name_if_found": company[:200],
                        "crawl_date": today_str(),
                        "search_query": query[:300],
                    }
                )

            if idx % 3 == 0:
                print(f"  cumulative: {len(all_rows)} rows", flush=True)
            time.sleep(args.rate_limit + random.uniform(20, 35))

        browser.close()

    n = write_csv(OUT_CSV, PHASE4B_FIELDS, all_rows)
    print(f"phase4b_sns_blog.csv: {n} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

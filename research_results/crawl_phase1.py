# -*- coding: utf-8 -*-
"""Phase 1: 求人URL収集（検索エンジン + エンゲージ直接一覧）"""
from __future__ import annotations

import argparse
import time
import urllib.parse

from playwright.sync_api import sync_playwright

from crawl_common import (
    BASE_DIR,
    USER_AGENT,
    deduplicate_rows,
    filter_job_urls,
    log_error,
    write_csv,
)
from engage_helpers import ENGAGE_LIST_SOURCES, crawl_engage_listing_pages

SEARCH_QUERIES = [
    "site:en-gage.net SES営業 インセンティブ",
    "site:en-gage.net SES営業 粗利",
    "site:en-gage.net IT営業 インセンティブ",
    "site:green-japan.com SES営業 インセンティブ",
    "site:green-japan.com SES営業 粗利",
    "site:green-japan.com IT人材 営業",
    "site:jp.indeed.com SES営業 インセンティブ",
    "site:jp.indeed.com SES営業 歩合",
    "site:doda.jp SES営業 インセンティブ",
    "site:type.jp SES営業 インセンティブ",
    "site:tenshoku.mynavi.jp SES営業",
    "site:next.rikunabi.com SES営業",
    "site:wantedly.com SES営業 インセンティブ",
    "site:wantedly.com SES営業 粗利",
    '"SES営業" "粗利" "インセンティブ" -site:note.com -site:qiita.com',
    '"SES営業" "還元" "報酬" -site:note.com',
    '"BP営業" "粗利" "インセンティブ"',
    '"IT人材営業" "粗利" "歩合"',
    '"SES" "営業" "粗利30%" OR "粗利40%" OR "粗利50%"',
    '"SES" "営業" "ストック型" "インセンティブ"',
]

OUT_RAW = BASE_DIR / "phase1_urls.csv"
OUT_DEDUP = BASE_DIR / "phase1_urls_dedup.csv"
FIELDS = ["query", "result_url", "title", "snippet", "search_engine"]


def _bing_results(page, query: str, max_pages: int, rate_limit: float) -> list[dict]:
    rows: list[dict] = []
    for page_num in range(max_pages):
        first = page_num * 10 + 1
        url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query, "first": str(first)})
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            items = page.locator("li.b_algo h2 a").all()
            batch: list[dict] = []
            for a in items:
                href = a.get_attribute("href") or ""
                if href.startswith("http") and "bing.com" not in href:
                    batch.append(
                        {
                            "result_url": href.split("?")[0],
                            "title": a.inner_text(timeout=2000)[:200],
                            "snippet": "",
                            "search_engine": "bing",
                        }
                    )
            if not batch:
                break
            rows.extend(batch)
            print(f"  bing page {page_num + 1}: +{len(batch)}")
        except Exception as e:
            log_error("phase1_bing", url, type(e).__name__, str(e))
            break
        time.sleep(rate_limit)
    return [{"query": query, **r} for r in rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--rate-limit", type=float, default=5.0)
    parser.add_argument("--queries", type=str, default="")
    parser.add_argument("--direct-only", action="store_true")
    parser.add_argument("--skip-direct", action="store_true")
    parser.add_argument("--skip-search", action="store_true")
    args = parser.parse_args()

    queries = SEARCH_QUERIES
    if args.queries:
        queries = [q.strip() for q in args.queries.split(",") if q.strip()]

    all_rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        if not args.skip_direct:
            direct = crawl_engage_listing_pages(
                page, ENGAGE_LIST_SOURCES, args.max_pages, max(args.rate_limit, 5)
            )
            all_rows.extend(direct)
            print(f"engage direct listings: {len(direct)} URLs")

        if not args.direct_only and not args.skip_search:
            for idx, query in enumerate(queries, 1):
                print(f"[{idx}/{len(queries)}] bing: {query}")
                batch = _bing_results(page, query, min(args.max_pages, 3), args.rate_limit)
                all_rows.extend(batch)
                if idx % 5 == 0:
                    print(f"  cumulative: {len(all_rows)} URLs")
                time.sleep(args.rate_limit)

        browser.close()

    n_raw = write_csv(OUT_RAW, FIELDS, all_rows)
    deduped = deduplicate_rows(all_rows)
    job_filtered = filter_job_urls(deduped)
    n_dedup = write_csv(OUT_DEDUP, FIELDS, job_filtered)

    print(f"phase1_urls.csv: {n_raw} rows")
    print(f"phase1_urls_dedup.csv: {n_dedup} rows (dedup + job filter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

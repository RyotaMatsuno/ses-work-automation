# -*- coding: utf-8 -*-
"""Phase 4D: 人材紹介・転職口コミサイト（Google/Bingスニペットのみ）"""
from __future__ import annotations

import argparse
import random
import time

from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, today_str, write_csv
from phase4_helpers import (
    PHASE4D_FIELDS,
    extract_company_from_text,
    log_error_phase4,
    search_web,
)

OUT_CSV = BASE_DIR / "phase4d_review_sites.csv"

QUERIES: list[tuple[str, str]] = [
    ("openwork", 'site:openwork.jp "SES" "営業" "インセンティブ" OR "歩合"'),
    ("jobtalk", 'site:jobtalk.jp "SES" "営業" "インセンティブ"'),
    ("en-hyouban", 'site:en-hyouban.com "SES" "営業" "インセンティブ"'),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--rate-limit", type=float, default=10.0)
    args = parser.parse_args()

    all_rows: list[dict] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        for idx, (site, query) in enumerate(QUERIES, 1):
            print(f"[4D {idx}/{len(QUERIES)}] {site}: {query}", flush=True)
            try:
                results = search_web(
                    page,
                    query,
                    max_results=args.max_results,
                    max_pages=min(10, args.max_results // 10 + 1),
                    rate_limit=args.rate_limit,
                    phase="phase4d",
                )
            except Exception as e:
                log_error_phase4("phase4d", query, type(e).__name__, str(e))
                continue

            for r in results:
                url = r.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                company = extract_company_from_text(f"{title} {snippet}")
                all_rows.append(
                    {
                        "site": site,
                        "url": url,
                        "title": title[:300],
                        "snippet": snippet[:500],
                        "company_name": company[:200],
                        "crawl_date": today_str(),
                        "search_query": query[:300],
                    }
                )

            time.sleep(args.rate_limit + random.uniform(20, 35))

        browser.close()

    n = write_csv(OUT_CSV, PHASE4D_FIELDS, all_rows)
    print(f"phase4d_review_sites.csv: {n} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

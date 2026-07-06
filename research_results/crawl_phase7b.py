# -*- coding: utf-8 -*-
"""Phase 7B: 求人ボックス全件企業名抽出"""
from __future__ import annotations

import argparse
import re
import time
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, check_robots_txt, today_str, write_csv
from phase4_helpers import company_core
from phase7_helpers import (
    BING_UA,
    extract_company_from_job_title,
    fetch_bing_rss_snippets,
    log_error,
    normalize_company_name,
    progress_log,
)

OUT_CSV = BASE_DIR / "phase7b_kyujinbox_companies.csv"
FIELDS = ["company_name", "job_title", "search_query", "crawl_date"]

BASE = "https://xn--pckua2a7gp15o89zb.com"
SEARCH_QUERIES = [
    "SES営業",
    "SES 営業 インセンティブ",
    "IT営業 SES",
    "BP営業",
    "人材コーディネーター SES",
]


def _search_url(keyword: str, page_num: int) -> str:
    return f"{BASE}/search?q={quote(keyword)}&page={page_num}"


def _parse_listing_page(html: str) -> list[tuple[str, str]]:
    """一覧ページから (company_name, job_title) を抽出。"""
    soup = BeautifulSoup(html, "lxml")
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    selectors = [
        "a[href*='/job/']",
        "a[href*='/jb/']",
        "a[href*='/kJ/']",
        ".job-list-item",
        ".result",
        "article a",
    ]
    for sel in selectors:
        for a in soup.select(sel):
            href = a.get("href", "")
            text = a.get_text(" ", strip=True)
            if not text or len(text) < 5:
                continue
            if any(x in href for x in ("/adv/", "/news/", "help.", "corporate.")):
                continue
            company, job = extract_company_from_job_title(text)
            if not company:
                m = re.search(r"(株式会社|合同会社|有限会社)[^\s|｜]{1,40}", text)
                company = m.group(0) if m else ""
                job = text
            if not company and not re.search(r"営業|SES|コーディネーター", text):
                continue
            key = f"{company}|{job}"
            if key in seen:
                continue
            seen.add(key)
            results.append((normalize_company_name(company or text[:50]), job[:300]))

    return results


def _bing_kyujinbox(keyword: str, rate_limit: float) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    query = f'site:xn--pckua2a7gp15o89zb.com "{keyword}"'
    for item in fetch_bing_rss_snippets(query, max_results=50):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        combined = f"{title} {snippet}"
        company, job = extract_company_from_job_title(title)
        if not company:
            m = re.search(r"(株式会社|合同会社|有限会社)[^\s|｜]{1,40}", combined)
            company = m.group(0) if m else ""
        if not job:
            job = title
        if not company and not re.search(r"営業|SES|コーディネーター", combined):
            continue
        key = company_core(company or job)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "company_name": normalize_company_name(company or "不明"),
                "job_title": job[:300],
                "search_query": keyword,
                "crawl_date": today_str(),
            }
        )
    time.sleep(rate_limit)
    return rows


def crawl_kyujinbox_direct(page, keyword: str, rate_limit: float, max_pages: int = 50) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    for page_num in range(1, max_pages + 1):
        url = _search_url(keyword, page_num)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            html = page.content()
            if "ページが見つかりません" in page.inner_text("body") or len(html) < 1000:
                break
            batch = _parse_listing_page(html)
            if not batch:
                break
            new = 0
            for company, job in batch:
                key = company_core(company) or company
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "company_name": company,
                        "job_title": job,
                        "search_query": keyword,
                        "crawl_date": today_str(),
                    }
                )
                new += 1
            print(f"    page {page_num}: +{new} (total {len(rows)})", flush=True)
            if new == 0:
                break
        except Exception as e:
            log_error("phase7b", url, type(e).__name__, str(e))
            break
        time.sleep(rate_limit)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--max-pages", type=int, default=50)
    args = parser.parse_args()

    robots = check_robots_txt(BASE, "/search")
    print(f"[7B] kyujinbox robots: {robots.reason}", flush=True)

    all_rows: list[dict] = []

    if robots.allowed:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="ja-JP", user_agent=BING_UA).new_page()
            for i, keyword in enumerate(SEARCH_QUERIES, 1):
                print(f"[7B] query {i}/{len(SEARCH_QUERIES)}: {keyword}", flush=True)
                batch = crawl_kyujinbox_direct(page, keyword, args.rate_limit, args.max_pages)
                if not batch:
                    print(f"  direct empty → Bing fallback", flush=True)
                    batch = _bing_kyujinbox(keyword, args.rate_limit)
                all_rows.extend(batch)
                progress_log(len(all_rows), len(all_rows), "cumulative")
            browser.close()
    else:
        log_error("phase7b", BASE, "ROBOTS_SKIP", robots.reason)
        for i, keyword in enumerate(SEARCH_QUERIES, 1):
            print(f"[7B] Bing fallback {i}/{len(SEARCH_QUERIES)}: {keyword}", flush=True)
            all_rows.extend(_bing_kyujinbox(keyword, args.rate_limit))

    # URL重複ではなく company+job で dedupe
    deduped: dict[str, dict] = {}
    for r in all_rows:
        key = f"{company_core(r.get('company_name',''))}|{r.get('job_title','')}"
        deduped[key] = r

    final = list(deduped.values())
    n = write_csv(OUT_CSV, FIELDS, final)
    print(f"phase7b_kyujinbox_companies.csv: {n} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

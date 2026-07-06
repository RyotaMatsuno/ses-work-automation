# -*- coding: utf-8 -*-
"""Phase 2: Green直接クロール"""
from __future__ import annotations

import argparse
import re
import time
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawl_common import (
    BASE_DIR,
    USER_AGENT,
    check_robots_txt,
    log_error,
    retry_call,
    today_str,
    write_csv,
)

BASE_URL = "https://www.green-japan.com"
SEARCH_KEYWORDS = ["SES営業", "IT人材営業", "BP営業"]
OUT_CSV = BASE_DIR / "phase2_green.csv"
FIELDS = [
    "company_name",
    "employment_type",
    "salary_text",
    "incentive_text",
    "location",
    "employee_count",
    "founded_year",
    "job_url",
    "crawl_date",
    "raw_text",
    "search_keyword",
]

ROBOTS = check_robots_txt(BASE_URL, "/search")


def _search_url(keyword: str, page: int = 1) -> str:
    # Green検索API風URL（キーワード検索）
    return f"{BASE_URL}/search?keyword={quote(keyword)}&page={page}"


def _parse_job_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for a in soup.select("a[href*='/job/']"):
        href = a.get("href", "")
        full = urljoin(BASE_URL, href)
        if "/company/" in full and "/job/" in full and full not in urls:
            urls.append(full.split("?")[0])
    return urls


def _extract_detail(page, url: str, keyword: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    text = page.inner_text("body")
    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    company = ""
    for sel in ["h2 a", ".company-name", "a[href*='/company/']"]:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(strip=True)
            if t and "Green" not in t and len(t) < 100:
                company = t
                break

    employment = "正社員" if "正社員" in text else ""
    if "業務委託" in text:
        employment = "業務委託"
    elif "契約" in text:
        employment = "契約社員"

    salary = ""
    m = re.search(r"(\d{3,4}万円[〜~\-－]?\d{0,4}万円?)", text)
    if m:
        salary = m.group(1)

    incentive = ""
    for line in text.splitlines():
        if any(k in line for k in ["インセンティブ", "粗利", "歩合", "成果", "還元", "ストック"]):
            incentive += line.strip() + " "

    location = ""
    m_loc = re.search(r"東京都|大阪府|福岡県|(?:北海道|.{2,3}県)", text)
    if m_loc:
        location = m_loc.group(0)

    return {
        "company_name": company[:200],
        "employment_type": employment,
        "salary_text": salary[:300],
        "incentive_text": incentive[:1000].strip(),
        "location": location,
        "employee_count": "",
        "founded_year": "",
        "job_url": url,
        "crawl_date": today_str(),
        "raw_text": text[:8000],
        "search_keyword": keyword,
    }


def _collect_green_urls_from_phase1() -> list[str]:
    from crawl_common import read_csv

    urls: list[str] = []
    for row in read_csv(BASE_DIR / "phase1_urls_dedup.csv"):
        u = row.get("result_url", "")
        if "green-japan.com" in u and "/job/" in u and u not in urls:
            urls.append(u.split("?")[0])
    return urls


def crawl_green(max_pages: int, rate_limit: float, limit: int) -> list[dict]:
    delay = max(rate_limit, ROBOTS.crawl_delay)
    all_job_urls: list[str] = []

    if ROBOTS.allowed:
        print(f"green robots: {ROBOTS.reason}, delay={delay}s")
    else:
        print(f"green /search disallowed: {ROBOTS.reason}")
        print("fallback: phase1_urls_dedup.csv の Green 求人URLを使用")
        all_job_urls = _collect_green_urls_from_phase1()
        print(f"  phase1 green URLs: {len(all_job_urls)}")

    rows: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        if ROBOTS.allowed:
            for keyword in SEARCH_KEYWORDS:
                print(f"keyword: {keyword}")
                for page_num in range(1, max_pages + 1):
                    url = _search_url(keyword, page_num)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(2000)
                        links = _parse_job_links(page.content())
                    except Exception as e:
                        log_error("phase2_green", url, type(e).__name__, str(e))
                        break
                    new = [u for u in links if u not in all_job_urls]
                    all_job_urls.extend(new)
                    print(f"  page {page_num}: +{len(new)} (total {len(all_job_urls)})")
                    if not new:
                        break
                    time.sleep(delay)

        targets = all_job_urls[:limit] if limit else all_job_urls
        for i, job_url in enumerate(targets, 1):
            kw = next((k for k in SEARCH_KEYWORDS if k), "")
            try:
                row = retry_call(
                    lambda u=job_url, k=kw: _extract_detail(page, u, k),
                    phase="phase2_green",
                    url=job_url,
                )
                rows.append(row)
            except Exception:
                pass
            if i % 10 == 0:
                print(f"  detail {i}/{len(targets)}")
            time.sleep(delay)

        browser.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    rows = crawl_green(args.max_pages, args.rate_limit, args.limit)
    n = write_csv(OUT_CSV, FIELDS, rows)
    print(f"phase2_green.csv: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

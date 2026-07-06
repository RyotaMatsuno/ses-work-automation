# -*- coding: utf-8 -*-
"""Phase 2: エンゲージ直接クロール"""
from __future__ import annotations

import argparse
import re
import time

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
from engage_helpers import ENGAGE_LIST_SOURCES, crawl_engage_listing_pages, normalize_engage_job_url

BASE_URL = "https://en-gage.net"
OUT_CSV = BASE_DIR / "phase2_engage.csv"
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
]

ROBOTS = check_robots_txt(BASE_URL, "/search2/")


def _extract_detail(page, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    text = page.inner_text("body")
    norm_url = normalize_engage_job_url(url)

    company = ""
    m_co = re.search(r"株式会社[^\s\n|｜]+|合同会社[^\s\n|｜]+|有限会社[^\s\n|｜]+", text)
    if m_co:
        company = m_co.group(0)

    employment = ""
    for kw in ["正社員", "契約社員", "業務委託", "派遣", "アルバイト"]:
        if kw in text:
            employment = kw
            break

    salary = ""
    m = re.search(r"月給\s*[\d,]+円[^\n]{0,100}", text)
    if m:
        salary = m.group(0).strip()
    else:
        m2 = re.search(r"年俸\s*[\d,]+円[^\n]{0,100}", text)
        if m2:
            salary = m2.group(0).strip()

    incentive = ""
    for line in text.splitlines():
        if any(k in line for k in ["インセンティブ", "粗利", "歩合", "成果報酬", "コミッション", "還元"]):
            incentive += line.strip() + " "

    location = ""
    m_loc = re.search(
        r"(?:東京都|大阪府|北海道|京都府|.{2,3}県)[^\n]{0,50}", text
    )
    if m_loc:
        location = m_loc.group(0).strip()

    employee_count = ""
    m_emp = re.search(r"従業員数[^\d]*(\d[\d,]*)\s*人", text)
    if m_emp:
        employee_count = m_emp.group(1).replace(",", "")

    founded = ""
    m_f = re.search(r"設立[^\d]*(\d{4})\s*年", text)
    if m_f:
        founded = m_f.group(1)

    return {
        "company_name": company[:200],
        "employment_type": employment,
        "salary_text": salary[:300],
        "incentive_text": incentive[:1000].strip(),
        "location": location[:200],
        "employee_count": employee_count,
        "founded_year": founded,
        "job_url": norm_url,
        "crawl_date": today_str(),
        "raw_text": text[:8000],
    }


def crawl_engage(max_pages: int, rate_limit: float, limit: int) -> list[dict]:
    if not ROBOTS.allowed:
        print(f"SKIP engage: {ROBOTS.reason}")
        return []

    delay = max(rate_limit, ROBOTS.crawl_delay)
    print(f"engage robots: {ROBOTS.reason}, delay={delay}s")

    rows: list[dict] = []
    seen_jobs: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        list_rows = crawl_engage_listing_pages(page, ENGAGE_LIST_SOURCES, max_pages, delay)
        job_urls = [r["result_url"] for r in list_rows]
        print(f"listing URLs collected: {len(job_urls)}")

        targets = job_urls[:limit] if limit else job_urls
        for i, job_url in enumerate(targets, 1):
            if job_url in seen_jobs:
                continue
            seen_jobs.add(job_url)
            try:
                row = retry_call(lambda u=job_url: _extract_detail(page, u), phase="phase2_engage", url=job_url)
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
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    rows = crawl_engage(args.max_pages, args.rate_limit, args.limit)
    n = write_csv(OUT_CSV, FIELDS, rows)
    print(f"phase2_engage.csv: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

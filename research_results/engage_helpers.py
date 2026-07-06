# -*- coding: utf-8 -*-
"""エンゲージ求人URL・詳細抽出ヘルパー"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse, urlunparse

from playwright.sync_api import Page

ENGAGE_LIST_SOURCES = [
    ("engage:SESの求人", "https://en-gage.net/search2/SES%E3%81%AE%E6%B1%82%E4%BA%BA"),
    ("engage:IT営業", "https://en-gage.net/search2/IT%E5%96%B6%E6%A5%AD%E3%81%AE%E6%B1%82%E4%BA%BA"),
    ("engage:営業の求人", "https://en-gage.net/search2/%E5%96%B6%E6%A5%AD%E3%81%AE%E6%B1%82%E4%BA%BA"),
    ("engage:BP営業", "https://en-gage.net/search2/BP%E5%96%B6%E6%A5%AD"),
    ("engage:システム開発", "https://en-gage.net/search2/%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E9%96%8B%E7%99%BA"),
]


def normalize_engage_job_url(url: str) -> str:
    """desc/12345 形式に正規化"""
    m = re.search(r"/user/search/desc/(\d+)", url)
    if m:
        return f"https://en-gage.net/user/search/desc/{m.group(1)}/"
    m2 = re.search(r"/([^/]+)/work_(\d+)", url)
    if m2:
        return f"https://en-gage.net/{m2.group(1)}/work_{m2.group(2)}/"
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", "", ""))


def extract_engage_list_links(page: Page) -> list[dict]:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    seen: set[str] = set()
    out: list[dict] = []
    for href in hrefs:
        if "/user/search/desc/" in href or "/work_" in href:
            norm = normalize_engage_job_url(href)
            if norm in seen:
                continue
            seen.add(norm)
            out.append({"result_url": norm, "title": "", "snippet": ""})
    return out


def engage_list_page_url(base: str, page_num: int) -> str:
    if page_num <= 1:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}page={page_num}"


def crawl_engage_listing_pages(
    page: Page,
    sources: list[tuple[str, str]],
    max_pages: int,
    rate_limit: float,
    log_fn=print,
) -> list[dict]:
    rows: list[dict] = []
    for query_label, base_url in sources:
        log_fn(f"engage list: {query_label}")
        empty_streak = 0
        for page_num in range(1, max_pages + 1):
            url = engage_list_page_url(base_url, page_num)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
                batch = extract_engage_list_links(page)
            except Exception as e:
                log_fn(f"  error page {page_num}: {e}")
                break
            new = 0
            for item in batch:
                key = item["result_url"]
                if not any(r["result_url"] == key for r in rows):
                    rows.append({**item, "query": query_label, "search_engine": "engage_list"})
                    new += 1
            log_fn(f"  page {page_num}: +{new} unique (total {len(rows)})")
            if new == 0:
                empty_streak += 1
                if empty_streak >= 2:
                    break
            else:
                empty_streak = 0
            time.sleep(rate_limit)
    return rows

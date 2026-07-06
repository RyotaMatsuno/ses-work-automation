# -*- coding: utf-8 -*-
"""Phase 7A: SES企業リスト取得（SES Beginner / SES MEDIA）"""
from __future__ import annotations

import argparse
import re
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, check_robots_txt, today_str, write_csv
from phase7_helpers import (
    BING_UA,
    fetch_bing_rss_snippets,
    log_error,
    parse_ses_beginner_tables,
    parse_ses_media_page,
    progress_log,
)

OUT_BEGINNER = BASE_DIR / "phase7a_ses_beginner_list.csv"
OUT_MEDIA = BASE_DIR / "phase7a_ses_media_list.csv"
OUT_MASTER = BASE_DIR / "phase7a_ses_companies_master.csv"

BEGINNER_FIELDS = ["company_name", "capital", "location", "source", "crawl_date"]
MEDIA_FIELDS = ["company_name", "capital", "location", "source", "crawl_date"]
MASTER_FIELDS = ["company_name", "source", "location"]

BEGINNER_URL = "https://ses-beginner.jp/ses-company-rankinglist/"
SES_MEDIA_URLS = [
    "https://sesmedia.jp/",
    "https://sesmedia.jp/companies",
    "https://sesmedia.jp/company-list",
    "https://sesmedia.jp/ses-company-list",
]


def _fetch_html_playwright(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="ja-JP", user_agent=BING_UA).new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    return html


def crawl_ses_beginner(rate_limit: float) -> list[dict]:
    robots = check_robots_txt("https://ses-beginner.jp", "/ses-company-rankinglist/")
    print(f"[7A] SES Beginner robots: {robots.reason}", flush=True)
    rows: list[dict] = []

    if robots.allowed:
        try:
            html = _fetch_html_playwright(BEGINNER_URL)
            for r in parse_ses_beginner_tables(html):
                r["crawl_date"] = today_str()
                rows.append({k: r.get(k, "") for k in BEGINNER_FIELDS})
        except Exception as e:
            log_error("phase7a_beginner", BEGINNER_URL, type(e).__name__, str(e))
    else:
        log_error("phase7a_beginner", BEGINNER_URL, "ROBOTS_SKIP", robots.reason)

    if not rows:
        print("[7A] SES Beginner → Bing fallback", flush=True)
        results = fetch_bing_rss_snippets(
            f"site:ses-beginner.jp SES企業 一覧 資本金", max_results=50
        )
        for item in results:
            text = f"{item['title']} {item['snippet']}"
            soup = BeautifulSoup(text, "lxml")
            for part in re_split_company_lines(text):
                rows.append(
                    {
                        "company_name": part,
                        "capital": "",
                        "location": "",
                        "source": "ses_beginner_bing",
                        "crawl_date": today_str(),
                    }
                )

    time.sleep(rate_limit)
    print(f"[7A] SES Beginner: {len(rows)} rows", flush=True)
    return rows


def re_split_company_lines(text: str) -> list[str]:
    names: list[str] = []
    for m in re.finditer(r"(株式会社|合同会社|有限会社)[^\s|｜]{1,30}", text):
        names.append(m.group(0))
    return names


def crawl_ses_media(rate_limit: float) -> list[dict]:
    rows: list[dict] = []
    fetched = False

    for url in SES_MEDIA_URLS:
        robots = check_robots_txt("https://sesmedia.jp", urlparse_path(url))
        if not robots.allowed:
            log_error("phase7a_media", url, "ROBOTS_SKIP", robots.reason)
            continue
        try:
            html = _fetch_html_playwright(url)
            batch = parse_ses_media_page(html)
            if batch:
                fetched = True
                for r in batch:
                    r["crawl_date"] = today_str()
                    rows.append(
                        {
                            "company_name": r["company_name"],
                            "capital": r.get("capital", ""),
                            "location": r.get("location", ""),
                            "source": r.get("source", "ses_media"),
                            "crawl_date": today_str(),
                        }
                    )
                print(f"[7A] SES MEDIA {url}: +{len(batch)}", flush=True)
        except Exception as e:
            log_error("phase7a_media", url, type(e).__name__, str(e))
        time.sleep(rate_limit)

    if not fetched or len(rows) < 100:
        print("[7A] SES MEDIA → Bing fallback", flush=True)
        for q in [
            'site:sesmedia.jp "SES" 企業 一覧',
            'site:sesmedia.jp "株式会社" SES',
            "site:sesmedia.jp SES企業 リスト",
        ]:
            results = fetch_bing_rss_snippets(q, max_results=50)
            for item in results:
                text = f"{item['title']} {item['snippet']}"
                for name in re_split_company_lines(text):
                    rows.append(
                        {
                            "company_name": name,
                            "capital": "",
                            "location": "",
                            "source": "ses_media_bing",
                            "crawl_date": today_str(),
                        }
                    )
            time.sleep(rate_limit)

    print(f"[7A] SES MEDIA: {len(rows)} rows", flush=True)
    return rows


def urlparse_path(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path or "/"


def merge_7a(beginner: list[dict], media: list[dict]) -> list[dict]:
    from phase4_helpers import company_core

    merged: dict[str, dict] = {}
    for r in beginner + media:
        name = (r.get("company_name") or "").strip()
        if not name:
            continue
        key = company_core(name)
        if not key:
            continue
        src = r.get("source", "")
        loc = r.get("location", "")
        if key not in merged:
            merged[key] = {"company_name": name, "source": src, "location": loc}
        else:
            existing_src = merged[key]["source"]
            if src not in existing_src:
                merged[key]["source"] = f"{existing_src};{src}"
            if loc and not merged[key]["location"]:
                merged[key]["location"] = loc
    return list(merged.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-limit", type=float, default=10.0)
    args = parser.parse_args()

    beginner = crawl_ses_beginner(args.rate_limit)
    write_csv(OUT_BEGINNER, BEGINNER_FIELDS, beginner)

    media = crawl_ses_media(args.rate_limit)
    write_csv(OUT_MEDIA, MEDIA_FIELDS, media)

    master = merge_7a(beginner, media)
    n = write_csv(OUT_MASTER, MASTER_FIELDS, master)
    print(f"phase7a_ses_companies_master.csv: {n} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

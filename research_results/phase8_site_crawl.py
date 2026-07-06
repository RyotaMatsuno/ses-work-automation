# -*- coding: utf-8 -*-
"""Phase 8B/8C: サイト直接検索フォールバック"""
from __future__ import annotations

import re
import urllib.parse
from typing import Callable

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from crawl_common import today_str
from crawl_phase6 import extract_domain


def _keywords_from_query(query: str) -> str:
    parts = re.findall(r'"([^"]+)"', query)
    if parts:
        return " ".join(parts)
    return re.sub(r"site:\S+", "", query).strip()


def _normalize_job_url(url: str) -> str:
    return url.split("?")[0].split("#")[0]


def crawl_chiebukuro(page: Page, query: str) -> list[dict]:
    kw = _keywords_from_query(query)
    url = "https://chiebukuro.yahoo.co.jp/search/?p=" + urllib.parse.quote(kw)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    soup = BeautifulSoup(page.content(), "lxml")
    rows: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "detail.chiebukuro.yahoo.co.jp" not in href:
            continue
        u = _normalize_job_url(href)
        if u in seen:
            continue
        seen.add(u)
        title = a.get_text(" ", strip=True)[:300]
        rows.append(
            {
                "query": query,
                "url": u,
                "title": title,
                "snippet": title[:500],
                "domain": "detail.chiebukuro.yahoo.co.jp",
                "crawl_date": today_str(),
            }
        )
    return rows[:30]


def crawl_oshiete(page: Page, query: str) -> list[dict]:
    kw = _keywords_from_query(query)
    url = "https://oshiete.goo.ne.jp/search?q=" + urllib.parse.quote(kw)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
    except Exception:
        return [
            {
                "query": query,
                "url": "https://help.goo.ne.jp/help/article/2864/",
                "title": "「教えて!goo」サービス終了のお知らせ",
                "snippet": "2025年9月17日にサービス終了。oshiete.goo.ne.jpはDNS解決不可のため直接検索不可。",
                "domain": "oshiete.goo.ne.jp",
                "crawl_date": today_str(),
            }
        ]
    soup = BeautifulSoup(page.content(), "lxml")
    rows: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "oshiete.goo.ne.jp" not in href or "/detail/" not in href:
            continue
        u = _normalize_job_url(urllib.parse.urljoin(url, href))
        if u in seen:
            continue
        seen.add(u)
        title = a.get_text(" ", strip=True)[:300]
        if not title:
            continue
        rows.append(
            {
                "query": query,
                "url": u,
                "title": title,
                "snippet": title[:500],
                "domain": "oshiete.goo.ne.jp",
                "crawl_date": today_str(),
            }
        )
    if not rows:
        return [
            {
                "query": query,
                "url": "https://help.goo.ne.jp/help/article/2864/",
                "title": "「教えて!goo」サービス終了のお知らせ",
                "snippet": "2025年9月17日にサービス終了。oshiete.goo.ne.jpはDNS解決不可のため直接検索不可。",
                "domain": "oshiete.goo.ne.jp",
                "crawl_date": today_str(),
            }
        ]
    return rows[:30]


def crawl_quora(page: Page, query: str) -> list[dict]:
    kw = _keywords_from_query(query)
    url = "https://jp.quora.com/search?q=" + urllib.parse.quote(kw)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    soup = BeautifulSoup(page.content(), "lxml")
    rows: list[dict] = []
    seen: set[str] = set()
    skip_paths = ("/about/", "/press", "/search", "/login", "/terms", "/privacy")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "quora.com" not in href:
            continue
        u = _normalize_job_url(urllib.parse.urljoin(url, href))
        if u in seen or any(p in u for p in skip_paths):
            continue
        if u.count("/") < 4:
            continue
        seen.add(u)
        title = a.get_text(" ", strip=True)[:300]
        if len(title) < 5:
            continue
        rows.append(
            {
                "query": query,
                "url": u,
                "title": title,
                "snippet": title[:500],
                "domain": extract_domain(u),
                "crawl_date": today_str(),
            }
        )
    return rows[:30]


def crawl_crowdworks(page: Page, query: str) -> list[dict]:
    kw = _keywords_from_query(query)
    url = (
        "https://crowdworks.jp/public/jobs/search?"
        + urllib.parse.urlencode({"search[keywords]": kw})
    )
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    soup = BeautifulSoup(page.content(), "lxml")
    rows: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"/public/jobs/\d+", href):
            continue
        u = _normalize_job_url(urllib.parse.urljoin(url, href))
        if u in seen:
            continue
        title = a.get_text(" ", strip=True)[:300]
        if not title:
            continue
        seen.add(u)
        rows.append(
            {
                "query": query,
                "url": u,
                "title": title,
                "snippet": title[:500],
                "domain": "crowdworks.jp",
                "crawl_date": today_str(),
            }
        )
    return rows[:30]


def crawl_lancers(page: Page, query: str) -> list[dict]:
    kw = _keywords_from_query(query)
    url = "https://www.lancers.jp/work/search?" + urllib.parse.urlencode({"keyword": kw})
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    soup = BeautifulSoup(page.content(), "lxml")
    rows: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/work/detail/" not in href:
            continue
        u = _normalize_job_url(urllib.parse.urljoin(url, href))
        if u in seen:
            continue
        title = a.get_text(" ", strip=True)[:300]
        if not title:
            continue
        seen.add(u)
        rows.append(
            {
                "query": query,
                "url": u,
                "title": title,
                "snippet": title[:500],
                "domain": "lancers.jp",
                "crawl_date": today_str(),
            }
        )
    return rows[:30]


SITE_CRAWLERS: dict[str, Callable[[Page, str], list[dict]]] = {
    "detail.chiebukuro.yahoo.co.jp": crawl_chiebukuro,
    "oshiete.goo.ne.jp": crawl_oshiete,
    "jp.quora.com": crawl_quora,
    "quora.com": crawl_quora,
    "crowdworks.jp": crawl_crowdworks,
    "lancers.jp": crawl_lancers,
}


def site_domain_from_query(query: str) -> str | None:
    m = re.search(r"site:([^\s\"]+)", query)
    return m.group(1).lower().replace("www.", "") if m else None


def crawl_site_direct(page: Page, query: str) -> list[dict]:
    domain = site_domain_from_query(query)
    if not domain:
        return []
    for key, fn in SITE_CRAWLERS.items():
        if key in domain:
            return fn(page, query)
    return []

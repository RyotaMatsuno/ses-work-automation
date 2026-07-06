# -*- coding: utf-8 -*-
"""Phase 6: Bing検索フォールバック全面展開"""
from __future__ import annotations

import argparse
import csv
import html
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, today_str, write_csv
from phase4_helpers import (
    extract_company_from_text,
    extract_incentive_lines,
    extract_rate_pct,
    is_captcha_page,
)

OUT_BING = BASE_DIR / "phase6_bing_results.csv"
OUT_INCENTIVE = BASE_DIR / "phase6_incentive_mentions.csv"
OUT_DETAILED = BASE_DIR / "phase6_detailed.csv"
OUT_ERROR = BASE_DIR / "phase6_error_log.csv"

BING_FIELDS = ["query", "url", "title", "snippet", "domain", "crawl_date"]
INCENTIVE_FIELDS = ["query", "url", "title", "snippet", "domain", "crawl_date"]
DETAILED_FIELDS = [
    "company_name",
    "incentive_text",
    "incentive_rate_pct",
    "job_title",
    "url",
    "source_query",
    "snippet",
    "crawl_date",
]
ERROR_FIELDS = ["timestamp", "phase", "url", "error_type", "message"]

BING_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

QUERIES = [
    '"SES営業" "粗利" "インセンティブ"',
    '"SES営業" "粗利" "%"',
    '"SES営業" "粗利" "還元"',
    '"SES営業" "歩合" "粗利"',
    '"SES営業" "ストック型" "インセンティブ"',
    '"BP営業" "粗利" "インセンティブ"',
    '"BP営業" "粗利" "%"',
    '"IT人材営業" "粗利" "インセンティブ"',
    '"SES営業" "インセンティブ" "上限なし"',
    '"SES営業" "報酬設計" "粗利"',
    '"SES" "営業" "粗利30%"',
    '"SES" "営業" "粗利40%"',
    '"SES" "営業" "粗利50%"',
    '"SES" "営業" "粗利60%"',
    '"SES" "営業" "粗利20%"',
    '"SES営業" "高還元" "インセンティブ"',
    '"SES営業" "年収1000万"',
    '"SES営業" "業務委託" "粗利"',
    'site:doda.jp "SES営業" インセンティブ',
    'site:green-japan.com "SES営業" インセンティブ',
    'site:jp.indeed.com "SES営業" インセンティブ',
    'site:tenshoku.mynavi.jp "SES営業"',
    'site:next.rikunabi.com "SES営業"',
    'site:type.jp "SES営業"',
    'site:wantedly.com "SES営業" インセンティブ',
    'site:note.com "SES営業" "粗利" "インセンティブ"',
    'site:note.com "SES営業" "報酬設計"',
    'site:x.com "SES営業" "粗利"',
    'site:x.com "BP営業" "粗利"',
    'site:openwork.jp "SES" "営業" "インセンティブ"',
]


def _bing_search_url(query: str, first: int) -> str:
    params = {"q": query, "first": str(first), "setlang": "ja", "cc": "JP"}
    return "https://www.bing.com/search?" + urllib.parse.urlencode(params)


def _new_browser_context(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        locale="ja-JP",
        user_agent=BING_UA,
        viewport={"width": 1366, "height": 900},
    )
    return browser, context


def log_error(phase: str, url: str, error_type: str, message: str) -> None:
    write_header = not OUT_ERROR.exists()
    with OUT_ERROR.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ERROR_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "phase": phase,
                "url": url,
                "error_type": error_type,
                "message": message[:500],
            }
        )


def is_bing_captcha_page(page) -> bool:
    """Bing 用 CAPTCHA 判定（'robot' 文字列による誤検知を避ける）。"""
    url = (page.url or "").lower()
    if any(x in url for x in ("/sorry", "challenge", "captcha")):
        return True
    try:
        body = page.content().lower()
    except Exception:
        body = ""
    strong_markers = (
        "hcaptcha",
        "recaptcha",
        "unusual traffic",
        "automated queries",
        "verify you are human",
        "human verification",
    )
    if any(m in url or m in body for m in strong_markers):
        return page.locator("li.b_algo").count() == 0
    return False


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def normalize_url(url: str) -> str:
    return url.split("#")[0].split("?")[0].rstrip("/")


def _resolve_bing_redirect(context, href: str) -> str:
    """Bing の /ck/a リダイレクト URL を実 URL に解決。"""
    if not href:
        return ""
    if "bing.com/ck/" not in href and "bing.com" not in href:
        return normalize_url(href)
    try:
        resp = context.request.get(href, max_redirects=5, timeout=30000)
        final = resp.url or href
        if "bing.com" not in urlparse(final).netloc.lower():
            return normalize_url(final)
    except Exception:
        pass
    return ""


def parse_bing_results(page, context=None) -> list[dict]:
    """Bing SERP から URL / タイトル / スニペットを抽出。"""
    rows: list[dict] = []
    items = page.locator("li.b_algo").all()
    for item in items:
        link = item.locator("h2 a").first
        href = link.get_attribute("href") or ""
        if not href:
            continue
        url = href
        if context and ("bing.com/ck/" in href or href.startswith("https://www.bing.com/")):
            url = _resolve_bing_redirect(context, href)
        elif "bing.com" in href:
            continue
        else:
            url = normalize_url(href)
        if not url or "bing.com" in url:
            continue
        title = ""
        snippet = ""
        try:
            title = link.inner_text(timeout=2000)[:300]
        except Exception:
            pass
        for sel in (".b_caption p", "div.b_caption", ".b_lineclamp2", ".b_algoSlug"):
            try:
                loc = item.locator(sel).first
                if loc.count():
                    snippet = loc.inner_text(timeout=2000)[:500]
                    if snippet:
                        break
            except Exception:
                pass
        rows.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
            }
        )
    return rows


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(" ", strip=True)


def _fetch_bing_rss(query: str, *, max_results: int = 100) -> list[dict]:
    """Bing RSS (format=rss) で検索結果を取得。Turnstile回避。"""
    rows: list[dict] = []
    seen: set[str] = set()

    for page_num in range(10):
        if len(rows) >= max_results:
            break
        first = page_num * 10 + 1
        params: dict[str, str] = {"q": query, "format": "rss", "setlang": "ja", "cc": "JP"}
        if page_num > 0:
            params["first"] = str(first)
        url = "https://www.bing.com/search?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": BING_UA, "Accept-Language": "ja-JP,ja;q=0.9"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                root = ET.fromstring(resp.read())
        except Exception as e:
            log_error("phase6_bing_rss", url, type(e).__name__, str(e))
            break

        batch: list[dict] = []
        for item in root.findall(".//item"):
            link = normalize_url(item.findtext("link", ""))
            if not link or link in seen:
                continue
            title = html.unescape(item.findtext("title", "") or "")[:300]
            snippet = _strip_html(html.unescape(item.findtext("description", "") or ""))[:500]
            batch.append({"url": link, "title": title, "snippet": snippet})

        if not batch:
            break

        new_count = 0
        for item in batch:
            u = item["url"]
            if u in seen:
                continue
            seen.add(u)
            rows.append(
                {
                    "query": query,
                    "url": u,
                    "title": item["title"],
                    "snippet": item["snippet"],
                    "domain": extract_domain(u),
                    "crawl_date": today_str(),
                }
            )
            new_count += 1
            if len(rows) >= max_results:
                break

        if new_count == 0:
            break
        time.sleep(2)

    return rows[:max_results]


def search_bing_query(
    query: str,
    *,
    max_results: int = 100,
    page=None,
    context=None,
) -> list[dict]:
    """1クエリあたり最大 max_results 件を Bing から収集（RSS優先、HTMLフォールバック）。"""
    rows = _fetch_bing_rss(query, max_results=max_results)
    if len(rows) >= max_results or page is None:
        return rows

    seen = {r["url"] for r in rows}
    max_pages = (max_results + 9) // 10
    for page_num in range(max_pages):
        if len(rows) >= max_results:
            break
        first = page_num * 10 + 1
        url = _bing_search_url(query, first)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            if is_bing_captcha_page(page):
                log_error("phase6_bing_html", url, "CAPTCHA", f"query={query}")
                break
            for item in parse_bing_results(page, context=context):
                u = item["url"]
                if u in seen:
                    continue
                seen.add(u)
                rows.append(
                    {
                        "query": query,
                        "url": u,
                        "title": item["title"],
                        "snippet": item["snippet"],
                        "domain": extract_domain(u),
                        "crawl_date": today_str(),
                    }
                )
                if len(rows) >= max_results:
                    break
        except Exception as e:
            log_error("phase6_bing_html", url, type(e).__name__, str(e))
            break

    return rows[:max_results]


def run_bing_search(*, query_interval: float = 30.0, max_results: int = 100) -> list[dict]:
    all_rows: list[dict] = []
    for i, query in enumerate(QUERIES, 1):
        print(f"[6/1] query {i}/{len(QUERIES)}: {query[:70]}...", flush=True)
        try:
            batch = search_bing_query(query, max_results=max_results)
            all_rows.extend(batch)
            print(f"  +{len(batch)} (cumulative {len(all_rows)})", flush=True)
        except Exception as e:
            log_error("phase6_bing", query, type(e).__name__, str(e))
        if i < len(QUERIES):
            time.sleep(query_interval)
    return all_rows


def dedupe_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        key = normalize_url(r.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def filter_incentive_mentions(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        text = f"{r.get('snippet', '')} {r.get('title', '')}"
        if "粗利" in text and "%" in text:
            out.append(r)
    return out


def fetch_and_extract_details(
    rows: list[dict],
    *,
    page_interval: float = 10.0,
) -> list[dict]:
    detailed: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        for i, r in enumerate(rows, 1):
            url = r.get("url", "")
            if not url:
                continue
            print(f"[6/3] detail {i}/{len(rows)}: {url[:80]}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                if is_captcha_page(page):
                    log_error("phase6_detail", url, "CAPTCHA", "blocked on target page")
                    time.sleep(page_interval)
                    continue
                body = page.inner_text("body")
                title = ""
                try:
                    title = page.title()[:300]
                except Exception:
                    pass
                incentive = extract_incentive_lines(body)
                if not incentive:
                    incentive = extract_incentive_lines(f"{r.get('snippet', '')} {r.get('title', '')}")
                company = extract_company_from_text(body) or extract_company_from_text(title)
                rate = extract_rate_pct(f"{incentive} {body[:5000]}")
                detailed.append(
                    {
                        "company_name": company[:200],
                        "incentive_text": incentive,
                        "incentive_rate_pct": rate if rate is not None else "",
                        "job_title": title,
                        "url": url,
                        "source_query": r.get("query", ""),
                        "snippet": r.get("snippet", ""),
                        "crawl_date": today_str(),
                    }
                )
            except Exception as e:
                log_error("phase6_detail", url, type(e).__name__, str(e))
            time.sleep(page_interval)

        browser.close()
    return detailed


def print_domain_stats(rows: list[dict]) -> None:
    counts = Counter(r.get("domain", "") for r in rows if r.get("domain"))
    print("\n===== ドメイン別件数 =====", flush=True)
    for domain, cnt in counts.most_common(30):
        print(f"  {domain}: {cnt}", flush=True)
    print(f"  (total unique domains: {len(counts)})", flush=True)


def print_csv_to_terminal(path: Path) -> None:
    if not path.exists():
        print(f"{path.name}: ファイルなし", flush=True)
        return
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        content = f.read()
    print(f"\n===== {path.name} (全件) =====\n", flush=True)
    print(content, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-interval", type=float, default=30.0, help="クエリ間隔（秒）")
    parser.add_argument("--page-interval", type=float, default=10.0, help="詳細取得間隔（秒）")
    parser.add_argument("--max-results", type=int, default=100, help="クエリあたり最大件数")
    parser.add_argument("--skip-search", action="store_true", help="Bing検索をスキップ（後処理のみ）")
    parser.add_argument("--skip-detail", action="store_true", help="詳細取得をスキップ")
    args = parser.parse_args()

    if args.skip_search and OUT_BING.exists():
        from crawl_common import read_csv

        raw_rows = read_csv(OUT_BING)
        print(f"[6/1] skip search, loaded {len(raw_rows)} rows from {OUT_BING.name}", flush=True)
    else:
        raw_rows = run_bing_search(query_interval=args.query_interval, max_results=args.max_results)
        n = write_csv(OUT_BING, BING_FIELDS, raw_rows)
        print(f"phase6_bing_results.csv: {n} rows", flush=True)

    deduped = dedupe_rows(raw_rows)
    print(f"[6/2] deduped: {len(raw_rows)} -> {len(deduped)}", flush=True)
    print_domain_stats(deduped)

    incentive_rows = filter_incentive_mentions(deduped)
    write_csv(OUT_INCENTIVE, INCENTIVE_FIELDS, incentive_rows)
    print(f"phase6_incentive_mentions.csv: {len(incentive_rows)} rows", flush=True)

    if not args.skip_detail and incentive_rows:
        detailed = fetch_and_extract_details(incentive_rows, page_interval=args.page_interval)
        write_csv(OUT_DETAILED, DETAILED_FIELDS, detailed)
        print(f"phase6_detailed.csv: {len(detailed)} rows", flush=True)
    elif args.skip_detail:
        print("[6/3] detail crawl skipped", flush=True)
    else:
        write_csv(OUT_DETAILED, DETAILED_FIELDS, [])
        print("phase6_detailed.csv: 0 rows (no incentive mentions)", flush=True)

    print_csv_to_terminal(OUT_INCENTIVE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

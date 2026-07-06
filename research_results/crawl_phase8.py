# -*- coding: utf-8 -*-
"""Phase 8: 上場SES企業IR分析 + Q&Aサイト/クラウドソーシング検索"""
from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, today_str, write_csv
from crawl_phase6 import (
    _bing_search_url,
    extract_domain,
    is_bing_captcha_page,
    parse_bing_results,
    search_bing_query,
)
from phase4_helpers import extract_incentive_lines, extract_rate_pct, is_captcha_page
from phase8_ir_extract import COMPANY_PDFS, analyze_pdf
from phase8_site_crawl import crawl_site_direct

OUT_8A = BASE_DIR / "phase8a_ir_analysis.csv"
OUT_8B = BASE_DIR / "phase8b_qa_sites.csv"
OUT_8C = BASE_DIR / "phase8c_crowdsourcing.csv"
OUT_ERROR = BASE_DIR / "phase8_error_log.csv"
PDF_CACHE = BASE_DIR / "phase8_pdfs"
PDF_CACHE.mkdir(parents=True, exist_ok=True)

FIELDS_8A = [
    "company_name",
    "ticker",
    "revenue",
    "personnel_cost",
    "employee_count",
    "sales_staff_count",
    "cost_per_sales_person",
    "sales_cost_ratio",
    "ir_pdf_url",
    "segment_revenue_notes",
    "crawl_date",
    "notes",
]
FIELDS_8B = ["query", "url", "title", "snippet", "domain", "detail_text", "crawl_date"]
FIELDS_8C = [
    "query",
    "url",
    "title",
    "snippet",
    "domain",
    "incentive_text",
    "incentive_rate_pct",
    "detail_text",
    "crawl_date",
]
ERROR_FIELDS = ["timestamp", "phase", "url", "error_type", "message"]

QUERIES_8B = [
    'site:detail.chiebukuro.yahoo.co.jp "SES営業" "インセンティブ"',
    'site:detail.chiebukuro.yahoo.co.jp "SES営業" "粗利"',
    'site:detail.chiebukuro.yahoo.co.jp "SES営業" "歩合"',
    'site:oshiete.goo.ne.jp "SES営業" "インセンティブ"',
    'site:jp.quora.com "SES営業" "報酬"',
]

QUERIES_8C = [
    'site:crowdworks.jp "SES営業" "粗利"',
    'site:lancers.jp "SES営業" "粗利"',
    'site:crowdworks.jp "SES" "営業" "インセンティブ"',
]


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


def normalize_url(url: str) -> str:
    return url.split("#")[0].split("?")[0].rstrip("/")


def download_pdf_playwright(urls: list[str], dest: Path, request_context) -> str:
    for url in urls:
        if not url:
            continue
        try:
            resp = request_context.get(url, timeout=120000)
            if resp.ok and len(resp.body()) > 5000:
                dest.write_bytes(resp.body())
                return url
        except Exception as e:
            log_error("phase8a_pdf", url, type(e).__name__, str(e))
    return ""


def empty_row(company: dict[str, str], pdf_url: str, note: str) -> dict[str, Any]:
    return {
        "company_name": company["company_name"],
        "ticker": company.get("ticker", ""),
        "revenue": "",
        "personnel_cost": "",
        "employee_count": "",
        "sales_staff_count": "",
        "cost_per_sales_person": "",
        "sales_cost_ratio": "",
        "ir_pdf_url": pdf_url,
        "segment_revenue_notes": "",
        "crawl_date": today_str(),
        "notes": note,
    }


def run_phase8a() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with sync_playwright() as p:
        request_context = p.request.new_context(ignore_https_errors=True)
        for ticker, meta in COMPANY_PDFS.items():
            company = {**meta, "ticker": ticker}
            print(f"[8A] {company['company_name']} ({ticker})...", flush=True)
            dest = PDF_CACHE / f"{ticker}.pdf"
            urls = [meta.get("pdf_url", "")]
            if meta.get("fallback_pdf"):
                urls.append(meta["fallback_pdf"])
            pdf_url = ""
            if dest.exists() and dest.stat().st_size > 5000:
                pdf_url = meta.get("pdf_url", "")
            else:
                pdf_url = download_pdf_playwright(urls, dest, request_context)

            if not dest.exists() or dest.stat().st_size < 5000:
                log_error("phase8a", meta.get("ir_page", ""), "DOWNLOAD_FAIL", f"ticker={ticker}")
                row = empty_row(company, pdf_url or urls[0], "PDF取得失敗")
                if ticker == "2458":
                    row["notes"] = "2023年10月上場廃止(テクノプロHD子会社化)。最新有報PDF未取得"
                rows.append(row)
                continue

            try:
                row = analyze_pdf(company, dest, pdf_url or urls[0], today_str())
                if ticker == "2458" and not row.get("revenue"):
                    row["notes"] = (
                        (row.get("notes") or "")
                        + "; 2023年10月上場廃止。取得PDFが最新期でない可能性"
                    ).strip("; ")
                rows.append(row)
                print(
                    f"  revenue={row['revenue']} personnel={row['personnel_cost']} "
                    f"emp={row['employee_count']} sales_staff={row['sales_staff_count']}",
                    flush=True,
                )
            except Exception as e:
                log_error("phase8a", pdf_url, type(e).__name__, str(e))
                rows.append(empty_row(company, pdf_url, f"parse error: {e}"))
        request_context.dispose()
    return rows


def _bing_html_search(page, context, query: str, *, max_results: int = 50) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for first in (1, 11, 21):
        if len(rows) >= max_results:
            break
        url = _bing_search_url(query, first)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            if is_bing_captcha_page(page):
                log_error("phase8_bing_html", url, "CAPTCHA", f"query={query}")
                break
            for item in parse_bing_results(page, context=context):
                u = item.get("url", "")
                if not u or u in seen:
                    continue
                seen.add(u)
                rows.append(
                    {
                        "query": query,
                        "url": u,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "domain": extract_domain(u),
                        "crawl_date": today_str(),
                    }
                )
                if len(rows) >= max_results:
                    break
        except Exception as e:
            log_error("phase8_bing_html", url, type(e).__name__, str(e))
            break
    return rows[:max_results]


def _site_filter(query: str, rows: list[dict]) -> list[dict]:
    m = re.search(r"site:([^\s\"]+)", query)
    if not m:
        return rows
    domain = m.group(1).lower().replace("www.", "")
    return [
        r
        for r in rows
        if domain in (r.get("url", "").lower())
        or domain in (r.get("domain", "").lower())
    ]


def bing_search_queries(
    queries: list[str],
    *,
    query_interval: float = 20.0,
    max_results: int = 50,
) -> list[dict]:
    all_rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="ja-JP",
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        for i, query in enumerate(queries, 1):
            print(f"[Bing] {i}/{len(queries)}: {query[:70]}...", flush=True)
            try:
                if "site:" in query.lower():
                    batch = crawl_site_direct(page, query)
                    if not batch:
                        batch = _bing_html_search(page, context, query, max_results=max_results)
                else:
                    batch = search_bing_query(
                        query,
                        max_results=max_results,
                        page=page,
                        context=context,
                    )
                batch = _site_filter(query, batch)
                for r in batch:
                    r.setdefault("crawl_date", today_str())
                    r.setdefault("domain", extract_domain(r.get("url", "")))
                all_rows.extend(batch)
                print(f"  +{len(batch)} (total {len(all_rows)})", flush=True)
            except Exception as e:
                log_error("phase8_bing", query, type(e).__name__, str(e))
            if i < len(queries):
                time.sleep(query_interval)
        browser.close()
    return all_rows


def fetch_page_text(url: str, page) -> str:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        text = page.inner_text("body")[:8000]
        if is_captcha_page(page) and len(text.strip()) < 500:
            return ""
        return text
    except Exception as e:
        log_error("phase8_detail", url, type(e).__name__, str(e))
        return ""


def enrich_qa_details(rows: list[dict], page_interval: float = 5.0) -> list[dict]:
    qa_domains = ("chiebukuro.yahoo.co.jp", "oshiete.goo.ne.jp", "quora.com")
    targets = [
        r
        for r in rows
        if any(d in r.get("url", "") for d in qa_domains)
        and any(
            k in f"{r.get('title', '')} {r.get('snippet', '')}"
            for k in ("SES", "営業", "粗利", "インセンティブ", "歩合", "報酬")
        )
    ]

    detail_map: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="ja-JP", user_agent=USER_AGENT).new_page()
        for i, r in enumerate(targets[:30], 1):
            url = r.get("url", "")
            if not url or url in detail_map:
                continue
            print(f"[8B detail] {i}/{min(len(targets), 30)}: {url[:80]}", flush=True)
            detail_map[url] = fetch_page_text(url, page)
            time.sleep(page_interval)
        browser.close()

    enriched: list[dict] = []
    for r in rows:
        out = dict(r)
        body = detail_map.get(r.get("url", ""), "")
        out["detail_text"] = body[:3000]
        enriched.append(out)
    return enriched


def enrich_crowd_details(rows: list[dict], page_interval: float = 5.0) -> list[dict]:
    targets = [
        r
        for r in rows
        if any(d in r.get("url", "") for d in ("crowdworks.jp", "lancers.jp"))
        and any(
            k in f"{r.get('title', '')} {r.get('snippet', '')}"
            for k in ("粗利", "インセンティブ", "歩合", "%", "成果", "報酬")
        )
    ]

    detail_map: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="ja-JP", user_agent=USER_AGENT).new_page()
        for i, r in enumerate(targets[:25], 1):
            url = r.get("url", "")
            if not url or url in detail_map:
                continue
            print(f"[8C detail] {i}/{min(len(targets), 25)}: {url[:80]}", flush=True)
            body = fetch_page_text(url, page)
            incentive = extract_incentive_lines(body) or extract_incentive_lines(
                f"{r.get('snippet', '')} {r.get('title', '')}"
            )
            rate = extract_rate_pct(f"{incentive} {body[:5000]}")
            detail_map[url] = {
                "detail_text": body[:3000],
                "incentive_text": incentive,
                "incentive_rate_pct": rate if rate is not None else "",
            }
            time.sleep(page_interval)
        browser.close()

    enriched: list[dict] = []
    for r in rows:
        out = dict(r)
        extra = detail_map.get(r.get("url", ""), {})
        out["detail_text"] = extra.get("detail_text", "")[:3000]
        out["incentive_text"] = extra.get("incentive_text", "")
        out["incentive_rate_pct"] = extra.get("incentive_rate_pct", "")
        if not out["incentive_text"]:
            out["incentive_text"] = extract_incentive_lines(
                f"{r.get('snippet', '')} {r.get('title', '')}"
            )
        if not out["incentive_rate_pct"]:
            rate = extract_rate_pct(f"{out['incentive_text']} {r.get('snippet', '')}")
            out["incentive_rate_pct"] = rate if rate is not None else ""
        enriched.append(out)
    return enriched


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-interval", type=float, default=20.0)
    parser.add_argument("--skip-8a", action="store_true")
    parser.add_argument("--skip-8b", action="store_true")
    parser.add_argument("--skip-8c", action="store_true")
    parser.add_argument("--skip-detail", action="store_true")
    args = parser.parse_args()

    if not args.skip_8a:
        rows_8a = run_phase8a()
        n = write_csv(OUT_8A, FIELDS_8A, rows_8a)
        print(f"phase8a_ir_analysis.csv: {n} rows", flush=True)
    else:
        print("[8A] skipped", flush=True)

    if not args.skip_8b:
        raw_8b = dedupe_rows(bing_search_queries(QUERIES_8B, query_interval=args.query_interval))
        if not args.skip_detail:
            raw_8b = enrich_qa_details(raw_8b)
        else:
            for r in raw_8b:
                r["detail_text"] = ""
        n = write_csv(OUT_8B, FIELDS_8B, raw_8b)
        print(f"phase8b_qa_sites.csv: {n} rows", flush=True)
    else:
        print("[8B] skipped", flush=True)

    if not args.skip_8c:
        raw_8c = dedupe_rows(bing_search_queries(QUERIES_8C, query_interval=args.query_interval))
        if not args.skip_detail:
            raw_8c = enrich_crowd_details(raw_8c)
        else:
            for r in raw_8c:
                r["detail_text"] = ""
                r["incentive_text"] = ""
                r["incentive_rate_pct"] = ""
        n = write_csv(OUT_8C, FIELDS_8C, raw_8c)
        print(f"phase8c_crowdsourcing.csv: {n} rows", flush=True)
    else:
        print("[8C] skipped", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Phase 4A: 求人サイト横断クロール（Green〜レバテックキャリア 計20サイト）"""
from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, check_robots_txt, is_likely_job_url, retry_call, write_csv
from phase4_helpers import (
    PHASE4A_FIELDS,
    PHASE4A_SITE_OUTPUT,
    extract_job_detail_generic,
    is_captcha_page,
    is_sales_job,
    log_error_phase4,
    progress_log,
    search_web,
)

STANDARD_KEYWORDS = ["SES営業", "IT営業", "BP営業", "人材コーディネーター SES"]

GREEN_KEYWORDS = ["SES営業", "IT人材営業", "BP営業", "SESコーディネーター"]
KYUJINBOX_KEYWORDS = ["SES営業 インセンティブ", "SES営業 粗利", "SES営業 歩合"]
WANTEDLY_KEYWORDS = ["SES営業", "SES 営業 高還元", "SES 営業 粗利"]
STANBY_KEYWORDS = ["SES営業", "IT営業 インセンティブ"]

SITE_OUTPUT = PHASE4A_SITE_OUTPUT

ALL_SITES = list(SITE_OUTPUT.keys())


@dataclass
class SiteConfig:
    base: str
    robots_path: str
    keywords: list[str]
    bing_domain: str
    link_pattern: str
    build_url: Callable[[str, int], str]
    channel: str


def _collect_links_by_pattern(html: str, base: str, pattern: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    regex = re.compile(pattern, re.I)
    urls: list[str] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        full = urljoin(base, href).split("?")[0].split("#")[0]
        if regex.search(full) and full not in urls:
            urls.append(full)
    return urls


def _collect_green_links(html: str) -> list[str]:
    return _collect_links_by_pattern(html, "https://www.green-japan.com", r"green-japan\.com/company/\d+/job/")


def _collect_kyujinbox_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    base = "https://xn--pckua2a7gp15o89zb.com"
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        full = urljoin(base, href).split("?")[0]
        if re.search(r"/job/\d+|/jb/\d+|/kJ/", full) and full not in urls:
            urls.append(full)
    return urls


def _collect_wantedly_links(html: str) -> list[str]:
    return _collect_links_by_pattern(
        html, "https://www.wantedly.com", r"wantedly\.com/(projects|companies)/"
    )


def _collect_stanby_links(html: str) -> list[str]:
    return _collect_links_by_pattern(html, "https://jp.stanby.com", r"stanby\.com/(job|jobs)/")


def _green_search_url(keyword: str, page_num: int) -> str:
    return f"https://www.green-japan.com/search?keyword={quote(keyword)}&page={page_num}"


def _kyujinbox_search_url(keyword: str, page_num: int) -> str:
    return f"https://xn--pckua2a7gp15o89zb.com/search?q={quote(keyword)}&page={page_num}"


def _wantedly_search_url(keyword: str, page_num: int) -> str:
    return f"https://www.wantedly.com/projects?keyword={quote(keyword)}&page={page_num}"


def _stanby_search_url(keyword: str, page_num: int) -> str:
    return f"https://jp.stanby.com/search?q={quote(keyword)}&page={page_num}"


def _doda_search_url(keyword: str, page_num: int) -> str:
    return (
        f"https://doda.jp/DodaFront/View/JobSearchList/j_id___{page_num}/"
        f"?kw={quote(keyword)}"
    )


def _mynavi_search_url(keyword: str, page_num: int) -> str:
    return f"https://tenshoku.mynavi.jp/list/kw{quote(keyword)}/pg{page_num}/"


def _rikunabi_search_url(keyword: str, page_num: int) -> str:
    return f"https://next.rikunabi.com/job_search/kw{quote(keyword)}/?page={page_num}"


def _type_search_url(keyword: str, page_num: int) -> str:
    return f"https://type.jp/job/search?keyword={quote(keyword)}&page={page_num}"


def _indeed_search_url(keyword: str, page_num: int) -> str:
    start = (page_num - 1) * 10
    return f"https://jp.indeed.com/jobs?q={quote(keyword)}&start={start}"


def _directscout_search_url(keyword: str, page_num: int) -> str:
    return f"https://directscout.recruit.co.jp/job_descriptions?keyword={quote(keyword)}&page={page_num}"


def _daijob_search_url(keyword: str, page_num: int) -> str:
    return f"https://www.daijob.com/jobs/search?keywords={quote(keyword)}&page={page_num}"


def _careerindex_search_url(keyword: str, page_num: int) -> str:
    return f"https://careerindex.jp/jobs?keyword={quote(keyword)}&page={page_num}"


def _hatalike_search_url(keyword: str, page_num: int) -> str:
    return f"https://hatalike.jp/search/?keyword={quote(keyword)}&page={page_num}"


def _baitorunext_search_url(keyword: str, page_num: int) -> str:
    return f"https://baitorunext.jp/search/?keyword={quote(keyword)}&page={page_num}"


def _miidas_search_url(keyword: str, page_num: int) -> str:
    return f"https://miidas.jp/search?keyword={quote(keyword)}&page={page_num}"


def _woman_type_search_url(keyword: str, page_num: int) -> str:
    return f"https://woman-type.jp/job/search?keyword={quote(keyword)}&page={page_num}"


def _re_katsu_search_url(keyword: str, page_num: int) -> str:
    return f"https://re-katsu.jp/career/search?keyword={quote(keyword)}&page={page_num}"


def _job_medley_search_url(keyword: str, page_num: int) -> str:
    return f"https://job-medley.com/search/?keyword={quote(keyword)}&page={page_num}"


def _geekly_search_url(keyword: str, page_num: int) -> str:
    return f"https://www.geekly.co.jp/jobs?keyword={quote(keyword)}&page={page_num}"


def _levtech_search_url(keyword: str, page_num: int) -> str:
    return f"https://career.levtech.jp/jobs/search?keyword={quote(keyword)}&page={page_num}"


def _make_collect(base: str, pattern: str) -> Callable[[str], list[str]]:
    def collect(html: str) -> list[str]:
        return _collect_links_by_pattern(html, base, pattern)

    return collect


SITE_CONFIGS: dict[str, SiteConfig] = {
    "green": SiteConfig(
        "https://www.green-japan.com",
        "/search",
        GREEN_KEYWORDS,
        "green-japan.com",
        r"green-japan\.com/company/\d+/job/",
        _green_search_url,
        "green",
    ),
    "kyujinbox": SiteConfig(
        "https://xn--pckua2a7gp15o89zb.com",
        "/search",
        KYUJINBOX_KEYWORDS,
        "xn--pckua2a7gp15o89zb.com",
        r"/job/\d+|/jb/\d+|/kJ/",
        _kyujinbox_search_url,
        "kyujinbox",
    ),
    "wantedly": SiteConfig(
        "https://www.wantedly.com",
        "/projects",
        WANTEDLY_KEYWORDS,
        "wantedly.com",
        r"wantedly\.com/(projects|companies)/",
        _wantedly_search_url,
        "wantedly",
    ),
    "stanby": SiteConfig(
        "https://jp.stanby.com",
        "/search",
        STANBY_KEYWORDS,
        "jp.stanby.com",
        r"stanby\.com/(job|jobs)/",
        _stanby_search_url,
        "stanby",
    ),
    "doda": SiteConfig(
        "https://doda.jp",
        "/DodaFront/View/JobSearchList",
        STANDARD_KEYWORDS,
        "doda.jp",
        r"doda\.jp/.*/JobSearchDetail/|doda\.jp/job/",
        _doda_search_url,
        "doda",
    ),
    "mynavi": SiteConfig(
        "https://tenshoku.mynavi.jp",
        "/list/",
        STANDARD_KEYWORDS,
        "tenshoku.mynavi.jp",
        r"tenshoku\.mynavi\.jp/job/|scouting\.mynavi\.jp/job-detail/",
        _mynavi_search_url,
        "mynavi",
    ),
    "rikunabi": SiteConfig(
        "https://next.rikunabi.com",
        "/job_search/",
        STANDARD_KEYWORDS,
        "next.rikunabi.com",
        r"next\.rikunabi\.com/viewjob/",
        _rikunabi_search_url,
        "rikunabi",
    ),
    "type": SiteConfig(
        "https://type.jp",
        "/job/search",
        STANDARD_KEYWORDS,
        "type.jp",
        r"type\.jp/job-",
        _type_search_url,
        "type",
    ),
    "indeed": SiteConfig(
        "https://jp.indeed.com",
        "/jobs",
        STANDARD_KEYWORDS,
        "jp.indeed.com",
        r"jp\.indeed\.com/(viewjob|rc/clk)",
        _indeed_search_url,
        "indeed",
    ),
    "directscout": SiteConfig(
        "https://directscout.recruit.co.jp",
        "/job_descriptions",
        STANDARD_KEYWORDS,
        "directscout.recruit.co.jp",
        r"directscout\.recruit\.co\.jp/job_descriptions/",
        _directscout_search_url,
        "directscout",
    ),
    "daijob": SiteConfig(
        "https://www.daijob.com",
        "/jobs/search",
        STANDARD_KEYWORDS,
        "daijob.com",
        r"daijob\.com/jobs/",
        _daijob_search_url,
        "daijob",
    ),
    "careerindex": SiteConfig(
        "https://careerindex.jp",
        "/jobs",
        STANDARD_KEYWORDS,
        "careerindex.jp",
        r"careerindex\.jp/jobs/",
        _careerindex_search_url,
        "careerindex",
    ),
    "hatalike": SiteConfig(
        "https://hatalike.jp",
        "/search/",
        STANDARD_KEYWORDS,
        "hatalike.jp",
        r"hatalike\.jp/.*/job/",
        _hatalike_search_url,
        "hatalike",
    ),
    "baitorunext": SiteConfig(
        "https://baitorunext.jp",
        "/search/",
        STANDARD_KEYWORDS,
        "baitorunext.jp",
        r"baitorunext\.jp/.*/job/",
        _baitorunext_search_url,
        "baitorunext",
    ),
    "miidas": SiteConfig(
        "https://miidas.jp",
        "/search",
        STANDARD_KEYWORDS,
        "miidas.jp",
        r"miidas\.jp/(jobs|positions)/",
        _miidas_search_url,
        "miidas",
    ),
    "woman_type": SiteConfig(
        "https://woman-type.jp",
        "/job/search",
        STANDARD_KEYWORDS,
        "woman-type.jp",
        r"woman-type\.jp/job-",
        _woman_type_search_url,
        "woman_type",
    ),
    "re_katsu": SiteConfig(
        "https://re-katsu.jp",
        "/career/search",
        STANDARD_KEYWORDS,
        "re-katsu.jp",
        r"re-katsu\.jp/career/.+/detail",
        _re_katsu_search_url,
        "re_katsu",
    ),
    "job_medley": SiteConfig(
        "https://job-medley.com",
        "/search/",
        STANDARD_KEYWORDS,
        "job-medley.com",
        r"job-medley\.com/.*/\d+",
        _job_medley_search_url,
        "job_medley",
    ),
    "geekly": SiteConfig(
        "https://www.geekly.co.jp",
        "/jobs",
        STANDARD_KEYWORDS,
        "geekly.co.jp",
        r"geekly\.co\.jp/(jobs|recruit)/",
        _geekly_search_url,
        "geekly",
    ),
    "levtech": SiteConfig(
        "https://career.levtech.jp",
        "/jobs/search",
        STANDARD_KEYWORDS,
        "career.levtech.jp",
        r"career\.levtech\.jp/jobs/",
        _levtech_search_url,
        "levtech",
    ),
}


def _filter_job_urls(urls: list[str], cfg: SiteConfig) -> list[str]:
    regex = re.compile(cfg.link_pattern, re.I)
    out: list[str] = []
    for u in urls:
        if cfg.bing_domain in u and (regex.search(u) or is_likely_job_url(u)):
            if u not in out:
                out.append(u)
    return out


def _bing_collect_job_urls(
    page,
    keyword: str,
    cfg: SiteConfig,
    max_results: int,
    rate_limit: float,
    phase: str,
) -> list[str]:
    """robots.txtブロックまたはCAPTCHA時のBing検索フォールバック。"""
    query = f"site:{cfg.bing_domain} {keyword}"
    rows = search_web(
        page,
        query,
        max_results=max_results,
        max_pages=10,
        rate_limit=rate_limit,
        phase=phase,
        use_google_first=False,
    )
    urls: list[str] = []
    for r in rows:
        u = r.get("url", "").split("?")[0].split("#")[0]
        if u and u not in urls:
            urls.append(u)
    return _filter_job_urls(urls, cfg)


def _direct_search_with_captcha_fallback(
    page,
    cfg: SiteConfig,
    max_pages: int,
    rate_limit: float,
    phase: str,
) -> list[str]:
    """直接検索。CAPTCHA検出時はBingへフォールバック。"""
    collect = _make_collect(cfg.base, cfg.link_pattern)
    all_urls: list[str] = []
    captcha_hit = False

    for keyword in cfg.keywords:
        print(f"  keyword: {keyword}", flush=True)
        for page_num in range(1, max_pages + 1):
            url = cfg.build_url(keyword, page_num)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                if is_captcha_page(page):
                    captcha_hit = True
                    log_error_phase4(phase, url, "CAPTCHA", "Direct search blocked; switching to Bing")
                    break
                links = collect(page.content())
            except Exception as e:
                log_error_phase4(phase, url, type(e).__name__, str(e))
                break
            new = [u for u in links if u not in all_urls]
            all_urls.extend(new)
            print(f"    page {page_num}: +{len(new)} (total {len(all_urls)})", flush=True)
            if not new:
                break
            time.sleep(rate_limit)
        if captcha_hit:
            break

    if captcha_hit:
        print(f"[4A:{cfg.channel}] CAPTCHA → Bing fallback", flush=True)
        for keyword in cfg.keywords:
            bing_urls = _bing_collect_job_urls(
                page, keyword, cfg, max_results=200, rate_limit=rate_limit, phase=phase
            )
            for u in bing_urls:
                if u not in all_urls:
                    all_urls.append(u)
            print(f"  bing {keyword}: +{len(bing_urls)} (total {len(all_urls)})", flush=True)
    return all_urls


def crawl_site(site: str, max_pages: int, rate_limit: float, limit: int) -> list[dict]:
    cfg = SITE_CONFIGS[site]
    robots = check_robots_txt(cfg.base, cfg.robots_path)
    delay = max(rate_limit, robots.crawl_delay)
    print(f"[4A:{site}] robots: {robots.reason}, delay={delay}s", flush=True)

    rows: list[dict] = []
    job_urls: list[str] = []
    phase = f"phase4a_{site}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        if not robots.allowed:
            log_error_phase4(phase, cfg.base, "ROBOTS_SKIP", robots.reason)
            print(f"[4A:{site}] robots disallowed → Bing fallback", flush=True)
            for keyword in cfg.keywords:
                bing_urls = _bing_collect_job_urls(
                    page, keyword, cfg, max_results=200, rate_limit=delay, phase=phase
                )
                for u in bing_urls:
                    if u not in job_urls:
                        job_urls.append(u)
                print(f"  bing {keyword}: +{len(bing_urls)} (total {len(job_urls)})", flush=True)
        else:
            job_urls = _direct_search_with_captcha_fallback(
                page, cfg, max_pages=max_pages, rate_limit=delay, phase=phase
            )

        targets = job_urls[:limit] if limit else job_urls
        print(f"[4A:{site}] detail crawl: {len(targets)} URLs", flush=True)

        for i, job_url in enumerate(targets, 1):
            kw = cfg.keywords[0]
            try:
                row = retry_call(
                    lambda u=job_url, k=kw, ch=cfg.channel: extract_job_detail_generic(page, u, k, ch),
                    phase=phase,
                    url=job_url,
                )
                if is_sales_job(row.get("job_title", ""), row.get("raw_text", "")):
                    rows.append(row)
            except Exception:
                pass
            progress_log(i, len(targets))
            time.sleep(delay)

        browser.close()

    out = BASE_DIR / SITE_OUTPUT[site]
    n = write_csv(out, PHASE4A_FIELDS, rows)
    print(f"[4A:{site}] {out.name}: {n} rows (sales-filtered)", flush=True)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=["all", *ALL_SITES], default="all")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=0, help="詳細取得上限（0=無制限）")
    args = parser.parse_args()

    sites = ALL_SITES if args.site == "all" else [args.site]
    for site in sites:
        try:
            crawl_site(site, args.max_pages, args.rate_limit, args.limit)
        except Exception as e:
            log_error_phase4(f"phase4a_{site}", "", type(e).__name__, str(e))
            print(f"[4A:{site}] FATAL: {e}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Phase 4 共通ユーティリティ（営業求人フィルタ・検索・名寄せ）"""
from __future__ import annotations

import csv
import random
import re
import time
import urllib.parse
from pathlib import Path
from typing import Callable

from crawl_common import BASE_DIR, USER_AGENT, today_str

ERROR_LOG_PHASE4 = BASE_DIR / "error_log_phase4.csv"
ERROR_FIELDS = ["timestamp", "phase", "url", "error_type", "message"]

PHASE4A_SITE_OUTPUT = {
    "green": "phase4a_green.csv",
    "kyujinbox": "phase4a_kyujinbox.csv",
    "wantedly": "phase4a_wantedly.csv",
    "stanby": "phase4a_stanby.csv",
    "doda": "phase4a_doda.csv",
    "mynavi": "phase4a_mynavi.csv",
    "rikunabi": "phase4a_rikunabi.csv",
    "type": "phase4a_type.csv",
    "indeed": "phase4a_indeed.csv",
    "directscout": "phase4a_directscout.csv",
    "daijob": "phase4a_daijob.csv",
    "careerindex": "phase4a_careerindex.csv",
    "hatalike": "phase4a_hatalike.csv",
    "baitorunext": "phase4a_baitorunext.csv",
    "miidas": "phase4a_miidas.csv",
    "woman_type": "phase4a_woman_type.csv",
    "re_katsu": "phase4a_re_katsu.csv",
    "job_medley": "phase4a_job_medley.csv",
    "geekly": "phase4a_geekly.csv",
    "levtech": "phase4a_levtech.csv",
}

PHASE4A_FIELDS = [
    "company_name",
    "job_title",
    "employment_type",
    "salary_text",
    "incentive_text",
    "location",
    "job_url",
    "crawl_date",
    "raw_text",
    "search_keyword",
    "channel",
]

PHASE4B_FIELDS = [
    "source_type",
    "url",
    "title",
    "snippet",
    "company_name_if_found",
    "crawl_date",
    "search_query",
]

PHASE4C_FIELDS = [
    "company_name",
    "hp_url",
    "recruit_url",
    "incentive_text",
    "salary_text",
    "raw_text",
    "crawl_date",
    "filter_reason",
]

PHASE4D_FIELDS = [
    "site",
    "url",
    "title",
    "snippet",
    "company_name",
    "crawl_date",
    "search_query",
]

PHASE4E_FIELDS = [
    "company_name",
    "corporate_url",
    "recruit_url",
    "ses_sales_recruit_url",
    "source",
    "crawl_date",
    "priority",
]

SALES_HINT = re.compile(
    r"営業|コーディネーター|セールス|人材営業|BP営業|SES営業|キャリアアドバイザー",
    re.I,
)
ENGINEER_ONLY = re.compile(
    r"(?:エンジニア募集|SE募集|PG募集|プログラマ募集|開発者募集|"
    r"システムエンジニア[^営]*$|エンジニア[^営]*$)",
    re.I,
)
ENGINEER_STRONG = re.compile(
    r"システムエンジニア|プログラマ|PG\b|SE\b|エンジニア|開発者",
    re.I,
)

COMPANY_PREFIXES = ("株式会社", "合同会社", "有限会社", "一般社団法人", "（株）", "(株)")


def log_error_phase4(phase: str, url: str, error_type: str, message: str) -> None:
    write_header = not ERROR_LOG_PHASE4.exists()
    with ERROR_LOG_PHASE4.open("a", encoding="utf-8-sig", newline="") as f:
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


def is_sales_job(title: str, text: str) -> bool:
    """営業職求人のみ通す。エンジニア専募集は除外（兼務は含む）。"""
    title = title or ""
    text = text or ""
    combined = f"{title}\n{text[:3000]}"
    if not SALES_HINT.search(combined):
        return False
    if ENGINEER_ONLY.search(title) and not SALES_HINT.search(title):
        return False
    if ENGINEER_STRONG.search(title) and not SALES_HINT.search(title):
        if not SALES_HINT.search(text[:800]):
            return False
    return True


def company_core(name: str) -> str:
    s = (name or "").strip()
    for p in COMPANY_PREFIXES:
        s = s.replace(p, "")
    s = re.sub(r"[\s　・]", "", s)
    return s.lower()


def extract_company_from_text(text: str) -> str:
    m = re.search(r"(株式会社|合同会社|有限会社)[^\s\n|｜]{1,40}", text or "")
    return m.group(0) if m else ""


def extract_incentive_lines(text: str, limit: int = 1000) -> str:
    parts: list[str] = []
    for line in (text or "").splitlines():
        if any(k in line for k in ["インセンティブ", "粗利", "歩合", "成果", "還元", "ストック", "報酬"]):
            parts.append(line.strip())
    return " ".join(parts)[:limit]


def extract_rate_pct(text: str) -> float | None:
    m = re.search(r"(?:粗利|還元)[^\d]{0,10}(\d{1,2})\s*[％%]", text or "")
    if m:
        return float(m.group(1))
    m2 = re.search(r"(\d{1,2})\s*[％%].{0,8}(?:粗利|還元|インセンティブ)", text or "")
    if m2:
        return float(m2.group(1))
    return None


def is_captcha_page(page) -> bool:
    url = (page.url or "").lower()
    try:
        body = page.content().lower()
    except Exception:
        body = ""
    markers = ("sorry", "captcha", "unusual traffic", "robot", "hcaptcha", "recaptcha")
    return any(m in url or m in body for m in markers)


def _parse_google_results(page) -> list[dict]:
    rows: list[dict] = []
    for sel in ["div.g a[href^='http']", "a[href^='http']"]:
        links = page.locator(sel).all()
        if links:
            for a in links:
                href = a.get_attribute("href") or ""
                if not href.startswith("http"):
                    continue
                if any(x in href for x in ("google.", "gstatic.", "youtube.com/results")):
                    continue
                title = ""
                try:
                    title = a.inner_text(timeout=1000)[:200]
                except Exception:
                    pass
                rows.append({"url": href.split("#")[0], "title": title, "snippet": ""})
            if rows:
                break
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        u = r["url"]
        if u not in seen:
            seen.add(u)
            out.append(r)
    return out


def _parse_bing_results(page) -> list[dict]:
    rows: list[dict] = []
    for a in page.locator("li.b_algo h2 a").all():
        href = a.get_attribute("href") or ""
        if href.startswith("http") and "bing.com" not in href:
            title = ""
            try:
                title = a.inner_text(timeout=1000)[:200]
            except Exception:
                pass
            rows.append({"url": href.split("?")[0], "title": title, "snippet": ""})
    return rows


def search_web(
    page,
    query: str,
    *,
    max_results: int = 100,
    max_pages: int = 10,
    rate_limit: float = 10.0,
    phase: str = "phase4_search",
    use_google_first: bool = True,
) -> list[dict]:
    """Google→CAPTCHA時Bing。各クエリ最大max_results件。"""
    rows: list[dict] = []
    engine = "google" if use_google_first else "bing"
    blocked_google = False

    for page_num in range(max_pages):
        if len(rows) >= max_results:
            break
        if engine == "google":
            start = page_num * 10
            url = "https://www.google.com/search?" + urllib.parse.urlencode(
                {"q": query, "hl": "ja", "start": str(start)}
            )
        else:
            first = page_num * 10 + 1
            url = "https://www.bing.com/search?" + urllib.parse.urlencode(
                {"q": query, "first": str(first)}
            )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            if engine == "google" and is_captcha_page(page):
                blocked_google = True
                log_error_phase4(phase, url, "CAPTCHA", "Google blocked; switching to Bing")
                engine = "bing"
                page_num -= 1
                continue
            batch = _parse_google_results(page) if engine == "google" else _parse_bing_results(page)
            if not batch:
                break
            for item in batch:
                if len(rows) >= max_results:
                    break
                item["search_engine"] = engine
                item["search_query"] = query
                rows.append(item)
        except Exception as e:
            log_error_phase4(phase, url, type(e).__name__, str(e))
            if engine == "google" and not blocked_google:
                engine = "bing"
                continue
            break

        sleep_s = rate_limit + random.uniform(0, 5)
        if engine == "bing" and blocked_google:
            sleep_s = max(sleep_s, 30.0) + random.uniform(0, 10)
        time.sleep(sleep_s)

    return rows[:max_results]


def extract_job_detail_generic(page, url: str, keyword: str, channel: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    text = page.inner_text("body")
    title = ""
    try:
        title = page.title()[:300]
    except Exception:
        pass

    company = extract_company_from_text(text)
    employment = "正社員" if "正社員" in text else ""
    if "業務委託" in text:
        employment = "業務委託"
    elif "契約" in text and "正社員" not in text:
        employment = "契約社員"

    salary = ""
    m = re.search(r"(\d{3,4}万円[〜~\-－]?\d{0,4}万円?)", text)
    if m:
        salary = m.group(1)

    location = ""
    m_loc = re.search(r"東京都|大阪府|福岡県|(?:北海道|.{2,3}県)", text)
    if m_loc:
        location = m_loc.group(0)

    return {
        "company_name": company[:200],
        "job_title": title[:300],
        "employment_type": employment,
        "salary_text": salary[:300],
        "incentive_text": extract_incentive_lines(text),
        "location": location,
        "job_url": url,
        "crawl_date": today_str(),
        "raw_text": text[:8000],
        "search_keyword": keyword,
        "channel": channel,
    }


def crawl_listing_urls(
    page,
    build_search_url: Callable[[str, int], str],
    collect_links: Callable[[str], list[str]],
    keywords: list[str],
    *,
    max_pages: int,
    rate_limit: float,
    phase: str,
    allowed: bool = True,
) -> list[str]:
    if not allowed:
        return []
    all_urls: list[str] = []
    for keyword in keywords:
        print(f"  keyword: {keyword}", flush=True)
        for page_num in range(1, max_pages + 1):
            url = build_search_url(keyword, page_num)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                html = page.content()
                links = collect_links(html)
            except Exception as e:
                log_error_phase4(phase, url, type(e).__name__, str(e))
                break
            new = [u for u in links if u not in all_urls]
            all_urls.extend(new)
            print(f"    page {page_num}: +{len(new)} (total {len(all_urls)})", flush=True)
            if not new:
                break
            time.sleep(rate_limit)
    return all_urls


def progress_log(i: int, total: int, label: str = "detail") -> None:
    if i % 50 == 0 or i == total:
        print(f"  {label} {i}/{total}", flush=True)

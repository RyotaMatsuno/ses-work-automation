# -*- coding: utf-8 -*-
"""Phase 4E: 全社の採用HPリスト作成（Phase1-3 + Phase4A-4Dのユニーク企業）"""
from __future__ import annotations

import argparse
import re
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, read_csv, today_str, write_csv
from phase4_helpers import (
    PHASE4A_SITE_OUTPUT,
    PHASE4E_FIELDS,
    company_core,
    log_error_phase4,
    progress_log,
    search_web,
)

OUT_CSV = BASE_DIR / "phase4e_company_hp_list.csv"

RECRUIT_PATH_HINTS = re.compile(
    r"/recruit|/careers|/jobs|/employment|/採用|/saiyo|/career|/job/",
    re.I,
)
SES_SALES_HINT = re.compile(r"SES営業|IT営業|BP営業|人材.*営業|コーディネーター.*SES", re.I)

JOB_BOARD_DOMAINS = (
    "en-gage.net",
    "green-japan.com",
    "wantedly.com",
    "indeed.com",
    "doda.jp",
    "mynavi.jp",
    "rikunabi.com",
    "type.jp",
    "directscout.recruit.co.jp",
    "daijob.com",
    "careerindex.jp",
    "hatalike.jp",
    "baitorunext.jp",
    "miidas.jp",
    "woman-type.jp",
    "re-katsu.jp",
    "job-medley.com",
    "geekly.co.jp",
    "levtech.jp",
    "stanby.com",
    "kyujinbox",
    "openwork.jp",
    "jobtalk.jp",
    "en-hyouban.com",
    "wikipedia.org",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "note.com",
    "google.com",
    "bing.com",
)

RECRUIT_PATHS = [
    "/recruit",
    "/recruit/",
    "/careers",
    "/careers/",
    "/jobs",
    "/jobs/",
    "/採用",
    "/採用情報",
    "/company/recruit",
    "/employment",
    "/saiyo",
    "/career",
]


def _is_job_board_url(url: str) -> bool:
    u = (url or "").lower()
    return any(d in u for d in JOB_BOARD_DOMAINS)


def _is_recruit_url(url: str) -> bool:
    return bool(RECRUIT_PATH_HINTS.search(url or ""))


def _collect_companies_from_csv(path, name_field: str, source: str) -> dict[str, dict]:
    """{company_core: {company_name, source, priority, incentive_hint}}"""
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    for r in read_csv(path):
        name = (r.get(name_field) or "").strip()
        if not name or len(name) < 3:
            continue
        if name in ("株式会社の", "株式会社の採用・求人情報", "株式会社一"):
            continue
        key = company_core(name)
        if not key:
            continue
        incentive_hint = False
        text = " ".join(
            str(r.get(k, "") or "")
            for k in (
                "incentive_description",
                "incentive_text",
                "raw_text",
                "snippet",
                "notes",
            )
        )
        if re.search(r"インセンティブ|粗利|還元|歩合|ストック", text):
            incentive_hint = True
        if key not in out:
            out[key] = {
                "company_name": name,
                "source": source,
                "priority": incentive_hint,
                "incentive_hint": incentive_hint,
            }
        else:
            if incentive_hint:
                out[key]["priority"] = True
                out[key]["incentive_hint"] = True
            if source and source not in out[key]["source"]:
                out[key]["source"] = f"{out[key]['source']};{source}"
    return out


def collect_all_companies() -> list[dict]:
    """Phase1-3 + Phase4A-4D からユニーク企業を収集。"""
    merged: dict[str, dict] = {}

    sources: list[tuple] = [
        (BASE_DIR / "phase2_engage.csv", "company_name", "engage"),
        (BASE_DIR / "phase3_extracted.csv", "company_name", "engage"),
    ]

    for fname in PHASE4A_SITE_OUTPUT.values():
        sources.append((BASE_DIR / fname, "company_name", fname.replace("phase4a_", "").replace(".csv", "")))

    sources += [
        (BASE_DIR / "phase4b_sns_blog.csv", "company_name_if_found", "sns_blog"),
        (BASE_DIR / "phase4c_company_hp.csv", "company_name", "company_hp"),
        (BASE_DIR / "phase4d_review_sites.csv", "company_name", "review"),
    ]

    for path, field, source in sources:
        batch = _collect_companies_from_csv(path, field, source)
        for key, info in batch.items():
            if key not in merged:
                merged[key] = info
            else:
                if info.get("priority"):
                    merged[key]["priority"] = True
                    merged[key]["incentive_hint"] = True
                existing_src = merged[key]["source"]
                if source not in existing_src:
                    merged[key]["source"] = f"{existing_src};{source}"

    companies = list(merged.values())
    companies.sort(key=lambda x: (not x.get("priority", False), x["company_name"]))
    return companies


def _pick_corporate_url(results: list[dict]) -> str:
    for r in results:
        u = r.get("url", "")
        if not u or _is_job_board_url(u):
            continue
        if _is_recruit_url(u):
            continue
        return u.split("?")[0].split("#")[0]
    for r in results:
        u = r.get("url", "")
        if u and not _is_job_board_url(u):
            return u.split("?")[0].split("#")[0]
    return ""


def _pick_recruit_url(results: list[dict], corporate_url: str) -> str:
    for r in results:
        u = r.get("url", "")
        if u and _is_recruit_url(u) and not _is_job_board_url(u):
            return u.split("?")[0].split("#")[0]
    if corporate_url:
        parsed = urlparse(corporate_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        for path in RECRUIT_PATHS:
            candidate = urljoin(base, path)
            if any(r.get("url", "").startswith(candidate.rstrip("/")) for r in results):
                return candidate
    return ""


def _probe_recruit_paths(page, corporate_url: str, rate_limit: float) -> str:
    if not corporate_url:
        return ""
    parsed = urlparse(corporate_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in RECRUIT_PATHS:
        url = urljoin(base, path)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            text = page.inner_text("body")
            if any(k in text for k in ["採用", "募集", "recruit", "career", "jobs"]):
                return url
        except Exception:
            pass
        time.sleep(rate_limit / 4)
    return ""


def _find_ses_sales_recruit(
    page,
    corporate_url: str,
    recruit_url: str,
    company_name: str,
    rate_limit: float,
    priority: bool,
) -> str:
    """SES営業募集ページURL（あれば）。"""
    candidates: list[str] = []

    if recruit_url:
        try:
            page.goto(recruit_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            html = page.content()
            parsed = urlparse(recruit_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
                href = m.group(1)
                full = urljoin(base, href).split("?")[0].split("#")[0]
                if SES_SALES_HINT.search(full) or (
                    SES_SALES_HINT.search(href) and "job" in href.lower()
                ):
                    candidates.append(full)
            text = page.inner_text("body")
            if SES_SALES_HINT.search(text):
                for a in page.locator("a[href]").all()[:80]:
                    href = a.get_attribute("href") or ""
                    full = urljoin(base, href).split("?")[0]
                    try:
                        link_text = a.inner_text(timeout=500)
                    except Exception:
                        link_text = ""
                    if SES_SALES_HINT.search(link_text) or SES_SALES_HINT.search(full):
                        if full.startswith("http") and not _is_job_board_url(full):
                            candidates.append(full)
        except Exception:
            pass
        time.sleep(rate_limit / 2)

    if priority and corporate_url and not candidates:
        parsed = urlparse(corporate_url)
        domain = parsed.netloc.replace("www.", "")
        query = f"site:{domain} SES営業 採用"
        try:
            results = search_web(
                page,
                query,
                max_results=5,
                max_pages=1,
                rate_limit=rate_limit,
                phase="phase4e_ses",
            )
            for r in results:
                u = r.get("url", "")
                if u and not _is_job_board_url(u):
                    candidates.append(u.split("?")[0])
        except Exception:
            pass

    if not candidates and priority:
        query = f'"{company_name}" SES営業 採用'
        try:
            results = search_web(
                page,
                query,
                max_results=5,
                max_pages=1,
                rate_limit=rate_limit,
                phase="phase4e_ses",
            )
            for r in results:
                u = r.get("url", "")
                if u and not _is_job_board_url(u) and SES_SALES_HINT.search(
                    f"{r.get('title', '')} {u}"
                ):
                    candidates.append(u.split("?")[0])
        except Exception:
            pass

    return candidates[0] if candidates else ""


def crawl_company(
    page,
    company: dict,
    rate_limit: float,
) -> dict:
    name = company["company_name"]
    query = f"{name} 採用"
    results = search_web(
        page,
        query,
        max_results=10,
        max_pages=2,
        rate_limit=rate_limit,
        phase="phase4e",
    )
    corporate_url = _pick_corporate_url(results)
    recruit_url = _pick_recruit_url(results, corporate_url)

    if corporate_url and not recruit_url:
        recruit_url = _probe_recruit_paths(page, corporate_url, rate_limit)

    ses_url = ""
    if company.get("priority") or recruit_url:
        ses_url = _find_ses_sales_recruit(
            page,
            corporate_url,
            recruit_url,
            name,
            rate_limit,
            priority=bool(company.get("priority")),
        )

    return {
        "company_name": name,
        "corporate_url": corporate_url,
        "recruit_url": recruit_url,
        "ses_sales_recruit_url": ses_url,
        "source": company.get("source", ""),
        "crawl_date": today_str(),
        "priority": "yes" if company.get("priority") else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-limit", type=float, default=20.0, help="リクエスト間隔（秒）")
    parser.add_argument("--limit", type=int, default=0, help="処理上限（0=全社）")
    parser.add_argument("--priority-only", action="store_true", help="インセンティブ言及企業のみ")
    args = parser.parse_args()

    companies = collect_all_companies()
    if args.priority_only:
        companies = [c for c in companies if c.get("priority")]
    if args.limit:
        companies = companies[: args.limit]

    print(f"[4E] target companies: {len(companies)}", flush=True)

    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        for i, co in enumerate(companies, 1):
            try:
                row = crawl_company(page, co, args.rate_limit)
                rows.append(row)
                if not row["corporate_url"]:
                    log_error_phase4("phase4e", co["company_name"], "NO_CORPORATE", "corporate URL not found")
            except Exception as e:
                log_error_phase4("phase4e", co.get("company_name", ""), type(e).__name__, str(e))
                rows.append(
                    {
                        "company_name": co["company_name"],
                        "corporate_url": "",
                        "recruit_url": "",
                        "ses_sales_recruit_url": "",
                        "source": co.get("source", ""),
                        "crawl_date": today_str(),
                        "priority": "yes" if co.get("priority") else "",
                    }
                )
            progress_log(i, len(companies), "company")
            time.sleep(args.rate_limit)

        browser.close()

    n = write_csv(OUT_CSV, PHASE4E_FIELDS, rows)
    found_corp = sum(1 for r in rows if r.get("corporate_url"))
    found_recruit = sum(1 for r in rows if r.get("recruit_url"))
    found_ses = sum(1 for r in rows if r.get("ses_sales_recruit_url"))
    print(
        f"phase4e_company_hp_list.csv: {n} rows "
        f"(corporate={found_corp}, recruit={found_recruit}, ses_sales={found_ses})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

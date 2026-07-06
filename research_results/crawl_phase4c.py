# -*- coding: utf-8 -*-
"""Phase 4C: 企業HP直接調査（Phase3でインセンティブ言及ありの会社）"""
from __future__ import annotations

import argparse
import re
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from crawl_common import BASE_DIR, USER_AGENT, read_csv, today_str, write_csv
from phase4_helpers import (
    PHASE4C_FIELDS,
    company_core,
    extract_incentive_lines,
    log_error_phase4,
    progress_log,
    search_web,
)

OUT_CSV = BASE_DIR / "phase4c_company_hp.csv"

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
]


def _load_target_companies() -> list[dict]:
    """Phase3から対象会社を抽出（粗利/ストック/率数値）。"""
    path = BASE_DIR / "phase3_extracted.csv"
    if not path.exists():
        return []

    targets: dict[str, dict] = {}
    for r in read_csv(path):
        company = (r.get("company_name") or "").strip()
        if not company or company in ("株式会社の", "株式会社の採用・求人情報", "株式会社一"):
            continue
        desc = r.get("incentive_description") or ""
        rate = r.get("incentive_rate_pct")
        reasons: list[str] = []
        if "粗利" in desc or "粗利" in (r.get("notes") or ""):
            reasons.append("粗利言及")
        if "ストック" in desc:
            reasons.append("ストック言及")
        if rate and str(rate).strip() not in ("", "nan", "None"):
            try:
                if float(rate) > 0:
                    reasons.append(f"率={rate}%")
            except (ValueError, TypeError):
                pass
        if not reasons:
            continue
        key = company_core(company)
        if key not in targets:
            targets[key] = {
                "company_name": company,
                "filter_reason": ";".join(reasons),
                "source_url": r.get("source_url", ""),
            }
        else:
            existing = targets[key]["filter_reason"]
            for reason in reasons:
                if reason not in existing:
                    targets[key]["filter_reason"] = existing + ";" + reason
    return list(targets.values())


def _find_recruit_page(page, hp_url: str, rate_limit: float) -> tuple[str, str]:
    """採用ページURLと本文テキストを返す。"""
    parsed = urlparse(hp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    texts: list[tuple[str, str]] = []

    for path in RECRUIT_PATHS:
        url = urljoin(base, path)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            if page.locator("body").count():
                text = page.inner_text("body")
                if any(k in text for k in ["採用", "募集", "営業", "キャリア", "recruit"]):
                    texts.append((url, text))
        except Exception:
            pass
        time.sleep(rate_limit / 2)

    if not texts:
        try:
            page.goto(hp_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            text = page.inner_text("body")
            texts.append((hp_url, text))
        except Exception:
            return hp_url, ""

    best = max(texts, key=lambda x: len(x[1]))
    return best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-limit", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    companies = _load_target_companies()
    if args.limit:
        companies = companies[: args.limit]
    print(f"[4C] target companies: {len(companies)}", flush=True)

    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", user_agent=USER_AGENT)
        page = context.new_page()

        for i, co in enumerate(companies, 1):
            name = co["company_name"]
            query = f"{name} 公式サイト"
            try:
                results = search_web(
                    page,
                    query,
                    max_results=5,
                    max_pages=1,
                    rate_limit=args.rate_limit,
                    phase="phase4c",
                )
            except Exception as e:
                log_error_phase4("phase4c", name, type(e).__name__, str(e))
                continue

            hp_url = ""
            for r in results:
                u = r.get("url", "")
                if u and not any(
                    x in u.lower()
                    for x in (
                        "en-gage.net",
                        "green-japan",
                        "wantedly",
                        "indeed",
                        "doda",
                        "wikipedia",
                        "facebook",
                        "linkedin",
                    )
                ):
                    hp_url = u
                    break

            if not hp_url:
                log_error_phase4("phase4c", name, "NO_HP", "official site not found")
                progress_log(i, len(companies), "company")
                time.sleep(args.rate_limit)
                continue

            try:
                recruit_url, text = _find_recruit_page(page, hp_url, args.rate_limit)
                incentive = extract_incentive_lines(text)
                salary = ""
                m = re.search(r"(\d{3,4}万円[〜~\-－]?\d{0,4}万円?)", text)
                if m:
                    salary = m.group(1)
                if any(k in text for k in ["営業", "SES", "コーディネーター", "人材"]):
                    rows.append(
                        {
                            "company_name": name,
                            "hp_url": hp_url,
                            "recruit_url": recruit_url,
                            "incentive_text": incentive,
                            "salary_text": salary,
                            "raw_text": text[:8000],
                            "crawl_date": today_str(),
                            "filter_reason": co["filter_reason"],
                        }
                    )
            except Exception as e:
                log_error_phase4("phase4c", hp_url, type(e).__name__, str(e))

            progress_log(i, len(companies), "company")
            time.sleep(args.rate_limit)

        browser.close()

    n = write_csv(OUT_CSV, PHASE4C_FIELDS, rows)
    print(f"phase4c_company_hp.csv: {n} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

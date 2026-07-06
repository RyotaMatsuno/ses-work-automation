# -*- coding: utf-8 -*-
"""Phase 7 共通ユーティリティ"""
from __future__ import annotations

import csv
import html
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup

from crawl_common import BASE_DIR, read_csv, today_str, write_csv
from phase4_helpers import company_core, extract_rate_pct

ERROR_LOG = BASE_DIR / "phase7_error_log.csv"
ERROR_FIELDS = ["timestamp", "phase", "url", "error_type", "message"]

BING_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

COMPANY_NAME_RE = re.compile(r"(株式会社|合同会社|有限会社)[^\s\n|｜]{1,40}")


class BingBlockedError(RuntimeError):
    """Bing RSS が IP ブロック等で利用不可。"""


def log_error(phase: str, url: str, error_type: str, message: str) -> None:
    write_header = not ERROR_LOG.exists()
    with ERROR_LOG.open("a", encoding="utf-8-sig", newline="") as f:
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


def progress_log(i: int, total: int, label: str = "items") -> None:
    if i % 100 == 0 or i == total:
        print(f"  {label} {i}/{total}", flush=True)


def normalize_company_name(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r"\s+", " ", s)
    if s and "株式会社" not in s and "合同会社" not in s and "有限会社" not in s:
        if re.match(r"^[A-Za-z0-9\u4e00-\u9fff\u30a0-\u30ff]+$", s) and len(s) <= 40:
            pass  # keep as-is for short names like "Adapt"
    return s[:200]


def extract_company_from_job_title(title: str) -> tuple[str, str]:
    """求人タイトルから会社名と職種を推定。'会社名｜職種' / '会社名 / 職種' 等。"""
    title = (title or "").strip()
    if not title:
        return "", ""
    m = COMPANY_NAME_RE.search(title)
    if m:
        return m.group(0), title
    for sep in ("｜", "|", "／", "/", " – ", " - ", "【"):
        if sep in title:
            parts = title.split(sep, 1)
            company = parts[0].strip()
            job = parts[1].strip() if len(parts) > 1 else title
            if company:
                return normalize_company_name(company), job[:300]
    return "", title[:300]


def fetch_bing_rss_snippets(query: str, *, max_results: int = 50) -> list[dict]:
    """Bing RSS でスニペット収集（Turnstile回避）。"""
    rows: list[dict] = []
    seen: set[str] = set()
    params = {"q": query, "format": "rss", "setlang": "ja", "cc": "JP"}
    url = "https://www.bing.com/search?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": BING_UA, "Accept-Language": "ja-JP,ja;q=0.9"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            root = ET.fromstring(resp.read())
    except urllib.error.HTTPError as e:
        log_error("phase7_bing", url, "BING_BLOCK", f"HTTP {e.code}: {e.reason}")
        if e.code in (403, 429, 503):
            raise BingBlockedError(f"HTTP {e.code}") from e
        return rows
    except Exception as e:
        log_error("phase7_bing", url, type(e).__name__, str(e))
        err = str(e).lower()
        if any(x in err for x in ("blocked", "forbidden", "429", "captcha")):
            raise BingBlockedError(str(e)) from e
        return rows

    for item in root.findall(".//item"):
        link = (item.findtext("link", "") or "").split("?")[0]
        if not link or link in seen:
            continue
        seen.add(link)
        title = html.unescape(item.findtext("title", "") or "")
        desc = item.findtext("description", "") or ""
        snippet = BeautifulSoup(html.unescape(desc), "lxml").get_text(" ", strip=True)[:800]
        rows.append({"url": link, "title": title[:300], "snippet": snippet})
        if len(rows) >= max_results:
            break
    return rows


def parse_ses_beginner_tables(html: str) -> list[dict]:
    """SES Beginner 一覧ページの table から会社名・資本金を抽出。"""
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    seen: set[str] = set()
    for table in soup.select("table"):
        for tr in table.select("tr"):
            cells = [c.get_text(strip=True) for c in tr.select("td")]
            if len(cells) < 2:
                continue
            name, capital = cells[0], cells[1]
            if name in ("会社名", "") or not name:
                continue
            key = company_core(name)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "company_name": normalize_company_name(name),
                    "capital": capital[:100],
                    "location": "",
                    "source": "ses_beginner",
                }
            )
    return rows


def parse_ses_media_page(html: str) -> list[dict]:
    """SES MEDIA 企業リストページから会社名・所在地を抽出。"""
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    seen: set[str] = set()

    for table in soup.select("table"):
        headers = [th.get_text(strip=True) for th in table.select("th")]
        for tr in table.select("tr"):
            cells = [c.get_text(strip=True) for c in tr.select("td")]
            if len(cells) < 1:
                continue
            name = cells[0]
            if name in ("会社名", "企業名", "") or len(name) < 2:
                continue
            location = ""
            if len(cells) >= 2:
                location = cells[1]
            elif "所在地" in headers:
                idx = headers.index("所在地") if "所在地" in headers else -1
                if idx >= 0 and idx < len(cells):
                    location = cells[idx]
            key = company_core(name)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "company_name": normalize_company_name(name),
                    "capital": "",
                    "location": location[:100],
                    "source": "ses_media",
                }
            )

    # リスト形式（table以外）
    for li in soup.select("li, .company-item, article"):
        text = li.get_text(" ", strip=True)
        m = COMPANY_NAME_RE.search(text)
        if m:
            name = m.group(0)
            key = company_core(name)
            if key not in seen:
                seen.add(key)
                loc_m = re.search(r"(東京都|大阪府|.{2,3}県)[^\s]{0,20}", text)
                rows.append(
                    {
                        "company_name": name,
                        "capital": "",
                        "location": loc_m.group(0) if loc_m else "",
                        "source": "ses_media",
                    }
                )
    return rows


def load_existing_surveyed_cores() -> set[str]:
    """Phase 1-6 で調査済みの company_core 集合。"""
    cores: set[str] = set()
    sources = [
        (BASE_DIR / "phase2_engage.csv", "company_name"),
        (BASE_DIR / "phase3_extracted.csv", "company_name"),
        (BASE_DIR / "phase4e_company_hp_list.csv", "company_name"),
        (BASE_DIR / "phase6_detailed.csv", "company_name"),
        (BASE_DIR / "phase6_incentive_mentions.csv", "title"),
    ]
    for path in BASE_DIR.glob("phase4a_*.csv"):
        sources.append((path, "company_name"))
    for path, field in sources:
        for r in read_csv(path):
            name = (r.get(field) or "").strip()
            if not name:
                continue
            c = company_core(name)
            if not c:
                c = company_core(extract_company_from_job_title(name)[0])
            if c:
                cores.add(c)
    return cores


def append_csv_rows(path: Path, fieldnames: list[str], new_rows: list[dict]) -> int:
    """既存CSVに追記（resume用）。"""
    existing = read_csv(path) if path.exists() else []
    merged = existing + new_rows
    write_csv(path, fieldnames, merged)
    return len(merged)


def incentive_flags_from_text(text: str) -> tuple[str, str | None]:
    """(incentive_disclosed, incentive_rate) をテキストから推定。"""
    text = text or ""
    rate = extract_rate_pct(text)
    has_pct = bool(re.search(r"\d{1,2}\s*[％%]", text))
    has_kw = bool(re.search(r"粗利|還元|インセンティブ|歩合", text))
    if rate is not None:
        return "あり", str(rate)
    if has_pct and has_kw:
        return "あり", None
    if has_kw:
        return "あり", None
    return "なし", None

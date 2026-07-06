# -*- coding: utf-8 -*-
"""SES営業求人クロール共通ユーティリティ"""
from __future__ import annotations

import csv
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable
from urllib.robotparser import RobotFileParser

SES_WORK_ROOT = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
BASE_DIR = SES_WORK_ROOT / "research_results"
BASE_DIR.mkdir(parents=True, exist_ok=True)

if str(SES_WORK_ROOT) not in sys.path:
    sys.path.insert(0, str(SES_WORK_ROOT))

try:
    from common.io_utils import setup_stdout

    setup_stdout()
except Exception:
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 "
    "TERRA-SES-JobSurvey/1.0 (+research; contact: ses-work-automation)"
)

ERROR_LOG = BASE_DIR / "error_log.csv"
ERROR_FIELDS = ["timestamp", "phase", "url", "error_type", "message"]

# 求人ページ以外とみなすURLパターン
NON_JOB_URL_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"note\.com",
        r"qiita\.com",
        r"wantedly\.com/.+/post_articles/",
        r"/blog/",
        r"/column/",
        r"/news/",
        r"/article/",
        r"/media/",
        r"/recruit/archives/",
        r"\.pdf$",
        r"wikipedia\.org",
        r"youtube\.com",
        r"twitter\.com",
        r"x\.com",
        r"facebook\.com",
        r"linkedin\.com",
        r"/login",
        r"/signup",
        r"/privacy",
        r"/terms",
        r"/company/?$",
        r"/about/?$",
    ]
]

JOB_URL_HINTS = [
    re.compile(p, re.I)
    for p in [
        r"en-gage\.net/.+/work_",
        r"en-gage\.net/user/search/desc/",
        r"green-japan\.com/company/\d+/job/",
        r"jp\.indeed\.com/(viewjob|rc/clk)",
        r"doda\.jp/.*/JobSearchDetail/",
        r"type\.jp/job-",
        r"tenshoku\.mynavi\.jp/job/",
        r"next\.rikunabi\.com/viewjob/",
        r"wantedly\.com/projects/",
        r"directscout\.recruit\.co\.jp/job_descriptions/",
        r"en-gage\.net/search2/",
        r"careerindex\.jp/jobs/",
        r"hatalike\.jp/.*/job/",
        r"baitorunext\.jp/.*/job/",
        r"miidas\.jp/(jobs|positions)/",
        r"woman-type\.jp/job-",
        r"re-katsu\.jp/career/.+/detail",
        r"job-medley\.com/.*/\d+",
        r"geekly\.co\.jp/(jobs|recruit)/",
        r"career\.levtech\.jp/jobs/",
        r"scouting\.mynavi\.jp/job-detail/",
    ]
]


@dataclass
class RobotsCheckResult:
    allowed: bool
    crawl_delay: float
    reason: str


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunparse((scheme, netloc, path, "", parsed.query, ""))


def dedup_key(url: str) -> str:
    return normalize_url(url)


def is_likely_job_url(url: str) -> bool:
    if any(p.search(url) for p in NON_JOB_URL_PATTERNS):
        return False
    if any(p.search(url) for p in JOB_URL_HINTS):
        return True
    # ドメインが求人サイトなら許容
    host = urllib.parse.urlparse(url).netloc.lower()
    job_domains = (
        "en-gage.net",
        "green-japan.com",
        "jp.indeed.com",
        "doda.jp",
        "type.jp",
        "tenshoku.mynavi.jp",
        "next.rikunabi.com",
        "wantedly.com",
        "directscout.recruit.co.jp",
        "hatalike.jp",
        "mid-tenshoku.com",
        "daijob.com",
    )
    return any(d in host for d in job_domains)


def deduplicate_rows(rows: Iterable[dict], url_field: str = "result_url") -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = dedup_key(row.get(url_field, ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def filter_job_urls(rows: Iterable[dict], url_field: str = "result_url") -> list[dict]:
    return [r for r in rows if is_likely_job_url(r.get(url_field, ""))]


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


def retry_call(
    fn: Callable[[], object],
    *,
    phase: str,
    url: str = "",
    retries: int = 3,
    delay: float = 2.0,
):
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay * attempt)
    assert last_err is not None
    log_error(phase, url, type(last_err).__name__, str(last_err))
    raise last_err


def check_robots_txt(base_url: str, path: str, user_agent: str = USER_AGENT, timeout: float = 15.0) -> RobotsCheckResult:
    parsed = urllib.parse.urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        rp.parse(body.splitlines())
    except Exception as e:
        return RobotsCheckResult(False, 10.0, f"robots.txt unreadable: {e}")

    allowed = rp.can_fetch(user_agent, urllib.parse.urljoin(base_url, path))
    crawl_delay = rp.crawl_delay(user_agent) or 10.0
    crawl_delay = max(float(crawl_delay), 10.0)
    if not allowed:
        return RobotsCheckResult(False, crawl_delay, f"Disallowed by robots.txt: {path}")
    return RobotsCheckResult(True, crawl_delay, "ok")


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows_list:
            w.writerow(row)
    return len(rows_list)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def today_str() -> str:
    return date.today().isoformat()

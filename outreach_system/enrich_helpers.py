# -*- coding: utf-8 -*-
"""enrich_emails 共通ユーティリティ"""
from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from typing import Iterable

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20
HP_RATE_LIMIT_SEC = 3.0
GOOGLE_RATE_LIMIT_SEC = 20.0

EMAIL_PATTERNS = [
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(
        r"[a-zA-Z0-9._%+-]+\s*[\[（(]\s*(?:at|AT)\s*[\]）)]\s*[a-zA-Z0-9.-]+\.\w+",
        re.I,
    ),
]
PRIORITY_PREFIXES = ["info@", "contact@", "sales@", "corp@", "support@"]
EXCLUDE_PREFIXES = ["noreply@", "no-reply@", "do-not-reply@", "example@"]

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
HP_DOMAIN_RE = re.compile(r"\.(co\.jp|or\.jp|com|net|jp)(?:[/:]|$)", re.I)

CONTACT_PATHS = [
    "/contact",
    "/inquiry",
    "/お問い合わせ",
    "/company",
    "/about",
    "/会社概要",
    "/recruit",
    "/採用",
]

CONTACT_LINK_HINT = re.compile(r"contact|inquiry|お問い合わせ|問合|問い合わせ", re.I)
EXTERNAL_FORM_HINT = re.compile(
    r"docs\.google\.com/forms|forms\.gle|hubspot|form\.run|form\.mailchimp",
    re.I,
)

IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico)(?:\?|$)", re.I)


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ja-JP,ja;q=0.9"})
    return s


def normalize_email(raw: str) -> str | None:
    text = raw.strip()
    text = re.sub(r"\s*[\[（(]\s*(?:at|AT)\s*[\]）)]\s*", "@", text)
    text = text.replace(" ", "")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text):
        return None
    lower = text.lower()
    if any(lower.startswith(p) for p in EXCLUDE_PREFIXES):
        return None
    if IMAGE_EXT.search(lower):
        return None
    return text


def pick_best_email(candidates: Iterable[str]) -> str | None:
    normalized = []
    for c in candidates:
        e = normalize_email(c)
        if e:
            normalized.append(e)
    if not normalized:
        return None
    unique = list(dict.fromkeys(normalized))
    for prefix in PRIORITY_PREFIXES:
        for e in unique:
            if e.lower().startswith(prefix):
                return e
    return unique[0]


def extract_emails_from_text(text: str) -> list[str]:
    found: list[str] = []
    for pat in EMAIL_PATTERNS:
        found.extend(pat.findall(text))
    return found


def extract_emails_from_html(html: str) -> list[str]:
    emails = extract_emails_from_text(html)
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select('a[href^="mailto:"]'):
        href = a.get("href", "")
        if href.lower().startswith("mailto:"):
            emails.append(href[7:].split("?")[0])
    return emails


def extract_form_urls(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    soup = BeautifulSoup(html, "html.parser")

    for form in soup.find_all("form"):
        action = (form.get("action") or "").strip()
        if action and action not in ("#", "javascript:void(0)"):
            urls.append(urllib.parse.urljoin(base_url, action))

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        if CONTACT_LINK_HINT.search(href) or CONTACT_LINK_HINT.search(text):
            urls.append(urllib.parse.urljoin(base_url, href))

    for m in EXTERNAL_FORM_HINT.finditer(html):
        start = max(0, m.start() - 30)
        chunk = html[start : m.end() + 80]
        for u in URL_RE.findall(chunk):
            urls.append(u)

    cleaned: list[str] = []
    seen: set[str] = set()
    for u in urls:
        if u.startswith("http") and u not in seen:
            seen.add(u)
            cleaned.append(u)
    return cleaned


def extract_url_from_memo(memo: str) -> str | None:
    for u in URL_RE.findall(memo or ""):
        if HP_DOMAIN_RE.search(u):
            return u.rstrip(".,)")
    return None


def is_hp_candidate(url: str) -> bool:
    if not url.startswith("http"):
        return False
    lower = url.lower()
    skip_hosts = (
        "google.com",
        "youtube.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "wikipedia.org",
        "amazon.",
        "yahoo.co.jp/search",
        "bing.com",
        "mizuhobank.co.jp",
        "yayoi-kk.co.jp",
        "freee.co.jp",
        "ht-tax.or.jp",
        "bizreach.jp",
        "doda.jp",
        "rikunabi.com",
        "mynavi.jp",
    )
    if any(h in lower for h in skip_hosts):
        return False
    return bool(HP_DOMAIN_RE.search(lower))


def robots_allowed(url: str, sess: requests.Session) -> bool:
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = sess.get(robots_url, timeout=REQUEST_TIMEOUT)
        if resp.status_code >= 400:
            return True
        rp.parse(resp.text.splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def fetch_page(url: str, sess: requests.Session) -> str | None:
    try:
        resp = sess.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code >= 400:
            return None
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception:
        return None


def company_tokens(name: str) -> list[str]:
    core = re.sub(r"(株式会社|有限会社|合同会社|一般社団法人)", "", name).strip()
    tokens = [core] if len(core) >= 2 else []
    parts = re.split(r"[\s・\-]+", core)
    tokens.extend(p for p in parts if len(p) >= 2)
    return list(dict.fromkeys(tokens))


def score_hp_candidate(url: str, title: str, tokens: list[str]) -> int:
    if not is_hp_candidate(url):
        return -100
    score = 1
    blob = f"{url} {title}".lower()
    for token in tokens:
        if token.lower() in blob:
            score += 3
    if any(x in url.lower() for x in ("/company", "/about", "/corporate")):
        score += 1
    return score


def bing_search_hp(company: str, sess: requests.Session) -> str | None:
    tokens = company_tokens(company)
    short = re.sub(r"(株式会社|有限会社|合同会社)", "", company).strip()
    queries = [
        f"{company} 公式サイト",
        f"{short} 株式会社",
        f"{company} 会社概要",
    ]
    best_url: str | None = None
    best_score = -1

    for query in queries:
        params = {"q": query, "format": "rss", "setlang": "ja", "cc": "JP"}
        url = "https://www.bing.com/search?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                root = ET.fromstring(resp.read())
        except Exception:
            continue

        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            score = score_hp_candidate(link, title, tokens)
            if score > best_score:
                best_score = score
                best_url = link

        time.sleep(GOOGLE_RATE_LIMIT_SEC)
        if best_score >= 4:
            break

    return best_url if best_score > 0 else None


def google_search_hp(company: str, sess: requests.Session) -> str | None:
    query = urllib.parse.quote(f"{company} 公式")
    url = f"https://www.google.com/search?q={query}&hl=ja&num=5"
    html = fetch_page(url, sess)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if href.startswith("/url?"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            target = qs.get("q", [""])[0]
            if target.startswith("http") and is_hp_candidate(target):
                candidates.append(target)
        elif href.startswith("http") and is_hp_candidate(href):
            candidates.append(href)

    return candidates[0] if candidates else None


def build_crawl_urls(base_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    urls = [base_url.rstrip("/")]
    for path in CONTACT_PATHS:
        urls.append(urllib.parse.urljoin(root + "/", path.lstrip("/")))
    return list(dict.fromkeys(urls))


def crawl_for_contacts(
    base_url: str,
    sess: requests.Session,
    *,
    dry_run_log: bool = False,
) -> tuple[str | None, str | None, str | None]:
    """Returns (resolved_url, best_email, form_url)."""
    if not robots_allowed(base_url, sess):
        if dry_run_log:
            print(f"  [robots] disallowed: {base_url}")
        return base_url, None, None

    all_emails: list[str] = []
    form_urls: list[str] = []

    for page_url in build_crawl_urls(base_url):
        if not robots_allowed(page_url, sess):
            continue
        html = fetch_page(page_url, sess)
        time.sleep(HP_RATE_LIMIT_SEC)
        if not html:
            continue
        all_emails.extend(extract_emails_from_html(html))
        form_urls.extend(extract_form_urls(html, page_url))

    email = pick_best_email(all_emails)
    form_url = form_urls[0] if form_urls else None
    return base_url, email, form_url

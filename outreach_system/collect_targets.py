import argparse
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
TARGETS_CSV = BASE_DIR / "targets.csv"
COLLECT_LOG_JSON = BASE_DIR / "collect_log.json"

USER_AGENT = "Mozilla/5.0"
REQUEST_TIMEOUT = 15
REQUEST_SLEEP_SECONDS = 1

QUERIES = [
    "SES企業 東京 メールアドレス site:*.co.jp",
    "SIer 東京 採用 contact site:*.co.jp",
    "システム開発 受託 東京 問い合わせ site:*.co.jp",
    "SES派遣 IT企業 関東 mail",
    "フリーランスエンジニア 紹介 SES 東京",
]
FALLBACK_DOMAINS = {
    "SES企業 東京 メールアドレス site:*.co.jp": [
        "https://www.techbrain.co.jp",
        "https://www.mst-inc.co.jp",
        "https://www.brainets.co.jp",
    ],
    "SIer 東京 採用 contact site:*.co.jp": [
        "https://www.nsw.co.jp",
        "https://www.tis.co.jp",
    ],
    "システム開発 受託 東京 問い合わせ site:*.co.jp": [
        "https://www.nttdata.co.jp",
        "https://www.hitachi-solutions.co.jp",
    ],
    "SES派遣 IT企業 関東 mail": [
        "https://www.isg.co.jp",
        "https://www.fsi.co.jp",
    ],
    "フリーランスエンジニア 紹介 SES 東京": [
        "https://www.techbrain.co.jp",
        "https://www.brainets.co.jp",
    ],
}
KNOWN_COMPANY_NAMES = {
    "www.techbrain.co.jp": "テックブレーン株式会社",
    "www.mst-inc.co.jp": "エム・エス・ティー株式会社",
    "www.brainets.co.jp": "株式会社ブレインズ",
    "www.isg.co.jp": "株式会社ISG",
    "www.fsi.co.jp": "富士ソフト株式会社",
    "www.nsw.co.jp": "NSW株式会社",
    "www.tis.co.jp": "TIS株式会社",
    "www.nttdata.co.jp": "株式会社NTTデータ",
    "www.hitachi-solutions.co.jp": "株式会社日立ソリューションズ",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
CSV_COLUMNS = ["company", "contact_name", "email", "type", "memo"]
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.co.jp",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "example.com",
    "example.jp",
    "example.co.jp",
    "test.com",
    "test.co.jp",
}
INVALID_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
SKIP_URL_HOSTS = {
    "google.co.jp",
    "www.google.co.jp",
    "google.com",
    "www.google.com",
    "webcache.googleusercontent.com",
}


def sleep_after_request() -> None:
    time.sleep(REQUEST_SLEEP_SECONDS)


def fetch_url(session: requests.Session, url: str) -> Optional[str]:
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        sleep_after_request()
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding
        return response.text
    except requests.RequestException as exc:
        print(f"取得エラー: {url} ({exc})")
        return None


def normalize_site_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    host = parsed.netloc.lower()
    if host in SKIP_URL_HOSTS or host.endswith(".google.co.jp") or host.endswith(".google.com"):
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_google_result_url(href: str) -> Optional[str]:
    if href.startswith("/url?"):
        query = parse_qs(urlparse(href).query)
        return query.get("q", [None])[0]
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return None


def google_search_domains(session: requests.Session, query: str, limit: int = 5) -> List[str]:
    search_url = f"https://www.google.co.jp/search?q={quote_plus(query)}&num=10&hl=ja"
    html = fetch_url(session, search_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    domains: List[str] = []
    seen: Set[str] = set()
    for link in soup.select("a[href]"):
        result_url = extract_google_result_url(link.get("href", ""))
        if not result_url:
            continue
        site_url = normalize_site_url(result_url)
        if not site_url or site_url in seen:
            continue
        seen.add(site_url)
        domains.append(site_url)
        if len(domains) >= limit:
            break
    if domains:
        return domains

    fallback_domains = FALLBACK_DOMAINS.get(query, [])
    print(f"Google検索結果を抽出できないためフォールバック候補を使用: {query}")
    return fallback_domains[:limit]


def candidate_pages(site_url: str) -> Iterable[str]:
    parsed = urlparse(site_url)
    root = f"{parsed.scheme}://{parsed.netloc}/"
    yield root
    yield urljoin(root, "contact")
    yield urljoin(root, "contact/")
    yield urljoin(root, "contact.html")
    yield urljoin(root, "inquiry")
    yield urljoin(root, "inquiry/")
    yield urljoin(root, "inquiry.php")


def extract_emails(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    text_parts = [soup.get_text(" ", strip=True)]
    for link in soup.select("a[href^='mailto:']"):
        text_parts.append(link.get("href", "").replace("mailto:", ""))
    text = "\n".join(text_parts)

    emails: List[str] = []
    seen: Set[str] = set()
    for email in EMAIL_RE.findall(text):
        cleaned = email.strip().rstrip(".").lower()
        domain = cleaned.split("@")[-1]
        if domain in PERSONAL_EMAIL_DOMAINS or cleaned in seen or cleaned.endswith(INVALID_EMAIL_SUFFIXES):
            continue
        seen.add(cleaned)
        emails.append(cleaned)
    return emails


def extract_company_name(html: str, site_url: str) -> str:
    known_name = KNOWN_COMPANY_NAMES.get(urlparse(site_url).netloc.lower())
    if known_name:
        return known_name

    soup = BeautifulSoup(html, "html.parser")
    og_site_name = soup.find("meta", property="og:site_name")
    if og_site_name and og_site_name.get("content"):
        return normalize_company_name(og_site_name["content"])

    if soup.title and soup.title.string:
        return normalize_company_name(soup.title.string)

    host = urlparse(site_url).netloc
    return host.removeprefix("www.")


def normalize_company_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    for separator in ["｜", "|", " - ", " – ", " — ", "／", "/"]:
        if separator in cleaned:
            cleaned = cleaned.split(separator)[0].strip()
    return cleaned


def judge_company_type(site_url: str, html: str) -> str:
    text = f"{site_url}\n{BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)}"
    if any(keyword in text for keyword in ["SES", "ses", "派遣", "技術者派遣"]):
        return "ses"
    return "prime"


def load_existing_companies(csv_path: Path) -> Set[str]:
    if not csv_path.exists():
        return set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return {row.get("company", "").strip() for row in reader if row.get("company", "").strip()}


def collect_targets() -> Dict[str, object]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    existing_companies = load_existing_companies(TARGETS_CSV)
    collected: List[Dict[str, str]] = []
    skipped_duplicates = 0
    seen_companies = set(existing_companies)
    visited_sites: Set[str] = set()
    query_logs: List[Dict[str, object]] = []

    for query in QUERIES:
        domains = google_search_domains(session, query)
        query_logs.append({"query": query, "domains": domains})
        for site_url in domains:
            if site_url in visited_sites:
                continue
            visited_sites.add(site_url)

            for page_url in candidate_pages(site_url):
                html = fetch_url(session, page_url)
                if not html:
                    continue
                emails = extract_emails(html)
                if not emails:
                    continue

                company = extract_company_name(html, site_url)
                if company in seen_companies:
                    skipped_duplicates += 1
                    break

                row = {
                    "company": company,
                    "contact_name": "",
                    "email": emails[0],
                    "type": judge_company_type(site_url, html),
                    "memo": page_url,
                }
                collected.append(row)
                seen_companies.add(company)
                break

    return {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "queries": query_logs,
        "candidates": collected,
        "added_count": len(collected),
        "skipped_duplicate_count": skipped_duplicates,
    }


def append_targets(rows: List[Dict[str, str]], csv_path: Path) -> None:
    file_exists = csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        if not file_exists or csv_path.stat().st_size == 0:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_collect_log(result: Dict[str, object]) -> None:
    with COLLECT_LOG_JSON.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)


def print_preview(rows: List[Dict[str, str]]) -> None:
    for row in rows:
        print(f"{row['company']} / {row['email']} / {row['type']} / {row['memo']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IT・SES企業の連絡先を収集してtargets.csvへ追記します。")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="収集結果を表示し、CSVには書き込みません。")
    mode.add_argument("--run", action="store_true", help="収集結果をtargets.csvへ追記します。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = collect_targets()
    candidates = result["candidates"]

    if args.dry_run:
        print_preview(candidates)
    else:
        append_targets(candidates, TARGETS_CSV)

    write_collect_log(result)
    print(f"追加{result['added_count']}社 / スキップ{result['skipped_duplicate_count']}社（重複）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

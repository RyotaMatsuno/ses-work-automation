# -*- coding: utf-8 -*-
"""Phase 9 共通ユーティリティ（公式API・名寄せ）"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from crawl_common import BASE_DIR, SES_WORK_ROOT, today_str

ENV_PATH = SES_WORK_ROOT / "config" / ".env"

GBIZ_API_BASE = "https://api.info.gbiz.go.jp/hojin"
NTA_API_BASE = "https://api.houjin-bangou.nta.go.jp/4"

PREFECTURES = {
    "東京都": "13",
    "神奈川県": "14",
    "埼玉県": "11",
    "千葉県": "12",
    "愛知県": "23",
}

GBIZ_NAME_KEYWORDS = ["システム", "ソフト", "テクノロジー", "ソリューション", "IT"]
# 情報通信業に相当する営業品目（gBiz API business_item パラメータ）
GBIZ_BUSINESS_ITEM = "情報処理"
NTA_NAME_KEYWORDS = [
    "システムエンジニアリング",
    "システム開発",
    "ソフトウェア",
    "SES",
    "技術者派遣",
]

INDUSTRY_PATTERN = re.compile(r"情報通信")
NAME_KEYWORD_PATTERN = re.compile(
    r"システム|ソフト|テクノロジー|ソリューション|\bIT\b|ＩＴ",
    re.I,
)

POPULATION_ESTIMATE = 10_000

OUT_9A = BASE_DIR / "phase9a_gbiz_companies.csv"
OUT_9B = BASE_DIR / "phase9b_nta_companies.csv"
OUT_NEW = BASE_DIR / "phase9_new_companies.csv"
OUT_SCREENING = BASE_DIR / "phase9_screening_results.csv"
OUT_SUMMARY = BASE_DIR / "phase9_summary.md"
MASTER_FINAL = BASE_DIR / "ses_company_master_final.csv"

FIELDS_9A = [
    "corporate_number",
    "name",
    "location",
    "employee_number",
    "capital_stock",
    "date_of_establishment",
    "business_summary",
    "industry",
    "prefecture",
    "search_keyword",
    "source",
    "crawl_date",
]

FIELDS_9B = [
    "corporate_number",
    "name",
    "location",
    "employee_number",
    "capital_stock",
    "date_of_establishment",
    "business_summary",
    "search_keyword",
    "source",
    "crawl_date",
]

FIELDS_NEW = [
    "company_name",
    "company_core",
    "corporate_number",
    "location",
    "employee_number",
    "capital_stock",
    "date_of_establishment",
    "business_summary",
    "source_list",
    "crawl_date",
]

FIELDS_SCREENING = [
    "company_name",
    "company_core",
    "corporate_number",
    "is_ses_company",
    "bing_snippet_ses",
    "bing_snippet",
    "has_incentive_mention",
    "incentive_detail",
    "incentive_rate",
    "screened_date",
    "worker_part",
]


def load_env_value(key: str) -> str:
    val = (os.environ.get(key) or "").strip()
    if val:
        return val
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return ""


def gbiz_token() -> str:
    return load_env_value("GBIZ_API_TOKEN") or load_env_value("GBIZINFO_API_TOKEN")


def nta_app_id() -> str:
    return load_env_value("NTA_APP_ID") or load_env_value("HOUJIN_BANGOU_APP_ID")


def _http_json(
    url: str,
    *,
    headers: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "TERRA-SES-Phase9/1.0",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_text(
    url: str,
    *,
    headers: dict | None = None,
    timeout: float = 60.0,
) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TERRA-SES-Phase9/1.0",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def gbiz_search_page(
    *,
    token: str,
    name: str,
    prefecture: str,
    page: int = 1,
    limit: int = 1000,
    business_item: str = GBIZ_BUSINESS_ITEM,
) -> dict:
    params = {
        "name": name,
        "prefecture": prefecture,
        "page": str(page),
        "limit": str(limit),
        "metadata_flg": "true",
    }
    if business_item:
        params["business_item"] = business_item
    url = f"{GBIZ_API_BASE}/v2/hojin?{urllib.parse.urlencode(params)}"
    return _http_json(url, headers={"X-hojinInfo-api-token": token})


def normalize_gbiz_row(item: dict, *, prefecture: str, keyword: str) -> dict | None:
    corp = (item.get("corporate_number") or "").strip()
    name = (item.get("name") or "").strip()
    if not corp or not name:
        return None

    industry = item.get("industry") or ""
    if isinstance(industry, list):
        industry = " / ".join(str(x) for x in industry if x)
    industry = str(industry)

    if industry and not INDUSTRY_PATTERN.search(industry):
        return None
    if not NAME_KEYWORD_PATTERN.search(name):
        return None

    location = (item.get("location") or "").strip()
    if not location:
        pref = item.get("prefecture_name") or ""
        city = item.get("city_name") or ""
        location = f"{pref}{city}".strip()

    return {
        "corporate_number": corp,
        "name": name,
        "location": location[:200],
        "employee_number": str(item.get("employee_number") or ""),
        "capital_stock": str(item.get("capital_stock") or ""),
        "date_of_establishment": str(item.get("date_of_establishment") or ""),
        "business_summary": str(item.get("business_summary") or "")[:1000],
        "industry": industry[:200],
        "prefecture": prefecture,
        "search_keyword": keyword,
        "source": "gbizinfo",
        "crawl_date": today_str(),
    }


def nta_name_search(
    *,
    app_id: str,
    name: str,
    divide: int = 1,
    mode: int = 2,
) -> ET.Element:
    params = {
        "id": app_id,
        "name": name,
        "type": "12",
        "mode": str(mode),
        "divide": str(divide),
        "change": "0",
    }
    url = f"{NTA_API_BASE}/name?{urllib.parse.urlencode(params)}"
    xml_text = _http_text(url)
    return ET.fromstring(xml_text)


def parse_nta_corporations(root: ET.Element) -> tuple[list[dict], int, int]:
    divide_size = 1
    divide_number = 1
    ds = root.find(".//divideSize")
    dn = root.find(".//divideNumber")
    if ds is not None and ds.text:
        divide_size = int(ds.text)
    if dn is not None and dn.text:
        divide_number = int(dn.text)

    rows: list[dict] = []
    for corp in root.findall(".//corporation"):
        corp_num = (corp.findtext("corporateNumber") or "").strip()
        name = (corp.findtext("name") or "").strip()
        if not corp_num or not name:
            continue
        pref = (corp.findtext("prefectureName") or "").strip()
        city = (corp.findtext("cityName") or "").strip()
        street = (corp.findtext("streetNumber") or "").strip()
        location = f"{pref}{city}{street}".strip()
        rows.append(
            {
                "corporate_number": corp_num,
                "name": name,
                "location": location[:200],
                "employee_number": "",
                "capital_stock": "",
                "date_of_establishment": "",
                "business_summary": "",
            }
        )
    return rows, divide_number, divide_size


def ses_signal_from_snippets(snippets: list[str]) -> bool:
    combined = " ".join(snippets)
    if re.search(r"\bSES\b|エスイーエス|技術者派遣|派遣.*エンジニア|請負.*開発", combined, re.I):
        return True
    if re.search(r"システム開発|受託開発|IT人材|エンジニア派遣", combined, re.I):
        return True
    return False


def rate_limit_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)

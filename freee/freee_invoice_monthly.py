"""
freee_invoice_monthly.py
前月稼働分のfreee請求書を月次で作成する。

既定はdry-run。実POSTは --execute 指定時のみ行う。

※廃止: freee_invoice_v2.py に一本化（2026-06-19）
"""

import sys

print("このスクリプトは廃止されました。freee_invoice_v2.py を使用してください。")
sys.exit(0)

import argparse
import calendar
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(ROOT_DIR, "freee_auth")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if AUTH_DIR not in sys.path:
    sys.path.insert(0, AUTH_DIR)

from token_manager import get_headers

import sheets_reader as SR

FREEE_BASE_INV = "https://api.freee.co.jp/iv"
COMPANY_ID = 11712776
TEMPLATE_ID = 3323260
LINE_UNIT = "式"
GENSHEN = "株式会社TERRA"
NO_BILLING_TEXT = "請求なし"

PARTNER_IDS = {
    "株式会社TERRA": 91256138,
    "株式会社フラップテック": 113795090,
    "グレイスライン株式会社": 117422289,
}

GL_SITE = {
    "石崎春光": "30",
    "山内清": "45",
    "荒井大輝": "45",
}


def gv(row, index):
    return row[index].strip() if index < len(row) and row[index] else ""


def to_int(value):
    try:
        cleaned = str(value).replace(",", "").replace("¥", "").replace("円", "").strip()
        if not cleaned:
            return 0
        return int(cleaned)
    except Exception:
        return 0


def parse_optional_int(value):
    cleaned = str(value).replace(",", "").replace("¥", "").replace("円", "").strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except Exception:
        return None


def get_target_dates(today=None):
    today = today or date.today()
    billing_date = today.replace(day=1)
    close = billing_date - timedelta(days=1)
    target_month = close.month
    subject = f"{target_month}月分請求書"
    return {
        "target_year": close.year,
        "target_month": target_month,
        "close": close,
        "billing_date": billing_date,
        "subject": subject,
    }


def included(status, target_month):
    return ("稼働中" in status) or (f"{target_month}月末終了" in status)


def bucket(partner, site):
    if partner == "株式会社フラップテック":
        return "45"
    site_days = to_int(site)
    if site_days <= 30:
        return "30"
    if site_days <= 45:
        return "45"
    return "46"


def is_japanese_holiday(day):
    try:
        import jpholiday

        return jpholiday.is_holiday(day)
    except Exception:
        return False


def payment_date(close, bucket_days):
    day = close + timedelta(days=int(bucket_days))
    while day.weekday() >= calendar.SATURDAY or is_japanese_holiday(day):
        day += timedelta(days=1)
    return day.isoformat()


def freee_headers():
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    return headers


def load_people(target_month):
    ss = SR._open()
    people = []
    warnings = []

    for row in ss.worksheet("TERRA").get_all_values()[4:]:
        name = gv(row, 3)
        if not name or name in ("氏名", "稼働中合計"):
            continue

        status = gv(row, 2)
        kubun = gv(row, 1)
        case = gv(row, 6)
        tanka = to_int(gv(row, 7))
        site = gv(row, 8)
        shiire = to_int(gv(row, 13))
        tantou = gv(row, 0)
        terra_amount_raw = gv(row, 15)

        if not included(status, target_month):
            continue

        if kubun == "P" and any(k in case for k in ("GL", "FT", "グレイスライン", "フラップテック")):
            warnings.append(f"TERRA {name}: GL/FT経由のP行のためTERRA計上せず")
            continue

        if NO_BILLING_TEXT in terra_amount_raw:
            warnings.append(f"TERRA {name}: TERRA請求額が'{NO_BILLING_TEXT}'のため除外")
            continue

        if not site:
            warnings.append(f"TERRA {name}: サイト空白のため除外")
            continue

        explicit_amount = parse_optional_int(terra_amount_raw)
        if explicit_amount is not None:
            if kubun == "P" and explicit_amount == 15000:
                people.append({"partner": GENSHEN, "name": name, "site": site, "prop": True})
            else:
                people.append(
                    {"partner": GENSHEN, "name": name, "site": site, "prop": False, "amount": explicit_amount}
                )
            continue

        if kubun == "P":
            people.append({"partner": GENSHEN, "name": name, "site": site, "prop": True})
            continue

        profit = tanka - shiire
        if tantou == "TERRA折半":
            amount = int(profit * 0.50)
        elif tantou == "岡本折半":
            amount = int(profit * 0.80)
        else:
            amount = int(profit * 0.80)
        people.append({"partner": GENSHEN, "name": name, "site": site, "prop": False, "amount": amount})

    for row in ss.worksheet("フラップテック").get_all_values()[3:]:
        name = gv(row, 2)
        if not name or name == "氏名":
            continue

        status = gv(row, 1)
        tantou = gv(row, 0)
        tanka = to_int(gv(row, 6))
        shiire = to_int(gv(row, 7))
        site = gv(row, 12)

        if not included(status, target_month):
            continue
        if not site:
            warnings.append(f"FT {name}: サイト空白のため除外")
            continue

        profit = tanka - shiire
        amount = int(profit * 0.48) if tantou == "小坂折半" else int(profit * 0.68)
        people.append(
            {
                "partner": "株式会社フラップテック",
                "name": name,
                "site": site,
                "prop": False,
                "amount": amount,
            }
        )

    for row in ss.worksheet("グレイスライン").get_all_values()[3:]:
        name = gv(row, 1)
        if not name or name == "氏名":
            continue

        status = gv(row, 0)
        tanka = to_int(gv(row, 5))
        shiire = to_int(gv(row, 6))

        if not included(status, target_month):
            continue

        site = GL_SITE.get(name, "")
        if not site:
            warnings.append(f"GL {name}: サイト不明のため除外")
            continue

        people.append(
            {
                "partner": "グレイスライン株式会社",
                "name": name,
                "site": site,
                "prop": False,
                "amount": int((tanka - shiire) * 0.60),
            }
        )

    return people, warnings


def group_people(people):
    groups = defaultdict(list)
    for person in people:
        groups[(person["partner"], bucket(person["partner"], person["site"]))].append(person)
    return groups


def build_lines(partner, people):
    # 源泉徴収ルール（確定）: TERRA=あり / GL=なし / FT=なし
    withholding_flag = partner == GENSHEN
    props = [person for person in people if person.get("prop")]
    inds = [person for person in people if not person.get("prop")]
    lines = []

    if props:
        lines.append(
            {
                "type": "item",
                "description": "プロパー稼働分",
                "quantity": len(props),
                "unit": LINE_UNIT,
                "unit_price": "15000",
                "tax_rate": 10,
                "reduced_tax_rate": False,
                "withholding": withholding_flag,
            }
        )

    for person in inds:
        lines.append(
            {
                "type": "item",
                "description": f"{person['name']}様稼働分",
                "quantity": 1,
                "unit": LINE_UNIT,
                "unit_price": str(person["amount"]),
                "tax_rate": 10,
                "reduced_tax_rate": False,
                "withholding": withholding_flag,
            }
        )

    return lines


def build_payload(partner, bucket_days, people, dates):
    return {
        "company_id": COMPANY_ID,
        "partner_id": PARTNER_IDS[partner],
        "template_id": TEMPLATE_ID,
        "billing_date": dates["billing_date"].isoformat(),
        "payment_date": payment_date(dates["close"], bucket_days),
        "subject": dates["subject"],
        "payment_type": "transfer",
        "tax_entry_method": "out",
        "tax_fraction": "omit",
        "withholding_tax_entry_method": "out",
        "partner_title": "御中",
        "sending_status": "unsent",
        "lines": build_lines(partner, people),
    }


def fetch_existing_invoice_keys(billing_date, subject):
    existing = set()
    offset = 0
    while True:
        res = requests.get(
            f"{FREEE_BASE_INV}/invoices",
            headers=freee_headers(),
            params={"company_id": COMPANY_ID, "limit": 100, "offset": offset},
        )
        if res.status_code != 200:
            raise RuntimeError(f"GET /iv/invoices failed status={res.status_code}: {res.text[:300]}")

        invoices = res.json().get("invoices") or []
        for invoice in invoices:
            if invoice.get("billing_date") == billing_date and invoice.get("subject") == subject:
                existing.add((invoice.get("partner_id"), invoice.get("payment_date")))

        if len(invoices) < 100:
            break
        offset += 100

    return existing


def create_invoice(payload):
    res = requests.post(f"{FREEE_BASE_INV}/invoices", headers=freee_headers(), json=payload)
    if res.status_code not in (200, 201):
        raise RuntimeError(f"POST /iv/invoices failed status={res.status_code}: {res.text[:300]}")
    return res.json()["invoice"]["id"]


def run(execute=False):
    dates = get_target_dates()
    mode = "EXECUTE" if execute else "DRY-RUN"

    print(f"=== freee請求書月次自動生成 / {mode} ===")
    print(f"対象稼働月: {dates['target_year']}-{dates['target_month']:02d}")
    print(f"締め日 close: {dates['close'].isoformat()}")
    print(f"billing_date: {dates['billing_date'].isoformat()}")
    print(f"subject: {dates['subject']}")
    if not execute:
        print("DRY-RUN: payloadを表示します。POSTは行いません。")

    people, warnings = load_people(dates["target_month"])
    groups = group_people(people)
    existing = fetch_existing_invoice_keys(dates["billing_date"].isoformat(), dates["subject"])
    print(f"[dedup] {dates['billing_date'].isoformat()} '{dates['subject']}' 既存請求書 {len(existing)} 件")

    created = skipped = errors = total = 0
    for partner, bucket_days in sorted(groups, key=lambda item: (item[0], int(item[1]))):
        group = groups[(partner, bucket_days)]
        total += 1
        try:
            payload = build_payload(partner, bucket_days, group, dates)
            key = (payload["partner_id"], payload["payment_date"])

            if not execute:
                if key in existing:
                    skipped += 1
                    status = "DRY-SKIP"
                    note = " / 既存あり"
                else:
                    created += 1
                    status = "DRY"
                    note = ""
                print(f"[{status}] {partner} / {bucket_days}日 / 支払期限{payload['payment_date']}{note}")
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                continue

            if key in existing:
                skipped += 1
                print(f"SKIP {partner} / {bucket_days}日 / 支払期限{payload['payment_date']} / 既存あり")
                continue

            invoice_id = create_invoice(payload)
            created += 1
            print(f"OK {partner} / {bucket_days}日 / 支払期限{payload['payment_date']} / invoice_id={invoice_id}")
        except Exception as exc:
            errors += 1
            print(f"NG {partner} / {bucket_days}日 / {exc}")

    if warnings:
        print("=== 警告/除外 ===")
        for warning in warnings:
            print(f"  ・{warning}")

    label = "作成予定" if not execute else "作成"
    print(f"=== 完了: {label}{created}件 / SKIP{skipped}件 / エラー{errors}件 / 対象{total}件 ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="freee請求書月次自動生成")
    parser.add_argument("--execute", action="store_true", help="実際にPOSTして請求書を作成する")
    args = parser.parse_args()
    run(execute=args.execute)

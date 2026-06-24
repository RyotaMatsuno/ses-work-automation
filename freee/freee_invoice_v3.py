"""
freee_invoice_v3.py
5月分請求書をfreee /iv APIで下書き作成する。

既定はdry-run。実POSTは --execute 指定時のみ行う。
"""

import argparse
import json
import os
import runpy
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FREEE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DIR = os.path.join(ROOT_DIR, "freee_auth")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if AUTH_DIR not in sys.path:
    sys.path.insert(0, AUTH_DIR)

from token_manager import get_headers

FREEE_BASE_INV = "https://api.freee.co.jp/iv"
COMPANY_ID = 11712776
TEMPLATE_ID = 3323260
BILLING_DATE = "2026-06-01"
SUBJECT = "5月分請求書"
LINE_UNIT = "式"
GENSHEN = "株式会社TERRA"

PARTNER_IDS = {
    "株式会社TERRA": 91256138,
    "株式会社フラップテック": 113795090,
    "グレイスライン株式会社": 117422289,
}


def freee_headers():
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    return headers


def load_proposal2_context():
    path = os.path.join(FREEE_DIR, "_proposal2.py")
    cwd = os.getcwd()
    try:
        os.chdir(ROOT_DIR)
        return runpy.run_path(path)
    finally:
        os.chdir(cwd)


def fetch_existing_invoice_keys():
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
            if invoice.get("billing_date") == BILLING_DATE and invoice.get("subject") == SUBJECT:
                existing.add((invoice.get("partner_id"), invoice.get("payment_date")))

        if len(invoices) < 100:
            break
        offset += 100
    return existing


def build_lines(partner, people):
    withholding_flag = partner == GENSHEN
    props = [p for p in people if p.get("prop")]
    inds = [p for p in people if not p.get("prop")]
    lines = []

    if props:
        pm = sum(p["pm"] for p in props)
        lines.append(
            {
                "type": "item",
                "description": "プロパー稼働分",
                "quantity": round(pm, 2),
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


def build_payload(partner, bucket, people, pay_date):
    partner_id = PARTNER_IDS[partner]
    payment_date = pay_date(bucket)
    return {
        "company_id": COMPANY_ID,
        "partner_id": partner_id,
        "template_id": TEMPLATE_ID,
        "billing_date": BILLING_DATE,
        "payment_date": payment_date,
        "subject": SUBJECT,
        "payment_type": "transfer",
        "tax_entry_method": "out",
        "tax_fraction": "omit",
        "withholding_tax_entry_method": "out",
        "partner_title": "御中",
        "sending_status": "unsent",
        "lines": build_lines(partner, people),
    }


def create_invoice(payload):
    res = requests.post(f"{FREEE_BASE_INV}/invoices", headers=freee_headers(), json=payload)
    if res.status_code not in (200, 201):
        raise RuntimeError(f"POST /iv/invoices failed status={res.status_code}: {res.text[:300]}")
    return res.json()["invoice"]["id"]


def run(execute=False):
    mode = "EXECUTE" if execute else "DRY-RUN"
    print(f"=== freee請求書自動生成 v3 / {mode} ===")
    if not execute:
        print("DRY-RUN: payloadを表示します。POSTは行いません。")

    ctx = load_proposal2_context()
    groups = ctx["groups"]
    pay_date = ctx["pay_date"]

    existing = fetch_existing_invoice_keys()
    print(f"[dedup] {BILLING_DATE} '{SUBJECT}' 既存請求書 {len(existing)} 件")

    created = skipped = errors = 0
    total = 0
    for partner, bucket in sorted(groups, key=lambda x: (x[0], int(x[1]))):
        people = groups[(partner, bucket)]
        try:
            payload = build_payload(partner, bucket, people, pay_date)
            key = (payload["partner_id"], payload["payment_date"])
            total += 1

            if key in existing:
                skipped += 1
                print(f"SKIP {partner} / {bucket}日 / 支払期限{payload['payment_date']} / 既存あり")
                continue

            if not execute:
                created += 1
                print(f"[DRY] {partner} / {bucket}日 / 支払期限{payload['payment_date']}")
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                continue

            invoice_id = create_invoice(payload)
            created += 1
            print(f"OK {partner} / {bucket}日 / 支払期限{payload['payment_date']} / invoice_id={invoice_id}")
        except Exception as exc:
            errors += 1
            print(f"NG {partner} / {bucket}日 / {exc}")

    label = "作成予定" if not execute else "作成"
    print(f"=== 完了: {label}{created}件 / SKIP{skipped}件 / エラー{errors}件 / 対象{total}件 ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="freee請求書自動生成 v3")
    parser.add_argument("--execute", action="store_true", help="実際にPOSTして請求書を作成する")
    args = parser.parse_args()
    run(execute=args.execute)

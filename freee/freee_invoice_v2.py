"""
freee_invoice_v2.py
契約マスターSheetを正として稼働中人員の請求書をfreee /iv APIで下書き作成。

CostGuard: LLM呼び出しなし（freee API / Sheets API のみ）— cost_guard_v2 Phase 7.4 対象外・確認済み。

請求ルール:
【TERRA】源泉あり / 件名: {Y}年{M}月分請求書
  P（GL/FT経由以外）: 15,000円固定・プロパー合算行
  P（GL/FT経由）: 請求なし
  BP: 粗利×80% / TERRA折半: 粗利×50% / 岡本折半: 粗利×80%
【フラップテック】源泉なし
  通常・岡本折半・岡本全額: 粗利×68% / 小坂折半: 粗利×48%
【グレイスライン】源泉なし
  粗利×60% / 摘要に月数明記
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import requests
from dateutil.relativedelta import relativedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(ROOT_DIR, "freee_auth")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if AUTH_DIR not in sys.path:
    sys.path.insert(0, AUTH_DIR)

from token_manager import get_headers

import sheets_reader as SR

FREEE_BASE_ACCT = "https://api.freee.co.jp/api/1"
FREEE_BASE_INV = "https://api.freee.co.jp/iv"
FREEE_BASE = FREEE_BASE_ACCT
COMPANY_ID = 11712776
TEMPLATE_ID = 3323260
LINE_UNIT = ""
GENSHEN = "株式会社TERRA"

# 源泉徴収ポリシー (default False).
# 現行運用では TERRA(GENSHEN) のみ源泉あり。金額計算ロジックは変更しない。
# TODO: CEO未確認 — ポリシー変更時は松野確認必須。
WITHHOLDING_DEFAULT = False
WITHHOLDING_PARTNERS: frozenset[str] = frozenset({GENSHEN})


def partner_applies_withholding(partner: str) -> bool:
    if partner in WITHHOLDING_PARTNERS:
        return True
    return WITHHOLDING_DEFAULT


class DuplicateInvoiceError(Exception):
    """partner_id × payment_date × total_amount の重複請求書検出時に送出。"""


def freee_headers():
    h = get_headers()
    h["Content-Type"] = "application/json"
    return h


def _load_env():
    env = {}
    env_path = os.path.join(ROOT_DIR, "config", ".env")
    if not os.path.exists(env_path):
        return env
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _notify_matsuno(text):
    try:
        from line_webhook.line_bridge import push_or_log

        uid = _load_env().get("MATSUNO_LINE_USER_ID", "")
        if uid:
            push_or_log(uid, text, "freee_invoice_v2")
    except Exception as exc:
        print(f"[notify] LINE通知スキップ: {exc}")


def get_payment_bucket(site_days: int, source: str) -> str:
    if source == "FT":
        return "45"
    if site_days <= 30:
        return "30"
    if site_days <= 45:
        return "45"
    return "60"


def estimate_total_amount(lines, withholding=False):
    sub = 0
    for line in lines:
        qty = float(line.get("quantity", 1))
        sub += int(float(line["unit_price"]) * qty)
    tax = int(sub * 10 / 100)
    total = sub + tax
    if withholding:
        total -= int(sub * 1021 / 10000)
    return total


def is_japanese_holiday(day):
    try:
        import jpholiday

        return jpholiday.is_holiday(day)
    except Exception:
        return False


def payment_date(close: date, bucket_days: str) -> str:
    day = close + timedelta(days=int(bucket_days))
    while day.weekday() >= calendar.SATURDAY or is_japanese_holiday(day):
        day += timedelta(days=1)
    return day.isoformat()


def invoice_dates(target_month: date) -> dict:
    close = (target_month.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
    billing = close + timedelta(days=1)
    return {
        "close": close,
        "billing_date": billing,
        "subject": f"{target_month.year}年{target_month.month}月分請求書",
    }


def group_entries(entries):
    groups = defaultdict(list)
    for entry in entries:
        bucket = get_payment_bucket(entry["site_days"], entry["source"])
        groups[(entry["partner"], bucket)].append(entry)
    return groups


def build_lines(partner, people, target_month: date):
    withholding_flag = partner_applies_withholding(partner)
    props = [p for p in people if p.get("is_prop")]
    inds = [p for p in people if not p.get("is_prop")]
    lines = []

    if props:
        lines.append(
            {
                "type": "item",
                "description": "プロパー稼働分",
                "quantity": len(props),
                **({"unit": LINE_UNIT} if LINE_UNIT else {}),
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
                "description": person["description"],
                "quantity": 1,
                **({"unit": LINE_UNIT} if LINE_UNIT else {}),
                "unit_price": str(person["seikyu"]),
                "tax_rate": 10,
                "reduced_tax_rate": False,
                "withholding": withholding_flag,
            }
        )
    return lines


def build_payload(partner, bucket, people, dates):
    lines = build_lines(partner, people, dates["billing_date"])
    return {
        "company_id": COMPANY_ID,
        "partner_id": None,
        "template_id": TEMPLATE_ID,
        "billing_date": dates["billing_date"].isoformat(),
        "payment_date": payment_date(dates["close"], bucket),
        "subject": dates["subject"],
        "payment_type": "transfer",
        "tax_entry_method": "out",
        "tax_fraction": "omit",
        "withholding_tax_entry_method": "out",
        "partner_title": "御中",
        "sending_status": "unsent",
        "lines": lines,
    }


def get_or_create_partner(name, dry_run=False):
    res = requests.get(
        f"{FREEE_BASE}/partners",
        headers=freee_headers(),
        params={"company_id": COMPANY_ID, "keyword": name},
    )
    partners = res.json().get("partners", [])
    if partners:
        return partners[0]["id"]
    if dry_run:
        print(f"  [DRY] partner-missing:{name}")
        return 0
    res2 = requests.post(
        f"{FREEE_BASE}/partners",
        headers=freee_headers(),
        json={"company_id": COMPANY_ID, "name": name, "partner_type": "customer"},
    )
    return res2.json()["partner"]["id"]


def fetch_existing_invoice_keys(billing_date: str, subject: str):
    existing = set()
    offset = 0
    while True:
        try:
            r = requests.get(
                f"{FREEE_BASE_INV}/invoices",
                headers=freee_headers(),
                params={"company_id": COMPANY_ID, "limit": 100, "offset": offset},
            )
        except Exception as e:
            print(f"[dedup] 一覧取得エラー: {e}")
            return None
        if r.status_code != 200:
            print(f"[dedup] 一覧取得失敗 status={r.status_code}: {r.text[:150]}")
            return None
        invs = r.json().get("invoices") or []
        for inv in invs:
            if inv.get("billing_date") == billing_date and inv.get("subject") == subject:
                existing.add((inv.get("partner_id"), inv.get("payment_date")))
        if len(invs) < 100:
            break
        offset += 100
    return existing


def fetch_existing_invoice_triples():
    triples = set()
    offset = 0
    while True:
        try:
            r = requests.get(
                f"{FREEE_BASE_INV}/invoices",
                headers=freee_headers(),
                params={"company_id": COMPANY_ID, "limit": 100, "offset": offset},
            )
        except Exception as e:
            print(f"[dedup] 一覧取得エラー: {e}")
            return None
        if r.status_code != 200:
            print(f"[dedup] 一覧取得失敗 status={r.status_code}: {r.text[:150]}")
            return None
        invs = r.json().get("invoices") or []
        for inv in invs:
            partner_id = inv.get("partner_id")
            payment_date_val = inv.get("payment_date")
            total_amount = inv.get("total_amount")
            if partner_id is not None and payment_date_val and total_amount is not None:
                triples.add((int(partner_id), str(payment_date_val), int(total_amount)))
        if len(invs) < 100:
            break
        offset += 100
    return triples


def check_duplicate_invoice(partner_id, payment_date_str, total_amount, existing_triples):
    if not existing_triples:
        return
    key = (int(partner_id), str(payment_date_str), int(total_amount))
    if key in existing_triples:
        raise DuplicateInvoiceError(
            f"重複請求書: partner_id={partner_id} payment_date={payment_date_str} total_amount={total_amount:,}円"
        )


def create_group_invoice(partner, bucket, people, dates, *, dry_run=False, existing_keys=None, existing_triples=None):
    payload = build_payload(partner, bucket, people, dates)
    partner_id = get_or_create_partner(partner, dry_run=dry_run)
    payload["partner_id"] = partner_id
    withholding = partner_applies_withholding(partner)
    total_amount = estimate_total_amount(payload["lines"], withholding=withholding)
    key = (partner_id, payload["payment_date"])
    if existing_keys and key in existing_keys:
        print(f"  SKIP {partner} / {bucket}日 / 支払期限{payload['payment_date']} / 既存あり")
        return "skip"
    if not dry_run or partner_id:
        check_duplicate_invoice(partner_id, payload["payment_date"], total_amount, existing_triples)

    if dry_run:
        print(f"\n■ {partner} / {bucket}日バケット / 支払期限 {payload['payment_date']}")
        print(f"  件名: {payload['subject']}")
        print(f"  源泉徴収: {'あり' if withholding else 'なし'} / 合計(税込源泉控除後目安): {total_amount:,}円")
        for person in people:
            if person.get("is_prop"):
                print(f"  - プロパー: {person['name']} | {person['rule']} | 15,000円")
            else:
                print(
                    f"  - {person['name']} | {person['rule']} | 粗利{person['profit']:,}円 → 請求{person['seikyu']:,}円"
                )
        for line in payload["lines"]:
            qty = line.get("quantity", 1)
            print(f"  明細: {line['description']} × {qty} @ {line['unit_price']}円")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return True

    res = requests.post(f"{FREEE_BASE_INV}/invoices", headers=freee_headers(), json=payload)
    if res.status_code in (200, 201):
        inv_id = res.json()["invoice"]["id"]
        print(f"  OK {partner} / {bucket}日 / ID:{inv_id} / 合計目安:{total_amount:,}円")
        return True
    print(f"  NG {partner} / {res.status_code}: {res.text[:200]}")
    return False


def _guard_execute(execute: bool) -> bool:
    if not execute:
        return False
    if os.environ.get("FREEE_WRITE_APPROVED", "").strip() != "1":
        print("[freee_invoice_v2] FREEE_WRITE_APPROVED=1 未設定: 実POSTブロック")
        return False
    return True


def run(target_month=None, dry_run=True, limit=None):
    today = date.today()
    if target_month is None:
        target_month = today.replace(day=1) + relativedelta(months=1)
    if isinstance(target_month, str):
        y, m = map(int, target_month.split("-"))
        target_month = date(y, m, 1)

    dates = invoice_dates(target_month)
    execute = not dry_run

    print("=== freee請求書自動生成 v2 ===")
    if dry_run:
        print("DRY-RUN: 請求書・取引先の作成/更新は行いません")
    else:
        if not _guard_execute(True):
            raise RuntimeError("--execute には FREEE_WRITE_APPROVED=1（松野承認）が必要です")
        print("EXECUTE: freeeへ請求書ドラフトを作成します")
    print(f"請求対象月: {target_month.year}年{target_month.month}月分")
    print(f"請求日(billing_date): {dates['billing_date']}  締め日(close): {dates['close']}")
    print(f"件名: {dates['subject']}")
    print()

    entries, meta = SR.load_active_entries(target_month=target_month)
    if limit is not None:
        entries = entries[:limit]

    print(f"対象人員: {len(entries)}名")
    for e in entries:
        bucket = get_payment_bucket(e["site_days"], e["source"])
        print(
            f"  {e['source']} | {e['name']} | 粗利{e['profit']:,}円 | 請求{e['seikyu']:,}円 | "
            f"{e['rule']} | サイト{e['site_days']}日→バケット{bucket}"
        )
    print()

    if meta["excluded_gl_ft_props"]:
        print("GL経由TERRAプロパー除外:")
        for item in meta["excluded_gl_ft_props"]:
            print(f"  - {item}")
        print()
    if meta["skipped_no_start"]:
        print("開始日未入力スキップ:")
        for item in meta["skipped_no_start"]:
            print(f"  - {item}")
        print()
    if meta["skipped_inactive"]:
        print("契約期間外スキップ:")
        for item in meta["skipped_inactive"]:
            print(f"  - {item}")
        print()
    if meta["skipped_other"]:
        print("その他スキップ:")
        for item in meta["skipped_other"]:
            print(f"  - {item}")
        print()
    for msg in meta.get("site_missing_warnings", []):
        print(msg)
    if meta.get("site_missing_warnings"):
        print()

    groups = group_entries(entries)
    print(f"請求書グループ: {len(groups)}枚（取引先×支払サイトバケット）")
    for (partner, bucket), people in sorted(groups.items(), key=lambda x: (x[0][0], int(x[0][1]))):
        print(f"  - {partner} / {bucket}日: {len(people)}名")
    print()

    existing_keys = fetch_existing_invoice_keys(dates["billing_date"].isoformat(), dates["subject"])
    if existing_keys is None:
        print("[dedup] 冪等チェックに失敗したため、二重請求防止のため処理を中止します。")
        return
    print(f"[dedup] {dates['billing_date']} '{dates['subject']}' 既存請求書 {len(existing_keys)} 件")

    existing_triples = fetch_existing_invoice_triples()
    if existing_triples is None:
        print("[dedup] 三重キー取得に失敗したため、二重請求防止のため処理を中止します。")
        return
    print(f"[dedup] 既存請求書キー(partner×支払日×合計) {len(existing_triples)} 件")
    print()

    ok = ng = skipped = dup = 0
    for (partner, bucket), people in sorted(groups.items(), key=lambda x: (x[0][0], int(x[0][1]))):
        try:
            r = create_group_invoice(
                partner,
                bucket,
                people,
                dates,
                dry_run=dry_run,
                existing_keys=existing_keys,
                existing_triples=existing_triples,
            )
        except DuplicateInvoiceError as exc:
            msg = f"[freee請求] {partner}: {exc}"
            print(f"  DUPLICATE {partner} / {exc}")
            _notify_matsuno(msg)
            dup += 1
            continue
        if r == "skip":
            skipped += 1
        elif r:
            ok += 1
        else:
            ng += 1

    print()
    if dry_run:
        print(f"=== DRY-RUN完了: 作成予定{ok}枚 / SKIP{skipped}枚 / 重複{dup}枚 / エラー{ng}枚 ===")
    else:
        print(f"=== 完了: 作成{ok}枚 / SKIP{skipped}枚 / 重複{dup}枚 / エラー{ng}枚 ===")
    print("-> https://secure.freee.co.jp/invoices")

    if ok > 0 and execute:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from auto_status_update import update_status_after_invoice

            invoiced_names = [e["name"] for e in entries]
            print("\n[auto_status] 請求書作成済み人員のステータスを稼働中に更新...")
            update_status_after_invoice(names=invoiced_names)
        except Exception as exc:
            print(f"[auto_status] ステータス更新スキップ（エラー: {exc}）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="freee請求書自動生成 v2")
    parser.add_argument("target_month", nargs="?", help="請求対象月 YYYY-MM")
    parser.add_argument("--dry-run", action="store_true", help="payloadを表示し、POST/作成は行わない（デフォルト）")
    parser.add_argument("--execute", action="store_true", help="freeeへ実POST/作成（FREEE_WRITE_APPROVED=1 必須）")
    parser.add_argument("--limit", type=int, help="先頭N件のみ処理")
    args = parser.parse_args()
    dry_run = not args.execute
    if args.target_month:
        y, m = map(int, args.target_month.split("-"))
        run(date(y, m, 1), dry_run=dry_run, limit=args.limit)
    else:
        run(dry_run=dry_run, limit=args.limit)

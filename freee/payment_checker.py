# -*- coding: utf-8 -*-
"""
freee payment status checker.

Usage:
  python freee/payment_checker.py --dry-run
  python freee/payment_checker.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
SES_WORK_DIR = BASE_DIR.parent
ENV_PATH = SES_WORK_DIR / "config" / ".env"
LOG_PATH = SES_WORK_DIR / "logs" / "payment_check.log"
NOTIFIED_PATH = SES_WORK_DIR / "logs" / "payment_notified.json"
FREEE_AUTH_DIR = SES_WORK_DIR / "freee_auth"
LINE_NOTIFY_DIR = SES_WORK_DIR / "line_notify"
FREEE_BASE = "https://api.freee.co.jp/api/1"
DEFAULT_COMPANY_ID = "11712776"
ALERT_PAYMENT_STATUSES = {"unsettled", "partially_paid", "unpaid"}
PAID_PAYMENT_STATUSES = {"paid", "settled"}

sys.path.insert(0, str(FREEE_AUTH_DIR))
sys.path.insert(0, str(LINE_NOTIFY_DIR))
from notify_line import send_line_message  # noqa: E402
from token_manager import get_headers  # noqa: E402


@dataclass
class PaymentAlert:
    invoice_id: int
    partner_name: str
    amount: int | None
    payment_due_date: date
    payment_status: str

    @property
    def overdue_days(self) -> int:
        return (date.today() - self.payment_due_date).days

    @property
    def notify_key(self) -> str:
        return f"{self.invoice_id}:{self.payment_due_date.isoformat()}:{self.payment_status}"


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config() -> dict[str, str]:
    config = dotenv_values(ENV_PATH, encoding="utf-8")
    return {k: v for k, v in config.items() if k and v is not None}


def freee_headers() -> dict[str, str]:
    headers = get_headers()
    headers["Accept"] = "application/json"
    return headers


import jpholiday as _jpholiday


def _is_business_day(d: date) -> bool:
    """土日・日本祝日でなければTrue"""
    return d.weekday() < 5 and not _jpholiday.is_holiday(d)


def _next_business_day(d: date) -> date:
    """d が休業日なら次の営業日を返す"""
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


def should_run_today() -> bool:
    """
    毎月15日・末日（28日タスク）に起動されるが、
    その日が土日祝の場合は翌営業日のみ実行する。
    実行日が「15日または月末の翌営業日」であればTrue。
    """
    today = date.today()
    year, month = today.year, today.month

    # 月末日を計算
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    target_days = [
        _next_business_day(date(year, month, 15)),  # 15日サイト
        _next_business_day(last_day),  # 月末サイト
    ]
    return today in target_days


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    logging.warning("invalid date skipped: %s", text)
    return None


def as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def list_invoices(config: dict[str, str]) -> list[dict[str, Any]]:
    company_id = config.get("FREEE_COMPANY_ID", DEFAULT_COMPANY_ID).strip()
    invoices: list[dict[str, Any]] = []
    limit = 100
    offset = 0

    while True:
        params = {
            "company_id": company_id,
            "invoice_status": "approved",
            "limit": limit,
            "offset": offset,
        }
        response = requests.get(
            f"{FREEE_BASE}/invoices",
            headers=freee_headers(),
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        batch = response.json().get("invoices", [])
        if not isinstance(batch, list):
            raise RuntimeError("freee invoices response format is invalid")

        invoices.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    return invoices


def partner_name(invoice: dict[str, Any]) -> str:
    return str(
        invoice.get("partner_display_name")
        or invoice.get("partner_name")
        or invoice.get("partner", {}).get("name")
        or "(取引先名なし)"
    )


def amount_value(invoice: dict[str, Any]) -> int | None:
    return as_int(invoice.get("total_amount") or invoice.get("amount") or invoice.get("total"))


def due_date_value(invoice: dict[str, Any]) -> date | None:
    return parse_date(invoice.get("payment_due_date") or invoice.get("due_date"))


def collect_alerts(invoices: list[dict[str, Any]], today: date) -> list[PaymentAlert]:
    alerts: list[PaymentAlert] = []
    paid_count = 0
    not_due_count = 0

    for invoice in invoices:
        status = str(invoice.get("payment_status") or "").strip().lower()
        invoice_id = as_int(invoice.get("id"))
        due_date = due_date_value(invoice)

        if status in PAID_PAYMENT_STATUSES:
            paid_count += 1
            continue
        if not invoice_id or not due_date:
            logging.info("invoice skipped: missing id or payment_due_date partner=%s", partner_name(invoice))
            continue
        if status not in ALERT_PAYMENT_STATUSES:
            logging.info("invoice skipped: unsupported payment_status=%s id=%s", status or "(blank)", invoice_id)
            continue
        if due_date > today:
            not_due_count += 1
            continue

        alerts.append(
            PaymentAlert(
                invoice_id=invoice_id,
                partner_name=partner_name(invoice),
                amount=amount_value(invoice),
                payment_due_date=due_date,
                payment_status=status,
            )
        )

    logging.info(
        "classification: total=%s paid=%s not_due=%s alerts=%s", len(invoices), paid_count, not_due_count, len(alerts)
    )
    return alerts


def load_notified() -> dict[str, Any]:
    if not NOTIFIED_PATH.exists():
        return {}
    with NOTIFIED_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def save_notified(data: dict[str, Any]) -> None:
    NOTIFIED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NOTIFIED_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def format_amount(amount: int | None) -> str:
    return f"{amount:,}" if amount is not None else "-"


def build_alert_message(alerts: list[PaymentAlert]) -> str:
    lines = ["【未入金アラート】"]
    for alert in alerts:
        lines.extend(
            [
                f"▶ {alert.partner_name}",
                f"  請求額: {format_amount(alert.amount)}円",
                f"  支払期日: {alert.payment_due_date.isoformat()}（{alert.overdue_days}日超過）",
            ]
        )
    return "\n".join(lines)


def send_alert(config: dict[str, str], message: str) -> bool:
    token = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = config.get("MATSUNO_LINE_USER_ID", "")
    if not token or not user_id:
        logging.warning("LINE env is not set; notification skipped")
        return False
    return send_line_message(token, user_id, message, "松野")


def run(dry_run: bool) -> int:
    setup_logging()
    config = load_config()
    logging.info("payment_checker start: dry_run=%s", dry_run)

    invoices = list_invoices(config)
    alerts = collect_alerts(invoices, date.today())
    if not alerts:
        logging.info("payment alerts not found")
        return 0

    notified = load_notified()
    pending = [alert for alert in alerts if alert.notify_key not in notified]
    if not pending:
        logging.info("all payment alerts already notified")
        return 0

    message = build_alert_message(pending)
    logging.warning("payment alert pending: count=%s\n%s", len(pending), message)

    if dry_run:
        logging.info("DRY-RUN: LINE notification and notified flag update skipped")
        print(message)
        return 0

    if not send_alert(config, message):
        return 1

    now = datetime.now().isoformat(timespec="seconds")
    for alert in pending:
        notified[alert.notify_key] = {
            "invoice_id": alert.invoice_id,
            "partner_name": alert.partner_name,
            "payment_due_date": alert.payment_due_date.isoformat(),
            "payment_status": alert.payment_status,
            "notified_at": now,
        }
    save_notified(notified)
    logging.info("payment_checker done: notified=%s", len(pending))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="freee請求書の入金状況を確認します")
    parser.add_argument("--dry-run", action="store_true", help="LINE送信と通知済みフラグ更新をスキップします")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dry_run and not should_run_today():
        logging.info("today is not a target business day; skipped")
        return 0
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

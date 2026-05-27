# -*- coding: utf-8 -*-
"""
freee confirmed invoice PDF sender.

Usage:
  python freee/invoice_sender.py --dry-run
  python freee/invoice_sender.py --target-month 2026-05 --dry-run
"""
from __future__ import annotations

import argparse
import calendar
import logging
import os
import re
import smtplib
import ssl
import sys
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values


BASE_DIR = Path(__file__).resolve().parent
SES_WORK_DIR = BASE_DIR.parent
ENV_PATH = SES_WORK_DIR / "config" / ".env"
LOG_PATH = SES_WORK_DIR / "logs" / "invoice_send.log"
TEMP_DIR = BASE_DIR / "temp"
FREEE_AUTH_DIR = SES_WORK_DIR / "freee_auth"
FREEE_BASE = "https://api.freee.co.jp/api/1"
NOTION_VERSION = "2022-06-28"
SMTP_HOST = "mail65.onamae.ne.jp"
SMTP_PORT = 465
DEFAULT_COMPANY_ID = "11712776"
FROM_BY_ASSIGNEE = {
    "松野": "r-matsuno@terra-ltd.co.jp",
    "岡本": "r-okamoto@terra-ltd.co.jp",
    "共通": "sessales@terra-ltd.co.jp",
}

sys.path.insert(0, str(FREEE_AUTH_DIR))
from token_manager import get_headers  # noqa: E402


@dataclass
class Recipient:
    email: str
    assignee: str
    source: str


@dataclass
class Invoice:
    invoice_id: int
    partner_name: str
    issue_date: str
    amount: int | None
    pdf_path: Path | None = None
    recipient: Recipient | None = None


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


def notion_headers(config: dict[str, str]) -> dict[str, str]:
    token = config.get("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def month_range(target_month: date) -> tuple[str, str]:
    last_day = calendar.monthrange(target_month.year, target_month.month)[1]
    return (
        target_month.replace(day=1).strftime("%Y-%m-%d"),
        target_month.replace(day=last_day).strftime("%Y-%m-%d"),
    )


def parse_target_month(value: str | None) -> date:
    if not value:
        today = date.today()
        return today.replace(day=1)
    return datetime.strptime(value, "%Y-%m").date().replace(day=1)


def list_confirmed_invoices(config: dict[str, str], target_month: date) -> list[Invoice]:
    company_id = config.get("FREEE_COMPANY_ID", DEFAULT_COMPANY_ID).strip()
    start_date, end_date = month_range(target_month)
    params = {
        "company_id": company_id,
        "start_issue_date": start_date,
        "end_issue_date": end_date,
        "invoice_status": "approved",
    }
    response = requests.get(
        f"{FREEE_BASE}/invoices",
        headers=freee_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    invoices = []
    for item in response.json().get("invoices", []):
        status = str(item.get("invoice_status") or item.get("status") or "")
        if status and status not in ("confirmed", "approved"):
            continue
        invoices.append(
            Invoice(
                invoice_id=int(item["id"]),
                partner_name=str(item.get("partner_name") or item.get("partner", {}).get("name") or ""),
                issue_date=str(item.get("issue_date") or ""),
                amount=item.get("total_amount"),
            )
        )
    return invoices


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "invoice"


def download_invoice_pdf(config: dict[str, str], invoice: Invoice) -> Path:
    company_id = config.get("FREEE_COMPANY_ID", DEFAULT_COMPANY_ID).strip()
    params = {"company_id": company_id}
    url = f"{FREEE_BASE}/invoices/{invoice.invoice_id}/download"
    response = requests.get(url, headers=freee_headers(), params=params, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    content = response.content
    if "application/json" in content_type:
        data = response.json()
        download_url = data.get("download_url") or data.get("url")
        if not download_url:
            raise RuntimeError(f"PDF download URL not found: invoice_id={invoice.invoice_id}")
        pdf_response = requests.get(download_url, timeout=60)
        pdf_response.raise_for_status()
        content = pdf_response.content

    if not content.startswith(b"%PDF"):
        logging.warning("PDF signature not found: invoice_id=%s content_type=%s", invoice.invoice_id, content_type)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMP_DIR / f"{invoice.issue_date}_{safe_filename(invoice.partner_name)}_{invoice.invoice_id}.pdf"
    path.write_bytes(content)
    return path


def prop_text(prop: dict[str, Any]) -> str:
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join(part.get("plain_text", "") for part in prop.get("title", []))
    if prop_type == "rich_text":
        return "".join(part.get("plain_text", "") for part in prop.get("rich_text", []))
    if prop_type == "email":
        return prop.get("email") or ""
    if prop_type == "phone_number":
        return prop.get("phone_number") or ""
    if prop_type == "select":
        select = prop.get("select")
        return select.get("name", "") if select else ""
    return ""


def extract_email_from_props(props: dict[str, Any], preferred_names: list[str]) -> str:
    for name in preferred_names:
        value = prop_text(props.get(name, {})).strip()
        if "@" in value:
            return value

    joined = "\n".join(prop_text(value) for value in props.values())
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", joined)
    return match.group(0) if match else ""


def query_notion_database(
    config: dict[str, str],
    database_id: str,
    prop_name: str,
    keyword: str,
) -> list[dict[str, Any]]:
    if not config.get("NOTION_API_KEY") or not database_id or not keyword:
        return []

    payload = {"filter": {"property": prop_name, "rich_text": {"contains": keyword}}, "page_size": 5}
    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=notion_headers(config),
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        logging.warning("Notion query failed: db=%s prop=%s status=%s", database_id, prop_name, response.status_code)
        return []
    return response.json().get("results", [])


def select_assignee(props: dict[str, Any]) -> str:
    assignee = prop_text(props.get("担当者", {})).strip()
    return assignee if assignee in FROM_BY_ASSIGNEE else "共通"


def resolve_recipient(config: dict[str, str], partner_name: str) -> Recipient | None:
    engineer_db = config.get("NOTION_ENGINEER_DB_ID", "")
    project_db = config.get("NOTION_PROJECT_DB_ID", "")
    keywords = [partner_name, partner_name.replace("株式会社", "").replace("合同会社", "").strip()]

    for keyword in [k for k in keywords if k]:
        for page in query_notion_database(config, engineer_db, "所属会社", keyword):
            props = page.get("properties", {})
            email = extract_email_from_props(props, ["所属メール", "メール"])
            if email:
                return Recipient(email=email, assignee=select_assignee(props), source="engineer_db")

        for page in query_notion_database(config, project_db, "クライアント", keyword):
            props = page.get("properties", {})
            email = extract_email_from_props(props, ["メール", "所属メール", "案件詳細"])
            if email:
                return Recipient(email=email, assignee=select_assignee(props), source="project_db")

    return None


def sender_password(config: dict[str, str], sender: str) -> str:
    env_by_sender = {
        "r-matsuno@terra-ltd.co.jp": ["MATSUNO_MAIL_PASSWORD", "OUTREACH_MAIL_PASSWORD"],
        "r-okamoto@terra-ltd.co.jp": ["OKAMOTO_MAIL_PASSWORD"],
        "sessales@terra-ltd.co.jp": ["SESSALES_MAIL_PASSWORD", "SESSALES_PASSWORD"],
    }
    for key in env_by_sender.get(sender, []):
        if config.get(key):
            return config[key]
    raise RuntimeError(f"SMTP password not set for {sender}")


def build_message(config: dict[str, str], invoice: Invoice, target_month: date) -> EmailMessage:
    if not invoice.recipient or not invoice.pdf_path:
        raise RuntimeError("recipient and pdf_path are required")

    sender = FROM_BY_ASSIGNEE.get(invoice.recipient.assignee, FROM_BY_ASSIGNEE["共通"])
    subject = f"【請求書】{target_month.year}年{target_month.month}月分 {invoice.partner_name}"
    body = (
        f"{invoice.partner_name}\n\n"
        "いつもお世話になっております。\n"
        f"{target_month.year}年{target_month.month}月分の請求書をお送りいたします。\n"
        "添付PDFをご確認ください。\n\n"
        "何卒よろしくお願いいたします。\n"
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = invoice.recipient.email
    message.set_content(body, subtype="plain", charset="utf-8")
    message.add_attachment(
        invoice.pdf_path.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=invoice.pdf_path.name,
    )
    return message


def send_invoice_mail(config: dict[str, str], invoice: Invoice, target_month: date) -> None:
    message = build_message(config, invoice, target_month)
    sender = str(message["From"])
    password = sender_password(config, sender)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def notify_matsuno_line(config: dict[str, str], text: str, dry_run: bool) -> None:
    logging.warning(text)
    if dry_run:
        logging.info("DRY-RUN: LINE notification skipped")
        return

    token = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = config.get("MATSUNO_LINE_USER_ID", "")
    if not token or not user_id:
        logging.warning("LINE env is not set; notification skipped")
        return

    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]},
        timeout=30,
    )
    if response.status_code >= 400:
        logging.warning("LINE notification failed: status=%s body=%s", response.status_code, response.text[:200])


def cleanup_pdf(invoice: Invoice) -> None:
    if invoice.pdf_path and invoice.pdf_path.exists():
        invoice.pdf_path.unlink()


def run(target_month: date, dry_run: bool) -> int:
    setup_logging()
    config = load_config()
    logging.info("invoice_sender start: target_month=%s dry_run=%s", target_month.strftime("%Y-%m"), dry_run)

    invoices = list_confirmed_invoices(config, target_month)
    if not invoices:
        logging.info("confirmed invoices not found; skipped")
        return 0

    ok = 0
    skipped = 0
    for invoice in invoices:
        logging.info("invoice found: id=%s partner=%s amount=%s", invoice.invoice_id, invoice.partner_name, invoice.amount)
        try:
            invoice.pdf_path = download_invoice_pdf(config, invoice)
            logging.info("PDF downloaded: %s", invoice.pdf_path)
            invoice.recipient = resolve_recipient(config, invoice.partner_name)
            if not invoice.recipient:
                skipped += 1
                notify_matsuno_line(
                    config,
                    f"請求書送付先不明: {invoice.partner_name} invoice_id={invoice.invoice_id} 手動対応してください。",
                    dry_run=dry_run,
                )
                continue

            logging.info(
                "recipient resolved: partner=%s to=%s assignee=%s source=%s",
                invoice.partner_name,
                invoice.recipient.email,
                invoice.recipient.assignee,
                invoice.recipient.source,
            )
            if dry_run:
                logging.info("DRY-RUN: mail skipped: invoice_id=%s to=%s", invoice.invoice_id, invoice.recipient.email)
            else:
                send_invoice_mail(config, invoice, target_month)
                logging.info("mail sent: invoice_id=%s to=%s", invoice.invoice_id, invoice.recipient.email)
            ok += 1
        except Exception as exc:
            skipped += 1
            logging.exception("invoice processing failed: invoice_id=%s error=%s", invoice.invoice_id, exc)
        finally:
            if not dry_run:
                cleanup_pdf(invoice)

    logging.info("invoice_sender done: ok=%s skipped=%s", ok, skipped)
    return 0 if skipped == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="freee confirmed invoice PDF sender")
    parser.add_argument("--dry-run", action="store_true", help="PDF取得まで実施し、メール送信はスキップします")
    parser.add_argument("--target-month", help="対象月をYYYY-MMで指定します。省略時は当月です")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(parse_target_month(args.target_month), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

"""Cloud Scheduler 向け請求書エンドポイントのヘルパー。"""

from __future__ import annotations

import os
import sys
import threading
from datetime import date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

FREEE_URL = "https://secure.freee.co.jp/invoices"


def run_in_thread(fn, *args, **kwargs) -> None:
    threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()


def get_next_month() -> str:
    today = date.today()
    if today.month == 12:
        return f"{today.year + 1}-01"
    return f"{today.year}-{today.month + 1:02d}"


def get_current_month() -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}"


def invoice_prep_handler() -> tuple[str, int]:
    sheets_dir = os.path.join(ROOT_DIR, "sheets")
    if sheets_dir not in sys.path:
        sys.path.insert(0, sheets_dir)
    from master_column_manager import populate_active_status

    target_month = get_next_month()
    run_in_thread(populate_active_status, target_month, execute=True)
    return "OK", 200


def invoice_draft_handler() -> tuple[str, int]:
    from freee.invoice_workflow import run_monthly_workflow

    target_month = get_current_month()
    run_in_thread(run_monthly_workflow, target_month, execute=True)
    return "OK", 200


def invoice_reminder_handler() -> tuple[str, int]:
    from shibusawa.invoice_review import _notify_line, fetch_invoices, parse_target_month, subject_for_month

    target_month = get_current_month()
    try:
        drafts = fetch_invoices(target_month, draft_only=True)
    except Exception as exc:
        _notify_line(f"【請求書チェック日】ドラフト取得失敗: {exc}")
        return "OK", 200
    y, m = parse_target_month(target_month)
    subj = subject_for_month(y, m)
    if drafts:
        _notify_line(f"【請求書チェック日】未確認{len(drafts)}件あります（{subj}）\n{FREEE_URL}")
    else:
        _notify_line("【請求書】全件確定済みです✅")
    return "OK", 200

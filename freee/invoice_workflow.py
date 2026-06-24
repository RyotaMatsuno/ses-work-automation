#!/usr/bin/env python3
"""請求書月次ワークフロー: ドラフト生成 → 渋沢レビュー → LINE通知。"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _guard_execute(execute: bool) -> bool:
    if not execute:
        return False
    if os.environ.get("FREEE_WRITE_APPROVED", "").strip() != "1":
        print("[invoice_workflow] FREEE_WRITE_APPROVED=1 未設定: 実POSTブロック")
        return False
    return True


def create_invoice_drafts(target_month: str, *, execute: bool = False) -> None:
    from freee.freee_invoice_v2 import run

    y, m = map(int, target_month.split("-"))
    run(date(y, m, 1), dry_run=not execute)


def shibusawa_review(target_month: str, *, dry_run: bool = False):
    from shibusawa.invoice_review import run_review

    return run_review(target_month, dry_run=dry_run, notify=not dry_run)


def notify_line(text: str) -> None:
    from shibusawa.invoice_review import _notify_line

    _notify_line(text)


def run_monthly_workflow(target_month: str, *, execute: bool = False) -> dict:
    print(f"=== invoice_workflow / {'EXECUTE' if execute else 'DRY-RUN'} / {target_month} ===")
    if execute and not _guard_execute(True):
        raise RuntimeError("--execute には FREEE_WRITE_APPROVED=1（松野承認）が必要です")

    create_invoice_drafts(target_month, execute=execute)
    review = shibusawa_review(target_month, dry_run=not execute)
    return {"target_month": target_month, "execute": execute, "review_ok": review.ok}


def main() -> None:
    parser = argparse.ArgumentParser(description="請求書月次ワークフロー")
    parser.add_argument("target_month", help="対象月 YYYY-MM")
    parser.add_argument("--dry-run", action="store_true", help="ドラフト生成・レビューともdry-run")
    parser.add_argument("--execute", action="store_true", help="実ドラフト生成+レビュー通知")
    args = parser.parse_args()
    execute = args.execute and not args.dry_run
    run_monthly_workflow(args.target_month, execute=execute)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
mail_pipeline 日次メトリクスサマリー。
毎日 23:00 に Windowsタスクスケジューラから実行する。
LINE 月200通上限に配慮し、夜1回のみ push する。
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from dotenv import dotenv_values

BASE = Path(__file__).resolve().parent
METRICS_PATH = BASE / "metrics.jsonl"
ENV_PATH = BASE.parent / "config" / ".env"

_ENV = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
for k, v in _ENV.items():
    if k not in os.environ:
        os.environ[k] = v


def load_today_metrics() -> list[dict]:
    if not METRICS_PATH.exists():
        return []
    today = date.today().isoformat()
    result = []
    with open(METRICS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("ts_start", "")
                if ts[:10] == today:
                    result.append(entry)
            except json.JSONDecodeError:
                continue
    return result


def build_summary(entries: list[dict]) -> str:
    if not entries:
        return "[mail_pipeline 日次サマリー]\nデータなし（本日の実行記録が見つかりません）"

    total_new = sum(e.get("mails_new", 0) for e in entries)
    total_eng = sum(e.get("notion_engineer_created", 0) for e in entries)
    total_prj = sum(e.get("notion_project_created", 0) for e in entries)
    total_err = sum(e.get("notion_errors", 0) for e in entries)
    total_imap_err = sum(e.get("imap_errors", 0) for e in entries)
    total_cost = sum(e.get("cost_usd", 0.0) for e in entries)
    failures = [e for e in entries if e.get("exit_code", 0) != 0]
    runs = len(entries)
    today_str = date.today().strftime("%m/%d")

    status = "✅全正常" if not failures and total_err == 0 else f"❌失敗{len(failures)}回 Notionエラー{total_err}件"
    imap_note = f" IMAPエラー:{total_imap_err}" if total_imap_err > 0 else ""

    return (
        f"[mail_pipeline {today_str} 日次サマリー]\n"
        f"実行: {runs}回 / 新規メール: {total_new}通\n"
        f"Notion登録: engineer={total_eng} project={total_prj}\n"
        f"本日コスト: ${total_cost:.4f}{imap_note}\n"
        f"{status}"
    )


def push_summary() -> None:
    entries = load_today_metrics()
    summary = build_summary(entries)
    print(summary)

    matsuno_uid = os.environ.get("MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "line_webhook"))
        from line_bridge import push_or_log

        result = push_or_log(matsuno_uid, summary, task_id="daily_summary")
        print(f"LINE push: {result}")
    except Exception as e:
        print(f"LINE push失敗（ログのみ）: {e}")


if __name__ == "__main__":
    push_summary()

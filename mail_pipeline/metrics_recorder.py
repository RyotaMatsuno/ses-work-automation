# -*- coding: utf-8 -*-
"""mail_pipeline 実行メトリクスを metrics.jsonl に追記する."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
METRICS_PATH = BASE / "metrics.jsonl"
MAX_SIZE_MB = 50


class MetricsRecorder:
    def __init__(self):
        self.start = time.time()
        self.metrics = {
            "ts_start": datetime.now(timezone.utc).isoformat(),
            "accounts_fetched": 0,
            "mails_fetched": 0,
            "mails_new": 0,
            "mails_fresh": 0,
            "mails_reclass": 0,
            "mails_skipped_dup": 0,
            "reclass_attempted": 0,
            "reclass_promoted": 0,
            "db_backlog_remaining": 0,
            "batch_api_calls": 0,
            "batch_api_items_total": 0,
            "notion_engineer_created": 0,
            "notion_project_created": 0,
            "notion_errors": 0,
            "imap_errors": 0,
            "cost_usd": 0.0,
            "process_limit": 0,
            "fetch_limit": 0,
            "exit_code": 0,
            "error_message": "",
        }

    def inc(self, key: str, n: int = 1) -> None:
        self.metrics[key] = self.metrics.get(key, 0) + n

    def set(self, key: str, value) -> None:
        self.metrics[key] = value

    def finalize(self, exit_code: int = 0, error_message: str = "") -> dict:
        self.metrics["ts_end"] = datetime.now(timezone.utc).isoformat()
        self.metrics["elapsed_seconds"] = round(time.time() - self.start, 2)
        self.metrics["exit_code"] = exit_code
        self.metrics["error_message"] = error_message[:500] if error_message else ""
        self._rotate_if_needed()
        with open(METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.metrics, ensure_ascii=False) + "\n")
        return self.metrics

    def _rotate_if_needed(self) -> None:
        if not METRICS_PATH.exists():
            return
        if METRICS_PATH.stat().st_size > MAX_SIZE_MB * 1024 * 1024:
            archive = METRICS_PATH.with_suffix(f".jsonl.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
            METRICS_PATH.rename(archive)

    def build_line_summary(self) -> str:
        m = self.metrics
        ts = m.get("ts_start", "")[:16].replace("T", " ")
        hour_str = ts[11:13] if len(ts) > 13 else "??"
        status = "✅正常" if m["exit_code"] == 0 and m["notion_errors"] == 0 else "❌異常"
        err_note = f" / エラー{m['notion_errors']}件" if m["notion_errors"] > 0 else ""
        return (
            f"[mail_pipeline {hour_str}:00台]\n"
            f"取得:{m['mails_fetched']} 新規:{m['mails_new']} skip:{m['mails_skipped_dup']}\n"
            f"Notion登録: engineer={m['notion_engineer_created']} project={m['notion_project_created']}\n"
            f"所要:{m['elapsed_seconds']:.0f}秒 cost:${m['cost_usd']:.4f}\n"
            f"{status}{err_note}"
        )

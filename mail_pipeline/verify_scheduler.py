#!/usr/bin/env python3
"""mail_pipeline Task 5: Windowsタスクスケジューラ自動実行の確認スクリプト。"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SES_WORK = Path(__file__).resolve().parent.parent
PIPELINE_LOG = SES_WORK / "mail_pipeline" / "pipeline.log"
TASK_NAME = "SES_MailPipeline"
MAX_AGE_HOURS = 3


def _query_task() -> str:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"],
        capture_output=True,
        text=True,
        encoding="cp932",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"schtasks failed: {result.returncode}")
    return result.stdout


def _parse_field(text: str, *labels: str) -> str:
    for line in text.splitlines():
        for label in labels:
            if label in line:
                return line.split(":", 1)[-1].strip()
    return ""


def _pipeline_log_recent() -> bool:
    if not PIPELINE_LOG.exists():
        return False
    mtime = datetime.fromtimestamp(PIPELINE_LOG.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=MAX_AGE_HOURS)


def verify_scheduler(*, require_enabled: bool = True) -> dict[str, str | bool]:
    raw = _query_task()
    state = _parse_field(raw, "状態", "Status")
    next_run = _parse_field(raw, "次回の実行時刻", "Next Run Time")
    last_run = _parse_field(raw, "最終実行時刻", "Last Run Time")
    last_result = _parse_field(raw, "最終結果", "Last Result")
    task_to_run = _parse_field(raw, "実行するタスク", "Task To Run")

    enabled = "無効" not in state and "Disabled" not in state
    ok = True
    notes: list[str] = []

    if require_enabled and not enabled:
        ok = False
        notes.append("タスクが無効(Disabled)です。schtasks /Change /TN SES_MailPipeline /ENABLE")
    if "wd_mail_pipeline.bat" not in task_to_run:
        ok = False
        notes.append("実行コマンドが wd_mail_pipeline.bat ではありません")
    if not _pipeline_log_recent():
        ok = False
        notes.append(f"pipeline.log が {MAX_AGE_HOURS} 時間以内に更新されていません")

    return {
        "ok": ok,
        "task_name": TASK_NAME,
        "state": state,
        "next_run": next_run,
        "last_run": last_run,
        "last_result": last_result,
        "task_to_run": task_to_run,
        "pipeline_log_recent": _pipeline_log_recent(),
        "notes": "; ".join(notes),
    }


def main() -> int:
    try:
        report = verify_scheduler()
    except Exception as exc:
        print(f"VERIFY NG: {exc}")
        return 1

    print(f"タスク: {report['task_name']}")
    print(f"状態: {report['state']}")
    print(f"次回実行: {report['next_run']}")
    print(f"最終実行: {report['last_run']} (結果={report['last_result']})")
    print(f"コマンド: {report['task_to_run']}")
    print(f"pipeline.log 直近更新: {report['pipeline_log_recent']}")

    if report["ok"]:
        print("VERIFY OK")
        return 0
    print(f"VERIFY NG: {report['notes']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

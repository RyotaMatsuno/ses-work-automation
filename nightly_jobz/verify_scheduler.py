#!/usr/bin/env python3
"""nightly_jobz: Windowsタスクスケジューラ自動実行の確認。"""

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
LOG_DIR = SES_WORK / "nightly_jobz" / "logs"
TASK_NAME = "SES_NightlyJobz"
MAX_LOG_AGE_DAYS = 2


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


def _recent_log_exists() -> bool:
    if not LOG_DIR.exists():
        return False
    cutoff = datetime.now() - timedelta(days=MAX_LOG_AGE_DAYS)
    for path in LOG_DIR.glob("nightly_*.log"):
        if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
            return True
    for path in LOG_DIR.glob("briefing_*.json"):
        if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
            return True
    return False


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
        notes.append("タスクが無効です")
    if "wd_nightly_jobz.bat" not in task_to_run:
        ok = False
        notes.append("wd_nightly_jobz.bat が実行コマンドに含まれていません")
    if "23:55" not in next_run and "23:55" not in raw:
        # 初回登録直後は next_run が空のことがある
        if not next_run:
            notes.append("次回実行時刻未設定（登録直後は正常な場合あり）")
    if not _recent_log_exists():
        notes.append(f"直近{MAX_LOG_AGE_DAYS}日以内の nightly ログなし（DRY_RUN未実行の場合）")

    return {
        "ok": ok,
        "task_name": TASK_NAME,
        "state": state,
        "next_run": next_run,
        "last_run": last_run,
        "last_result": last_result,
        "task_to_run": task_to_run,
        "recent_log": _recent_log_exists(),
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
    print(f"直近ログ: {report['recent_log']}")
    if report["notes"]:
        print(f"備考: {report['notes']}")

    if report["ok"]:
        print("VERIFY OK")
        return 0
    print("VERIFY NG")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

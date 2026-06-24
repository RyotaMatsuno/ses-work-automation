#!/usr/bin/env python3
"""SES_NightlyJobz を Windows タスクスケジューラに登録する。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SES_WORK = Path(__file__).resolve().parent.parent
BAT_PATH = SES_WORK / "wd_nightly_jobz.bat"
TASK_NAME = "SES_NightlyJobz"
START_TIME = "23:55"


def register(*, force: bool = True) -> int:
    if not BAT_PATH.exists():
        print(f"NG: bat not found: {BAT_PATH}")
        return 1

    cmd = [
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        f'cmd /c "{BAT_PATH}"',
        "/SC",
        "DAILY",
        "/ST",
        START_TIME,
    ]
    if force:
        cmd.append("/F")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp932", errors="replace")
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip() or f"schtasks failed: {result.returncode}")
        return result.returncode

    print(f"OK: {TASK_NAME} registered at {START_TIME} daily -> {BAT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(register())

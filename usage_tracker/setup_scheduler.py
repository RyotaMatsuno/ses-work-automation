"""
setup_scheduler.py - Windowsタスクスケジューラに usage_tracker_daily を登録
"""

import subprocess
import sys
from pathlib import Path

BAT_PATH = Path(__file__).resolve().parent / "run_usage_tracker.bat"
TASK_NAME = "usage_tracker_daily"


def register() -> None:
    cmd = f'schtasks /create /tn "{TASK_NAME}" /tr "{BAT_PATH}" /sc DAILY /st 09:05 /f'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="cp932")
    if result.returncode == 0:
        print(f"[setup_scheduler] '{TASK_NAME}' registered at 09:05 daily.", flush=True)
    else:
        print(f"[setup_scheduler] ERROR: {result.stdout} {result.stderr}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    register()

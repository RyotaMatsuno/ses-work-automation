# -*- coding: utf-8 -*-
"""Register hourly Windows Task Scheduler job for line bridge worker health check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BAT_PATH = Path(__file__).resolve().parent / "run_check_worker_health.bat"
TASK_NAME = "line_bridge_worker_health"


def register() -> None:
    cmd = f'schtasks /create /tn "{TASK_NAME}" /tr "{BAT_PATH}" /sc HOURLY /mo 1 /f'
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="cp932",
    )
    if result.returncode == 0:
        print(
            f"[setup_scheduler] '{TASK_NAME}' registered (hourly).",
            flush=True,
        )
        return
    print(
        f"[setup_scheduler] ERROR: {result.stdout} {result.stderr}",
        flush=True,
    )
    sys.exit(1)


if __name__ == "__main__":
    register()

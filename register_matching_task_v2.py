# -*- coding: utf-8 -*-
import os
import subprocess


TASK_NAME = "jobz_matching_daily"
BAT_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_matching_and_notify.bat"
LOG_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\matching_daily.log"
START_TIME = "08:00"


def main():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    base_command = [
        "schtasks",
        "/create",
        "/tn",
        TASK_NAME,
        "/tr",
        f'"{BAT_PATH}"',
        "/sc",
        "DAILY",
        "/st",
        START_TIME,
        "/F",
    ]
    command = base_command + [
        "/RU",
        "",
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 and "Access is denied" in (result.stderr + result.stdout):
        result = subprocess.run(base_command, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    result.check_returncode()

    print(f"registered task: {TASK_NAME}")


if __name__ == "__main__":
    main()

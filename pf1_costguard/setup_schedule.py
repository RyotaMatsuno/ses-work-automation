# -*- coding: utf-8 -*-
"""SES_CostGuard の実行間隔を5分ごとに変更し、即時実行する。"""

import subprocess
from typing import List


def run_command(command: List[str], label: str) -> bool:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        print(f"[{label}] failed to start: {e}")
        return False

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    print(f"[{label}] returncode={result.returncode}")
    if stdout:
        print(f"[{label} stdout] {stdout}")
    if stderr:
        print(f"[{label} stderr] {stderr}")
    return result.returncode == 0


def main() -> None:
    changed = run_command(
        ["schtasks", "/Change", "/TN", "SES_CostGuard", "/RI", "5"],
        "change interval",
    )
    ran = run_command(
        ["schtasks", "/Run", "/TN", "SES_CostGuard"],
        "run now",
    )

    if changed and ran:
        print("OK: SES_CostGuard schedule changed to every 5 minutes and started.")
    else:
        print("NG: SES_CostGuard schedule update or run failed.")


if __name__ == "__main__":
    main()

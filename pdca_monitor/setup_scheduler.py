"""Register Windows Task Scheduler jobs for pdca_monitor."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
COLLECTOR_BAT = BASE_DIR / "run_collector.bat"
REPORTER_BAT = BASE_DIR / "run_reporter.bat"
PYTHON = Path(r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe")

COLLECTOR_TASK = "jobz_pdca_collector"
REPORTER_TASK = "jobz_pdca_reporter"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _delete_task(name: str) -> None:
    _run(["schtasks", "/delete", "/tn", name, "/f"])


def register_collector() -> None:
    if not COLLECTOR_BAT.exists():
        raise FileNotFoundError(COLLECTOR_BAT)
    _delete_task(COLLECTOR_TASK)
    # /sc minute では /d（曜日指定）が使えないため、平日判定は weekday_guard に委譲
    cmd = [
        "schtasks",
        "/create",
        "/tn",
        COLLECTOR_TASK,
        "/tr",
        str(COLLECTOR_BAT),
        "/sc",
        "minute",
        "/mo",
        "5",
        "/st",
        "08:00",
        "/et",
        "20:00",
        "/f",
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    print(f"登録完了: {COLLECTOR_TASK}")
    print(f"  実行: {COLLECTOR_BAT}")
    print("  スケジュール: 08:00-20:00 / 5分間隔（平日は weekday_guard + collector 時刻ガード）")


def register_reporter() -> None:
    if not REPORTER_BAT.exists():
        raise FileNotFoundError(REPORTER_BAT)
    _delete_task(REPORTER_TASK)
    cmd = [
        "schtasks",
        "/create",
        "/tn",
        REPORTER_TASK,
        "/tr",
        str(REPORTER_BAT),
        "/sc",
        "weekly",
        "/d",
        "FRI",
        "/st",
        "18:00",
        "/f",
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    print(f"登録完了: {REPORTER_TASK}")
    print(f"  実行: {REPORTER_BAT}")
    print("  スケジュール: 毎週金曜 18:00")


def query_task(name: str) -> None:
    result = _run(["schtasks", "/query", "/tn", name, "/fo", "LIST", "/v"])
    if result.returncode != 0:
        print(f"query failed: {name}\n{result.stderr}")
        return
    for line in result.stdout.splitlines():
        if any(
            key in line
            for key in ("タスク名", "次回の実行", "実行するタスク", "繰り返し", "Task Name", "Next Run", "Task To Run")
        ):
            print(line.strip())


def main() -> int:
    if not PYTHON.exists():
        print(f"ERROR: Python not found: {PYTHON}")
        return 1
    try:
        register_collector()
        register_reporter()
        print("\n--- 登録確認 ---")
        query_task(COLLECTOR_TASK)
        query_task(REPORTER_TASK)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

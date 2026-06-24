"""
setup_scheduler.py - jobz_importer を SES_MailPipeline の30分後に登録する。

SES_MailPipeline: 30分間隔（例 10:00, 10:30, ...）
jobz_importer:    30分間隔・30分オフセット（例 10:30, 11:00, ...）
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BAT_PATH = BASE_DIR / "run_importer.bat"
TASK_NAME = "jobz_importer"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    if not BAT_PATH.exists():
        print(f"ERROR: {BAT_PATH} が見つかりません")
        sys.exit(1)

    # 既存タスクを削除（存在しなくてもOK）
    _run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"])

    # mail_pipeline と同様に30分間隔、開始時刻を30分オフセット
    create_cmd = [
        "schtasks",
        "/create",
        "/tn",
        TASK_NAME,
        "/tr",
        str(BAT_PATH),
        "/sc",
        "minute",
        "/mo",
        "30",
        "/st",
        "00:30",
        "/f",
    ]
    result = _run(create_cmd)
    if result.returncode != 0:
        print("schtasks登録失敗:")
        print(result.stderr or result.stdout)
        sys.exit(1)

    print(f"タスク登録完了: {TASK_NAME}")
    print(f"  実行ファイル: {BAT_PATH}")
    print("  スケジュール: 30分間隔（SES_MailPipelineの30分後オフセット）")

    query = _run(["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST", "/v"])
    if query.stdout:
        for line in query.stdout.splitlines():
            if any(k in line for k in ("タスク名", "次回の実行時刻", "実行するタスク", "繰り返し")):
                print(line.strip())


if __name__ == "__main__":
    main()

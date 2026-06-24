import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 30秒待ってからrunnerログとbatログを確認
time.sleep(30)

print("=== runner実行確認（手動トリガー後） ===\n")

# batログ
bat_log = "task_auto_runner/logs/bat_run.log"
if os.path.exists(bat_log):
    with open(bat_log, encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(f"--- bat_run.log ({os.path.getsize(bat_log)} bytes) ---")
    print(content[-1500:] if content else "(空)")
else:
    print("bat_run.log なし")

# runnerログ
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
runner_log = f"task_auto_runner/logs/runner_{today}.log"
if os.path.exists(runner_log):
    with open(runner_log, encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(f"\n--- runner_{today}.log 末尾 ---")
    print(content[-2000:])
else:
    print(f"\nrunner_{today}.log なし")

# タスク状態
result = subprocess.run(
    ["schtasks", "/query", "/tn", "SES_TaskAutoRunner", "/fo", "LIST", "/v"],
    capture_output=True,
    encoding="cp932",
    errors="replace",
)
for line in result.stdout.split("\n"):
    if "前回" in line or "状態" in line:
        print(f"  {line.strip()}")

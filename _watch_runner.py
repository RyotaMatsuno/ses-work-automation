import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 3分待ってからrunner本番実行の途中経過を確認
time.sleep(180)

from datetime import datetime

today = datetime.now().strftime("%Y%m%d")

print(f"=== runner本番実行 経過確認 ({datetime.now().strftime('%H:%M:%S')}) ===\n")

runner_log = f"task_auto_runner/logs/runner_{today}.log"
with open(runner_log, encoding="utf-8", errors="replace") as f:
    content = f.read()
# 19:06以降のログ
idx = content.find("2026-06-12 19:06")
if idx == -1:
    idx = content.find("2026-06-12 19:0", content.find("19:03:57"))
print(content[idx : idx + 2500] if idx != -1 else "19:06以降のログまだなし")

# running_tasksの状態
print("\n=== running_tasks/ ===")
if os.path.exists("running_tasks"):
    for f2 in os.listdir("running_tasks"):
        p = os.path.join("running_tasks", f2)
        print(f"  {f2} ({os.path.getsize(p)}bytes)")
        with open(p, encoding="utf-8", errors="replace") as fh:
            print("    " + fh.read()[:300].replace("\n", "\n    "))

# runner_cost.jsonl
print("\n=== runner_cost.jsonl ===")
cost_file = "task_auto_runner/logs/runner_cost.jsonl"
if os.path.exists(cost_file):
    with open(cost_file, encoding="utf-8") as f:
        print(f.read())
else:
    print("  まだなし（実行中）")

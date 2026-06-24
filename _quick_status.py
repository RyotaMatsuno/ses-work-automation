import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
print(f"=== 経過確認 ({datetime.now().strftime('%H:%M:%S')}) ===\n")

runner_log = f"task_auto_runner/logs/runner_{today}.log"
with open(runner_log, encoding="utf-8", errors="replace") as f:
    content = f.read()
print("--- runner log 末尾1500字 ---")
print(content[-1500:])

print("\n--- running_tasks/ ---")
if os.path.exists("running_tasks"):
    files = os.listdir("running_tasks")
    for f2 in files:
        p = os.path.join("running_tasks", f2)
        with open(p, encoding="utf-8", errors="replace") as fh:
            c = fh.read()
        print(f"  {f2}: {c[:200]}")
    if not files:
        print("  (空)")

print("\n--- pending/done/blocked ---")
for d in ["pending_tasks", "done_tasks", "blocked_tasks"]:
    if os.path.exists(d):
        files = [f for f in os.listdir(d) if f.endswith(".md")]
        print(f"  {d}: {files}")

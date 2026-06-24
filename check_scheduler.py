import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
# タスクスケジューラの全タスク名をリストして関連タスクを確認
r = subprocess.run(["schtasks", "/query", "/FO", "LIST"], capture_output=True, encoding="utf-8", errors="replace")
lines = r.stdout.split("\n")
task_names = [
    l.replace("タスク名:", "").replace("Task Name:", "").strip() for l in lines if "タスク名:" in l or "Task Name:" in l
]
relevant = [
    t
    for t in task_names
    if any(k in t.lower() for k in ["mail", "pipeline", "matching", "ses", "terra", "jobz", "freee"])
]
print("関連タスク一覧:")
for t in relevant:
    print(f"  {t}")
if not relevant:
    print("  （該当なし）")
print(f"\n全タスク数: {len(task_names)}")

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.makedirs("auto_bug_watcher", exist_ok=True)
os.makedirs("auto_bug_watcher/collectors", exist_ok=True)
os.makedirs("auto_bug_watcher/actions", exist_ok=True)
os.makedirs("auto_bug_watcher/logs", exist_ok=True)
# __init__.py
for d in ["auto_bug_watcher", "auto_bug_watcher/collectors", "auto_bug_watcher/actions"]:
    open(f"{d}/__init__.py", "w").close()
print("dirs created")

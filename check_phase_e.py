import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\phase_e_status.txt"

results = {}

# TASKS.md
with open(base + r"\TASKS.md", encoding="utf-8") as f:
    tasks = f.read()

# Phase E部分だけ抽出
e_start = tasks.find("## Phase E")
e_section = tasks[e_start:] if e_start >= 0 else "Phase E not found"

# matching logの末尾
log_path = base + r"\logs\matching_v3_20260605.log"
if os.path.exists(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as f:
        log_content = f.read()
    log_tail = log_content[-2000:] if len(log_content) > 2000 else log_content
else:
    log_tail = "log not found"

combined = f"=== TASKS.md Phase E ===\n{e_section}\n\n=== matching log tail ===\n{log_tail}"
with open(out, "w", encoding="utf-8") as f:
    f.write(combined)
print(combined[:4000])

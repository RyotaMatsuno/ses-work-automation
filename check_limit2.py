import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_limit_fix.log"
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

print("Waiting 50s...")
time.sleep(50)

# ログ確認
size = os.path.getsize(log) if os.path.exists(log) else 0
print(f"Log: {size} bytes")

# line_query.pyの変更箇所を確認
with open(base + r"\line_query.py", encoding="utf-8", errors="replace") as f:
    content = f.read()
lines = content.split("\n")

# format_project_result の先頭30行を確認
start = next((i for i, l in enumerate(lines) if "def format_project_result" in l), 0)
snippet = "\n".join(lines[start : start + 45])
print(f"\n=== format_project_result snippet ===\n{snippet}")

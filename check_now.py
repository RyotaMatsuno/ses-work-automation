import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

for label, log in [
    ("daily_report", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_daily_report.log"),
    ("webhook", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_webhook_progress.log"),
]:
    size = os.path.getsize(log)
    print(f"{label}: {size}bytes")

daily = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\daily_report.py"
print(f"daily_report.py: {os.path.exists(daily)}")

wh = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh, encoding="utf-8") as f:
    content = f.read()
print(f"webhook '進捗': {'進捗' in content}")

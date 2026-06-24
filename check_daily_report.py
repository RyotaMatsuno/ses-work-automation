import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
time.sleep(180)

# ログ確認
for label, log in [
    ("daily_report", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_daily_report.log"),
    ("webhook", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_webhook_progress.log"),
]:
    size = os.path.getsize(log)
    print(f"{label}: {size}bytes")

# ファイル存在確認
daily = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\daily_report.py"
print(f"daily_report.py exists: {os.path.exists(daily)}")

# webhook進捗コマンド確認
wh = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh, encoding="utf-8") as f:
    content = f.read()
print(f"webhook has '進捗': {'進捗' in content}")

# daily_report dry-run
if os.path.exists(daily):
    r = subprocess.run(
        ["python", "daily_report.py", "--dry-run"],
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    print(f"\n--- dry-run ---\n{r.stdout[:800]}")
    if r.returncode != 0:
        print(f"ERR: {r.stderr[:300]}")

import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(120)
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\codex_v4.log",
    encoding="utf-8",
    errors="replace",
) as f:
    lines = f.readlines()
print(f"行数: {len(lines)}", flush=True)
for l in lines[-50:]:
    print(l, end="", flush=True)

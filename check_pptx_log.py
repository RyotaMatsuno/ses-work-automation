import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\codex_pptx_csv.log"
size = os.path.getsize(log_path)
print(f"log size: {size} bytes")
with open(log_path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"total lines: {len(lines)}")
print("--- last 50 lines ---")
for line in lines[-50:]:
    print(line, end="")

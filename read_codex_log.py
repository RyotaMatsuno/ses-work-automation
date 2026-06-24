import os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\codex_linequery_bugfix.log"
if os.path.exists(log_path):
    size = os.path.getsize(log_path)
    print(f"log size: {size} bytes")
    with open(log_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"lines: {len(lines)}")
    for l in lines[-50:]:
        print(l, end="")
else:
    print("log not found")

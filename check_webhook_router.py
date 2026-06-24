import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

with open(os.path.join(BASE, "line_webhook/webhook_server.py"), encoding="utf-8") as f:
    lines = f.readlines()

# メインのメッセージハンドラ部分を抽出
keywords = [
    "handle_message",
    "def process_",
    "text ==",
    "startswith",
    "endswith",
    "handle_reminder",
    "handle_intent",
    "handle_urge",
    "詳細",
    "detail",
]
found = []
for i, line in enumerate(lines):
    if any(kw in line for kw in keywords):
        start = max(0, i - 1)
        end = min(len(lines), i + 3)
        found.append(f"L{i + 1}: {''.join(lines[start:end]).rstrip()}")

print("\n".join(found[:40]), flush=True)

# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
lines = open(path, encoding="utf-8").readlines()

# notify_line / LINE送信 / LINE通知 部分
print("=== LINE送信・通知関連 ===")
for i, line in enumerate(lines):
    if any(k in line for k in ["notify", "push_message", "LINE", "line", "send"]):
        print(f"{i + 1}: {line}", end="")

print("\n=== attachments / 添付 関連 ===")
for i, line in enumerate(lines):
    if any(k in line for k in ["attachment", "attach", "添付", "docx", "pdf", "xlsx"]):
        print(f"{i + 1}: {line}", end="")

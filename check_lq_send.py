import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
wh_path = os.path.join(lw, "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    lines = f.readlines()

# L1650-1680: handle_line_query の呼び出しと送信処理
print("=== L1650-1685 ===")
for i in range(1649, 1685):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

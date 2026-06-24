import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
wh_path = os.path.join(lw, "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    lines = f.readlines()

# split_line_message の実装を確認
print("=== split_line_message ===")
in_func = False
for i, line in enumerate(lines, 1):
    if "def split_line_message" in line:
        in_func = True
    if in_func:
        print(f"L{i}: {line}", end="")
        if in_func and i > 3 and line.strip().startswith("def ") and "split_line_message" not in line:
            break

# line_query の結果を受け取ってLINEに送信している箇所を確認
print("\n=== handle_line_query 呼び出し箇所 ===")
for i, line in enumerate(lines, 1):
    if "handle_line_query" in line or ("line_query" in line and "result" in line.lower()):
        print(f"L{i}: {line.rstrip()[:150]}")

# split_line_message が line_query 結果に対して呼ばれているか確認
print("\n=== split_line_message 呼び出し箇所 ===")
for i, line in enumerate(lines, 1):
    if "split_line_message" in line:
        print(f"L{i}: {line.rstrip()[:150]}")

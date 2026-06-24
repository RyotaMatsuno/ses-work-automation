import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# webhook_server.pyの催促・進捗確認・マッチング関連部分を抽出
with open(os.path.join(BASE, "line_webhook/webhook_server.py"), encoding="utf-8") as f:
    lines = f.readlines()

# キーワードで関連行を抽出
keywords = ["催促", "意向確認状況", "進捗", "handle_command", "urge", "status_check", "matching", "マッチング"]
found_blocks = []
for i, line in enumerate(lines):
    if any(kw in line for kw in keywords):
        start = max(0, i - 2)
        end = min(len(lines), i + 8)
        block = "".join(lines[start:end])
        found_blocks.append(f"--- line {i + 1} ---\n{block}")

print("\n".join(found_blocks[:20]), flush=True)
print(f"\n総行数: {len(lines)}", flush=True)

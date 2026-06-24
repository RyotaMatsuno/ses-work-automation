import datetime
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
wh_path = os.path.join(lw, "webhook_server.py")

bak = wh_path + f".bak_{datetime.date.today().strftime('%m%d')}_split_lq"
shutil.copy(wh_path, bak)
print(f"Backup: {bak}")

with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# L1659: result が複数チャンクになる場合は push_message で分割送信
OLD = "    if result is not None: return reply_message(reply_token, result, sender_token)"

NEW = """    if result is not None:
        chunks = split_line_message(result)
        if len(chunks) == 1:
            reply_message(reply_token, chunks[0], sender_token)
        else:
            # 複数チャンク: 1通目はReply、2通目以降はPush
            reply_message(reply_token, chunks[0], sender_token)
            for chunk in chunks[1:]:
                push_message(user_id, chunk, sender_token)
        return"""

if OLD in content:
    content = content.replace(OLD, NEW)
    print("PATCHED: handle_line_query split送信")
else:
    print("NOT FOUND")

with open(wh_path, "w", encoding="utf-8") as f:
    f.write(content)
print("保存済み")

# 確認
with open(wh_path, encoding="utf-8") as f:
    lines = f.readlines()
print("\n=== L1657-1672 ===")
for i in range(1656, 1672):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

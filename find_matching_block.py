import sys

sys.stdout.reconfigure(encoding="utf-8")

wh_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# process_message内のマッチングコマンドブロックを探す
# 「マッチング」を含む短いテキストの条件分岐を探す
search = '"マッチング" in text_stripped'
idx = content.find(search)
print(f"マッチング条件: pos={idx}")
if idx >= 0:
    print(content[idx : idx + 300])

import sys

sys.stdout.reconfigure(encoding="utf-8")

wh_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# マッチングブロック全体を確認（returnまで）
idx = content.find('"マッチング" in text_stripped')
block_end = content.find("\n\n\n", idx)
print(content[idx : block_end + 10])

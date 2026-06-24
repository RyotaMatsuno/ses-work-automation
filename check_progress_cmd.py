import sys

sys.stdout.reconfigure(encoding="utf-8")

wh_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# 進捗コマンド分岐を確認
idx = content.find("進捗")
while idx >= 0:
    print(f"--- pos {idx} ---")
    print(content[max(0, idx - 50) : idx + 200])
    print()
    idx = content.find("進捗", idx + 1)

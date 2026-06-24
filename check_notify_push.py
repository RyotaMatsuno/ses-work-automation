import sys

sys.stdout.reconfigure(encoding="utf-8")

# notify_line.pyの送信ロジック確認（Push APIを使っている箇所）
notify_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
with open(notify_path, encoding="utf-8") as f:
    content = f.read()

# push送信箇所
idx = content.find("push")
print("push API使用箇所:")
print(content[idx : idx + 400])
print()
# LINE通知の全体フロー確認
idx2 = content.find("def send_line")
if idx2 < 0:
    idx2 = content.find("def notify")
print("送信関数:")
print(content[idx2 : idx2 + 400])

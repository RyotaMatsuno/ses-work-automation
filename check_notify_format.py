import sys
sys.stdout.reconfigure(encoding='utf-8')

# notify_line.pyの通知文フォーマット確認
notify_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
with open(notify_path, encoding="utf-8") as f:
    content = f.read()

# 通知文を組み立てている関数を探す
for keyword in ["def build", "def format", "def notify", "所属", "担当者"]:
    idx = content.find(keyword)
    if idx >= 0:
        print(f"--- '{keyword}' found at {idx} ---")
        print(content[idx:idx+300])
        print()

import sys

sys.stdout.reconfigure(encoding="utf-8")

wh_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# 既に進捗コマンドが入っているか確認
print(f"'進捗' in content: {'進捗' in content}")
print(f"'build_progress_reply' in content: {'build_progress_reply' in content}")

# マッチングコマンドの実際のコードを確認
idx = content.find("マッチング")
print(f"\nマッチング付近:\n{content[idx : idx + 400]}")

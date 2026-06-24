import sys

sys.stdout.reconfigure(encoding="utf-8")

notify_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
with open(notify_path, encoding="utf-8") as f:
    content = f.read()

# main()の後半 + build_line_accounts + build_project_messageの末尾
idx = content.find("notifications = build_notifications")
print("=== 通知送信部分 ===")
print(content[idx : idx + 1200])

print("\n=== build_line_accounts ===")
idx2 = content.find("def build_line_accounts")
print(content[idx2 : idx2 + 600])

print("\n=== build_project_message末尾 ===")
idx3 = content.find("def build_project_message")
print(content[idx3 : idx3 + 1000])

import sys

sys.stdout.reconfigure(encoding="utf-8")

notify_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
with open(notify_path, encoding="utf-8") as f:
    content = f.read()

idx = content.find("def build_project_message")
print(content[idx : idx + 1200])

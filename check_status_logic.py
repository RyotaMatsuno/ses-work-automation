import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py", encoding="utf-8") as f:
    content = f.read()

# process_message内のキーワード分岐を確認
lines = content.split("\n")
for i, l in enumerate(lines):
    if any(kw in l for kw in ["ステータス", "更新", "update", "意向確認", "面談"]):
        print(f"L{i + 1}: {l}")

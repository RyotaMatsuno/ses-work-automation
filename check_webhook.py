import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

checks = ["no name", "SKIP", "名前が取得", "関東", "中部", "OKAMOTO", "okamoto", "LINE_OKAMOTO"]
for k in checks:
    print(f"[{'OK' if k in content else 'NG'}] {k}")

print()
print("--- 末尾300文字 ---")
print(content[-300:])
print()
print(f"総行数: {len(content.splitlines())}行")

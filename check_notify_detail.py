import sys

sys.stdout.reconfigure(encoding="utf-8")

# notify_line.pyの全体像を確認
notify_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
with open(notify_path, encoding="utf-8") as f:
    content = f.read()

# 主要な関数・定数を抽出
import re

funcs = [(m.start(), m.group()) for m in re.finditer(r"^def \w+", content, re.MULTILINE)]
print("関数一覧:")
for pos, name in funcs:
    print(f"  {name}")

print()
# 4ケース判定ロジック
idx = content.find("4ケース")
if idx < 0:
    idx = content.find("ケース")
if idx >= 0:
    print("ケース判定:")
    print(content[idx : idx + 600])

# build_notificationsの中身
idx2 = content.find("def build_notifications")
print("\nbuild_notifications:")
print(content[idx2 : idx2 + 800])

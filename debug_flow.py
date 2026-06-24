import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
wh_path = os.path.join(ses, "line_webhook", "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    lines = f.readlines()

# L1440-1480: エンジニア登録後の逆マッチング処理フロー
print("=== L1440-1480: register flow after engineer ===")
for i in range(1439, 1480):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# L1550-1570: もう一つのregister_engineer呼び出し
print("\n=== L1550-1580 ===")
for i in range(1549, 1580):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# build_reverse_match_message_v2 に渡す matches の件数を確認
# [:3] で絞っているはずだが、21件になっているのはなぜか
print("\n=== all [:3] / [:5] slicing ===")
for i, line in enumerate(lines, 1):
    if "matches" in line and ("[" in line) and ("3" in line or "5" in line or "10" in line):
        print(f"L{i}: {line.rstrip()}")

# 逆マッチングに渡すactive_projectsの件数確認コード
print("\n=== active_projects query ===")
for i, line in enumerate(lines, 1):
    if "active_project" in line:
        print(f"L{i}: {line.rstrip()[:150]}")

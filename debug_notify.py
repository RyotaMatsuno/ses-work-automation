import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# notify_line.py の粗利計算・LINEメッセージ生成部分を詳しく見る
notify_path = os.path.join(ses, "matching_v2", "notify_line.py")
with open(notify_path, encoding="utf-8") as f:
    lines = f.readlines()

# L50-L150: メイン処理・粗利計算
print("=== notify_line.py L50-L160 ===")
for i in range(49, 160):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# L320-L420: メッセージフォーマット部分
print("\n=== notify_line.py L310-L430 ===")
for i in range(309, 430):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

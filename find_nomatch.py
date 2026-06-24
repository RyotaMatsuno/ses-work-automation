# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 「マッチ案件なし」というテキストがどこから来ているか探す
import subprocess

r = subprocess.run(
    ["rg", "-rn", "マッチ案件なし", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("=== 'マッチ案件なし' の出所 ===")
print(r.stdout or "見つかりません")

# 「有効案件なし」も
r2 = subprocess.run(
    ["rg", "-rn", "有効案件なし", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("=== '有効案件なし' の出所 ===")
print(r2.stdout or "見つかりません")

# -*- coding: utf-8 -*-
"""classify_system プロンプトと分類ルール部分を抽出"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pp = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(pp, "r", encoding="utf-8") as f:
    lines = f.readlines()

# L550-590: classify_system（LLM分類プロンプト）
print("=== 1. LLM分類プロンプト (classify_system) L550-590 ===")
for i in range(549, min(590, len(lines))):
    print(f"  {i + 1}: {lines[i].rstrip()}")

# ルール分類部分を探す（rule_classify / classify_by_rule）
print("\n\n=== 2. ルール分類ロジック ===")
for i, line in enumerate(lines):
    if "rule" in line.lower() and ("classify" in line.lower() or "分類" in line):
        start = max(0, i - 2)
        end = min(len(lines), i + 30)
        print(f"\n--- L{i + 1} ---")
        for j in range(start, end):
            print(f"  {j + 1}: {lines[j].rstrip()[:150]}")
        break

# project_system / engineer_system プロンプトも確認
print("\n\n=== 3. 構造化抽出プロンプト ===")
for i, line in enumerate(lines):
    if "project_system" in line and ("=" in line or '"""' in line):
        start = max(0, i)
        end = min(len(lines), i + 40)
        print(f"\n--- project_system L{i + 1} ---")
        for j in range(start, end):
            print(f"  {j + 1}: {lines[j].rstrip()[:150]}")
            if j > i and ('"""' in lines[j] and j != i):
                break
        break

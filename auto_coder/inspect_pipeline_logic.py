# -*- coding: utf-8 -*-
"""mail_pipeline.pyの判定ロジック部分を抽出"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pp = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(pp, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# キーワード検索(日本語含む)
keywords = [
    "判定",
    "分類",
    "案件",
    "人員",
    "除外",
    "スキップ",
    "prompt",
    "Batch",
    "batch",
    "custom_id",
    "メール種別",
    "type",
    "抽出",
    "構造化",
    "JSON",
]
for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    for kw in keywords:
        if kw in stripped and len(stripped) > 10:
            # プロンプト文字列（複数行）の場合は前後も出す
            if "prompt" in kw.lower() or "判定" in kw or "分類" in kw or "構造化" in kw:
                start = max(0, i - 1)
                end = min(len(lines), i + 5)
                print(f"\n=== L{i + 1} ({kw}) ===")
                for j in range(start, end):
                    print(f"  {j + 1}: {lines[j].rstrip()[:150]}")
                break
            # Batch API関連
            elif "batch" in kw.lower() or "custom_id" in kw:
                print(f"\n=== L{i + 1} ({kw}) ===")
                print(f"  {i + 1}: {stripped[:150]}")
                break

# 特にBatch APIのrequest生成部分を探す
print("\n\n=== Batch API request construction ===")
in_batch = False
for i, line in enumerate(lines):
    if "def " in line and ("batch" in line.lower() or "request" in line.lower()):
        in_batch = True
        print(f"\n--- Function at L{i + 1} ---")
    if in_batch:
        print(f"  {i + 1}: {line.rstrip()[:150]}")
        if line.strip().startswith("return ") or (line.strip() == "" and i > 0 and lines[i - 1].strip() == ""):
            in_batch = False

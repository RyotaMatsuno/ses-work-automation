# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 今日のmatching_v3ログ全文でPH・マッチ関連を確認
log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\matching_v3_20260615.log")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()

# 直近（08:00以降）のログを抽出
print("=== 08:00以降のログ ===")
recent = [l for l in lines if l[:16] >= "2026-06-15 08:00"]
for l in recent:
    print(l)

# 「マッチ」「LINE」「通知」「PH」関連
print("\n=== マッチ/通知/PH関連 全件 ===")
keywords = ["MATCH", "REVIEW", "マッチ", "通知", "LINE", "enqueue", "PH", "P.H", "notify", "push"]
for l in lines:
    if any(k in l for k in keywords):
        print(l)

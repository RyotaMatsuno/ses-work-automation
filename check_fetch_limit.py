# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mp = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py")
content = mp.read_text(encoding="utf-8", errors="replace")

# FETCH_LIMIT・取得件数設定を確認
for i, line in enumerate(content.splitlines(), 1):
    if any(k in line for k in ["FETCH_LIMIT", "fetch_limit", "200", "取得件数", "未読", "UNSEEN", "ALL", "最大"]):
        if any(k in line for k in ["FETCH", "fetch", "limit", "LIMIT", "件", "200", "未読", "UNSEEN"]):
            print(f"L{i}: {line.strip()[:120]}")

print("\n=== business_support判定ロジック ===")
for i, line in enumerate(content.splitlines(), 1):
    if "business_support" in line or "business support" in line.lower():
        print(f"L{i}: {line.strip()[:120]}")

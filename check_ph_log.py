# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 今日のmatching_v3ログを確認
log_dir = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs")
today = datetime.now().strftime("%Y%m%d")

# ログファイル一覧
logs = sorted(log_dir.glob("*.log"), reverse=True)
print(f"ログファイル: {[f.name for f in logs[:5]]}")

# 最新ログからPH関連を抽出
for log_file in logs[:3]:
    content = log_file.read_text(encoding="utf-8", errors="replace")
    ph_lines = [
        l
        for l in content.splitlines()
        if "PH" in l or "P.H" in l or "stale" in l.lower() or "鮮度" in l or "fresh" in l.lower()
    ]
    if ph_lines:
        print(f"\n=== {log_file.name} ===")
        for l in ph_lines[:20]:
            print(f"  {l}")

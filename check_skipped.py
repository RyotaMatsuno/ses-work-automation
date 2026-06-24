# -*- coding: utf-8 -*-
# まずスキップされているメールの実例を確認してSPECを設計する
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
today = "2026-06-15"

# スキップ（その他）の件名を全部出す
skipped = [l for l in lines if l.startswith(f"[{today}") and "スキップ（その他）" in l]
print(f"スキップ（その他）: {len(skipped)}件\n")
for l in skipped[:30]:
    # 件名部分を抽出
    idx = l.find("スキップ（その他）: ")
    if idx >= 0:
        print(f"  {l[idx + 12 :][:80]}")

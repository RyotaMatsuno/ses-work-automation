# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ws = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py")
lines = ws.read_text(encoding="utf-8", errors="replace").splitlines()

# マッチ関連メッセージを探す
for i, line in enumerate(lines, 1):
    if any(k in line for k in ["マッチ案件なし", "有効案件なし", "スキル・粗利", "案件なし", "マッチなし"]):
        print(f"L{i}: {line.strip()[:120]}")

# line_query.pyも
lq = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py")
lq_lines = lq.read_text(encoding="utf-8", errors="replace").splitlines()
print("\n--- line_query.py ---")
for i, line in enumerate(lq_lines, 1):
    if any(k in line for k in ["マッチ案件なし", "有効案件なし", "スキル・粗利", "案件なし", "マッチなし"]):
        print(f"L{i}: {line.strip()[:120]}")

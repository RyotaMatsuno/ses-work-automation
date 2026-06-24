# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ws = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py")
lines = ws.read_text(encoding="utf-8", errors="replace").splitlines()

# 「条件」「マッチ」含む行
for i, line in enumerate(lines, 1):
    if "条件" in line and ("マッチ" in line or "案件" in line):
        print(f"L{i}: {line.strip()[:150]}")

# 「PH」処理の周辺 - イニシャル+地名パターン
print("\n--- イニシャル処理 ---")
for i, line in enumerate(lines, 1):
    if "イニシャル" in line or ("初期" in line and "名前" in line) or "parse_name" in line or "parse_engineer" in line:
        print(f"L{i}: {line.strip()[:120]}")

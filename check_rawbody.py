# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
lines = open(path, encoding="utf-8").readlines()

# raw_body / original_text / 元データ保存 周辺を確認
for i, line in enumerate(lines):
    if any(k in line for k in ["raw_body", "original", "draft", "pipeline_draft", "DRAFT", "txt", "save"]):
        print(f"{i + 1}: {line}", end="")

# -*- coding: utf-8 -*-
# 実際のLINE出力をシミュレートして「途切れ」箇所を特定
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
if not result:
    print("result=None", flush=True)
    sys.exit()

# 各案件の「概要」行だけ抽出して末尾確認
lines = result.split("\n")
for i, line in enumerate(lines):
    if line.strip().startswith("概要:") or "概要:" in line:
        print(f"L{i}: {line[-80:]}", flush=True)

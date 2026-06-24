# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
if result:
    lines = result.split("\n")
    print(f"総行数: {len(lines)}", flush=True)
    print(f"総文字数: {len(result)}", flush=True)
    # 案件数カウント（①②③...の行）
    case_lines = [
        l
        for l in lines
        if l.strip() and (l.strip()[0] in "①②③④⑤⑥⑦⑧⑨⑩" or (len(l) > 1 and l.strip()[0].isdigit() and "." in l[:3]))
    ]
    print(f"案件行数（概算）: {len(case_lines)}", flush=True)
    print("--- 先頭10行 ---", flush=True)
    for l in lines[:10]:
        print(repr(l), flush=True)
    print("--- 末尾10行 ---", flush=True)
    for l in lines[-10:]:
        print(repr(l), flush=True)
else:
    print("結果なし（NoneまたはNo-match）", flush=True)

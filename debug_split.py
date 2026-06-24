# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
if not result:
    print("result=None", flush=True)
    sys.exit()


# split_line_messageをシミュレート
def split_line_message(text, limit=4900):
    chunks = []
    current = ""
    for line in text.splitlines():
        next_line = line if not current else current + "\n" + line
        if len(next_line) <= limit:
            current = next_line
            continue
        if current:
            chunks.append(current)
        current = line
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


chunks = split_line_message(result)
print(f"総文字数: {len(result)}", flush=True)
print(f"分割数: {len(chunks)}", flush=True)
for i, c in enumerate(chunks):
    lines = c.split("\n")
    # 案件番号行を抽出
    case_lines = [
        l
        for l in lines
        if l.strip() and l.strip()[0] in "①②③④⑤⑥⑦⑧⑨⑩" or (len(l) > 2 and l.strip()[:2].rstrip(".").isdigit())
    ]
    print(f"\n--- chunk {i + 1} ---", flush=True)
    print(f"  文字数: {len(c)}", flush=True)
    print(f"  行数: {len(lines)}", flush=True)
    print(f"  先頭3行: {lines[:3]}", flush=True)
    print(f"  末尾3行: {lines[-3:]}", flush=True)

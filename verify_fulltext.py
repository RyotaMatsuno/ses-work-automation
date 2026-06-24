# -*- coding: utf-8 -*-
import importlib
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
import line_query

importlib.reload(line_query)
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
if not result:
    print("result=None", flush=True)
    import sys

    sys.exit()

lines = result.split("\n")
print(f"総文字数: {len(result)}", flush=True)
print(f"総行数: {len(lines)}", flush=True)


# 分割チャンク数を計算
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
print(f"LINEチャンク数: {len(chunks)}", flush=True)
for i, c in enumerate(chunks):
    print(f"  chunk{i + 1}: {len(c)}文字", flush=True)

# 先頭案件①の概要が全文になっているか確認
idx1 = result.find("概要:")
if idx1 >= 0:
    # 次の案件番号まで
    idx2 = result.find("\n②", idx1)
    if idx2 < 0:
        idx2 = idx1 + 500
    print(f"\n①の概要プレビュー（先頭200文字）:\n{result[idx1 : idx1 + 200]}", flush=True)

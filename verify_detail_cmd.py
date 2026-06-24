# -*- coding: utf-8 -*-
import importlib
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

import line_query

importlib.reload(line_query)
from line_query import handle_line_query

# テスト1: 一覧照会
print("=== テスト1: HS 北小金 一覧 ===", flush=True)
result = handle_line_query("HS 北小金")
if result:
    lines = result.split("\n")
    print(f"総文字数: {len(result)}", flush=True)

    # チャンク数
    def split_msg(text, limit=4900):
        chunks, cur = [], ""
        for line in text.splitlines():
            nxt = line if not cur else cur + "\n" + line
            if len(nxt) <= limit:
                cur = nxt
            else:
                if cur:
                    chunks.append(cur)
                cur = line
        if cur:
            chunks.append(cur)
        return chunks or [text[:limit]]

    chunks = split_msg(result)
    print(f"チャンク数: {len(chunks)} 通", flush=True)

    # 先頭20行プレビュー
    print("\n--- 先頭20行 ---", flush=True)
    for l in lines[:20]:
        print(l, flush=True)
else:
    print("result=None", flush=True)

print("\n=== テスト2: 詳細 ① ===", flush=True)
result2 = handle_line_query("詳細 ①")
if result2:
    print(f"総文字数: {len(result2)}", flush=True)
    print(result2[:400], flush=True)
else:
    print("result=None", flush=True)

print("\n=== テスト3: 詳細 6 ===", flush=True)
result3 = handle_line_query("詳細 6")
if result3:
    print(f"総文字数: {len(result3)}", flush=True)
    print(result3[:300], flush=True)
else:
    print("result=None", flush=True)

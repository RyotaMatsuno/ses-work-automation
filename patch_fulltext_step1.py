# -*- coding: utf-8 -*-
# _clean_detail呼び出しを生テキスト直接参照に変更
# + 表示形式を「概要（連絡先）」と「案件内容（全文）」に分離

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 変更1: detail = _clean_detail(...) → raw_detail = _text_prop(...)
old1 = "        detail   = _clean_detail(_text_prop(pj, PROP_PJDETAIL))"
new1 = "        raw_detail = _text_prop(pj, PROP_PJDETAIL)"

if old1 not in content:
    print("ERROR: old1 not found", flush=True)
else:
    content = content.replace(old1, new1)
    print("変更1 OK", flush=True)

# 変更2: lines.extend の detail参照部分を確認して修正
# 現在: (f"  概要: {detail}" if detail else "")
old2 = '            (f"  \\u6982\\u8981: {detail}" if detail else ""),'
if old2 not in content:
    # 別パターンを探す
    idx = content.find("概要:")
    print(f"概要: の位置: {idx}", flush=True)
    print(repr(content[max(0, idx - 100) : idx + 100]), flush=True)
else:
    print("変更2パターン確認OK", flush=True)

# エンコードされた「概要」を探す
import re

m = re.search(r"u6982\\\\u8981[^\n]{0,200}", content)
if m:
    print(f"found: {m.group()}", flush=True)

# lines.extendブロック全体を確認
idx_extend = content.find('lines.extend([\n            "",\n            f"{_num_label(idx)} {pj_name}"')
if idx_extend < 0:
    idx_extend = content.find("lines.extend([")
    while idx_extend >= 0:
        snippet = content[idx_extend : idx_extend + 400]
        if "pj_name" in snippet or "req_sk" in snippet:
            print(f"\nlines.extend位置 {idx_extend}:", flush=True)
            print(snippet, flush=True)
            break
        idx_extend = content.find("lines.extend([", idx_extend + 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("\n変更1をファイルに書き込み完了", flush=True)

# -*- coding: utf-8 -*-
# format_project_result の detail表示部分を全文表示に変更
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 現在のdetail表示ブロック
old = """        if detail:
            lines.append(f"  \\u6982\\u8981: {detail}")  # \u6982\u8981:"""

new = """        if raw_detail:
            # \u6982\u8981\u5168\u6587\u8868\u793a\uff08\u6587\u5b57\u6570\u5236\u9650\u306a\u3057\uff09
            lines.append(f"  \u6982\u8981: {raw_detail}")"""

if old in content:
    content = content.replace(old, new)
    print("detail\u5168\u6587\u5316 OK", flush=True)
else:
    # \u5225\u30d1\u30bf\u30fc\u30f3\u3092\u63a2\u3059
    import re

    m = re.search(r"if detail:\s*\n\s*lines\.append.*?\u6982\u8981.*?\n", content)
    if m:
        print(f"found alt pattern: {repr(m.group())}", flush=True)
    else:
        # raw\u691c\u7d22
        idx = content.find("if detail:")
        while idx >= 0:
            snippet = content[idx : idx + 150]
            if "\u6982\u8981" in snippet or "detail" in snippet:
                print(f"pos {idx}: {repr(snippet)}", flush=True)
            idx = content.find("if detail:", idx + 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("\u66f8\u304d\u8fbc\u307f\u5b8c\u4e86", flush=True)

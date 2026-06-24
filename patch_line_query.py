# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = (
    "def handle_line_query(text: str) -> str | None:\n\n\n    if not text or not text.strip():\n\n\n        return None"
)

new = """def handle_line_query(text: str) -> str | None:
    # 50文字超はサマリー文章のためスルー（クエリ専用関数）
    if text and len(text.strip()) > 50:
        return None


    if not text or not text.strip():
        return None"""

if old in content:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCHED OK")
else:
    print("PATTERN NOT FOUND")
    # 実際の内容を確認
    idx = content.find("def handle_line_query")
    print(repr(content[idx : idx + 300]))

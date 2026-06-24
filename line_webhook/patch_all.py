import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 問題1: handle_line_queryに50文字ガードを追加
old = (
    "def handle_line_query(text: str) -> str | None:\n\n\n    if not text or not text.strip():\n\n\n        return None"
)
new = """def handle_line_query(text: str) -> str | None:
    # 50文字超はサマリー文章のためスルー（クエリ専用）
    if text and len(text.strip()) > 50:
        return None

    if not text or not text.strip():
        return None"""

if old in content:
    content = content.replace(old, new, 1)
    print("✅ 50文字ガード: PATCHED")
else:
    print("❌ 50文字ガード: PATTERN NOT FOUND")
    # 実際のパターンを確認
    idx = content.find("def handle_line_query")
    print(repr(content[idx : idx + 200]))

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

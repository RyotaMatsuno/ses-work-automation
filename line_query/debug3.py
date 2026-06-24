path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

# 文字化けしたキー → 正しいUTF-8キーに置換
replacements = [
    # _match_station内
    ('_text_prop(engineer, "\u6700\u5bc4\u308a\u99c5")', None),  # 最寄り駅（正常確認用）
]

# 文字化けしたバイト列を特定して置換
# cp932でエンコードされた文字化け文字列を探す
import re

# 現在のファイルの実際の文字列を確認
matches = list(re.finditer(r'_text_prop\(engineer,\s*"([^"]*)"', content))
for m in matches:
    key = m.group(1)
    print(f"key={repr(key)} at {m.start()}")

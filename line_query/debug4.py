path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

# まずcp932として読む
with open(path, encoding="cp932", errors="replace") as f:
    content_cp932 = f.read()

# cp932で読んだときに正しく表示されるか確認
import re

matches = list(re.finditer(r'_text_prop\([^,]+,\s*"([^"]*)"', content_cp932))
print("=== cp932で読んだ場合のキー ===")
for m in matches[:10]:
    print(f"  {repr(m.group(1))}")

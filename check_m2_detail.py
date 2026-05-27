
import re

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# extract_engineer()のreturn dict部分を探して確認
# まず関数の存在と構造を確認
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'extract_engineer' in line or 'raw_text' in line or 'drive_url' in line or 'build_skill' in line:
        print(f"{i+1}: {line}")

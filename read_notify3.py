
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\notify_out.txt", encoding="utf-8") as f:
    content = f.read()

# ASCII+日本語のみ残す（絵文字除去）
import re
# 絵文字・特殊記号をプレーンテキストに変換
content2 = content.encode("ascii", errors="replace").decode("ascii")
# 代わりにutf-8でファイルに書き出し
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\notify_ascii.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("Lines:", len(content.split('\n')))
print("Size:", len(content))
# 先頭500文字をASCII変換で表示
for line in content.split('\n')[:40]:
    safe = line.encode('cp932', errors='replace').decode('cp932', errors='replace')
    print(safe)

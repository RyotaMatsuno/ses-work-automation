import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

# 実際に存在するプロパティキー文字列を確認（正規表現で抽出してhexを再チェック）
import re

calls = re.findall(r'_(?:text|select|multi_select|number|date)_prop\([\w]+,\s*["\']([^"\']+)["\']', text)

sys.stdout.buffer.write(b"All keys with hex:\n")
for c in sorted(set(calls)):
    line = f"  {repr(c)}  ->  {c.encode('utf-8').hex()}\n"
    sys.stdout.buffer.write(line.encode("utf-8"))

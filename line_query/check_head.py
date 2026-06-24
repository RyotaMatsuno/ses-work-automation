import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8")

# ファイルの先頭1500文字を確認
print(text[:1500])

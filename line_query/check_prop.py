import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8")

# _prop と _text_prop の実装を確認
for func in ["def _prop(", "def _text_prop("]:
    idx = text.find(func)
    if idx >= 0:
        print(f"=== {func} ===")
        print(text[idx : idx + 400])
        print()

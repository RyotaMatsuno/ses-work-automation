import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8")

# engineer_query と format_engineer_result を確認
idx = text.find("def engineer_query")
print(text[idx : idx + 1000])

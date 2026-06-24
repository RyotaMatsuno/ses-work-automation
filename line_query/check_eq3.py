import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

idx = text.find("def engineer_query")
nxt = text.find("\ndef project_query")
print(text[idx:nxt])

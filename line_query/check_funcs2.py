import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

# calc_gross_profit, _gross_threshold, skill_match の実装を確認
for func in ["def calc_gross_profit", "def _gross_threshold", "def skill_match"]:
    idx = text.find(func)
    nxt = text.find("\ndef ", idx + 5)
    if nxt == -1:
        nxt = idx + 300
    print(text[idx:nxt])
    print()

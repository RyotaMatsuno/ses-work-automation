import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8")

# engineer_query の全体と format_ 関数を確認
idx_eq = text.find("def engineer_query")
idx_end = text.find("\ndef ", idx_eq + 10)
# 次の def を探す
idx_next = idx_eq + 10
for i in range(5):
    n = text.find("\ndef ", idx_next)
    if n == -1:
        break
    print(f"next def at {n}:", text[n : n + 50])
    idx_next = n + 5

print("\n--- full engineer_query ---")
# engineer_queryの全体
nxt = text.find("\ndef ", idx_eq + 10)
if nxt == -1:
    nxt = len(text)
print(text[idx_eq:nxt])

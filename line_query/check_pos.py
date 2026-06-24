import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

print("filesize:", len(raw))

text = raw.decode("utf-8", errors="replace")

for func in ["def _normalize_initial", "def _match_initial", "def _match_station", "def engineer_query"]:
    idx = text.find(func)
    print(f"{func}: pos={idx}")
    if idx >= 0:
        print("  snippet:", repr(text[idx : idx + 80]))

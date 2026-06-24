import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8", errors="replace")

start = text.find("def _normalize_initial")
end = text.find("def engineer_query")

print("=== CURRENT 3 FUNCTIONS ===")
print(repr(text[start:end]))

import os

fpath = os.path.join(os.path.dirname(__file__), "webhook_server.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# line_query の参照を探す
for keyword in ["line_query", "from line_query", "import line_query", "handle_line_query", "engineer_query"]:
    idx = text.find(keyword)
    if idx >= 0:
        print(f"{keyword}: pos={idx}")
        print("  context:", repr(text[max(0, idx - 30) : idx + 80]))
    else:
        print(f"{keyword}: NOT FOUND")

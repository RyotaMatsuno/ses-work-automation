import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8")

# format_project_result と format_engineer_result を表示
for func in ["def format_project_result", "def format_engineer_result"]:
    idx = text.find(func)
    nxt = text.find("\ndef ", idx + 10)
    if nxt == -1:
        nxt = idx + 1500
    print(f"=== {func} ===")
    print(text[idx:nxt])
    print()

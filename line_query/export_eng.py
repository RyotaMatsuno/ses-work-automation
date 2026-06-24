path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\engquery_func.txt"

with open(path, encoding="utf-8", errors="replace") as f:
    content = f.read()

s = content.find("def engineer_query")
e = content.find("\ndef ", s + 1)
with open(out, "w", encoding="utf-8") as f:
    f.write(content[s:e])
print("done")

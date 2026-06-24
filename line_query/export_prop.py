path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\prop_check.txt"

with open(path, encoding="utf-8", errors="replace") as f:
    content = f.read()

with open(out, "w", encoding="utf-8") as f:
    s = content.find("def _prop(")
    e = content.find("\ndef ", s + 1)
    f.write("=== _prop ===\n")
    f.write(content[s:e])
    f.write("\n\n")

    # engineer_queryのmatchedフィルタ部分
    s2 = content.find("def engineer_query")
    e2 = content.find("\ndef ", s2 + 1)
    f.write("=== engineer_query ===\n")
    f.write(content[s2:e2])

print("done")

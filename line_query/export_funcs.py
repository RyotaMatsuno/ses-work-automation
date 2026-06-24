path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8", errors="replace") as f:
    content = f.read()

# ファイルに書き出して確認
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\funcs_check.txt"
with open(out, "w", encoding="utf-8") as f:
    # _text_prop
    s = content.find("def _text_prop")
    e = content.find("\ndef ", s + 1)
    f.write("=== _text_prop ===\n")
    f.write(content[s:e])
    f.write("\n\n")
    # _match_initial
    s2 = content.find("def _match_initial")
    e2 = content.find("\ndef ", s2 + 1)
    f.write("=== _match_initial ===\n")
    f.write(content[s2:e2])
    f.write("\n\n")
    # _match_station
    s3 = content.find("def _match_station")
    e3 = content.find("\ndef ", s3 + 1)
    f.write("=== _match_station ===\n")
    f.write(content[s3:e3])

print("Written to funcs_check.txt")

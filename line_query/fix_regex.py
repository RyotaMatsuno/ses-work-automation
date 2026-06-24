path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

old = r'r"^([A-Za-z]{1,4})[\s/](.+)$"'
new = r'r"^([A-Za-z]{1,4})[\s\u3000/](.+)$"'

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: replaced")
else:
    print("NOT FOUND - showing surrounding lines:")
    for i, line in enumerate(content.splitlines()):
        if "re.match" in line or r"[\s" in line:
            print(f"  {i + 1}: {repr(line)}")

p = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\mail_fetcher.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

old = '                    cd = part.get("Content-Disposition", "")\n                    if "attachment" not in cd:'
new = '                    cd = str(part.get("Content-Disposition", "") or "")\n                    if "attachment" not in cd:'

if old in c:
    c = c.replace(old, new)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)
    print("mail_fetcher.py fixed OK")
else:
    print("Pattern not found - checking content...")
    idx = c.find("Content-Disposition")
    print(repr(c[idx - 30 : idx + 80]))

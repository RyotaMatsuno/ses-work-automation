
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\collect_help.txt", encoding="utf-8") as f:
    content = f.read()
safe = content.encode("cp932", errors="replace").decode("cp932")
print(safe)

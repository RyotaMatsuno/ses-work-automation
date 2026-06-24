path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\matching_content.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write(content)
print(f"written {len(content)} chars", flush=True)

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\gpt_review_request.md"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\gpt_review_out.txt"
try:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: {len(content)} chars")
except Exception as e:
    print(f"ERROR: {e}")

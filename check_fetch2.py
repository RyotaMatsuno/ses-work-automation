SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(SRC, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# fetch_all_pages の実装を確認
idx = text.find("def fetch_all_pages(")
nxt = text.find("\ndef ", idx + 5)
print(text[idx:nxt])

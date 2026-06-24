import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# handle_line_query の全体を表示
idx = text.find("def handle_line_query")
nxt = text.find("\ndef ", idx + 5)
if nxt == -1:
    nxt = idx + 2000
sys.stdout.buffer.write(text[idx:nxt].encode("utf-8", errors="replace"))

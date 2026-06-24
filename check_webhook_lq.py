import sys

# line_webhook にコピーされているファイルのengineer_queryを確認
fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

idx = text.find("def engineer_query")
nxt = text.find("\ndef project_query")
sys.stdout.buffer.write(text[idx:nxt].encode("utf-8"))

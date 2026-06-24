import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()

# "募集中" の実際のbytesを探す
# != "募集中" の前後を探す
idx = raw.find(b"!= ")
while idx != -1:
    chunk = raw[idx : idx + 30]
    sys.stdout.buffer.write(b"!= at " + str(idx).encode() + b": " + chunk.hex().encode()[:60] + b"\n")
    idx = raw.find(b"!= ", idx + 1)
    if idx > 20000:
        break

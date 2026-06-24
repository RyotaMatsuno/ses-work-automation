import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()

# fetch_all_pages の実際の定義行を探す
idx = raw.find(b"def fetch_all_pages(")
if idx >= 0:
    sys.stdout.buffer.write(b"found at " + str(idx).encode() + b"\n")
    sys.stdout.buffer.write(raw[idx : idx + 200] + b"\n")
else:
    sys.stdout.buffer.write(b"NOT FOUND\n")
    # 別のパターンを探す
    idx2 = raw.find(b"fetch_all_pages")
    while idx2 != -1 and idx2 < len(raw):
        sys.stdout.buffer.write(b"ref at " + str(idx2).encode() + b": " + raw[idx2 : idx2 + 60] + b"\n")
        idx2 = raw.find(b"fetch_all_pages", idx2 + 1)
        if idx2 > 20000:
            break

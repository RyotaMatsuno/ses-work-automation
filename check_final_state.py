import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()

# PROP_STATUS と VAL_RECRUITING の定義行を抽出
for line in raw.split(b"\n"):
    if b"PROP_STATUS" in line or b"VAL_RECRUITING" in line:
        sys.stdout.buffer.write(b"DEF: " + line[:80] + b"\n")

# engineer_query 内の != 比較行を抽出
text = raw.decode("utf-8", errors="replace")
for line in text.split("\n"):
    if "!=" in line and ("STATUS" in line or "status" in line or "RECRUIT" in line):
        sys.stdout.buffer.write(("COMPARE: " + line.strip() + "\n").encode("utf-8", errors="replace"))

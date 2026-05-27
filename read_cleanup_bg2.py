log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2_bg.log"
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_bg_read.txt"

with open(log_path, "rb") as f:
    raw = f.read()

# UTF-8デコード試み
try:
    text = raw.decode("utf-8")
except:
    text = raw.decode("cp932", errors="replace")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

# ファイルに書いてからprintはasciiのみ
print(f"length={len(text)}")
print(repr(text[:200]))

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2_bg.log"
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_bg_read_utf8.txt"

with open(log_path, "rb") as f:
    raw = f.read()

text = raw.decode("cp932", errors="replace")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"length={len(text)}")
print(f"saved to {out_path}")

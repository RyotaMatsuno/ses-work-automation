import time

time.sleep(5)

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2_bg.log"
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_bg_read.txt"

try:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content[:5000])
    print(f"Log length: {len(content)} chars")
    print("Last 500 chars:")
    print(content[-500:])
except Exception as e:
    print(f"Error: {e}")

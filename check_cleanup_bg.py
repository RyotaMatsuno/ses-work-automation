import time
import subprocess

time.sleep(20)

# ログ読み取り
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2_bg.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(content[:3000] if content else "(empty)")
except Exception as e:
    print(f"Error: {e}")

# プロセス確認
result = subprocess.run(
    ["tasklist", "/fi", "pid eq 26472", "/fo", "list"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("\nProcess check:")
print(result.stdout[:300])

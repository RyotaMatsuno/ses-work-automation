import subprocess
import sys

result = subprocess.run(
    [sys.executable, "matching_v2/notify_line.py", "--dry-run"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=60,
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")

# ファイルに書いて確認
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\notify_out.txt", "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(out)
    f.write("\n=== STDERR ===\n")
    f.write(err)
    f.write(f"\nRC: {result.returncode}\n")

print("done", result.returncode)

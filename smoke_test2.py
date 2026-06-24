import subprocess
import sys

result = subprocess.run(
    [sys.executable, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline\pipeline.py", "--dry-run"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=60,
)
print("RETURNCODE:", result.returncode, flush=True)

out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\smoke_out.txt"
with open(out_path, "wb") as f:
    f.write(result.stdout)
    f.write(b"\n=== STDERR ===\n")
    f.write(result.stderr)
print("出力保存:", out_path, flush=True)

# drafts確認
import os

drafts = os.listdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline\drafts")
print(f"drafts件数: {len(drafts)}", flush=True)
print("サンプル:", drafts[:3], flush=True)

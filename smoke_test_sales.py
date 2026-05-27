import subprocess, sys

result = subprocess.run(
    [sys.executable, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline\pipeline.py", "--dry-run"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    encoding='utf-8',
    errors='replace',
    timeout=60
)
print("RETURNCODE:", result.returncode, flush=True)
print("=== STDOUT ===", flush=True)
print(result.stdout[:3000], flush=True)
if result.stderr:
    print("=== STDERR ===", flush=True)
    print(result.stderr[:1000], flush=True)

import os, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8')

for label, logfile in [
    ("webhook", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_affiliation.log"),
    ("composer", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_composer.log"),
]:
    size = os.path.getsize(logfile)
    print(f"{label}: {size}bytes")

# pipeline動作確認
r = subprocess.run(
    ["python", "pipeline.py", "--dry-run"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1",
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
)
print(f"pipeline: {r.stdout.strip()}")
if r.returncode != 0:
    print(f"ERR: {r.stderr[-400:]}")

# fetcher.pyにaffiliationあるか確認
r2 = subprocess.run(
    ["python", "-c", "from fetcher import normalize_engineer; import inspect; src=inspect.getsource(normalize_engineer); print('affiliation' in src)"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1",
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
)
print(f"fetcher has affiliation: {r2.stdout.strip()}")

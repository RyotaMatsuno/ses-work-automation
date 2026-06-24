import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

print("Deploying to Cloud Run...")
r = subprocess.run(
    "gcloud run deploy line-webhook --source line_webhook --region asia-northeast1 --max-instances=1 --timeout=60 --allow-unauthenticated 2>&1",
    shell=True,
    capture_output=True,
    cwd=cwd,
    timeout=300,
)
out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
print(out[-2000:])

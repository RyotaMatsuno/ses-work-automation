import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

line_webhook_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pf5_cloudrun\deploy.log"

cmd = [
    "gcloud",
    "run",
    "deploy",
    "line-webhook",
    "--source",
    ".",
    "--region",
    "asia-northeast1",
    "--max-instances=1",
    "--timeout=60",
    "--allow-unauthenticated",
]

print(f"デプロイ開始: {' '.join(cmd)}", flush=True)
with open(log_path, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, cwd=line_webhook_dir, creationflags=subprocess.CREATE_NO_WINDOW)

print(f"deploy PID={proc.pid}")
print(f"log: {log_path}")

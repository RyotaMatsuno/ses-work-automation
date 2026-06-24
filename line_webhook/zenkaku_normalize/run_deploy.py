import subprocess

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

cmd = [
    GCLOUD,
    "run",
    "deploy",
    "line-webhook",
    "--source",
    "line_webhook",
    "--region",
    "asia-northeast1",
    "--platform",
    "managed",
    "--project",
    "ses-work-automation",
    "--quiet",
]

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\zenkaku_normalize\deploy.log"
with open(log_path, "w", encoding="utf-8") as logf:
    proc = subprocess.Popen(
        cmd,
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
        stdout=logf,
        stderr=logf,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

print(f"Deploy PID: {proc.pid}")
print(f"Log: {log_path}")

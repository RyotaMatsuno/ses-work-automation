# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

r = subprocess.run(
    [
        GCLOUD,
        "run",
        "deploy",
        "line-webhook",
        "--source",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
        "--region",
        "asia-northeast1",
        "--update-env-vars",
        "DEPLOY_TS=20260615",
        "--quiet",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=300,
)
print(r.stdout[-2000:])
if r.stderr:
    print("STDERR:", r.stderr[-500:])
print("exit:", r.returncode)

# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

r = subprocess.run(
    [
        "gcloud",
        "run",
        "deploy",
        "line-webhook",
        "--source",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
        "--region",
        "asia-northeast1",
        "--update-env-vars",
        "DEPLOY_TS=20260615",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=300,
)
print(r.stdout[-1500:])
if r.stderr:
    print("STDERR:", r.stderr[-800:])
print("exit:", r.returncode)

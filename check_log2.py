# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

r = subprocess.run(
    [
        GCLOUD,
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit",
        "30",
        "--format",
        "value(textPayload)",
        "--project",
        "ses-work-automation",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print(r.stdout[:3000] or "(なし)")
if r.stderr:
    print("STDERR:", r.stderr[:200])

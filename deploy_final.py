import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
LW = os.path.join(BASE, "line_webhook")

# line_query.pyをCloud Run側に同期（既にLW内なのでそのまま）
print("line_webhook/line_query.py を確認...", flush=True)
sz = os.path.getsize(os.path.join(LW, "line_query.py"))
print(f"line_query.py: {sz} bytes ✅", flush=True)

print("\nCloud Runデプロイ開始...", flush=True)
proc = subprocess.Popen(
    [
        GCLOUD,
        "run",
        "deploy",
        "line-webhook",
        "--source",
        LW,
        "--region",
        "asia-northeast1",
        "--project",
        "ses-work-automation",
        "--quiet",
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=LW,
    shell=True,
)

import threading

lines_out = []


def read():
    for l in proc.stdout:
        l = l.rstrip()
        lines_out.append(l)
        print(l, flush=True)


t = threading.Thread(target=read)
t.start()
proc.wait(timeout=250)
t.join(timeout=5)
print(f"\nreturncode: {proc.returncode}", flush=True)

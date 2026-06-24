import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
IMAGE = "asia-northeast1-docker.pkg.dev/ses-work-automation/cloud-run-source-deploy/line-webhook"
CWD = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

print("Cloud Runデプロイ開始...", flush=True)
proc = subprocess.Popen(
    [
        GCLOUD,
        "run",
        "deploy",
        "line-webhook",
        "--source",
        CWD,
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
    cwd=CWD,
    shell=True,
)

import threading

output_lines = []


def read_output():
    for line in proc.stdout:
        line = line.rstrip()
        output_lines.append(line)
        print(line, flush=True)


t = threading.Thread(target=read_output)
t.start()

# 最大240秒待機
proc.wait(timeout=240)
t.join(timeout=5)
print(f"デプロイ終了 returncode: {proc.returncode}", flush=True)

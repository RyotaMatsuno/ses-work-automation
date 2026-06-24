# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Cloud Runの最新ログから「マッチ案件なし」「PH」「京成小岩」を確認
r = subprocess.run(
    [
        GCLOUD,
        "logging",
        "read",
        'resource.type="cloud_run_revision" AND resource.labels.service_name="line-webhook" AND textPayload=~"マッチ案件なし|PH|京成小岩|スキル"',
        "--limit",
        "20",
        "--format",
        "value(textPayload,timestamp)",
        "--project",
        "ses-work-automation",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print("=== Cloud Runログ（マッチ関連）===")
print(r.stdout[:3000] or "(出力なし)")
if r.stderr:
    print("ERR:", r.stderr[:300])

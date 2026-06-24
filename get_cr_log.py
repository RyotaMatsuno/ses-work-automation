import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cr_log.txt"

# 直近30分のCloud Runログを取得
from datetime import datetime, timedelta, timezone

since = (datetime.now(timezone.utc) - timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")

cmd = f'gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook AND timestamp>=\\"{since}\\"" --limit=100 --format=json'
r = subprocess.run(cmd, shell=True, capture_output=True, cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
raw = r.stdout.decode("utf-8", errors="replace")

import json

try:
    entries = json.loads(raw)
    lines = []
    for e in entries:
        ts = e.get("timestamp", "")[:19]
        payload = e.get("textPayload") or str(e.get("jsonPayload", ""))
        lines.append(f"{ts} {payload[:200]}")
    result = "\n".join(lines) if lines else "NO LOGS"
except:
    result = raw[:3000]

with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(result[-3000:] if len(result) > 3000 else result)

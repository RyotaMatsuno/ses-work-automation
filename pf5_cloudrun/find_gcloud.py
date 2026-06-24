import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# gcloudのフルパスを探す
r = subprocess.run(["where", "gcloud"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(f"where gcloud: {r.stdout.strip()}")
r2 = subprocess.run(["where", "gcloud.cmd"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(f"where gcloud.cmd: {r2.stdout.strip()}")

import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Cloud Runの環境変数にパスワードが入ったか確認
import subprocess

gcloud = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
r = subprocess.run(
    [gcloud, "run", "services", "describe", "line-webhook", "--region", "asia-northeast1", "--format", "json"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
svc = json.loads(r.stdout)
env_vars = svc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [{}])[0].get("env", [])

print("=== Cloud Run 環境変数（パスワード系はマスク） ===")
smtp_keys = ["MATSUNO_MAIL_PASSWORD", "OKAMOTO_MAIL_PASSWORD", "SESSALES_MAIL_PASSWORD"]
for ev in env_vars:
    name = ev.get("name", "")
    val = ev.get("value", "")
    if name in smtp_keys:
        masked = "SET(OK)" if val else "EMPTY(NG)"
        print(f"  {name}: {masked}")

# revision確認
print("\n=== 最新revision ===")
revisions = svc.get("status", {}).get("traffic", [])
for t in revisions:
    print(f"  {t.get('revisionName')} - {t.get('percent')}%")

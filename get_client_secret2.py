import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
CLIENT_ID = "74735301292-op9eiut55pjdkhb44p25c6hlokcf01ql.apps.googleusercontent.com"
PROJECT = "ses-work-automation"

# まずgcloudの認証状態を確認
r = subprocess.run(
    [GCLOUD, "auth", "list", "--format", "json"], capture_output=True, text=True, encoding="utf-8", shell=True
)
print("auth list:", r.stdout[:500], flush=True)

# OAuth2クライアント情報取得（REST API経由）
r2 = subprocess.run(
    [GCLOUD, "alpha", "iap", "oauth-clients", "describe", CLIENT_ID, f"--project={PROJECT}", "--format=json"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    shell=True,
)
print("describe stdout:", r2.stdout[:1000], flush=True)
print("describe stderr:", r2.stderr[:500], flush=True)

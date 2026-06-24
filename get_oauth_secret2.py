import subprocess

import requests

# gcloud user accountのaccess tokenを取得
result = subprocess.run(
    ["gcloud", "auth", "print-access-token", "--account=mappi9118@gmail.com"], capture_output=True, text=True
)
token = result.stdout.strip()
print(f"Token obtained: {token[:20]}..." if token else f"Error: {result.stderr}")

if not token:
    exit(1)

headers = {"Authorization": f"Bearer {token}"}
PROJECT_ID = "ses-work-automation"
CLIENT_ID = "74735301292-op9eiut55pjdkhb44p25c6hlokcf01ql.apps.googleusercontent.com"
CLIENT_NUM = "74735301292"

# Google Auth Platform API (v1) でOAuthクライアント情報取得
endpoints = [
    f"https://oauth2.googleapis.com/tokeninfo?access_token={token}",
    "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getProjectConfig?key=AIzaSy",
]

# Cloud Resource Manager でプロジェクト確認
r = requests.get(f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}", headers=headers)
print(f"Project API: {r.status_code}")

# Google API Discovery
r2 = requests.get(f"https://clientauthconfig.googleapis.com/v1/projects/{PROJECT_ID}/oauthClients", headers=headers)
print(f"OAuthClients API: {r2.status_code} {r2.text[:400]}")

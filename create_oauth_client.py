import google.auth.transport.requests
import requests
from google.oauth2 import service_account

SA_FILE = "config/service_account.json"
creds = service_account.Credentials.from_service_account_file(
    SA_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
creds.refresh(google.auth.transport.requests.Request())
token = creds.token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
PROJECT_ID = "ses-work-automation"
PROJECT_NUM = "74735301292"

# Google Auth Platform API v1 でDesktopクライアント新規作成
# これでclient_secretごと返ってくる
url = f"https://oauth2.googleapis.com/v1alpha/projects/{PROJECT_NUM}/oauthClients"
body = {"displayName": "SES Drive Uploader", "clientType": "DESKTOP_APP"}
r = requests.post(url, headers=headers, json=body)
print(f"Status: {r.status_code}")
print(r.text[:500])

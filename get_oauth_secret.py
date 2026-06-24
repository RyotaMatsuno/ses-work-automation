import json

import google.auth.transport.requests
import requests
from google.oauth2 import service_account

SA_FILE = "config/service_account.json"
with open(SA_FILE) as f:
    sa = json.load(f)

PROJECT_ID = sa["project_id"]

# cloud-platform スコープでSAトークン取得
creds = service_account.Credentials.from_service_account_file(
    SA_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
req = google.auth.transport.requests.Request()
creds.refresh(req)
token = creds.token
headers = {"Authorization": f"Bearer {token}"}

# OAuth2 client list API
url = f"https://clientauthconfig.googleapis.com/v1/projects/{PROJECT_ID}/brands"
r = requests.get(url, headers=headers)
print(f"brands: {r.status_code} {r.text[:300]}")

# IAP API
url2 = f"https://iap.googleapis.com/v1/projects/{PROJECT_ID}/brands"
r2 = requests.get(url2, headers=headers)
print(f"IAP brands: {r2.status_code} {r2.text[:300]}")

"""
GCP Identity and Access Management API を使ってOAuthクライアントのsecretを取得。
サービスアカウントでGCP Cloud Resource Manager APIを叩く。
"""

import json

import requests
from google.oauth2 import service_account

SA_FILE = "config/service_account.json"
with open(SA_FILE) as f:
    sa = json.load(f)

PROJECT_ID = sa["project_id"]
CLIENT_ID_FULL = "74735301292-op9eiut55pjdkhb44p25c6hlokcf01ql.apps.googleusercontent.com"
CLIENT_NUM_ID = CLIENT_ID_FULL.split("-")[0]  # 74735301292

# サービスアカウントでGCP APIトークン取得
creds = service_account.Credentials.from_service_account_file(
    SA_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
creds.refresh(requests.Request())

# IAM credentials API でOAuthクライアント情報取得を試みる
# ※ このAPIはOAuth clientのsecretを返さないが試す
headers = {"Authorization": f"Bearer {creds.token}"}

# Cloud Resource Manager API
url = f"https://iam.googleapis.com/v1/projects/{PROJECT_ID}/serviceAccounts"
resp = requests.get(url, headers=headers)
print(f"IAM API: {resp.status_code}")

# Identity Platform API
url2 = f"https://identitytoolkit.googleapis.com/v2/projects/{PROJECT_ID}/oauthIdpConfigs"
resp2 = requests.get(url2, headers=headers)
print(f"Identity API: {resp2.status_code} {resp2.text[:200]}")

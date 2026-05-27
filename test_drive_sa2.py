
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SA_FILE = "config/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
service = build("drive", "v3", credentials=creds)

# ルートフォルダ一覧取得テスト
result = service.files().list(pageSize=5, fields="files(id, name)").execute()
files = result.get("files", [])
print("Drive API OK. Files visible:", len(files))
for f in files:
    print(f"  {f['id']} - {f['name']}")

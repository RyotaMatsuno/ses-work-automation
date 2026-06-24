import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
import tempfile

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_FILE = "config/drive_token.json"


def get_drive_service():
    with open(TOKEN_FILE, encoding="utf-8") as f:
        td = json.load(f)
    creds = Credentials(
        token=td.get("access_token"),
        refresh_token=td.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=td["client_id"],
        client_secret=td["client_secret"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        td["access_token"] = creds.token
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(td, f, indent=2, ensure_ascii=False)
    return build("drive", "v3", credentials=creds)


service = get_drive_service()

# テストファイル作成
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
    tmp.write("Jobz Drive test")
    tmp_path = tmp.name

result = (
    service.files()
    .create(
        body={"name": "jobz_test.txt"},
        media_body=MediaFileUpload(tmp_path, mimetype="text/plain"),
        fields="id,name,webViewLink",
    )
    .execute()
)

# 共有設定
service.permissions().create(fileId=result["id"], body={"type": "anyone", "role": "reader"}).execute()

print(f"アップロード成功: {result['name']}", flush=True)
print(f"URL: {result['webViewLink']}", flush=True)

# テスト後削除
service.files().delete(fileId=result["id"]).execute()
os.unlink(tmp_path)
print("テストファイル削除完了", flush=True)
print("Drive API OK", flush=True)

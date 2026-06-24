import sys

sys.stdout.reconfigure(encoding="utf-8")
import os
import tempfile

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SA_FILE = "google_credentials.json"

try:
    creds = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
    service = build("drive", "v3", credentials=creds)

    # テストファイルを作成してアップロード
    test_content = "Drive upload test from Jobz"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(test_content)
        tmp_path = tmp.name

    file_metadata = {"name": "jobz_test.txt"}
    media = MediaFileUpload(tmp_path, mimetype="text/plain")
    result = service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink").execute()

    # 共有設定
    service.permissions().create(fileId=result["id"], body={"type": "anyone", "role": "reader"}).execute()

    print(f"アップロード成功: {result.get('name')}", flush=True)
    print(f"URL: {result.get('webViewLink')}", flush=True)

    # テストファイル削除
    service.files().delete(fileId=result["id"]).execute()
    os.unlink(tmp_path)
    print("テストファイル削除完了", flush=True)
    print("Drive API認証 OK", flush=True)

except Exception as e:
    print(f"エラー: {e}", flush=True)

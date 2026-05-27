
from google.oauth2 import service_account
from googleapiclient.discovery import build

SA_FILE = "config/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
service = build("drive", "v3", credentials=creds)

# SES添付ファイル用フォルダ作成
folder_meta = {
    "name": "SES_attachments",
    "mimeType": "application/vnd.google-apps.folder"
}
folder = service.files().create(body=folder_meta, fields="id, name, webViewLink").execute()
folder_id = folder["id"]
print(f"Folder created: {folder['name']}")
print(f"Folder ID: {folder_id}")
print(f"Link: {folder.get('webViewLink','')}")

# 誰でも閲覧可能にする（リンク共有）
permission = {
    "type": "anyone",
    "role": "reader"
}
service.permissions().create(fileId=folder_id, body=permission).execute()
print("Public read permission set.")

# folder_idを.envに追記するためIDを出力
print(f"\nDRIVE_FOLDER_ID={folder_id}")

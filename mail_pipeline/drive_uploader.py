
"""
drive_uploader.py - Google Drive attachment uploader for SES mail pipeline
Uses OAuth2 refresh token stored in config/drive_token.json
"""

def upload_to_drive(filename: str, data_bytes: bytes, mime_type: str) -> str | None:
    try:
        import io
        from pathlib import Path
        from dotenv import dotenv_values
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import json

        base_dir = Path(__file__).parent.parent
        token_path = base_dir / "config" / "drive_token.json"
        env = dotenv_values(str(base_dir / "config" / ".env"))
        folder_id = env.get("DRIVE_FOLDER_ID")

        if not token_path.exists():
            print("[Drive] drive_token.json not found")
            return None
        if not folder_id:
            print("[Drive] DRIVE_FOLDER_ID not set")
            return None

        with open(token_path) as f:
            td = json.load(f)

        creds = Credentials(
            token=td.get("token"),
            refresh_token=td["refresh_token"],
            token_uri=td["token_uri"],
            client_id=td["client_id"],
            client_secret=td["client_secret"],
            scopes=td["scopes"],
        )

        # トークンが切れていれば自動リフレッシュ
        if not creds.valid:
            creds.refresh(Request())
            td["token"] = creds.token
            with open(token_path, "w") as f:
                json.dump(td, f, indent=2)

        service = build("drive", "v3", credentials=creds)
        file_meta = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype=mime_type, resumable=False)
        uploaded = service.files().create(
            body=file_meta, media_body=media, fields="id,webViewLink"
        ).execute()

        file_id = uploaded.get("id")
        service.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}
        ).execute()

        link = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
        print(f"[Drive] uploaded: {filename} -> {link}")
        return link

    except Exception as e:
        print(f"[Drive] upload failed: {e}")
        return None


if __name__ == "__main__":
    test_data = b"SES Drive uploader smoke test - OK 2026-05-27"
    result = upload_to_drive("ses_uploader_test.txt", test_data, "text/plain")
    if result:
        print(f"Smoke test PASSED: {result}")
    else:
        print("Smoke test FAILED")

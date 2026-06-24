# -*- coding: utf-8 -*-
"""
Google Drive uploader for SES Pipeline.
"""

import json
import mimetypes
import os
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(__file__).parent
TOKEN_PATH = BASE_DIR / "config" / "drive_token.json"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SPREADSHEET_URL_RE = re.compile(r"https://docs\.google\.com/spreadsheets/[^\s<>\"]+")


def extract_spreadsheet_url(text: str) -> str | None:
    match = SPREADSHEET_URL_RE.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip("。、,)")


def _load_token() -> dict:
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_token(token_data: dict) -> None:
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)


def _build_credentials(token_data: dict) -> Credentials:
    access_token = token_data.get("access_token") or token_data.get("token")
    return Credentials(
        token=access_token,
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri") or TOKEN_URI,
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes") or ["https://www.googleapis.com/auth/drive.file"],
    )


def upload_to_drive(file_path: str) -> str:
    if os.environ.get("DRY_RUN") == "1":
        dummy = f"https://drive.google.com/file/d/dry-run-{Path(file_path).name}/view"
        print(f"[DRY_RUN] Drive upload skipped: {file_path} -> {dummy}", flush=True)
        return dummy

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    token_data = _load_token()
    creds = _build_credentials(token_data)
    if not creds.valid:
        creds.refresh(Request())
        token_data["access_token"] = creds.token
        token_data["token"] = creds.token
        _save_token(token_data)

    service = build("drive", "v3", credentials=creds)
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=False)
    uploaded = (
        service.files()
        .create(
            body={"name": path.name},
            media_body=media,
            fields="id,webViewLink",
        )
        .execute()
    )

    file_id = uploaded["id"]
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    return uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"


if __name__ == "__main__":
    test_path = BASE_DIR / "drive_uploader_test.txt"
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("SES Pipeline Drive uploader test\n")
    print(upload_to_drive(str(test_path)), flush=True)

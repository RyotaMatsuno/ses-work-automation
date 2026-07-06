# -*- coding: utf-8 -*-
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
token_path = os.path.join(base, "sheets", "token_sheets.json")
SS_ID = "1xSmLwXiDrCVPztSnwhEU1SSBpKOInV5Dx63Zg_mKyR4"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_authorized_user_file(token_path, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
svc = build("sheets", "v4", credentials=creds)

titles = [
    "経常利益（実利率）",
    "経常利益（最終版）",
    "利率内訳",
    "赤字回収",
    "事務ボーナス",
]
for title in titles:
    try:
        r = svc.spreadsheets().values().get(
            spreadsheetId=SS_ID, range=f"'{title}'!A1:Z120"
        ).execute()
        vals = r.get("values", [])
        print("=" * 60, title, len(vals), "rows")
        for row in vals:
            print(" | ".join(str(c) for c in row))
    except Exception as e:
        print("ERR", title, e)

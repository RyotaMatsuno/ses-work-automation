"""
OAuth token でY.Sタブを持つスプレッドシートを探す
"""

import json

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

TOKEN_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sheets\token_sheets.json"

with open(TOKEN_PATH) as f:
    token_data = json.load(f)

creds = Credentials(
    token=token_data.get("token"),
    refresh_token=token_data.get("refresh_token"),
    token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
    client_id=token_data.get("client_id"),
    client_secret=token_data.get("client_secret"),
    scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/spreadsheets"]),
)

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

gc = gspread.authorize(creds)

print("スプレッドシートを検索中...")
files = gc.list_spreadsheet_files()
print(f"合計 {len(files)} 件")
for f in files:
    print(f"  ID: {f['id']}  名前: {f['name']}")

print("\n--- Y.S タブを検索 ---")
for f in files:
    try:
        ss = gc.open_by_key(f["id"])
        sheets = [ws.title for ws in ss.worksheets()]
        if any("Y.S" in s or "YS" in s or "吉田" in s for s in sheets):
            print(f"★ HIT: {f['name']} (ID: {f['id']})")
            print(f"   タブ: {sheets}")
    except Exception as e:
        print(f"  スキップ: {f['name']} - {e}")

"""
Y.Sタブを持つスプレッドシートを探す
"""

import gspread
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)

print("アクセス可能なスプレッドシートを検索中...")
files = gc.list_spreadsheet_files()
print(f"合計 {len(files)} 件のスプレッドシートが見つかりました")
for f in files:
    print(f"  ID: {f['id']}  名前: {f['name']}")

print("\n--- Y.Sタブを検索中 ---")
for f in files:
    try:
        ss = gc.open_by_key(f["id"])
        sheets = [ws.title for ws in ss.worksheets()]
        if any("Y.S" in s or "YS" in s for s in sheets):
            print(f"★ HIT: {f['name']} (ID: {f['id']})")
            print(f"   タブ: {sheets}")
    except Exception as e:
        print(f"  スキップ: {f['name']} - {e}")

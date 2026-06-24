# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import gspread
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

ws_ft = ss.worksheet("フラップテック")
data = ws_ft.get_all_values()

print("=== FTシート 全行（氏名列） ===", flush=True)
for i, row in enumerate(data, start=1):
    if len(row) > 2 and row[2]:
        print(f"  行{i}: {row[2]}", flush=True)

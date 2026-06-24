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

ws = ss.worksheet("TERRA")
data = ws.get_all_values()

# 氏名列(D=index3)で行番号マップ作成
name_to_row = {}
for i, row in enumerate(data, start=1):
    if len(row) > 3 and row[3]:
        name_to_row[row[3]] = i

print("名前マップ（関連分）:", flush=True)
for name in ["鶴川慶三", "齋藤よしまさ", "佐々木", "吉田祥平", "森"]:
    print(f"  {name}: 行{name_to_row.get(name, 'NOT FOUND')}", flush=True)

# ヘッダー行確認
print("\nヘッダー行(4行目):", data[3][:19], flush=True)

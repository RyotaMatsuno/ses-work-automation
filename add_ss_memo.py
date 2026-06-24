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

# 備考・メモシートに追記
ws_memo = ss.worksheet("備考・メモ")
data = ws_memo.get_all_values()
last_row = len(data) + 2

ws_memo.update(
    f"A{last_row}",
    [
        ["■ 契約マスター運用ルール（2026-06-01確定）"],
        ["契約マスターはGoogleスプレッドシートのみで管理する。ローカルExcel（契約マスター_v6.xlsx）は使用しない。"],
        [
            "スプレッドシートURL: https://docs.google.com/spreadsheets/d/1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI/edit"
        ],
        ["新規成約・退場・単価変更など全ての更新はスプレッドシートに直接行う。"],
    ],
)

print(f"[OK] 備考・メモシートに運用ルール追記（行{last_row}〜）", flush=True)

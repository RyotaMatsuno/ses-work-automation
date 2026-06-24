# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import json

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

TOKEN_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sheets\token_sheets.json"
with open(TOKEN_PATH) as f:
    td = json.load(f)
creds = Credentials(
    token=td.get("token"),
    refresh_token=td.get("refresh_token"),
    token_uri=td.get("token_uri", "https://oauth2.googleapis.com/token"),
    client_id=td.get("client_id"),
    client_secret=td.get("client_secret"),
    scopes=td.get("scopes", ["https://www.googleapis.com/auth/spreadsheets"]),
)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
gc = gspread.authorize(creds)

print("=== 所有スプレッドシート一覧 ===", flush=True)
files = gc.list_spreadsheet_files()
print(f"合計 {len(files)} 件", flush=True)
for f in files:
    print(f"  {f['id']}  |  {f['name']}", flush=True)

ORIG = "1nSbYDRA9nzezksBDZacTpR4udEIhWOtixcwD7jTXLFk"
FMT = "1TyKVdrwzUdURam5v9HG4A_RhyKJUhDmX"  # handoffより(33字・要検証)


def dump(label, key):
    print(f"\n=== {label}: {key} ===", flush=True)
    try:
        ss = gc.open_by_key(key)
        print(f"  タイトル: {ss.title}", flush=True)
        print(f"  タブ: {[ws.title for ws in ss.worksheets()]}", flush=True)
    except Exception as e:
        print(f"  [OPEN失敗] {e}", flush=True)


dump("元スキルシート", ORIG)
dump("フォーマット(handoff値)", FMT)
print("\n[DONE]", flush=True)
